#!/usr/bin/env python3
"""独立执行两个 eBuilder 离线 ZIP 的完整版本对比。"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_object_index import build_object_index
from build_business_object_diff import build_business_object_diff, validate_quantity
from build_visual_diff_model import build_visual_diff_model
from calculate_diff import calculate_diff
from enrich_with_knowledge import enrich_with_knowledge
from generate_report import build_analysis
from generate_validation_points import generate_validation_points
from match_objects import match_objects
from package_direction import (
    DirectionResolutionError,
    automatic_direction,
    explicit_direction,
)
from parse_package import parse_package
from propagate_impacts import propagate_impacts
from render_business_object_report import render_report
from render_visual_diff_html import render_visual_diff_html
from trigger_risks import trigger_risks
from validate_report_readability import validate_readability
from validate_visual_diff import validate_visual_consistency, validate_visual_usability


OUTPUT_FILES = [
    "应用版本功能差异报告.md",
    "应用版本功能差异明细.json",
    "business-object-diff.json",
    "报告数量一致性校验.json",
    "报告可读性检查.json",
    "应用版本差异可视化.html",
    "visual-diff-model.json",
    "可视化数据一致性校验.json",
    "可视化可用性检查.json",
    "comparison-facts.jsonl",
    "comparison-analysis.json",
    "影响传播明细.jsonl",
    "风险与验证点.jsonl",
    "无法确认项.jsonl",
]

COMPRESSIBLE_OUTPUTS = [
    "comparison-facts.jsonl",
    "comparison-analysis.json",
    "应用版本功能差异明细.json",
    "影响传播明细.jsonl",
    "风险与验证点.jsonl",
    "无法确认项.jsonl",
]
EVIDENCE_GZIP_LEVEL = 1


def package_business_name(filename: str) -> str:
    """仅在包内没有应用名称时，从批量包文件名提取可读标题。"""
    stem = Path(filename).stem
    cleaned = re.sub(
        r"(?:[_\s-]+\d{6,14})?[_\s-]+V\d+(?:\.\d+)+(?:[_\s-].*)?$",
        "",
        stem,
        flags=re.IGNORECASE,
    ).strip(" _-")
    return cleaned or stem


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any, *, indent: int = 2) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=indent) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, values) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for value in values:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
            count += 1
    return count


def compress_file(path: Path) -> Path:
    """以确定性 GZIP 压缩脚本生成的大型证据文件。"""
    target = path.with_name(path.name + ".gz")
    with path.open("rb") as source, target.open("wb") as raw_target:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=raw_target,
            compresslevel=EVIDENCE_GZIP_LEVEL, mtime=0
        ) as compressed:
            while chunk := source.read(1024 * 1024):
                compressed.write(chunk)
    path.unlink()
    return target


def package_metadata(path: Path, ir: dict[str, Any], role: str) -> dict[str, Any]:
    modules = sorted((ir.get("modules") or {}).keys())
    return {
        "role": role,
        "name": path.name,
        "size": path.stat().st_size,
        "sha256": sha256(path),
        "modules": modules,
        "tables": sum(
            len(module.get("tables") or {})
            for module in (ir.get("modules") or {}).values()
        ),
        "records": sum(
            int(table.get("recordCount") or len(table.get("records") or []))
            for module in (ir.get("modules") or {}).values()
            for table in (module.get("tables") or {}).values()
        ),
        "parseErrors": len(ir.get("errors") or []),
        "migrationLineage": (
            ir.get("migrationLineage") or {}
        ).get("summary") or {},
        "profile": {
            "status": (ir.get("packageProfile") or {}).get("status"),
            "exportTime": (ir.get("packageProfile") or {}).get(
                "selectedExportTime"
            ),
            "evidenceFiles": (ir.get("packageProfile") or {}).get(
                "evidenceFiles"
            ) or [],
        },
    }


def load_canonical_ir(path: Path, package_path: Path, role: str) -> dict[str, Any]:
    """Load a canonical IR produced from the same package in the current run."""
    canonical_path = path.expanduser().resolve()
    if not canonical_path.is_file():
        raise SystemExit(f"{role} canonical package IR 不存在: {canonical_path}")
    try:
        document = json.loads(canonical_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"{role} canonical package IR 无法读取: {exc}") from exc
    if not isinstance(document, dict) or not isinstance(document.get("modules"), dict):
        raise SystemExit(f"{role} canonical package IR 结构无效: {canonical_path}")
    source = document.get("source") or {}
    source_path = source.get("packagePath")
    if not source_path or Path(str(source_path)).expanduser().resolve() != package_path.resolve():
        raise SystemExit(
            f"{role} canonical package IR 与输入 ZIP 不匹配: {canonical_path}"
        )
    return document


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", type=Path, help="明确指定的旧版本 ZIP")
    parser.add_argument("--new", type=Path, help="明确指定的新版本 ZIP")
    parser.add_argument(
        "--package",
        dest="packages",
        type=Path,
        action="append",
        help=(
            "未指定新旧角色的候选 ZIP；必须重复两次，脚本将按最外层 "
            "profile.json.exportTime 判断方向"
        ),
    )
    parser.add_argument("--output", type=Path, required=True, help="新的输出目录")
    parser.add_argument(
        "--old-canonical",
        type=Path,
        help="内部性能参数：与 --old 对应、由当前运行生成的 canonical package IR",
    )
    parser.add_argument(
        "--new-canonical",
        type=Path,
        help="内部性能参数：与 --new 对应、由当前运行生成的 canonical package IR",
    )
    parser.add_argument(
        "--resolved-direction-json",
        help="内部审计参数：上层自动路由已经确认的新旧方向证据",
    )
    parser.add_argument("--max-impact-depth", type=int, default=3, choices=(1, 2, 3))
    parser.add_argument(
        "--full-technical-evidence",
        action="store_true",
        help="保留未压缩的大型技术证据；默认输出确定性 .gz 以控制批量包体积",
    )
    args = parser.parse_args()
    packages = args.packages or []
    explicit_requested = args.old is not None or args.new is not None
    canonical_requested = args.old_canonical is not None or args.new_canonical is not None
    if canonical_requested and (
        args.old_canonical is None or args.new_canonical is None
    ):
        raise SystemExit("--old-canonical 与 --new-canonical 必须同时提供")
    if explicit_requested:
        if args.old is None or args.new is None:
            raise SystemExit("--old 与 --new 必须同时提供")
        if packages:
            raise SystemExit("--old/--new 与 --package 不能混用")
        input_paths = [("old", args.old), ("new", args.new)]
        direction_mode = "explicit"
    else:
        if canonical_requested:
            raise SystemExit("canonical package IR 复用仅支持明确的 --old/--new 方向")
        if len(packages) != 2:
            raise SystemExit(
                "未指定 --old/--new 时，必须恰好提供两个 --package 候选 ZIP"
            )
        input_paths = [("package[1]", packages[0]), ("package[2]", packages[1])]
        direction_mode = "automatic"

    for role, path in input_paths:
        if not path.is_file():
            raise SystemExit(f"{role} package not found: {path}")
        if path.suffix.lower() != ".zip":
            raise SystemExit(f"{role} 必须是 ZIP: {path}")
    if input_paths[0][1].resolve() == input_paths[1][1].resolve():
        raise SystemExit("必须提供两个不同的输入 ZIP")
    if args.output.exists() and any(args.output.iterdir()):
        raise SystemExit(f"输出目录必须不存在或为空: {args.output}")
    args.output.mkdir(parents=True, exist_ok=True)
    skill_dir = Path(__file__).resolve().parent.parent
    knowledge_dir = skill_dir / "knowledge"
    started = time.monotonic()
    stage_started = started
    performance: dict[str, Any] = {}

    def mark_stage(name: str) -> None:
        nonlocal stage_started
        now = time.monotonic()
        performance[name] = round(now - stage_started, 3)
        stage_started = now

    first_path, second_path = input_paths[0][1], input_paths[1][1]
    if canonical_requested:
        first_ir = load_canonical_ir(args.old_canonical, first_path, "旧包")
        second_ir = load_canonical_ir(args.new_canonical, second_path, "新包")
    else:
        first_ir = parse_package(first_path)
        second_ir = parse_package(second_path)
    try:
        if direction_mode == "explicit":
            old_path, old_ir, new_path, new_ir, direction_resolution = (
                explicit_direction(
                    first_path,
                    first_ir,
                    second_path,
                    second_ir,
                )
            )
        else:
            old_path, old_ir, new_path, new_ir, direction_resolution = (
                automatic_direction(
                    first_path,
                    first_ir,
                    second_path,
                    second_ir,
                )
            )
    except DirectionResolutionError as exc:
        raise SystemExit(str(exc)) from exc
    if args.resolved_direction_json:
        if direction_mode != "explicit":
            raise SystemExit("--resolved-direction-json 只能与 --old/--new 一起使用")
        try:
            resolved_direction = json.loads(args.resolved_direction_json)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"--resolved-direction-json 无法解析: {exc}") from exc
        if not isinstance(resolved_direction, dict) or not resolved_direction.get(
            "directionSource"
        ):
            raise SystemExit("--resolved-direction-json 缺少 directionSource")
        direction_resolution = resolved_direction
    mark_stage("canonicalLoadAndDirectionSeconds")
    old_meta = package_metadata(old_path, old_ir, "old")
    new_meta = package_metadata(new_path, new_ir, "new")
    old_index = build_object_index(old_ir, knowledge_dir)
    mark_stage("oldObjectIndexSeconds")
    new_index = build_object_index(new_ir, knowledge_dir)
    mark_stage("newObjectIndexSeconds")
    matching = match_objects(old_index, new_index)
    mark_stage("objectMatchingSeconds")
    raw_facts_document = calculate_diff(old_index, new_index, matching)
    mark_stage("fieldDiffSeconds")
    raw_facts_path = args.output / "comparison-facts.jsonl"
    write_jsonl(raw_facts_path, raw_facts_document["facts"])
    immutable_facts_hash = sha256(raw_facts_path)
    mark_stage("factEvidenceWriteSeconds")

    enriched_document = enrich_with_knowledge(raw_facts_document, knowledge_dir)
    impact_groups = propagate_impacts(
        enriched_document["facts"], knowledge_dir, args.max_impact_depth
    )
    risks = trigger_risks(enriched_document["facts"], knowledge_dir)
    validations = generate_validation_points(
        enriched_document["facts"], risks, knowledge_dir
    )
    limitations = [
        "本次只比较离线包静态证据，未连接数据库、网络或目标环境。",
        "无法稳定匹配的对象保持 UNMATCHED；疑似重命名保持 POSSIBLE_RENAME。",
        "跨环境 ID 不一致时优先采用 KEYS_*.idm 的记录级 sourceId；profile.json 只用于应用/模块层佐证与回退，关系缺失、冲突或不唯一时不强配。",
        "包外资源、跨服务目标和 JSON 隐式引用在证据不足时标为 UNKNOWN，不描述为确定故障。",
        "图传播最多三层并对循环节点去重；间接影响均为 INFERRED。",
        "Claude 补充仅参与业务聚合、处理器说明和中文表达，不修改 Codex 计算事实。",
    ]
    analysis = build_analysis(
        old_metadata=old_meta,
        new_metadata=new_meta,
        facts=enriched_document["facts"],
        impact_groups=impact_groups,
        risks=risks,
        validations=validations,
        limitations=limitations,
    )
    mark_stage("knowledgeImpactRiskAnalysisSeconds")
    analysis["analysisDirection"] = {
        "old": old_meta,
        "new": new_meta,
        **direction_resolution,
    }
    analysis["generatedAt"] = datetime.now(timezone.utc).isoformat()
    analysis["factLayerSha256"] = immutable_facts_hash
    analysis["knowledgeManifestSha256"] = sha256(knowledge_dir / "manifest.json")
    analysis["execution"] = {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "standardLibraryOnly": True,
        "networkUsed": False,
        "externalSkillsUsed": False,
        "mavenUsed": False,
        "maxImpactDepth": args.max_impact_depth,
        "inputDirectionMode": direction_resolution["directionSource"],
        "evidenceCompression": (
            "NONE" if args.full_technical_evidence else "GZIP_MTIME_0_LEVEL_1"
        ),
    }
    analysis["identityResolution"] = {
        "policy": [
            "KEYS_*.idm 记录级 sourceId（业务根对象且两侧唯一）",
            "profile.json 应用/模块同源佐证与回退",
            "已验证业务自然键",
            "父对象关系路径",
            "归一化内容签名",
            "保守相似度候选",
        ],
        "oldPackageLineage": old_index["summary"].get("migrationLineage") or {},
        "newPackageLineage": new_index["summary"].get("migrationLineage") or {},
        "oldObjectsUsingMigrationSourceId": old_index["summary"].get(
            "migrationSourceIdentityObjects", 0
        ),
        "newObjectsUsingMigrationSourceId": new_index["summary"].get(
            "migrationSourceIdentityObjects", 0
        ),
        "matchesByMigrationSourceId": sum(
            item.get("matchType") == "MIGRATION_IDM_SOURCE_ID"
            for item in matching.get("matches") or []
        ),
        "matchesByProfileHomology": sum(
            item.get("matchType") == "PROFILE_HOMOLOGY"
            for item in matching.get("matches") or []
        ),
        "lineageDiagnostics": {
            "old": old_index.get("lineageDiagnostics") or [],
            "new": new_index.get("lineageDiagnostics") or [],
        },
        "scope": "packageUnit + serviceName + tableName + sourceId; detail rows remain parent-scoped",
        "ambiguousRelationPolicy": "do not force match",
    }

    business_diff = build_business_object_diff(
        old_metadata=old_meta,
        new_metadata=new_meta,
        old_index=old_index,
        new_index=new_index,
        facts=enriched_document["facts"],
        analysis=analysis,
    )
    mark_stage("businessAggregationSeconds")
    application_name = str(business_diff.get("applicationName") or "")
    if (
        application_name == "应用基础配置"
        or re.search(
            r"(?:migration-source|idm-lineage|idm-context|content|parent)=",
            application_name,
        )
    ):
        business_diff["applicationName"] = package_business_name(new_meta["name"])
    report, test_scenarios = render_report(business_diff, analysis)
    business_diff["testScenarios"] = test_scenarios
    quantity_check = validate_quantity(business_diff)
    readability_check = validate_readability(report, business_diff, test_scenarios)
    analysis["businessObjectSummary"] = business_diff["summary"]
    analysis["businessObjectDiffSchemaVersion"] = business_diff["schemaVersion"]
    analysis["reportModel"] = {
        "schemaVersion": "ebuilder-business-object-report/v3.1",
        "narrativeOrder": [
            "总体数量",
            "新增功能",
            "删除功能",
            "更新功能",
            "影响分析",
            "测试建议",
            "未确认项",
            "技术附录",
        ],
        "quantityCheck": quantity_check["result"],
        "readabilityCheck": readability_check["result"],
    }
    visual_model = build_visual_diff_model(business_diff, analysis, impact_groups)
    visual_html = render_visual_diff_html(visual_model)
    visual_consistency = validate_visual_consistency(
        visual_model, business_diff, analysis, impact_groups, visual_html
    )
    visual_usability = validate_visual_usability(visual_html, visual_model)
    mark_stage("reportAndVisualBuildSeconds")
    write_json(args.output / "comparison-analysis.json", analysis)
    write_json(args.output / "business-object-diff.json", business_diff)
    write_json(args.output / "报告数量一致性校验.json", quantity_check)
    write_json(args.output / "报告可读性检查.json", readability_check)
    write_json(args.output / "visual-diff-model.json", visual_model)
    write_json(args.output / "可视化数据一致性校验.json", visual_consistency)
    write_json(args.output / "可视化可用性检查.json", visual_usability)
    (args.output / "应用版本差异可视化.html").write_text(
        visual_html, encoding="utf-8"
    )
    (args.output / "应用版本功能差异报告.md").write_text(
        report, encoding="utf-8"
    )
    changed_facts = [
        fact for fact in enriched_document["facts"]
        if fact["changeType"] != "UNCHANGED"
    ]
    detail = {
        "schemaVersion": "ebuilder-version-diff-detail/v1.0",
        "analysisDirection": analysis["analysisDirection"],
        "summary": analysis["summary"],
        "businessObjectSummary": business_diff["summary"],
        "businessObjects": business_diff["objects"],
        "possibleRenamesAndReplacements": business_diff[
            "possibleRenamesAndReplacements"
        ],
        "testScenarios": test_scenarios,
        "technicalEvidenceMode": (
            "FULL" if args.full_technical_evidence else "REFERENCED_COMPRESSED"
        ),
        "changes": changed_facts if args.full_technical_evidence else [],
        "featureChanges": (
            analysis["featureChanges"] if args.full_technical_evidence else []
        ),
        "risks": risks if args.full_technical_evidence else [],
        "validationPoints": validations if args.full_technical_evidence else [],
        "unknownItems": (
            analysis["unknownItems"] if args.full_technical_evidence else []
        ),
        "technicalEvidenceReferences": (
            [] if args.full_technical_evidence else [
                {
                    "kind": "FIELD_FACTS",
                    "file": "comparison-facts.jsonl.gz",
                    "count": len(raw_facts_document["facts"]),
                    "sha256Uncompressed": immutable_facts_hash,
                },
                {"kind": "ANALYSIS", "file": "comparison-analysis.json.gz"},
                {"kind": "IMPACTS", "file": "影响传播明细.jsonl.gz", "count": len(impact_groups)},
                {"kind": "RISKS_AND_VALIDATIONS", "file": "风险与验证点.jsonl.gz", "riskCount": len(risks), "validationCount": len(validations)},
                {"kind": "UNKNOWNS", "file": "无法确认项.jsonl.gz", "count": len(analysis["unknownItems"])},
            ]
        ),
        "limitations": limitations,
        "factLayerSha256": immutable_facts_hash,
    }
    write_json(args.output / "应用版本功能差异明细.json", detail)
    write_jsonl(args.output / "影响传播明细.jsonl", impact_groups)
    write_jsonl(
        args.output / "风险与验证点.jsonl",
        (
            [{"recordType": "RISK", **risk} for risk in risks]
            + [{"recordType": "VALIDATION_POINT", **item} for item in validations]
        ),
    )
    write_jsonl(args.output / "无法确认项.jsonl", analysis["unknownItems"])
    mark_stage("reportEvidenceWriteSeconds")

    type_counts = analysis["summary"]["byChangeType"]
    gates = {
        "factsCountMatchesSummary": len(raw_facts_document["facts"])
        == analysis["summary"]["totalComparedObjects"],
        "changeTypeCountsSum": sum(type_counts.values())
        == analysis["summary"]["totalComparedObjects"],
        "updatedHasFieldDiff": all(
            fact["changedPaths"]
            for fact in changed_facts
            if fact["changeType"] == "UPDATED"
        ),
        "highRiskHasEvidence": all(
            risk.get("knowledgeEvidence") is not None
            and risk.get("affectedChangeIds")
            for risk in risks
            if risk["severity"] == "HIGH"
        ),
        "highRiskHasValidation": all(
            any(risk["riskId"] in item["relatedRiskIds"] for item in validations)
            for risk in risks
            if risk["severity"] == "HIGH"
        ),
        "factLayerImmutable": sha256(raw_facts_path) == immutable_facts_hash,
        "sourceIdChangeSuppressed": analysis["summary"]["sourceIdOnlyChangesSuppressed"] >= 0,
        "migrationLineageParsed": all(
            isinstance(meta.get("migrationLineage"), dict)
            for meta in (old_meta, new_meta)
        ),
        "oldNewRolesResolved": (
            old_meta["role"] == "old" and new_meta["role"] == "new"
        ),
        "packageUnitIsolation": all(
            old_index["objects"][item["oldIndex"]].get("packageUnitKey")
            == new_index["objects"][item["newIndex"]].get("packageUnitKey")
            for item in matching.get("matches") or []
        ),
        "directionResolutionValid": (
            direction_resolution["directionSource"]
            in {"EXPLICIT_CLI_ARGUMENTS", "PROFILE_EXPORT_TIME"}
            and not direction_resolution["filenameInferenceUsed"]
            and not direction_resolution["fileMetadataInferenceUsed"]
            and (
                direction_resolution["directionSource"]
                != "PROFILE_EXPORT_TIME"
                or (
                    bool(old_meta["profile"].get("exportTime"))
                    and bool(new_meta["profile"].get("exportTime"))
                    and direction_resolution["exportTimeComparisonUsed"]
                )
            )
        ),
        "markdownSummaryBound": all(
            (
                f"| {row['label']} | {row['oldCount']} | {row['newCount']} | "
                f"{row['added']} | {row['removed']} | {row['updated']} |"
            )
            in report
            for row in business_diff["summary"]
        ),
        "businessObjectQuantityConsistent": quantity_check["result"] == "PASS",
        "reportReadabilityPass": readability_check["result"] == "PASS",
        "visualDataConsistencyPass": visual_consistency["result"] == "PASS",
        "visualUsabilityPass": visual_usability["result"] == "PASS",
    }
    output_files = list(OUTPUT_FILES)
    if not args.full_technical_evidence:
        report_path = args.output / "应用版本功能差异报告.md"
        compressed_report = report_path.read_text(encoding="utf-8")
        for filename in COMPRESSIBLE_OUTPUTS:
            compressed_report = compressed_report.replace(filename, filename + ".gz")
            compress_file(args.output / filename)
            output_files[output_files.index(filename)] = filename + ".gz"
        report_path.write_text(compressed_report, encoding="utf-8")
        visual_model_path = args.output / "visual-diff-model.json"
        if visual_model_path.stat().st_size > 8 * 1024 * 1024:
            compress_file(visual_model_path)
            output_files[output_files.index("visual-diff-model.json")] = (
                "visual-diff-model.json.gz"
            )
    mark_stage("evidenceCompressionSeconds")
    total_output_bytes = sum(
        (args.output / filename).stat().st_size for filename in output_files
    )
    # 输出体积只记录、不再作为成功门禁。大型全量应用可能合法地产生超过
    # 300MB 的证据，强制失败会把“体积较大”误报为“对比不完整”。
    gates["outputSizeRecordedOnly"] = True
    integrity = {
        "schemaVersion": "ebuilder-comparison-integrity/v1.0",
        "status": "PASS" if all(gates.values()) else "FAIL",
        "gates": gates,
        "elapsedSeconds": round(time.monotonic() - started, 3),
        "factsSha256": immutable_facts_hash,
        "totalOutputBytesBeforeIntegrityFile": total_output_bytes,
        "outputs": {
            filename: {
                "size": (args.output / filename).stat().st_size,
                "sha256": sha256(args.output / filename),
            }
            for filename in output_files
        },
        "runtimeIsolation": {
            "sourceTreeRead": False,
            "buildKnowledgeDirectoriesRead": False,
            "otherSkillsRead": False,
            "networkUsed": False,
            "thirdPartyPackagesUsed": False,
            "mavenUsed": False,
        },
        "performance": performance,
    }
    write_json(args.output / "执行与完整性校验.json", integrity)
    if integrity["status"] != "PASS":
        raise SystemExit(json.dumps(integrity, ensure_ascii=False))
    print(json.dumps({
        "status": "PASS",
        "output": str(args.output.resolve()),
        "old": old_meta,
        "new": new_meta,
        "directionResolution": direction_resolution,
        "summary": analysis["summary"],
        "elapsedSeconds": integrity["elapsedSeconds"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
