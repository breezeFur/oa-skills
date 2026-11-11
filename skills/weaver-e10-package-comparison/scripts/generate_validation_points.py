#!/usr/bin/env python3
"""从实际变化与已触发风险生成可执行的配置检查和业务验证步骤。"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from knowledge_io import iter_jsonl

def _id(prefix: str, seed: str) -> str:
    return prefix + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:14].upper()


def choose_template(
    templates: list[dict[str, Any]],
    facts: list[dict[str, Any]],
) -> dict[str, Any]:
    tables = {fact["object"]["table"].lower() for fact in facts}
    kinds = {fact["object"]["moduleKind"] for fact in facts}
    if any(fact["changeType"] == "POSSIBLE_RENAME" for fact in facts):
        kind = "POSSIBLE_RENAME"
    elif any(fact["changeType"] == "REMOVED" for fact in facts):
        kind = "REMOVED_OBJECT"
    elif "ESB动作流" in kinds:
        kind = "ESB_FLOW"
    elif "页面与应用" in kinds:
        kind = "PAGE"
    elif "表单" in kinds and any("field" in table for table in tables):
        kind = "FORM_FIELD"
    elif "表单" in kinds:
        kind = "FORM_LAYOUT"
    elif "CusApp菜单" in kinds:
        kind = "MENU"
    elif "EDC报表" in kinds:
        kind = "REPORT"
    elif "权限" in kinds:
        kind = "PERMISSION"
    else:
        kind = "DATA_SCHEMA"
    return next(
        (template for template in templates if template["kind"] == kind),
        templates[0],
    )


def _applicability(facts: list[dict[str, Any]]) -> dict[str, list[str]]:
    kinds = {fact["object"]["moduleKind"] for fact in facts}
    terminals = []
    if kinds & {"表单", "页面与应用", "CusApp菜单"}:
        terminals.extend(["PC", "H5"])
    if kinds & {"ESB动作流", "工作流", "其他配置"}:
        terminals.append("服务端")
    if not terminals:
        terminals.append("对应业务终端")
    roles = ["有权限业务用户", "无权限或边界权限用户"]
    branches = ["正常路径", "边界值/空值路径"]
    if kinds & {"ESB动作流", "工作流"}:
        branches.append("失败与异常路径")
    return {
        "terminals": sorted(set(terminals)),
        "roles": roles,
        "branches": branches,
    }


def generate_validation_points(
    facts: list[dict[str, Any]],
    risks: list[dict[str, Any]],
    knowledge_dir: Path,
) -> list[dict[str, Any]]:
    templates = list(iter_jsonl(knowledge_dir / "validation-templates.jsonl"))
    changed = [fact for fact in facts if fact["changeType"] != "UNCHANGED"]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in changed:
        feature_id = fact.get("feature", {}).get("featureGroupId")
        key = feature_id or (
            f"{fact['object']['module']}::{fact['object']['table']}"
        )
        groups[key].append(fact)
    result: list[dict[str, Any]] = []
    for group_key, group_facts in sorted(groups.items()):
        template = choose_template(templates, group_facts)
        business_name = group_facts[0].get("feature", {}).get("businessName")
        tables = sorted({fact["object"]["table"] for fact in group_facts})
        paths = sorted({
            item.get("path")
            for fact in group_facts
            for item in fact.get("changedPaths") or []
            if item.get("path")
        })[:20]
        change_ids = sorted(fact["changeId"] for fact in group_facts)
        applicability = _applicability(group_facts)
        check_id = _id("CFG-", group_key)
        result.append({
            "validationId": check_id,
            "type": "CONFIGURATION_CHECK",
            "title": f"核对“{business_name}”的配置差异与引用闭环",
            "relatedChangeIds": change_ids,
            "relatedRiskIds": sorted({
                risk_id for fact in group_facts for risk_id in fact.get("riskIds") or []
            }),
            "preconditions": [
                "已保留旧包、新包及本报告中的对象逻辑键和字段前后值。",
                "已取得目标环境只读配置查询权限；未执行迁入时先作为迁入前检查清单。",
            ],
            "steps": [
                f"按模块与逻辑键定位以下配置表：{', '.join(tables[:20])}。",
                (
                    "逐项核对字段级前后值：" + "、".join(paths)
                    if paths else
                    "核对对象是否按报告新增、删除或保持无法确认状态。"
                ),
                "核对直接引用与跨服务 ID 映射是否存在，未知引用单独登记，不按故障关闭。",
                "将核对结果与变化编号逐项回填，并保留查询截图或导出片段。",
            ],
            "expectedResult": "配置对象、字段值和引用关系与新包静态证据一致；无法确认项仍保持待确认。",
            "evidenceToKeep": ["配置查询截图", "对象逻辑键与字段前后值", "ID 映射或未替换报告"],
            "applicability": applicability,
            "evidenceLevel": "OBSERVED",
        })
        test_id = _id("BIZ-", group_key)
        result.append({
            "validationId": test_id,
            "type": "BUSINESS_TEST",
            "title": f"验证“{business_name}”受影响业务路径",
            "relatedChangeIds": change_ids,
            "relatedRiskIds": sorted({
                risk_id for fact in group_facts for risk_id in fact.get("riskIds") or []
            }),
            "preconditions": [
                template["precondition"],
                "目标环境已由人工完成迁入或等价配置部署；本静态分析不代表该步骤已经发生。",
            ],
            "steps": [
                f"使用适用角色从真实入口进入“{business_name}”，先执行正常路径并记录输入。",
                template["steps"],
                "切换到边界权限、空值或异常分支，核对错误提示、数据副作用和回退行为。",
                "保存前后页面截图、关键请求响应、服务日志和受影响数据查询结果。",
            ],
            "expectedResult": template["expected"],
            "evidenceToKeep": template["evidenceToKeep"],
            "applicability": applicability,
            "evidenceLevel": "INFERRED",
        })

    change_by_id = {fact["changeId"]: fact for fact in changed}
    for risk in risks:
        if risk["severity"] not in {"HIGH", "UNKNOWN"}:
            continue
        related_facts = [
            change_by_id[change_id]
            for change_id in risk["affectedChangeIds"]
            if change_id in change_by_id
        ]
        if not related_facts:
            continue
        applicability = _applicability(related_facts)
        validation_id = _id("RSK-", risk["riskId"])
        guidance = [
            item for item in risk.get("verificationGuidance") or []
            if item
        ]
        result.append({
            "validationId": validation_id,
            "type": "RISK_ACCEPTANCE",
            "title": f"验证风险 {risk['riskId']}：{risk['title']}",
            "relatedChangeIds": risk["affectedChangeIds"],
            "relatedRiskIds": [risk["riskId"]],
            "preconditions": [
                "已准备受影响对象的代表数据和目标环境映射。",
                "对 UNKNOWN 风险只验证证据，不预设一定失败。",
            ],
            "steps": (
                guidance[:6]
                + [
                    "执行正常、边界和失败路径，核对是否出现报告所述风险表现。",
                    "保存能证明通过、失败或仍无法确认的截图与日志。",
                ]
            ),
            "expectedResult": (
                "取得足以将 UNKNOWN 更新为已确认或已排除的运行证据。"
                if risk["severity"] == "UNKNOWN"
                else "迁入后的引用、数据行为和失败路径符合新配置，未出现未处理的高风险后果。"
            ),
            "evidenceToKeep": ["运行截图", "服务日志", "请求响应", "数据前后查询", "映射核对结果"],
            "applicability": applicability,
            "evidenceLevel": "INFERRED",
        })
    return sorted(result, key=lambda item: item["validationId"])
