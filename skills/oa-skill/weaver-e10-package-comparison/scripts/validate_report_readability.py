#!/usr/bin/env python3
"""验证业务功能对象报告的结构、中文表达密度和技术噪声隔离。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


REQUIRED_SECTIONS = [
    "## 1. 报告范围",
    "## 2. 总体结论",
    "## 3. 功能对象变化汇总",
    "## 4. 新增功能",
    "## 5. 删除功能",
    "## 6. 更新功能",
    "## 7. 疑似重命名和功能替代",
    "## 8. 业务影响评估",
    "## 9. 重点测试建议",
    "## 10. 未确认项和能力边界",
    "## 附录A：完整新增对象",
    "## 附录B：完整删除对象",
    "## 附录C：完整更新对象",
    "## 附录D：技术证据索引",
]

FORBIDDEN_PHRASES = [
    "测试一下表单",
    "检查动作流",
    "迁入已经成功",
    "功能已经正常",
]


def validate_readability(
    report: str,
    model: dict[str, Any],
    scenarios: list[dict[str, Any]],
) -> dict[str, Any]:
    lines = report.splitlines()
    byte_count = len(report.encode("utf-8"))
    h3_count = sum(line.startswith("### ") for line in lines)
    table_count = sum(line.startswith("|---") for line in lines)
    active_count = sum(
        item.get("changeType") in {"ADDED", "REMOVED", "UPDATED"}
        for item in model.get("objects") or []
    )
    min_scenarios = min(20, max(1, active_count)) if active_count else 0
    scenario_gate = min_scenarios <= len(scenarios) <= 40
    checks = {
        "lineCountAtMost800": len(lines) <= 800,
        "sizeAtMost200KB": byte_count <= 200 * 1024,
        "h3CountAtMost80": h3_count <= 80,
        "allRequiredSectionsPresent": all(section in report for section in REQUIRED_SECTIONS),
        "noRawJsonCodeBlock": "```json" not in report.lower(),
        "noProgramDictionaryLiteral": not bool(re.search(r"\{'(?:kind|path|changeType)':", report)),
        "noRiskLedgerNarrative": "848项" not in report and "889项" not in report and "66035条" not in report,
        "noForbiddenPhrases": not any(phrase in report for phrase in FORBIDDEN_PHRASES),
        "testScenarioCountProportionateAndAtMost40": scenario_gate,
        "businessObjectCoreTablePresent": (
            "| 功能对象 | 旧版数量 | 新版数量 | 新增 | 删除 | 更新 | 净变化 |"
            in report
        ),
        "noBuildMachinePath": not bool(
            re.search(r"/Users/[^/]+/(?:Desktop|Downloads|\.codex)/", report)
        ),
        "noTechnicalPlaceholderBusinessNames": all(
            not any(
                token in str(item.get("businessName") or "")
                for token in ("migration-source=", "content=", "parent=")
            )
            for item in model.get("objects") or []
        ),
        "noArtificialPaddingComments": "留白仅用于保持报告章节间距" not in report,
        "allBusinessFeatureChangesRepresented": (
            (model.get("featureChangeCoverage") or {}).get("expected", 0)
            == (model.get("featureChangeCoverage") or {}).get("represented", 0)
        ),
        "updatedPageDoesNotClaimZeroComponents": all(
            (
                (item.get("oldSummary") or {}).get("componentCount") != 0
                or (item.get("newSummary") or {}).get("componentCount") != 0
                or "组件关系未完整解析" in report
            )
            for item in model.get("objects") or []
            if item.get("objectType") == "PAGE"
            and item.get("changeType") == "UPDATED"
        ),
        "noTechnicalChangePlaceholdersInCustomerReport": (
            not any(
                token in report
                for token in (
                    'type="',
                    "内容摘要 ",
                    "ebdd_page_layout",
                    "form_ecode_id.$ref",
                    "config.fieldUsage",
                    "config.eventGroup",
                    "config.flow.nodes",
                    "linkedNodes",
                    "rightTopDropDown",
                    "package-unit=",
                    "migration-source=",
                )
            )
            and not bool(re.search(r"\.\$ref\b|</?[A-Za-z][^>]*>", report))
        ),
        "zeroComponentPagesExplicitlyPending": all(
            (
                (item.get("newSummary") or {}).get("componentCount") != 0
                or "组件关系待确认" in report
            )
            for item in model.get("objects") or []
            if item.get("objectType") == "PAGE"
            and item.get("changeType") == "ADDED"
        ),
    }
    return {
        "schemaVersion": "ebuilder-report-readability-check/v3.1",
        "metrics": {
            "lines": len(lines),
            "bytes": byte_count,
            "h3Headings": h3_count,
            "testScenarios": len(scenarios),
            "minimumScenariosForThisDiff": min_scenarios,
            "tables": table_count,
        },
        "checks": checks,
        "result": "PASS" if all(checks.values()) else "FAIL",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="对比输出目录")
    args = parser.parse_args()
    report = (args.output / "应用版本功能差异报告.md").read_text(encoding="utf-8")
    model = json.loads((args.output / "business-object-diff.json").read_text(encoding="utf-8"))
    scenarios = model.get("testScenarios") or []
    result = validate_readability(report, model, scenarios)
    print(json.dumps(result, ensure_ascii=False))
    if result["result"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
