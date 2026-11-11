#!/usr/bin/env python3
"""校验 V12 明细差异报告是否完整且未混入可视化、风险或验证内容。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


FORBIDDEN_PHRASES = [
    "应用版本差异可视化",
    "风险总览",
    "风险与验证点",
    "重点测试",
    "配置检查点",
    "测试步骤",
    "验证点",
    "风险等级",
    "技术名称未还原",
    "节点参数发生变化，业务含义待确认",
    "未观察到可确认的动作流业务变化",
]


def _flow_has_business_evidence(item: dict) -> bool:
    for change in item.get("internalChanges") or []:
        kind = change.get("kind")
        if kind == "NODE_SET" and (
            change.get("oldCount") != change.get("newCount")
            or change.get("addedComponents")
            or change.get("removedComponents")
            or change.get("renamedNodes")
        ):
            return True
        if kind in {"FORMULA_CHANGE", "MAPPING_CHANGE"} and change.get("factCount", 0):
            return True
        if kind in {"CHILD_CONFIGURATION_CHANGE", "FLOW_STATUS_CHANGED", "FLOW_ROOT_SETTING_CHANGED", "NAME_CHANGED"}:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("business_object_diff", type=Path)
    parser.add_argument("detail_report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    model_path = args.business_object_diff.expanduser().resolve()
    report_path = args.detail_report.expanduser().resolve()
    output = args.output.expanduser().resolve()
    model = json.loads(model_path.read_text(encoding="utf-8"))
    text = report_path.read_text(encoding="utf-8") if report_path.is_file() else ""
    form_section_match = re.search(r"### 6\.1 表单更新(.*?)### 6\.2 页面更新", text, flags=re.DOTALL)
    form_section = form_section_match.group(1) if form_section_match else ""
    page_section_match = re.search(r"### 6\.2 页面更新(.*?)### 6\.3 动作流更新", text, flags=re.DOTALL)
    page_section = page_section_match.group(1) if page_section_match else ""
    flow_section_match = re.search(r"### 6\.3 动作流更新(.*?)### 6\.4 菜单与导航更新", text, flags=re.DOTALL)
    flow_section = flow_section_match.group(1) if flow_section_match else ""
    summary = model.get("summary") or []
    objects = model.get("objects") or []
    expected = {item.get("changeType"): sum(1 for obj in objects if obj.get("changeType") == item.get("changeType")) for item in ({"changeType": "ADDED"}, {"changeType": "REMOVED"}, {"changeType": "UPDATED"}, {"changeType": "POSSIBLE_RENAME"}, {"changeType": "UNMATCHED"})}
    forbidden_hits = sorted({phrase for phrase in FORBIDDEN_PHRASES if phrase in text})
    updated_flows = [
        item for item in objects
        if item.get("objectType") == "ESB_ACTION_FLOW" and item.get("changeType") == "UPDATED"
    ]
    updated_forms = [
        item for item in objects
        if item.get("objectType") == "FORM" and item.get("changeType") == "UPDATED"
    ]
    updated_pages = [
        item for item in objects
        if item.get("objectType") == "PAGE" and item.get("changeType") == "UPDATED"
    ]
    updated_menus = [
        item for item in objects
        if item.get("objectType") == "MENU" and item.get("changeType") == "UPDATED"
    ]
    checks = {
        "reportExists": report_path.is_file() and bool(text.strip()),
        "summaryRowsPresent": all(str(item.get("label")) in text for item in summary),
        "allChangedObjectNamesPresent": all(str(obj.get("businessName") or "未确认") in text for obj in objects if obj.get("changeType") != "UNCHANGED"),
        "allChangeTypesRepresented": all(heading in text for heading in ("新增功能", "删除功能", "更新功能", "疑似重命名和功能替代")),
        "fullAppendixPresent": "附录：完整对象明细" in text,
        "formSummaryLayerPresent": "表单变更摘要" in text and "| 表单名称 | 变更结论 | 用户可见影响 |" in text,
        "formEvidenceLayerPresent": (
            not updated_forms
            or (
                "表单对象展开明细" in text
                and "| 变化区域 | 变化类型 | 具体变化 |" in text
            )
        ),
        "noEmptyFormBoilerplate": "未观察到可命名字段增删" not in text,
        "noRawComponentIdentity": not bool(re.search(r'type="[A-Za-z][A-Za-z0-9_]*"', form_section)),
        "noRawDynamicTableName": not bool(re.search(r"\buf_[a-z0-9_]+\b", form_section, flags=re.IGNORECASE)),
        "pageSummaryLayerPresent": "页面变更摘要" in page_section and "| 页面名称 | 变更结论 | 具体变化 | 影响判断 |" in page_section,
        "pageEvidenceLayerPresent": (
            not updated_pages
            or (
                "页面对象展开明细" in page_section
                and "| 变化区域 | 变化类型 | 具体变化 |" in page_section
            )
        ),
        "flowSummaryLayerPresent": "动作流变更摘要" in flow_section and "| 动作流名称 | 变更结论 | 涉及节点 | 具体变化 | 业务影响 |" in flow_section,
        "flowEvidenceLayerPresent": (
            not updated_flows
            or (
                "动作流对象展开明细" in flow_section
                and "| 变化区域/节点 | 变化类型 | 具体变化 |" in flow_section
            )
        ),
        "noPageTechnicalBoilerplate": not any(phrase in page_section for phrase in ("组件关系未完整解析", "配置内容（长度", "对象实例或内部配置已切换")),
        "noFlowTechnicalBoilerplate": not any(phrase in flow_section for phrase in ("公式事实 0 项", "映射事实 0 项", "配置内容（长度", "对象实例或内部配置已切换")),
        "allUpdatedFlowsHaveBusinessEvidence": all(_flow_has_business_evidence(item) for item in updated_flows),
        "noIdenticalMenuTargetClaim": all(
            (item.get("oldSummary") or {}).get("openTarget") != (item.get("newSummary") or {}).get("openTarget")
            or any(change.get("kind") == "MENU_CONFIGURATION_CHANGE" for change in item.get("internalChanges") or [])
            for item in updated_menus
        ),
        "noVisualization": "应用版本差异可视化" not in text and "可视化" not in text,
        "noRiskOrValidationContent": not forbidden_hits,
        "noRawEvidencePaths": not bool(re.search(r"(?:comparison-facts|comparison-analysis|visual-diff-model|风险与验证点|无法确认项)\.json", text)),
        "noTechnicalObjectIdentity": not bool(re.search(
            r"(?:migration-source|profile-lineage|idm-lineage|idm-context|content|parent)=|undefined_迁出使用关联视图",
            text,
            flags=re.IGNORECASE,
        )),
        "noGeneratedNameTimestamp": not bool(re.search(r"(?<!\d)\d{14}(?!\d)", text)),
        "sizeAtMost300KB": report_path.is_file() and report_path.stat().st_size <= 300 * 1024,
    }
    validation = {
        "schemaVersion": "ebuilder-v12-detail-diff-validation/v1",
        "valid": all(bool(value) for value in checks.values()),
        "report": str(report_path),
        "checks": checks,
        "forbiddenPhraseHits": forbidden_hits,
        "objectCounts": expected,
        "reportBytes": report_path.stat().st_size if report_path.is_file() else 0,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    return 0 if validation["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
