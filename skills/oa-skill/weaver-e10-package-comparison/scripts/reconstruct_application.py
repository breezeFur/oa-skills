#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from business_report_common import safe_file_name


SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PARSE = SKILL_DIR / "scripts" / "parse_package.py"


def run(command):
    subprocess.run([str(x) for x in command], check=True)


def require_nonempty(paths):
    missing = [str(path) for path in paths if not path.is_file() or path.stat().st_size == 0]
    if missing:
        raise RuntimeError(f"required outputs were not generated: {missing}")


def write_service_outputs(app_ir_path, output):
    data = json.loads(app_ir_path.read_text(encoding="utf-8"))
    knowledge_catalog_path = SKILL_DIR / "reconstruct-knowledge" / "service-analysis-catalog.json"
    knowledge_catalog = json.loads(knowledge_catalog_path.read_text(encoding="utf-8"))
    fragment_dir = output / "service-fragments"
    fragment_dir.mkdir(parents=True, exist_ok=True)
    for fragment in data.get("serviceFragments", []):
        safe_name = fragment["service"].replace("/", "_")
        (fragment_dir / f"{safe_name}.json").write_text(
            json.dumps(fragment, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    coverage = {
        "schemaVersion": "ebuilder-service-coverage/v1.0",
        "sourceApplicationIR": str(app_ir_path),
        "knowledgeCoverage": knowledge_catalog.get("counts", {}),
        "services": data.get("serviceInventory", []),
        "summary": {
            "packageServices": len(data.get("serviceInventory", [])),
            "fullSemantic": sum(x.get("analysisLevel") == "FULL_SEMANTIC" for x in data.get("serviceInventory", [])),
            "structural": sum(x.get("analysisLevel") == "STRUCTURAL" for x in data.get("serviceInventory", [])),
            "evidenceOnly": sum(x.get("analysisLevel") == "EVIDENCE_ONLY" for x in data.get("serviceInventory", [])),
            "businessObjects": len(data.get("businessObjects", [])),
            "externalResources": len(data.get("externalResources", [])),
            "semanticOwnerServices": len(data.get("semanticServiceCoverage", [])),
        },
    }
    coverage_path = output / "service-coverage.json"
    coverage_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# 应用服务解析覆盖报告",
        "",
        f"- 包内服务：{coverage['summary']['packageServices']}",
        f"- 专用语义解析：{coverage['summary']['fullSemantic']}",
        f"- 配置结构解析：{coverage['summary']['structural']}",
        f"- 仅保留证据：{coverage['summary']['evidenceOnly']}",
        f"- 识别业务对象：{coverage['summary']['businessObjects']}",
        f"- 外部资源引用：{coverage['summary']['externalResources']}",
        f"- 已识别专用语义归属服务：{coverage['summary']['semanticOwnerServices']}",
        "",
        "| 服务 | 解析级别 | 表数 | 记录数 | 能力 |",
        "|---|---:|---:|---:|---|",
    ]
    for item in coverage["services"]:
        lines.append(
            f"| {item['service']} | {item['analysisLevel']} | {item['packageTableCount']} | "
            f"{item['packageRecordCount']} | {item['capability']} |"
        )
    lines.extend([
        "",
        "说明：STRUCTURAL 表示已按迁出配置、表链和业务链形成结构化片段，但尚无该服务的专用语义解释器；EVIDENCE_ONLY 表示服务或表未进入当前配置知识，应保留证据并补充资料，不能猜测业务语义。",
    ])
    report_path = output / "应用服务解析覆盖报告.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return coverage_path, fragment_dir, report_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--parse-script", default=str(DEFAULT_PARSE))
    args = parser.parse_args()
    source = Path(args.input).resolve()
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    canonical = output / "canonical-package-ir.json"
    inventory = output / "module-inventory.json"
    app_ir = output / "application-ir.json"
    validation = output / "application-ir.validation.json"
    plan_json = output / "build-plan.json"
    plan_md = output / "build-plan.md"
    import_requirements = output / "import-required-inputs.json"
    business_report_dir = output / "应用业务报告"

    if source.suffix.lower() == ".zip":
        run([sys.executable, args.parse_script, source, "--output", canonical])
    else:
        canonical = source
        canonical_data = json.loads(canonical.read_text(encoding="utf-8"))
        import_requirements.write_text(
            json.dumps(
                canonical_data.get("indexes", {}).get(
                    "importRequirements",
                    {
                        "schemaVersion": "1.0",
                        "requiredInputs": [],
                        "optionalInputs": [],
                        "optionalMappings": [],
                        "policy": {},
                    },
                ),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    run([sys.executable, SKILL_DIR / "scripts" / "detect_modules.py", canonical, "--output", inventory])
    run([sys.executable, SKILL_DIR / "scripts" / "build_application_ir.py", canonical, "--output", app_ir])
    run([sys.executable, SKILL_DIR / "scripts" / "validate_application_ir.py", app_ir, "--report", validation])
    service_coverage, service_fragments, service_report = write_service_outputs(app_ir, output)
    run([
        sys.executable,
        SKILL_DIR / "scripts" / "generate_build_plan.py",
        app_ir,
        "--output",
        plan_json,
        "--report",
        plan_md,
    ])
    app_name = safe_file_name(
        json.loads(app_ir.read_text(encoding="utf-8")).get("application", {}).get("name")
    )
    business_outputs = {
        "overviewReport": business_report_dir / f"{app_name}_应用功能全景报告.md",
        "objectIndex": business_report_dir / f"{app_name}_应用对象索引.md",
        "dependencyRiskReport": business_report_dir / f"{app_name}_依赖与风险清单.md",
        "businessFunctionMap": business_report_dir / f"{app_name}_业务功能映射.json",
        "validation": business_report_dir / f"{app_name}_业务可读版报告校验.json",
    }
    run([
        sys.executable,
        SKILL_DIR / "scripts" / "generate_business_readable_report.py",
        app_ir,
        "--output-dir",
        business_report_dir,
        "--build-plan",
        plan_json,
        "--import-requirements",
        import_requirements,
    ])
    run([
        sys.executable,
        SKILL_DIR / "scripts" / "validate_business_readable_report.py",
        app_ir,
        business_outputs["businessFunctionMap"],
        "--overview",
        business_outputs["overviewReport"],
        "--object-index",
        business_outputs["objectIndex"],
        "--risk-report",
        business_outputs["dependencyRiskReport"],
        "--import-requirements",
        import_requirements,
        "--report",
        business_outputs["validation"],
    ])
    require_nonempty(business_outputs.values())
    result = {
        "status": "complete",
        "canonicalIR": str(canonical),
        "moduleInventory": str(inventory),
        "applicationIR": str(app_ir),
        "importRequirements": str(import_requirements),
        "validation": str(validation),
        "buildPlan": str(plan_json),
        "buildPlanReport": str(plan_md),
        "serviceCoverage": str(service_coverage),
        "serviceFragments": str(service_fragments),
        "serviceCoverageReport": str(service_report),
        "businessReadableOutputs": {
            key: str(path) for key, path in business_outputs.items()
        },
        "nextSkills": [
            "explain-ebuilder-form",
            "explain-ebuilder-app-page",
            "explain-esb-action-flow",
            "explain-ai-application",
            "explain-workflow-pathdef",
            "explain-edc-multi-filling",
            "explain-edc-report",
            "explain-cusapp-menu",
            "generate-ai-builder-prompt",
            "verify-generated-function",
        ],
    }
    (output / "reconstruction-manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
