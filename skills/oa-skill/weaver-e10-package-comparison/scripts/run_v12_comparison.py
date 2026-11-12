#!/usr/bin/env python3
"""V12 完整总控：生成并校验业务报告、可视化、明细与技术证据。"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from package_direction import DirectionResolutionError, automatic_direction
from parse_package import parse_package
from customer_text_guard import find_customer_text_leaks


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
BUNDLED_PARSE = SCRIPTS / "parse_package.py"


def run_command(command: list[object], log_path: Path) -> None:
    command = [str(x) for x in command]
    completed = subprocess.run(command, text=True, capture_output=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "$ " + " ".join(command) + "\n\nSTDOUT\n" + completed.stdout +
        "\nSTDERR\n" + completed.stderr,
        encoding="utf-8",
    )
    if completed.returncode:
        raise RuntimeError(
            f"命令执行失败（{completed.returncode}）：{command[0]}\n"
            f"详见 {log_path}\n{completed.stderr[-4000:]}"
        )


def run_commands_parallel(tasks: list[tuple[list[object], Path]]) -> None:
    """Run independent subprocess stages concurrently and preserve per-stage logs."""
    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = [
            executor.submit(run_command, command, log_path)
            for command, log_path in tasks
        ]
        for future in futures:
            future.result()


def validate_zip(path: Path, role: str) -> Path:
    path = path.expanduser().resolve()
    if not path.is_file() or path.suffix.lower() != ".zip":
        raise SystemExit(f"{role} 必须是存在的 ZIP：{path}")
    return path


def resolve_direction(
    args: argparse.Namespace,
) -> tuple[Path, Path, dict, dict | None, dict | None]:
    if bool(args.old) != bool(args.new):
        raise SystemExit("--old 与 --new 必须同时提供")
    if args.old and args.new:
        old_path, new_path = validate_zip(args.old, "旧包"), validate_zip(args.new, "新包")
        if old_path == new_path:
            raise SystemExit("必须提供两个不同的输入 ZIP")
        return old_path, new_path, {
            "directionSource": "EXPLICIT_CLI_ARGUMENTS",
            "rule": "--old/--new roles take precedence over profile exportTime",
            "filenameInferenceUsed": False,
            "fileMetadataInferenceUsed": False,
            "exportTimeComparisonUsed": False,
            "inputOrder": [old_path.name, new_path.name],
        }, None, None
    if len(args.packages or []) != 2:
        raise SystemExit("未指定 --old/--new 时，必须重复提供两个 --package")
    first, second = validate_zip(args.packages[0], "候选包 1"), validate_zip(args.packages[1], "候选包 2")
    if first == second:
        raise SystemExit("必须提供两个不同的输入 ZIP")
    try:
        old_path, old_ir, new_path, new_ir, resolution = automatic_direction(
            first, parse_package(first), second, parse_package(second)
        )
    except DirectionResolutionError as exc:
        raise SystemExit(str(exc)) from exc
    return old_path, new_path, resolution, old_ir, new_ir


def write_canonical_ir(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def validate_preloaded_output(
    output: Path,
    canonical_paths: tuple[Path, Path] | None,
) -> None:
    if not output.exists() or not any(output.iterdir()):
        return
    if canonical_paths is None:
        raise SystemExit(f"输出目录必须不存在或为空：{output}")
    expected = {path.expanduser().resolve() for path in canonical_paths}
    existing_files = {
        path.resolve() for path in output.rglob("*") if path.is_file()
    }
    if existing_files != expected:
        raise SystemExit(
            f"预置 canonical IR 之外输出目录必须为空：{output}"
        )


def first_report(folder: Path, suffix: str) -> Path:
    candidates = sorted((folder / "应用业务报告").glob(f"*{suffix}"))
    if not candidates:
        raise RuntimeError(f"{folder} 中没有生成 {suffix}")
    return candidates[0]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_json_or_gzip(folder: Path, name: str) -> dict:
    plain = folder / name
    if plain.exists():
        return load_json(plain)
    compressed = folder / f"{name}.gz"
    if compressed.exists():
        with gzip.open(compressed, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def customer_report_has_technical_leak(path: Path) -> list[str]:
    return find_customer_text_leaks(path.read_text(encoding="utf-8"))


def write_v12_validation(output: Path, old_panorama: Path, new_panorama: Path, comparison: Path, direction: dict, old_path: Path, new_path: Path, visual_validation: dict, detail_validation: dict, layout_validation: dict) -> dict:
    result_json = output / "应用版本功能差异明细.json"
    report_md = output / "应用版本功能差异报告.md"
    comparison_validation = comparison / "应用全景对比实验校验.json"
    result = load_json(result_json)
    reconstruction_manifests = {
        "old": load_json(old_panorama / "reconstruction-manifest.json"),
        "new": load_json(new_panorama / "reconstruction-manifest.json"),
    }
    technical = output / "_技术对象差异"
    technical_analysis = load_json_or_gzip(technical, "comparison-analysis.json")
    old_metadata = (technical_analysis.get("analysisDirection") or {}).get("old") or {}
    new_metadata = (technical_analysis.get("analysisDirection") or {}).get("new") or {}
    technical_checks = {}
    for name in ("报告数量一致性校验.json", "报告可读性检查.json", "可视化数据一致性校验.json", "可视化可用性检查.json"):
        path = technical / name
        if path.exists():
            try:
                technical_checks[name] = load_json(path)
            except json.JSONDecodeError:
                technical_checks[name] = {"valid": False, "error": "JSON 无法解析"}
        else:
            technical_checks[name] = {"valid": False, "error": "文件缺失"}
    leaks = customer_report_has_technical_leak(report_md)
    validation = {
        "schemaVersion": "ebuilder-v12-report-validation/v1",
        "valid": bool(
            report_md.is_file() and report_md.stat().st_size and
            result_json.is_file() and result_json.stat().st_size and
            comparison_validation.is_file() and
            all(x.get("status") == "complete" for x in reconstruction_manifests.values()) and
            not leaks
        ),
        "customerReport": str(report_md),
        "customerReportNoTechnicalEvidence": not leaks,
        "technicalLeakMarkers": leaks,
        "oldPackage": {"path": str(old_path), "sha256": old_metadata.get("sha256") or sha256(old_path)},
        "newPackage": {"path": str(new_path), "sha256": new_metadata.get("sha256") or sha256(new_path)},
        "direction": direction,
        "businessChangeSummary": result.get("changeSummary", {}),
        "businessTestPointCount": len(result.get("testPoints", [])),
        "chainChangeSummary": {key: len(value) for key, value in result.get("chainChanges", {}).items()},
        "reconstruction": {
            side: {
                "status": manifest.get("status"),
                "applicationIR": manifest.get("applicationIR"),
                "businessReport": manifest.get("businessReadableOutputs", {}).get("overviewReport"),
                "mapping": manifest.get("businessReadableOutputs", {}).get("businessFunctionMap"),
            }
            for side, manifest in reconstruction_manifests.items()
        },
        "technicalAppendixChecks": technical_checks,
        "visualReport": str(output / "应用版本功能差异可视化.html"),
        "visualReportValidation": visual_validation,
        "detailDiffReport": str(output / "应用版本功能明细差异报告.md"),
        "detailDiffReportValidation": detail_validation,
        "outputLayoutValidation": layout_validation,
        "limitations": result.get("limitations", []),
    }
    (output / "报告可读性检查.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return validation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", type=Path)
    parser.add_argument("--new", type=Path)
    parser.add_argument("--package", dest="packages", type=Path, action="append")
    parser.add_argument("--old-canonical", type=Path)
    parser.add_argument("--new-canonical", type=Path)
    parser.add_argument("--resolved-direction-json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-impact-depth", type=int, default=3, choices=(1, 2, 3))
    parser.add_argument("--full-technical-evidence", action="store_true")
    args = parser.parse_args()
    canonical_requested = args.old_canonical is not None or args.new_canonical is not None
    if canonical_requested and (
        args.old_canonical is None or args.new_canonical is None
    ):
        raise SystemExit("--old-canonical 与 --new-canonical 必须同时提供")
    if canonical_requested and not (args.old and args.new):
        raise SystemExit("canonical package IR 复用仅支持明确的 --old/--new 方向")

    started = time.monotonic()
    timings: dict[str, object] = {}
    old_path, new_path, direction, old_ir, new_ir = resolve_direction(args)
    if args.resolved_direction_json:
        if not (args.old and args.new):
            raise SystemExit("--resolved-direction-json 只能与 --old/--new 一起使用")
        try:
            resolved_direction = json.loads(args.resolved_direction_json)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"--resolved-direction-json 无法解析: {exc}") from exc
        if not isinstance(resolved_direction, dict) or not resolved_direction.get(
            "directionSource"
        ):
            raise SystemExit("--resolved-direction-json 缺少 directionSource")
        direction = resolved_direction
    output = args.output.expanduser().resolve()
    provided_canonicals = (
        (
            args.old_canonical.expanduser().resolve(),
            args.new_canonical.expanduser().resolve(),
        )
        if canonical_requested
        else None
    )
    validate_preloaded_output(output, provided_canonicals)
    output.mkdir(parents=True, exist_ok=True)
    logs = output / "执行日志"
    technical = output / "_技术对象差异"
    old_panorama = output / "应用全景重建" / "旧版"
    new_panorama = output / "应用全景重建" / "新版"
    old_canonical = (
        provided_canonicals[0]
        if provided_canonicals
        else old_panorama / "canonical-package-ir.json"
    )
    new_canonical = (
        provided_canonicals[1]
        if provided_canonicals
        else new_panorama / "canonical-package-ir.json"
    )

    stage_started = time.monotonic()
    if provided_canonicals:
        for role, canonical in (("旧包", old_canonical), ("新包", new_canonical)):
            if not canonical.is_file():
                raise SystemExit(f"{role} canonical package IR 不存在：{canonical}")
    elif old_ir is not None and new_ir is not None:
        write_canonical_ir(old_canonical, old_ir)
        write_canonical_ir(new_canonical, new_ir)
    else:
        run_commands_parallel([
            ([sys.executable, SCRIPTS / "parse_package.py", old_path, "--output", old_canonical, "--compact-output"], logs / "parse-old.log"),
            ([sys.executable, SCRIPTS / "parse_package.py", new_path, "--output", new_canonical, "--compact-output"], logs / "parse-new.log"),
        ])
    timings["canonicalPreparationSeconds"] = round(time.monotonic() - stage_started, 3)
    timings["canonicalReused"] = bool(provided_canonicals)
    timings["packageFullParseCount"] = 0 if provided_canonicals else 2

    stage_started = time.monotonic()
    run_commands_parallel([
        ([sys.executable, SCRIPTS / "validate_customer_object_naming.py"], logs / "customer-object-naming-self-test.log"),
        ([sys.executable, SCRIPTS / "validate_business_child_rollup.py"], logs / "business-child-rollup-self-test.log"),
        ([sys.executable, SCRIPTS / "validate_customer_semantic_noise.py"], logs / "customer-semantic-noise-self-test.log"),
    ])
    timings["selfTestsSeconds"] = round(time.monotonic() - stage_started, 3)

    stage_started = time.monotonic()
    run_command([
        sys.executable, SCRIPTS / "compare_packages.py",
        "--old", old_path, "--new", new_path,
        "--old-canonical", old_canonical,
        "--new-canonical", new_canonical,
        "--resolved-direction-json", json.dumps(direction, ensure_ascii=False, separators=(",", ":")),
        "--output", technical,
        "--max-impact-depth", args.max_impact_depth,
        *( ["--full-technical-evidence"] if args.full_technical_evidence else [] ),
    ], logs / "v8-technical-comparison.log")
    timings["technicalComparisonSeconds"] = round(time.monotonic() - stage_started, 3)
    technical_integrity = load_json(technical / "执行与完整性校验.json")
    timings["technicalBreakdown"] = technical_integrity.get("performance") or {}

    reconstruct_script = SCRIPTS / "reconstruct_application.py"
    stage_started = time.monotonic()
    run_commands_parallel([
        ([sys.executable, reconstruct_script, old_canonical, "--output-dir", old_panorama, "--parse-script", BUNDLED_PARSE], logs / "reconstruct-old.log"),
        ([sys.executable, reconstruct_script, new_canonical, "--output-dir", new_panorama, "--parse-script", BUNDLED_PARSE], logs / "reconstruct-new.log"),
    ])
    timings["parallelPanoramaReconstructionSeconds"] = round(time.monotonic() - stage_started, 3)

    comparison = output / "应用全景对比"
    customer_report = output / "应用版本功能差异报告.md"
    customer_json = output / "应用版本功能差异明细.json"
    comparison_validation_path = comparison / "应用全景对比实验校验.json"
    stage_started = time.monotonic()
    run_command([
        sys.executable, SCRIPTS / "compare_reconstructed_application.py",
        old_panorama, new_panorama, "--output-dir", comparison,
        "--report-output", customer_report,
        "--json-output", customer_json,
        "--validation-output", comparison_validation_path,
        "--business-object-diff", technical / "business-object-diff.json",
    ], logs / "panorama-comparison.log")

    visual_report = output / "应用版本功能差异可视化.html"
    run_command([
        sys.executable, SCRIPTS / "render_panorama_visual_html.py",
        customer_json, "--output", visual_report,
    ], logs / "panorama-visualization.log")
    visual_validation_path = comparison / "应用全景对比可视化校验.json"
    run_command([
        sys.executable, SCRIPTS / "validate_panorama_visual.py",
        customer_json, visual_report, "--report", customer_report,
        "--output", visual_validation_path,
    ], logs / "panorama-visualization-validation.log")
    visual_validation = load_json(visual_validation_path)
    detail_report = output / "应用版本功能明细差异报告.md"
    run_command([
        sys.executable, SCRIPTS / "render_detail_diff_report.py",
        technical / "business-object-diff.json", "--output", detail_report,
    ], logs / "detail-diff-report.log")
    detail_validation_path = comparison / "明细差异报告校验.json"
    run_command([
        sys.executable, SCRIPTS / "validate_detail_diff_report.py",
        technical / "business-object-diff.json", detail_report, "--output", detail_validation_path,
    ], logs / "detail-diff-report-validation.log")
    detail_validation = load_json(detail_validation_path)
    layout_validation_path = output / "产物目录检查.json"
    run_command([
        sys.executable, SCRIPTS / "validate_output_layout.py",
        output, "--output", layout_validation_path,
    ], logs / "output-layout-validation.log")
    layout_validation = load_json(layout_validation_path)
    timings["customerReportAndValidationSeconds"] = round(time.monotonic() - stage_started, 3)
    timings["totalV12Seconds"] = round(time.monotonic() - started, 3)
    validation = write_v12_validation(output, old_panorama, new_panorama, comparison, direction, old_path, new_path, visual_validation, detail_validation, layout_validation)
    validation["valid"] = bool(validation["valid"] and visual_validation.get("valid") and detail_validation.get("valid") and layout_validation.get("valid"))
    (output / "报告可读性检查.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "version": "V15.6",
        "status": "complete" if validation["valid"] else "blocked",
        "method": "reconstruct-then-compare-business-panorama-with-customer-visual-and-v7-detail",
        "oldPackage": str(old_path),
        "newPackage": str(new_path),
        "direction": direction,
        "primaryReport": str(output / "应用版本功能差异报告.md"),
        "primaryJson": str(output / "应用版本功能差异明细.json"),
        "visualReport": str(output / "应用版本功能差异可视化.html"),
        "detailDiffReport": str(output / "应用版本功能明细差异报告.md"),
        "oldPanorama": str(first_report(old_panorama, "应用功能全景报告.md")),
        "newPanorama": str(first_report(new_panorama, "应用功能全景报告.md")),
        "technicalAppendix": str(technical),
        "validation": str(output / "报告可读性检查.json"),
        "outputLayoutValidation": str(layout_validation_path),
        "performance": timings,
    }
    (output / "V12执行清单.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": manifest, "businessChangeSummary": validation["businessChangeSummary"], "testPointCount": validation["businessTestPointCount"]}, ensure_ascii=False, indent=2))
    return 0 if validation["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
