#!/usr/bin/env python3
"""校验客户可视化报告是否为完整、可离线打开且不泄露技术对象的单文件。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from customer_text_guard import find_customer_text_leaks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("comparison_json", type=Path)
    parser.add_argument("visual_html", type=Path)
    parser.add_argument("--report", type=Path, help="对应的客户 Markdown 主报告")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.comparison_json.expanduser().resolve()
    visual = args.visual_html.expanduser().resolve()
    output = args.output.expanduser().resolve()
    checks: dict[str, object] = {}
    html = visual.read_text(encoding="utf-8") if visual.is_file() else ""
    report = args.report.expanduser().resolve() if args.report else None
    report_text = report.read_text(encoding="utf-8") if report and report.is_file() else ""
    source_data = json.loads(source.read_text(encoding="utf-8")) if source.is_file() else {}
    match = re.search(r'<script\s+id="report-data"\s+type="application/json">(.*?)</script>', html, re.S)
    embedded = None
    if match:
        try:
            embedded = json.loads(match.group(1).replace("<\\/", "</"))
        except json.JSONDecodeError:
            embedded = None
    checks["htmlExists"] = visual.is_file() and bool(html.strip())
    checks["embeddedModelParseable"] = isinstance(embedded, dict)
    checks["singleFileNoExternalAssets"] = not bool(re.search(r'<(?:link[^>]+href|script[^>]+src|img[^>]+src)=', html, re.I))
    checks["noNetworkCalls"] = not bool(re.search(r"https?://|fetch\s*\(|XMLHttpRequest|WebSocket|import\s*\(", html, re.I))
    html_leaks = find_customer_text_leaks(html, html=True)
    report_leaks = find_customer_text_leaks(report_text) if report else []
    checks["noTechnicalEvidence"] = not html_leaks and not report_leaks
    checks["reportExists"] = report is None or report.is_file()
    checks["reportNoTechnicalEvidence"] = report is None or not report_leaks
    required_controls = ["ebv-app", "ebv-search", "ebv-domain-filter", "ebv-change-filter", "ebv-reset", "overview-panel", "features-panel", "tests-panel", "report-data"]
    checks["customerControlsPresent"] = all(control in html for control in required_controls)
    checks["sizeAtMost2MB"] = visual.is_file() and visual.stat().st_size <= 2 * 1024 * 1024
    if isinstance(embedded, dict):
        checks["summaryMatches"] = (
            embedded.get("changeSummary") == {key: int((source_data.get("changeSummary") or {}).get(key, 0) or 0) for key in ("新增", "删除", "归属调整", "更新")} and
            len(embedded.get("features", [])) == len(source_data.get("featureChanges", [])) and
            len(embedded.get("tests", [])) <= len(source_data.get("testPoints", []))
        )
        checks["hasCustomerSections"] = all(key in embedded for key in ("summary", "changeSummary", "domains", "features", "chains", "tests"))
        source_features = source_data.get("featureChanges", [])
        embedded_features = embedded.get("features", [])
        object_name_errors = []
        for index, source_feature in enumerate(source_features):
            if index >= len(embedded_features):
                object_name_errors.append(f"第 {index + 1} 项功能变化未进入可视化")
                continue
            visual_feature = embedded_features[index]
            expected_display = source_feature.get("displayName") or source_feature.get("newName") or source_feature.get("oldName") or "未命名功能"
            if visual_feature.get("name") != expected_display:
                object_name_errors.append(f"{expected_display}：可视化标题未保留业务模型显示名")
            expected_objects = [
                item.get("newName") or item.get("oldName")
                for item in (source_feature.get("changedObjects") or [])
            ]
            actual_objects = [item.get("name") for item in (visual_feature.get("changedObjects") or [])]
            if expected_objects != actual_objects:
                object_name_errors.append(f"{expected_display}：可视化未完整保留实际变化对象名称")
        checks["concreteObjectNamesPreserved"] = not object_name_errors
    else:
        checks["summaryMatches"] = False
        checks["hasCustomerSections"] = False
        checks["concreteObjectNamesPreserved"] = False
        object_name_errors = ["可视化内嵌模型无法解析"]
    validation = {
        "schemaVersion": "ebuilder-v12-panorama-visual-validation/v1",
        "valid": all(bool(value) for value in checks.values()),
        "visualReport": str(visual),
        "customerReport": str(report) if report else None,
        "technicalLeakMarkers": {"html": html_leaks, "report": report_leaks},
        "concreteObjectNameErrors": object_name_errors,
        "checks": checks,
        "featureCount": len((embedded or {}).get("features", [])) if isinstance(embedded, dict) else 0,
        "testCount": len((embedded or {}).get("tests", [])) if isinstance(embedded, dict) else 0,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    return 0 if validation["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
