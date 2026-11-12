#!/usr/bin/env python3
"""从 V7 业务对象与分析结果确定性生成 V8 可视化模型。"""

from __future__ import annotations

import hashlib
import heapq
import json
from collections import Counter, defaultdict
from typing import Any


SEVERITY_ORDER = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "UNKNOWN": 3, "HIGH": 4}
ACTIVE_CHANGES = {"ADDED", "REMOVED", "UPDATED", "POSSIBLE_RENAME", "UNMATCHED"}
PATH_LABELS = {
    "record": "配置记录",
    "languageid": "语言",
    "langid": "语言",
    "layout_id.$ref": "所属布局",
    "page_id.$ref": "所属页面",
    "form_id.$ref": "表单绑定",
    "app_id.$ref": "应用绑定",
    "application_id.$ref": "动作流绑定",
    "target_id.$ref": "目标对象绑定",
    "ref_comp_id.$ref": "引用组件",
    "config.fieldUsage": "列表字段与查询配置",
    "config.eventGroup": "点击事件与交互动作",
    "config.flow.nodes": "组件子节点结构",
    "config.flow.parent.$ref": "组件父级",
    "other_properties.secLevel": "安全级别",
    "other_properties.showFormat": "显示格式",
}

CLIENT_MODULE_LABELS = {
    "weaver-ebuilder-form-service": "表单业务配置",
    "weaver-ebuilder-app-service": "页面与应用配置",
    "weaver-esb-setting-service": "动作流业务配置",
    "weaver-cusapp-service": "应用菜单与权限配置",
    "weaver-bpm-service": "审批流程配置",
    "weaver-edcreportd-service": "报表配置",
    "weaver-edcapp-service": "多级填报配置",
    "weaver-ai-application-service": "AI 应用关联配置",
}

CLIENT_TABLE_LABELS = {
    "ebdf_obj": "表单对象",
    "ebdf_button": "表单按钮",
    "ebdf_button_action": "按钮动作",
    "ebdf_button_esb": "按钮动作流绑定",
    "ebdf_button_esb_list": "按钮动作流列表",
    "ebdf_layout_component": "表单布局组件",
    "ebdf_data_association": "表单数据关联",
    "ebdf_permission": "表单权限",
    "ebdd_page": "业务页面",
    "ebdp_page": "业务页面",
    "ebdd_page_layout": "页面布局",
    "ebdd_layout_component": "页面组件",
    "ebdd_page_extended": "页面扩展配置",
    "esb_application": "动作流应用",
    "esb_flow": "动作流节点",
    "esb_flow_action": "动作流动作",
    "esb_formula": "动作流公式",
    "wfp_base": "审批流程",
    "wfp_opt_operator": "审批节点处理人",
    "wfp_opt_groupdt": "审批节点分组",
    "t_cus_app_system_menu": "系统菜单",
    "t_cus_app_tenant_menu": "应用菜单",
    "dataset": "业务数据集",
    "ebda_app": "应用基础配置",
    "ai_app_access_limit": "AI 应用访问限制",
    "ai_app_cross_config": "AI 应用跨模块关联",
    "ai_app_custom_config": "AI 应用自定义配置",
    "ai_app_home_config": "AI 应用首页配置",
    "ai_app_knowledge_config": "AI 应用知识库配置",
    "ai_app_knowlege_config": "AI 应用知识库配置",
    "ai_app_mcp_config": "AI 应用扩展能力配置",
    "ai_app_notice_config": "AI 应用通知配置",
    "ai_app_type": "AI 应用类型配置",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _stable_display(value: Any) -> str:
    """把结构化值转成跨 JSON 读写仍保持一致的显示文本。"""
    if isinstance(value, (dict, list)):
        return _canonical(value)
    return str(value or "")


def _stable_id(prefix: str, *parts: Any) -> str:
    seed = "\x1f".join(_canonical(part) if isinstance(part, (dict, list)) else str(part or "") for part in parts)
    return f"{prefix}-{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:20].upper()}"


def _text(value: Any, limit: int = 500) -> str:
    if value in (None, "", [], {}):
        return "未确认"
    if isinstance(value, (dict, list)):
        value = _canonical(value)
    text = str(value).replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _compact_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str) and len(value) <= 500:
        return value
    encoded = _canonical(value) if isinstance(value, (dict, list)) else str(value)
    if len(encoded) <= 800:
        return value
    return {
        "summary": encoded[:360] + "…",
        "length": len(encoded),
        "sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
    }


def _path_label(path: str) -> str:
    if path in PATH_LABELS:
        return PATH_LABELS[path]
    if path.startswith("show_position."):
        return "按钮显示位置"
    if path.startswith("config."):
        return "组件内部配置"
    if path.endswith(".$ref") or path.endswith("_id"):
        return "对象绑定"
    # 客户可视化不展示底层 JSON 路径；未知路径统一归入业务配置，
    # 完整路径仍由事实层和 business-object-diff 保留。
    return "业务配置"


def _client_impact_label(impact: dict[str, Any]) -> str:
    """把传播结果转成客户可读的业务模块/功能标签。"""

    module = str(impact.get("targetModule") or "").strip()
    table = str(impact.get("targetTable") or "").strip().lower()
    module_label = CLIENT_MODULE_LABELS.get(module, "关联业务模块")
    table_label = CLIENT_TABLE_LABELS.get(table)
    if not table_label:
        table_label = {
            "logic_flow": "页面业务逻辑",
            "custom_browser_info": "数据选择配置",
            "custom_browser_tree": "数据选择层级",
            "auth_role": "功能授权",
            "hrm_matrix": "矩阵权限",
            "browser_data_scope": "数据范围",
            "complex_field": "复杂字段关联",
            "form_style": "表单展示配置",
        }.get(table, "关联业务配置")
    return f"{module_label} · {table_label}"


def _client_risk_title(title: Any) -> str:
    """风险根因在可视化中只保留业务语义，不展示表名、字段名或技术规则码。"""

    text = str(title or "")
    if "包外或跨服务引用" in text:
        return "跨模块或包外业务引用需要确认"
    if "CONFIG_FOREIGN_KEY" in text or "JSON_REFERENCE" in text:
        return "跨环境业务关联需要重新核对"
    if "ID" in text and ("Map" in text or "替换" in text):
        return "迁入后的业务关联映射需要核对"
    return "业务配置关联需要核对"


def _evidence_refs(item: dict[str, Any]) -> list[dict[str, Any]]:
    refs = []
    for evidence in item.get("evidence") or []:
        change_id = str(evidence.get("changeId") or "")
        refs.append({
            "evidenceId": change_id or _stable_id("EVD", evidence),
            "file": "comparison-facts.jsonl.gz",
            "changeId": change_id or None,
            "module": evidence.get("module"),
            "table": evidence.get("table"),
            "recordOrdinal": evidence.get("recordOrdinal"),
        })
    return sorted(refs, key=lambda value: value["evidenceId"])


def _change_ids(item: dict[str, Any]) -> set[str]:
    values = {
        str(evidence.get("changeId"))
        for evidence in item.get("evidence") or []
        if evidence.get("changeId")
    }
    values.update(
        str(change.get("changeId"))
        for change in item.get("internalChanges") or []
        if change.get("changeId")
    )
    return values


def _field_candidates(item: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = []
    for change_index, change in enumerate(item.get("internalChanges") or []):
        fields = change.get("fields") or []
        for field_index, field in enumerate(fields):
            candidates.append({
                "changeId": change.get("changeId"),
                "path": str(field.get("path") or "业务配置"),
                "pathLabel": _path_label(str(field.get("path") or "业务配置")),
                "operation": field.get("operation") or change.get("changeType") or "UPDATED",
                "category": field.get("category") or change.get("kind") or "BUSINESS_CONFIGURATION",
                "before": _compact_value(field.get("before")),
                "after": _compact_value(field.get("after")),
                "sortKey": (change_index, field_index),
            })
        if not fields and change.get("kind") in {
            "FIELD_ADDED", "FIELD_REMOVED", "NODE_SET", "COMPONENT_SET",
            "FORMULA_CHANGE", "MAPPING_CHANGE", "NAME_CHANGED",
            "NODE_POST_VALIDATION_CHANGED",
        }:
            if change.get("kind") == "NODE_POST_VALIDATION_CHANGED":
                before_value = {
                    "ruleCount": change.get("oldRuleCount", 0),
                    "enabledCount": change.get("oldEnabledCount", 0),
                    "effectiveRules": change.get("effectiveBefore") or [],
                }
                after_value = {
                    "ruleCount": change.get("newRuleCount", 0),
                    "enabledCount": change.get("newEnabledCount", 0),
                    "effectiveRules": change.get("effectiveAfter") or [],
                }
            else:
                before_value = change.get("oldCount") if "oldCount" in change else change.get("oldName")
                after_value = change.get("newCount") if "newCount" in change else change.get("newName") or change.get("items")
            candidates.append({
                "changeId": change.get("changeId"),
                "path": str(change.get("kind")),
                "pathLabel": {
                    "FIELD_ADDED": "新增字段",
                    "FIELD_REMOVED": "删除字段",
                    "NODE_SET": "动作节点结构",
                    "COMPONENT_SET": "页面组件结构",
                    "FORMULA_CHANGE": "公式",
                    "MAPPING_CHANGE": "字段映射",
                    "NAME_CHANGED": "名称",
                    "NODE_POST_VALIDATION_CHANGED": f"{change.get('nodeName') or '流程节点'}节点后校验",
                }.get(change.get("kind"), "业务配置"),
                "operation": change.get("kind"),
                "category": "BUSINESS_STRUCTURE",
                "before": _compact_value(before_value),
                "after": _compact_value(after_value),
                "sortKey": (change_index, 0),
            })
    if item.get("changeType") == "UPDATED" and not candidates:
        candidates.append({
            "changeId": None,
            "path": "objectSummary",
            "pathLabel": "对象业务摘要",
            "operation": "UPDATED",
            "category": "BUSINESS_SUMMARY",
            "before": _compact_value(item.get("oldSummary")),
            "after": _compact_value(item.get("newSummary")),
            "sortKey": (0, 0),
        })
    return candidates


def build_visual_diff_model(
    business_diff: dict[str, Any],
    analysis: dict[str, Any],
    impact_groups: list[dict[str, Any]],
) -> dict[str, Any]:
    """只消费 V7 结果层；不重新解析、匹配或计算版本差异。"""
    objects = sorted(
        business_diff.get("objects") or [],
        key=lambda item: (
            str(item.get("packageUnitKey") or item.get("packageUnit") or ""),
            str(item.get("objectType") or ""),
            str(item.get("businessName") or ""),
            str(item.get("logicalKey") or ""),
        ),
    )
    risks = sorted(analysis.get("risks") or [], key=lambda item: str(item.get("riskId") or ""))
    validations = sorted(
        analysis.get("validationPoints") or [],
        key=lambda item: str(item.get("validationId") or ""),
    )
    validation_by_risk: dict[str, list[str]] = defaultdict(list)
    for validation in validations:
        for risk_id in validation.get("relatedRiskIds") or []:
            validation_by_risk[str(risk_id)].append(str(validation.get("validationId")))

    object_records = []
    object_change_ids: dict[str, set[str]] = {}
    change_to_nodes: dict[str, set[str]] = defaultdict(set)
    evidence_references: dict[str, dict[str, Any]] = {}
    field_lineage = []
    impact_records = []
    edges = []
    chains = []

    for item in objects:
        package_unit_key = str(item.get("packageUnitKey") or item.get("packageUnit") or "未分配应用")
        package_unit = _stable_display(item.get("packageUnit") or package_unit_key)
        # 同一逻辑键在“旧版删除 + 新版新增”场景下可能代表两个尚未确认
        # 替代关系的对象；把变化类型纳入节点身份，避免客户图中两项被覆盖。
        node_id = _stable_id(
            "NODE", package_unit_key, item.get("objectType"),
            item.get("logicalKey"), item.get("changeType")
        )
        change_ids = _change_ids(item)
        object_change_ids[node_id] = change_ids
        for change_id in change_ids:
            change_to_nodes[change_id].add(node_id)
        refs = _evidence_refs(item)
        for ref in refs:
            evidence_references[ref["evidenceId"]] = ref
        object_records.append({
            "nodeId": node_id,
            "nodeType": "BUSINESS_OBJECT",
            "objectType": item.get("objectType"),
            "logicalKey": item.get("logicalKey"),
            "packageUnit": package_unit,
            "packageUnitKey": package_unit_key,
            "businessName": item.get("businessName") or item.get("name") or "待确认业务功能",
            "technicalName": item.get("name"),
            "changeType": item.get("changeType"),
            "oldExists": bool(item.get("oldExists")),
            "newExists": bool(item.get("newExists")),
            "oldSummary": _compact_value(item.get("oldSummary")),
            "newSummary": _compact_value(item.get("newSummary")),
            "businessPurpose": item.get("businessPurpose"),
            "userEntry": item.get("userEntry"),
            "confidence": item.get("confidence") or "UNKNOWN",
            "evidenceLevel": "OBSERVED" if refs else "UNKNOWN",
            "evidenceReferences": [ref["evidenceId"] for ref in refs],
            "riskLevel": "NONE",
            "riskIds": [],
            "validationIds": [],
            "affectedFunctions": sorted(set(item.get("affectedFunctions") or [])),
            "searchableText": " ".join(
                str(value or "") for value in (
                    package_unit, item.get("objectType"), item.get("businessName"),
                    item.get("name"), item.get("businessPurpose"), item.get("userEntry"),
                )
            ).lower(),
        })

        candidates = _field_candidates(item)
        max_fields = 16
        selected = candidates[:max_fields]
        field_ids = []
        for index, candidate in enumerate(selected):
            field_id = _stable_id(
                "FIELD", node_id, candidate.get("changeId"), candidate["path"], index,
                candidate.get("before"), candidate.get("after"),
            )
            field_ids.append(field_id)
            field_lineage.append({
                "fieldId": field_id,
                "ownerNodeId": node_id,
                "packageUnit": package_unit,
                "objectType": item.get("objectType"),
                "businessName": item.get("businessName"),
                "technicalField": candidate["path"],
                "fieldName": candidate["pathLabel"],
                "operation": candidate["operation"],
                "category": candidate["category"],
                "before": candidate["before"],
                "after": candidate["after"],
                "directImpacts": sorted(set(item.get("affectedFunctions") or [])),
                "indirectImpacts": [],
                "evidenceLevel": "OBSERVED" if candidate.get("changeId") else "INFERRED",
                "evidenceReferences": ([candidate["changeId"]] if candidate.get("changeId") else [ref["evidenceId"] for ref in refs[:3]]),
                "searchableText": " ".join(str(value or "") for value in (
                    item.get("businessName"), candidate["pathLabel"], candidate["path"],
                    _text(candidate["before"], 120), _text(candidate["after"], 120),
                )).lower(),
            })
            edges.append({
                "edgeId": _stable_id("EDGE", node_id, field_id, "HAS_CHANGED_FIELD"),
                "source": node_id,
                "target": field_id,
                "relationType": "HAS_CHANGED_FIELD",
                "relationLabel": "包含变化字段",
                "direction": "FORWARD",
                "changeType": item.get("changeType"),
                "directOrIndirect": "DIRECT",
                "depth": 1,
                "confidence": item.get("confidence") or "UNKNOWN",
                "evidenceLevel": "OBSERVED" if candidate.get("changeId") else "INFERRED",
                "evidenceReferences": ([candidate["changeId"]] if candidate.get("changeId") else []),
            })
        impact_ids = []
        for label in sorted(set(item.get("affectedFunctions") or [])):
            impact_id = _stable_id("IMPACT", node_id, label, "DIRECT")
            impact_ids.append(impact_id)
            impact_records.append({
                "impactId": impact_id,
                "sourceNodeId": node_id,
                "packageUnit": package_unit,
                "label": label,
                "directOrIndirect": "DIRECT",
                "depth": 1,
                "evidenceLevel": "INFERRED",
            })
            edges.append({
                "edgeId": _stable_id("EDGE", node_id, impact_id, "DIRECT_IMPACT"),
                "source": node_id,
                "target": impact_id,
                "relationType": "DIRECT_IMPACT",
                "relationLabel": "直接影响",
                "direction": "FORWARD",
                "changeType": item.get("changeType"),
                "directOrIndirect": "DIRECT",
                "depth": 1,
                "confidence": item.get("confidence") or "UNKNOWN",
                "evidenceLevel": "INFERRED",
                "evidenceReferences": [ref["evidenceId"] for ref in refs[:3]],
            })

        field_names = [candidate["pathLabel"] for candidate in selected[:4]]
        relation_pending = not bool(item.get("userEntry"))
        chains.append({
            "chainId": _stable_id("CHAIN", node_id),
            "sourceNodeId": node_id,
            "packageUnit": package_unit,
            "businessName": item.get("businessName"),
            "objectType": item.get("objectType"),
            "changeType": item.get("changeType"),
            "evidenceLevel": "UNKNOWN" if relation_pending else "INFERRED",
            "relationPending": relation_pending,
            "changedStage": {
                "ADDED": "新版新增能力",
                "REMOVED": "旧版能力删除",
                "UPDATED": "现有能力调整",
                "POSSIBLE_RENAME": "疑似替代或重命名",
                "UNMATCHED": "关系待确认",
            }.get(item.get("changeType"), "业务能力"),
            "lanes": [
                {"lane": "用户入口", "text": item.get("userEntry") or "关系待确认", "evidenceLevel": "INFERRED" if item.get("userEntry") else "UNKNOWN"},
                {"lane": "页面/表单", "text": item.get("businessName") or "关系待确认", "evidenceLevel": "OBSERVED"},
                {"lane": "动作流/工作流/接口", "text": item.get("businessName") if item.get("objectType") in {"ESB_ACTION_FLOW", "WORKFLOW", "EXTERNAL_INTEGRATION"} else "关联执行关系待确认", "evidenceLevel": "OBSERVED" if item.get("objectType") in {"ESB_ACTION_FLOW", "WORKFLOW", "EXTERNAL_INTEGRATION"} else "UNKNOWN"},
                {"lane": "关键字段或数据变化", "text": "、".join(field_names) if field_names else "未观察到可命名字段变化", "evidenceLevel": "OBSERVED" if field_names else "UNKNOWN"},
                {"lane": "业务结果与后续影响", "text": "、".join(item.get("affectedFunctions") or []) or item.get("businessPurpose") or "影响待确认", "evidenceLevel": "INFERRED" if item.get("affectedFunctions") else "UNKNOWN"},
            ],
            "fieldIds": field_ids,
            "impactIds": impact_ids,
            "riskIds": [],
            "validationIds": [],
            "evidenceReferences": [ref["evidenceId"] for ref in refs],
        })

    node_by_id = {node["nodeId"]: node for node in object_records}
    fields_by_owner: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for field in field_lineage:
        fields_by_owner[field["ownerNodeId"]].append(field)
    for group in sorted(
        impact_groups,
        key=lambda item: (
            str(item.get("sourceModule") or ""),
            str(item.get("sourceTable") or ""),
            str(item.get("impactGroupId") or ""),
        ),
    ):
        source_node_ids = sorted({
            node_id
            for change_id in group.get("changeIds") or []
            for node_id in change_to_nodes.get(str(change_id), set())
        })
        related = list(group.get("directImpacts") or [])[:8]
        related.extend(list(group.get("indirectImpacts") or [])[:12])
        for node_id in source_node_ids:
            node = node_by_id.get(node_id)
            if not node:
                continue
            for impact in related:
                direct = "DIRECT" if impact.get("impactLevel") == "DIRECT" else "INDIRECT"
                depth = int(impact.get("depth") or (1 if direct == "DIRECT" else 2))
                label = _client_impact_label(impact)
                impact_id = _stable_id(
                    "IMPACT", node_id, label, direct, depth, impact.get("relationType")
                )
                impact_records.append({
                    "impactId": impact_id,
                    "sourceNodeId": node_id,
                    "packageUnit": node["packageUnit"],
                    "label": label,
                    "relationType": impact.get("relationType"),
                    "direction": impact.get("direction"),
                    "directOrIndirect": direct,
                    "depth": depth,
                    "evidenceLevel": impact.get("evidenceLevel") or (
                        "OBSERVED" if direct == "DIRECT" else "INFERRED"
                    ),
                })
                edges.append({
                    "edgeId": _stable_id("EDGE", node_id, impact_id, "IMPACT_PATH"),
                    "source": node_id,
                    "target": impact_id,
                    "relationType": impact.get("relationType") or "IMPACT_PATH",
                    "relationLabel": "直接影响" if direct == "DIRECT" else f"{depth} 层间接影响",
                    "direction": impact.get("direction") or "FORWARD",
                    "changeType": node.get("changeType"),
                    "directOrIndirect": direct,
                    "depth": depth,
                    "confidence": "HIGH" if direct == "DIRECT" else "MEDIUM",
                    "evidenceLevel": impact.get("evidenceLevel") or (
                        "OBSERVED" if direct == "DIRECT" else "INFERRED"
                    ),
                    "evidenceReferences": list(impact.get("edgePath") or []),
                })
                if direct == "INDIRECT":
                    for field in fields_by_owner.get(node_id, []):
                        if label not in field["indirectImpacts"]:
                            field["indirectImpacts"].append(label)
    for field in field_lineage:
        field["indirectImpacts"] = sorted(field["indirectImpacts"])[:20]

    risk_records = []
    risk_by_id = {}
    for risk in risks:
        risk_id = str(risk.get("riskId") or _stable_id("RISK", risk))
        validation_ids = sorted(set(validation_by_risk.get(risk_id) or []))
        affected_change_ids = sorted(set(str(value) for value in risk.get("affectedChangeIds") or []))
        affected_node_ids = sorted({
            node_id for change_id in affected_change_ids for node_id in change_to_nodes.get(change_id, set())
        })
        record = {
            "riskId": risk_id,
            "nodeId": _stable_id("RISKNODE", risk_id),
            "severity": risk.get("severity") or "UNKNOWN",
            "title": _client_risk_title(risk.get("title")),
            "riskType": risk.get("riskType"),
            "evidenceLevel": risk.get("evidenceLevel") or "UNKNOWN",
            "uncertaintyStatement": (
                risk.get("uncertaintyStatement")
                or (
                    "证据不足，需通过验证确认；UNKNOWN 不表示已经发生故障。"
                    if (risk.get("severity") or "UNKNOWN") == "UNKNOWN"
                    else None
                )
            ),
            "affectedNodeIds": affected_node_ids,
            "affectedChangeIds": affected_change_ids[:24],
            "affectedChangeCount": len(affected_change_ids),
            "validationIds": validation_ids,
            "triggerEvidence": _compact_value(risk.get("triggerEvidence")),
            "verificationGuidance": (risk.get("verificationGuidance") or [])[:6],
            "searchableText": " ".join(str(value or "") for value in (
                risk_id, risk.get("severity"), risk.get("title"), risk.get("riskType"),
            )).lower(),
        }
        risk_records.append(record)
        risk_by_id[risk_id] = record
        for node_id in affected_node_ids:
            edges.append({
                "edgeId": _stable_id("EDGE", node_id, record["nodeId"], "HAS_RISK"),
                "source": node_id,
                "target": record["nodeId"],
                "relationType": "HAS_RISK",
                "relationLabel": "关联风险",
                "direction": "FORWARD",
                "changeType": "UPDATED",
                "directOrIndirect": "DIRECT",
                "depth": 1,
                "confidence": "HIGH" if record["evidenceLevel"] == "OBSERVED" else "MEDIUM",
                "evidenceLevel": record["evidenceLevel"],
                "evidenceReferences": affected_change_ids[:8],
            })

    validation_records = []
    for validation in validations:
        validation_id = str(validation.get("validationId") or _stable_id("VAL", validation))
        record = {
            "validationId": validation_id,
            "nodeId": _stable_id("VALNODE", validation_id),
            "title": validation.get("title") or "业务验证场景",
            "type": validation.get("type"),
            "evidenceLevel": validation.get("evidenceLevel") or "INFERRED",
            "relatedRiskIds": sorted(set(validation.get("relatedRiskIds") or [])),
            "relatedChangeIds": sorted(set(validation.get("relatedChangeIds") or []))[:24],
            "steps": (validation.get("steps") or [])[:8],
            "expectedResult": validation.get("expectedResult"),
            "evidenceToKeep": (validation.get("evidenceToKeep") or [])[:8],
            "applicability": validation.get("applicability") or {},
            "searchableText": " ".join(str(value or "") for value in (
                validation_id, validation.get("title"), validation.get("expectedResult"),
            )).lower(),
        }
        validation_records.append(record)
        for risk_id in record["relatedRiskIds"]:
            if risk_id in risk_by_id:
                edges.append({
                    "edgeId": _stable_id("EDGE", risk_by_id[risk_id]["nodeId"], record["nodeId"], "VERIFIED_BY"),
                    "source": risk_by_id[risk_id]["nodeId"],
                    "target": record["nodeId"],
                    "relationType": "VERIFIED_BY",
                    "relationLabel": "通过场景验证",
                    "direction": "FORWARD",
                    "changeType": "UPDATED",
                    "directOrIndirect": "DIRECT",
                    "depth": 1,
                    "confidence": "HIGH",
                    "evidenceLevel": record["evidenceLevel"],
                    "evidenceReferences": record["relatedChangeIds"][:8],
                })

    chain_by_node = {chain["sourceNodeId"]: chain for chain in chains}
    for risk in risk_records:
        for node_id in risk["affectedNodeIds"]:
            node = node_by_id[node_id]
            node["riskIds"].append(risk["riskId"])
            node["validationIds"].extend(risk["validationIds"])
            if SEVERITY_ORDER.get(risk["severity"], 3) > SEVERITY_ORDER.get(node["riskLevel"], 0):
                node["riskLevel"] = risk["severity"]
            chain = chain_by_node[node_id]
            chain["riskIds"].append(risk["riskId"])
            chain["validationIds"].extend(risk["validationIds"])
    for node in object_records:
        node["riskIds"] = sorted(set(node["riskIds"]))
        node["validationIds"] = sorted(set(node["validationIds"]))
    for chain in chains:
        chain["riskIds"] = sorted(set(chain["riskIds"]))
        chain["validationIds"] = sorted(set(chain["validationIds"]))

    unknowns = analysis.get("unknownItems") or []
    unknown_by_reason = Counter(str(item.get("reason") or "未说明原因") for item in unknowns)
    unknown_by_module = Counter(str(item.get("module") or "未确认模块") for item in unknowns)
    unknown_samples = heapq.nsmallest(
        200,
        (
            {
                "changeId": item.get("changeId"),
                "module": item.get("module"),
                "table": item.get("table"),
                "reason": item.get("reason"),
            }
            for item in unknowns
        ),
        key=lambda item: (
            str(item.get("module") or ""), str(item.get("table") or ""),
            str(item.get("reason") or ""), str(item.get("changeId") or ""),
        ),
    )

    risk_counts = Counter(str(item.get("severity") or "UNKNOWN") for item in risk_records)
    change_counts = Counter(str(item.get("changeType") or "UNMATCHED") for item in object_records)
    direction = analysis.get("analysisDirection") or {}
    packages = {"old": direction.get("old") or {}, "new": direction.get("new") or {}}
    source_fingerprint = hashlib.sha256(
        _canonical({
            "businessObjectSummary": business_diff.get("summary") or [],
            "objects": [
                {"logicalKey": item.get("logicalKey"), "changeType": item.get("changeType"), "oldSummary": item.get("oldSummary"), "newSummary": item.get("newSummary")}
                for item in objects
            ],
            "factLayerSha256": analysis.get("factLayerSha256"),
        }).encode("utf-8")
    ).hexdigest()

    edge_index = {item["edgeId"]: item for item in edges}
    impact_index = {item["impactId"]: item for item in impact_records}
    model = {
        "schemaVersion": "ebuilder-visual-diff-model/v1.0",
        "application": {"name": business_diff.get("applicationName") or "eBuilder 应用"},
        "packages": packages,
        "directionResolution": {
            key: value for key, value in direction.items()
            if key not in {"old", "new"}
        },
        "summary": {
            "businessObjects": business_diff.get("summary") or [],
            "changeTypes": {key: change_counts.get(key, 0) for key in ("ADDED", "REMOVED", "UPDATED", "POSSIBLE_RENAME", "UNMATCHED", "UNCHANGED")},
            "riskLevels": {key: risk_counts.get(key, 0) for key in ("HIGH", "MEDIUM", "LOW", "UNKNOWN")},
            "validationScenarios": len(business_diff.get("testScenarios") or []),
            "technicalValidationPoints": len(validation_records),
            "businessFeatureChanges": len(analysis.get("featureChanges") or []),
        },
        "packageUnits": business_diff.get("packageUnits") or [],
        "packageUnitSummary": business_diff.get("packageUnitSummary") or [],
        "nodes": sorted(object_records, key=lambda item: item["nodeId"]),
        "edges": sorted(edge_index.values(), key=lambda item: item["edgeId"]),
        "businessChains": sorted(chains, key=lambda item: item["chainId"]),
        "fieldLineage": sorted(field_lineage, key=lambda item: item["fieldId"]),
        "impacts": sorted(impact_index.values(), key=lambda item: item["impactId"]),
        "risks": risk_records,
        "validations": validation_records,
        "unknownItems": {
            "total": len(unknowns),
            "byReason": dict(sorted(unknown_by_reason.items())),
            "byModule": dict(sorted(unknown_by_module.items())),
            "samples": unknown_samples,
            "sampleLimit": 200,
            "statement": "仅展示确定性排序后的代表样本；完整未确认项见无法确认项.jsonl.gz。",
        },
        "evidenceReferences": sorted(evidence_references.values(), key=lambda item: item["evidenceId"]),
        "generationMetadata": {
            "generator": "build_visual_diff_model.py",
            "generatorVersion": "1.0",
            "deterministic": True,
            "stableIdentityAlgorithm": "SHA-256 canonical seed, first 20 hex",
            "currentTimeUsedForIdentityOrOrdering": False,
            "sourceBusinessObjectSchema": business_diff.get("schemaVersion"),
            "sourceAnalysisSchema": analysis.get("schemaVersion"),
            "sourceFactLayerSha256": analysis.get("factLayerSha256"),
            "sourceFingerprint": source_fingerprint,
            "fieldDetailsPerObjectLimit": 16,
            "unknownSampleLimit": 200,
            "largeDataPolicy": "模型保留全部变化业务对象；HTML 首屏最多展开 80 项并支持筛选后局部展开。",
        },
    }
    return model
