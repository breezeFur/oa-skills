#!/usr/bin/env python3
"""Run V15.6 optimized comparison and retain the mode-specific three reports."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FULL_RUNNER = ROOT / "scripts" / "run_v13_comparison.py"
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


def validate_destination(output: Path) -> None:
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise SystemExit(f"输出目录必须不存在或为空：{output}")


def validate_deliverables(folder: Path, deliverables: tuple[str, ...]) -> None:
    entries = {path.name for path in folder.iterdir()}
    expected = set(deliverables)
    if entries != expected:
        missing = sorted(expected - entries)
        extra = sorted(entries - expected)
        raise RuntimeError(f"精简交付目录不符合预期；缺少={missing}，多余={extra}")
    for name in deliverables:
        path = folder / name
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"精简交付文件缺失或为空：{path}")


def build_full_command(args: argparse.Namespace, full_output: Path) -> list[str]:
    command = [sys.executable, str(FULL_RUNNER)]
    if args.old and args.new:
        command.extend(["--old", str(args.old), "--new", str(args.new)])
    else:
        for package in args.packages or []:
            command.extend(["--package", str(package)])
    command.extend([
        "--output", str(full_output),
        "--max-impact-depth", str(args.max_impact_depth),
    ])
    if args.full_technical_evidence:
        command.append("--full-technical-evidence")
    return command


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", type=Path)
    parser.add_argument("--new", type=Path)
    parser.add_argument("--package", dest="packages", type=Path, action="append")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-impact-depth", type=int, default=3, choices=(1, 2, 3))
    parser.add_argument("--full-technical-evidence", action="store_true")
    args = parser.parse_args()

    if bool(args.old) != bool(args.new):
        raise SystemExit("--old 与 --new 必须同时提供")
    if not (args.old and args.new) and len(args.packages or []) != 2:
        raise SystemExit("未指定 --old/--new 时，必须重复提供两个 --package")

    output = args.output.expanduser().resolve()
    validate_destination(output)
    output_preexisted = output.exists()
    summary: dict[str, object] = {}

    with tempfile.TemporaryDirectory(prefix="ebuilder-version-comparison-") as temp_name:
        full_output = Path(temp_name) / "full-output"
        completed = subprocess.run(build_full_command(args, full_output))
        if completed.returncode:
            return completed.returncode

        manifest_path = full_output / "V13执行清单.json"
        if not manifest_path.is_file():
            raise RuntimeError(f"完整对比未生成 V13 执行清单：{manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        deliverables = tuple(manifest.get("deliverables") or ())
        allowed = {APP_DELIVERABLES, WORKFLOW_DELIVERABLES}
        if deliverables not in allowed:
            raise RuntimeError(f"V13 执行清单包含未知交付集合：{deliverables}")
        source_files = [full_output / name for name in deliverables]
        for source in source_files:
            if not source.is_file() or source.stat().st_size == 0:
                raise RuntimeError(f"完整对比未生成必需报告：{source}")

        try:
            validate_destination(output)
            output.mkdir(parents=True, exist_ok=True)
            for source in source_files:
                shutil.copy2(source, output / source.name)
            validate_deliverables(output, deliverables)
        except Exception:
            for name in deliverables:
                (output / name).unlink(missing_ok=True)
            if not output_preexisted:
                output.rmdir()
            raise

        summary = {
            "status": "complete",
            "version": "V15.6",
            "comparisonMode": manifest.get("comparisonMode"),
            "mode": "compact-three-report-delivery",
            "output": str(output),
            "deliverables": [str(output / name) for name in deliverables],
            "intermediateArtifactsRetained": False,
            "performance": manifest.get("performance") or {},
        }

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
