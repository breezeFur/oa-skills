#!/usr/bin/env python3
"""V15.6 auto router with one-pass package parsing and canonical IR reuse."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from customer_text_guard import find_customer_text_leaks
from package_direction import (
    DirectionResolutionError,
    automatic_direction,
    explicit_direction,
)
from package_mode import PackageModeError, resolve_pair_mode
from workflow_compare import (
    build_workflow_ir,
    compare_workflow_irs,
    render_detail_report,
    render_html,
    render_report,
)


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
KNOWLEDGE = ROOT / "knowledge"
APP_DELIVERABLES = (
    "应用版本功能差异报告.md",
    "应用版本功能差异可视化.html",
    "应用版本功能明细差异报告.md",
)
WORKFLOW_DELIVERABLES = (
    "流程版本功能差异报告.md",
    "流程版本功能差异可视化.html",
    "流程版本功能明细差异报告.md",
)


def validate_zip(path: Path, role: str) -> Path:
    path = path.expanduser().resolve()
    if not path.is_file() or path.suffix.lower() != ".zip":
        raise SystemExit(f"{role}必须是存在的 ZIP：{path}")
    return path


def routing_ir(summary: dict) -> dict:
    return {
        "packageProfile": summary.get("packageProfile") or {},
        "modules": {
            "__routing__": {
                "tables": {
                    str(table): {} for table in (summary.get("routingTables") or [])
                }
            }
        },
    }


def parse_candidates_parallel(
    paths: tuple[Path, Path], staging: Path
) -> tuple[list[tuple[Path, dict, Path]], float]:
    started = time.monotonic()
    running = []
    for index, package_path in enumerate(paths, start=1):
        candidate_dir = staging / f"candidate-{index}"
        canonical = candidate_dir / "canonical-package-ir.json"
        candidate_dir.mkdir(parents=True, exist_ok=True)
        command = [
            sys.executable,
            str(SCRIPTS / "parse_package.py"),
            str(package_path),
            "--output",
            str(canonical),
            "--compact-output",
        ]
        process = subprocess.Popen(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        running.append((package_path, canonical, command, process))

    results: list[tuple[Path, dict, Path]] = []
    failures: list[str] = []
    for package_path, canonical, command, process in running:
        stdout, stderr = process.communicate()
        if process.returncode:
            failures.append(
                f"{package_path.name} 解析失败（{process.returncode}）：{stderr[-4000:]}"
            )
            continue
        try:
            summary = json.loads(stdout)
        except json.JSONDecodeError as exc:
            failures.append(f"{package_path.name} 解析摘要无效：{exc}")
            continue
        if not canonical.is_file() or canonical.stat().st_size == 0:
            failures.append(f"{package_path.name} 未生成 canonical package IR")
            continue
        results.append((package_path, routing_ir(summary), canonical))
    if failures:
        raise SystemExit("\n".join(failures))
    return results, round(time.monotonic() - started, 3)


def resolve_inputs(args: argparse.Namespace, staging: Path):
    if bool(args.old) != bool(args.new):
        raise SystemExit("--old 与 --new 必须同时提供")
    if args.old and args.new:
        first = validate_zip(args.old, "旧包")
        second = validate_zip(args.new, "新包")
        if first == second:
            raise SystemExit("必须提供两个不同的输入 ZIP")
    else:
        if len(args.packages or []) != 2:
            raise SystemExit("未指定 --old/--new 时，必须重复提供两个 --package")
        first = validate_zip(args.packages[0], "候选包 1")
        second = validate_zip(args.packages[1], "候选包 2")
        if first == second:
            raise SystemExit("必须提供两个不同的输入 ZIP")

    parsed, parse_seconds = parse_candidates_parallel((first, second), staging)
    first_path, first_ir, first_canonical = parsed[0]
    second_path, second_ir, second_canonical = parsed[1]
    if args.old and args.new:
        old_path, old_ir, new_path, new_ir, direction = explicit_direction(
            first_path, first_ir, second_path, second_ir
        )
    else:
        old_path, old_ir, new_path, new_ir, direction = automatic_direction(
            first_path, first_ir, second_path, second_ir
        )
    canonical_by_path = {
        first_path.resolve(): first_canonical,
        second_path.resolve(): second_canonical,
    }
    return (
        old_path,
        old_ir,
        canonical_by_path[old_path.resolve()],
        new_path,
        new_ir,
        canonical_by_path[new_path.resolve()],
        direction,
        parse_seconds,
    )


def write_manifest(output: Path, mode: str, deliverables: tuple[str, ...], **extra) -> dict:
    manifest = {
        "version": "V15.6",
        "status": "complete",
        "comparisonMode": mode,
        "deliverables": list(deliverables),
        **extra,
    }
    (output / "V13执行清单.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def run_application(
    args: argparse.Namespace,
    old_path: Path,
    old_canonical: Path,
    new_path: Path,
    new_canonical: Path,
    direction: dict,
    output: Path,
    parse_seconds: float,
) -> dict:
    old_target = output / "应用全景重建" / "旧版" / "canonical-package-ir.json"
    new_target = output / "应用全景重建" / "新版" / "canonical-package-ir.json"
    old_target.parent.mkdir(parents=True, exist_ok=True)
    new_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(old_canonical), old_target)
    shutil.move(str(new_canonical), new_target)
    command = [
        sys.executable,
        str(SCRIPTS / "run_v12_comparison.py"),
        "--old", str(old_path),
        "--new", str(new_path),
        "--old-canonical", str(old_target),
        "--new-canonical", str(new_target),
        "--resolved-direction-json", json.dumps(direction, ensure_ascii=False, separators=(",", ":")),
        "--output", str(output),
        "--max-impact-depth", str(args.max_impact_depth),
    ]
    if args.full_technical_evidence:
        command.append("--full-technical-evidence")
    completed = subprocess.run(command)
    if completed.returncode:
        raise SystemExit(completed.returncode)
    manifest_path = output / "V12执行清单.json"
    if not manifest_path.is_file():
        raise SystemExit(f"V12 应用引擎未生成执行清单：{manifest_path}")
    v12_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if v12_manifest.get("status") != "complete":
        raise SystemExit("V12 应用引擎未通过完整门禁")
    return write_manifest(
        output,
        "application",
        APP_DELIVERABLES,
        delegatedEngine="V12 application panorama comparison",
        oldPackage=str(old_path),
        newPackage=str(new_path),
        direction=direction,
        performance={
            "parallelPackageParseSeconds": parse_seconds,
            "packageFullParseCount": 2,
            "canonicalReuse": True,
            "v12": v12_manifest.get("performance") or {},
        },
    )


def validate_workflow_result(
    old_workflow_ir: dict,
    new_workflow_ir: dict,
    diff: dict,
    report: str,
    visual: str,
    detail: str,
) -> dict:
    old_coverage = old_workflow_ir["chainCoverage"]
    new_coverage = new_workflow_ir["chainCoverage"]
    leaks = {
        "report": find_customer_text_leaks(report),
        "visual": find_customer_text_leaks(visual, html=True),
        "detail": find_customer_text_leaks(detail),
    }
    names = [item["name"] for item in diff["changes"]]
    names_complete = all(
        name in report and name in visual and name in detail
        for name in names
    )
    no_external_dependency = not any(
        marker in visual.lower()
        for marker in ("http://", "https://", "fetch(", "xmlhttprequest", "src=\"//")
    )
    coverage_ledger_complete = bool(
        (diff.get("coverageLedger") or {}).get("complete")
        and not (diff.get("coverageLedger") or {}).get("unresolvedChangedTables")
    )
    list_coverage_honest = not (
        old_workflow_ir["summary"].get("listCoverage") == "NOT_PACKAGED"
        and new_workflow_ir["summary"].get("listCoverage") == "NOT_PACKAGED"
    ) or all("包内未提供" in content or "未携带列表" in content for content in (report, visual, detail))
    valid = bool(
        old_workflow_ir["summary"]["workflowCount"] > 0
        and new_workflow_ir["summary"]["workflowCount"] > 0
        and old_coverage["coreChainComplete"]
        and new_coverage["coreChainComplete"]
        and not any(leaks.values())
        and names_complete
        and no_external_dependency
        and coverage_ledger_complete
        and list_coverage_honest
    )
    return {
        "valid": valid,
        "coreWorkflowChainComplete": {
            "old": old_coverage["coreChainComplete"],
            "new": new_coverage["coreChainComplete"],
        },
        "chainCoverage": {"old": old_coverage, "new": new_coverage},
        "customerReportsNoTechnicalEvidence": not any(leaks.values()),
        "technicalLeakMarkers": leaks,
        "allChangedWorkflowNamesPreserved": names_complete,
        "offlineSingleFileVisual": no_external_dependency,
        "allChangedTablesAccountedFor": coverage_ledger_complete,
        "differenceCoverageLedger": diff.get("coverageLedger"),
        "listCoverageNotMisreportedAsUnchanged": list_coverage_honest,
    }


def run_workflow(
    old_path: Path,
    old_ir: dict,
    new_path: Path,
    new_ir: dict,
    direction: dict,
    output: Path,
    parse_seconds: float,
) -> dict:
    analysis = output / "_流程对比计算"
    analysis.mkdir(parents=True, exist_ok=True)
    old_workflow_ir = build_workflow_ir(old_ir, KNOWLEDGE)
    new_workflow_ir = build_workflow_ir(new_ir, KNOWLEDGE)
    diff = compare_workflow_irs(old_workflow_ir, new_workflow_ir, direction)
    report, visual, detail = render_report(diff), render_html(diff), render_detail_report(diff)
    validation = validate_workflow_result(
        old_workflow_ir, new_workflow_ir, diff, report, visual, detail
    )
    artifacts = {
        "旧版流程IR.json": old_workflow_ir,
        "新版流程IR.json": new_workflow_ir,
        "流程差异模型.json": diff,
        "流程对比校验.json": validation,
    }
    for name, model in artifacts.items():
        (analysis / name).write_text(
            json.dumps(model, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    customer_artifacts = dict(zip(WORKFLOW_DELIVERABLES, (report, visual, detail)))
    for name, content in customer_artifacts.items():
        (output / name).write_text(content, encoding="utf-8")
    if not validation["valid"]:
        raise SystemExit("流程对比门禁失败，详见 _流程对比计算/流程对比校验.json")
    return write_manifest(
        output,
        "workflow",
        WORKFLOW_DELIVERABLES,
        oldPackage=str(old_path),
        newPackage=str(new_path),
        direction=direction,
        workflowChangeSummary=diff["changeSummary"],
        workflowValidation=str(analysis / "流程对比校验.json"),
        performance={
            "parallelPackageParseSeconds": parse_seconds,
            "packageFullParseCount": 2,
            "canonicalReuse": True,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", type=Path)
    parser.add_argument("--new", type=Path)
    parser.add_argument("--package", dest="packages", type=Path, action="append")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-impact-depth", type=int, default=3, choices=(1, 2, 3))
    parser.add_argument("--full-technical-evidence", action="store_true")
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise SystemExit(f"输出目录必须不存在或为空：{output}")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ebuilder-canonical-stage-") as temp_name:
        try:
            (
                old_path,
                old_routing_ir,
                old_canonical,
                new_path,
                new_routing_ir,
                new_canonical,
                direction,
                parse_seconds,
            ) = resolve_inputs(args, Path(temp_name))
            mode = resolve_pair_mode(old_routing_ir, new_routing_ir)
        except (DirectionResolutionError, PackageModeError) as exc:
            raise SystemExit(str(exc)) from exc
        if mode == "application":
            manifest = run_application(
                args,
                old_path,
                old_canonical,
                new_path,
                new_canonical,
                direction,
                output,
                parse_seconds,
            )
        else:
            old_ir = json.loads(old_canonical.read_text(encoding="utf-8"))
            new_ir = json.loads(new_canonical.read_text(encoding="utf-8"))
            manifest = run_workflow(
                old_path,
                old_ir,
                new_path,
                new_ir,
                direction,
                output,
                parse_seconds,
            )
    print(json.dumps({"manifest": manifest}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
