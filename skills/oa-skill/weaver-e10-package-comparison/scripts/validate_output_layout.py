#!/usr/bin/env python3
"""校验 V12 完整工作区只保留一套用户交付原件。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT_DELIVERABLES = (
    "应用版本功能差异报告.md",
    "应用版本功能差异可视化.html",
    "应用版本功能差异明细.json",
    "应用版本功能明细差异报告.md",
)

FORBIDDEN_ALIASES = (
    "应用全景对比/应用全景对比实验报告.md",
    "应用全景对比/应用全景对比实验结果.json",
    "应用全景对比/应用全景对比可视化.html",
    "应用全景对比/应用版本功能明细差异报告.md",
    "旧版应用全景报告.md",
    "新版应用全景报告.md",
)


def panorama_reports(output: Path, side: str) -> list[Path]:
    return sorted((output / "应用全景重建" / side / "应用业务报告").glob("*应用功能全景报告.md"))


def build_validation(output: Path) -> dict:
    missing_deliverables = [name for name in ROOT_DELIVERABLES if not (output / name).is_file()]
    forbidden_aliases = [name for name in FORBIDDEN_ALIASES if (output / name).exists()]
    old_reports = panorama_reports(output, "旧版")
    new_reports = panorama_reports(output, "新版")
    role_directories = ("_技术对象差异", "应用全景重建", "应用全景对比", "执行日志")
    missing_role_directories = [name for name in role_directories if not (output / name).is_dir()]
    checks = {
        "rootDeliverablesExist": not missing_deliverables,
        "noDuplicatedStableEntryAliases": not forbidden_aliases,
        "exactlyOneOldPanoramaReport": len(old_reports) == 1,
        "exactlyOneNewPanoramaReport": len(new_reports) == 1,
        "roleDirectoriesPresent": not missing_role_directories,
    }
    return {
        "schemaVersion": "ebuilder-v12-output-layout-validation/v1",
        "valid": all(checks.values()),
        "checks": checks,
        "rootDeliverables": [str(output / name) for name in ROOT_DELIVERABLES],
        "oldPanoramaReport": str(old_reports[0]) if len(old_reports) == 1 else None,
        "newPanoramaReport": str(new_reports[0]) if len(new_reports) == 1 else None,
        "missingDeliverables": missing_deliverables,
        "forbiddenAliasesFound": forbidden_aliases,
        "missingRoleDirectories": missing_role_directories,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    validation_path = args.output.expanduser().resolve()
    validation = build_validation(output_dir)
    validation_path.parent.mkdir(parents=True, exist_ok=True)
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    return 0 if validation["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
