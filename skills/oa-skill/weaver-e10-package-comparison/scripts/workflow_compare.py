#!/usr/bin/env python3
"""Build Workflow IR and compare two workflow migration packages."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from workflow_sql_datasource import (
    analyze_workflow_sql_dataset,
    pair_workflow_sql_summaries,
)


ID_FIELDS = {
    "id", "workflowid", "workflow_id", "fixed_version_id", "activewfid",
    "nodeid", "node_id", "srcnodeid", "destnodeid", "conditionkey",
    "groupid", "groupdetailid", "foreign_key", "parent_id", "versionid",
    "objid", "sourceid", "targetid", "source_field", "target_field",
    "adjacent_multi_key", "back_handle_forecast_node",
}
NOISE_FIELDS = {
    "tenant_key", "create_time", "update_time", "creator", "updater",
    "modifier", "operator", "source_id", "import_id", "eid", "lastchangeid",
}
WORKFLOW_PREFIXES = ("wfp_", "wfpf_", "wfr_", "wf_multi_")
EXTRA_TABLES = {"browser_data_scope", "ebdf_app_ref_workflow", "dataset"}
FORM_TABLES = {
    "form", "form_field", "form_layout_multiple", "form_layout_version",
    "ebdd_page_extended", "ebdd_page_layout", "ebdd_layout_component",
    "form_view_relate_config", "field_permission", "form_table_field",
    "form_view_linkage", "form_view_linkage_detail", "form_condition",
    "form_condition_detail", "fd_effect", "fd_effect_value",
    "fd_linkage", "fd_linkage_ext", "fd_linkage_monitor_action",
    "fd_linkage_monitor_field", "fd_linkage_source",
    "fd_linkage_source_config", "fd_linkage_source_config_col",
    "fd_linkage_source_config_table", "fd_linkage_source_esb",
    "fd_linkage_source_excel", "fd_linkage_source_mapping",
    "fd_linkage_source_sql", "fd_linkage_source_sql_column",
    "express_formula", "custom_func",
}
INTEGRATION_TABLES = {
    "esb_application", "esb_flow_action", "esb_component_http",
    "esb_resource", "esb_rest_resource", "esb_interface_base",
}
LIST_TABLE_PREFIXES = ("ebdf_list",)
DERIVED_WORKFLOW_TABLES = {
    "wfp_chart", "wfp_chart_node", "wfp_chart_link",
    "wfp_multilang_nodelink", "wfp_multilang_wfbase", "wfp_multilangset",
    "wfp_node_menu", "wfp_sysfield_permission", "wfp_node_form_relate",
    "wfp_dellog",
}
TITLE_PART_LABELS = {
    "txtusertitle": "流程名称", "subtype": "分部", "depmarttype": "部门",
    "resourcetype": "发起人姓名", "txtuseryear": "年", "txtusermouth": "月",
    "txtuserdate": "日",
}

CONDITION_OPERATOR_LABELS = {
    "NULL": "为空", "NOT_NULL": "不为空", "EQ": "等于", "NE": "不等于",
    "GT": "大于", "GE": "大于等于", "LT": "小于", "LE": "小于等于",
    "CONTAINS": "包含", "NOT_CONTAINS": "不包含",
}
LINKAGE_PROPERTY_LABELS = {
    "hide": "隐藏", "show": "显示", "readonly": "设为只读",
    "read_only": "设为只读", "required": "设为必填", "disable": "禁用",
    "enable": "启用",
}

CATEGORIES = {
    "wfp_base": "流程定义与版本",
    "wfp_node": "流程节点",
    "wfp_link": "节点连线与出口",
    "wfr_conditionbase": "流转条件",
    "wfr_mapbase": "流转条件",
    "wfr_maplist": "流转条件",
    "wfr_expressionbase": "条件表达式",
    "wfr_expressions": "条件表达式",
    "wfr_valuebase": "条件取值",
    "wfr_valuemap": "条件取值",
    "wfp_opt_group": "节点操作者组",
    "wfp_opt_groupdt": "节点操作者规则",
    "wfp_opt_operator": "节点操作者",
    "wfp_opt_create": "发起人设置",
    "wfp_node_menu": "节点操作菜单",
    "wfp_custommenu_action": "节点自定义操作",
    "wfp_add_action": "节点附加动作",
    "wfp_subset": "子流程设置",
    "wfp_subsetdetail": "子流程触发规则",
    "wfp_relateform": "关联表单",
    "wfp_node_form_relate": "节点表单绑定",
    "wfp_sysfield_permission": "系统字段权限",
    "wfp_field_mapping": "流程字段映射",
    "wfp_variables": "流程变量与表单引用",
    "wfp_context": "流程上下文",
    "wfp_auth": "流程权限",
    "wfp_share_config": "流程共享范围",
    "wfp_resourceshare_config": "流程资源共享",
    "wfp_remind_config": "流程提醒",
    "wfp_overtime": "流程超时处理",
    "wfp_reject_reason_set": "退回原因设置",
    "wfp_stage_set": "流程阶段",
    "wfp_deftitle_format_config": "流程标题规则",
    "wfp_title_config": "流程标题规则",
    "wfp_print_template": "流程打印模板",
    "wfp_outerwfset": "外部流程触发",
    "wfp_action_flow_map": "动作流绑定",
    "wfp_auto_approve": "自动审批与后置处理",
    "wfp_opt_matrix": "节点操作者矩阵",
    "wfp_opt_matrixrule": "节点操作者矩阵",
    "wf_multi_org_dt": "多组织适用范围",
    "wfp_relatematter_set": "关联事项显示设置",
    "wfp_markset": "流程编号规则",
    "wfp_markdef": "流程编号规则",
    "wfp_markfield": "流程编号规则",
    "browser_data_scope": "浏览数据范围",
    "ebdf_app_ref_workflow": "应用与流程绑定",
    "esb_rest_resource": "外部接口服务",
    "dataset": "工作流 SQL 数据源",
}

SUMMARY_FIELDS = {
    "wfp_base": ("workflowname", "workflowdesc", "status", "bridge_service", "module"),
    "wfp_node": ("nodename", "nodetype", "nodeattr", "orderid", "is_died", "delete_type"),
    "wfp_link": ("linkname", "isdefault", "isreject", "ismustpass", "orderid"),
    "wfp_opt_group": ("groupname", "sourcetype", "datasrc", "mustreview", "delete_type"),
    "wfp_node_menu": ("menutype", "title", "orderid", "useable", "istop", "feedback_control", "default_sign", "delete_type"),
    "wfp_add_action": ("action_name", "actionname", "name", "action_type", "orderid", "delete_type"),
    "wfp_subsetdetail": ("subWfId", "subwfid", "sub_wf_id", "triNodeId", "trinodeid", "delete_type"),
    "wfp_relateform": ("relatetype", "formid", "form_id", "delete_type"),
    "wfp_field_mapping": ("source", "actual_value", "custom_value", "is_merge", "delete_type"),
    "wfp_node_form_relate": ("enable_node_permission", "m_layout_mode", "strong_related", "allow_modify", "scaling", "delete_type"),
    "wfp_sysfield_permission": ("field_type", "isview", "isedit", "ismandatory", "scene", "orderid", "delete_type"),
    "wfr_conditionbase": ("conditionname", "conditioncn", "conditiondesc", "source", "module", "orders", "delete_type"),
    "wfr_expressionbase": ("compareoption1", "compareoption2", "detailoption", "containtype", "typehrm", "delete_type"),
    "wfr_expressions": ("relation", "isroot", "delete_type"),
    "wfr_maplist": ("orderid", "delete_type"),
    "wfr_valuebase": ("valuetext", "browsertype", "total", "valueoption", "valuetype", "delete_type"),
    "wfr_valuemap": ("valuecount", "delete_type"),
    "wfp_opt_operator": ("type", "orders", "delete_type"),
    "wfp_opt_matrix": ("targetscope", "delete_type"),
    "wfp_opt_matrixrule": ("type", "target_name", "target_type", "source_name", "source_type", "operate", "virtualid", "is_field_empty", "delete_type"),
    "wfp_auto_approve": ("allow_handle_user", "adjacent_options", "back_handle_cfg", "follow_up_type", "follow_up_commit", "follow_up_check", "follow_up_options", "hand_way", "compensate_tip", "sign_mark", "sign_content", "auto_handle", "delete_type"),
    "wfp_relatematter_set": ("enable_custom", "allow_related_matter", "web_print_show", "related_range_type", "related_matter_readonly", "delete_type"),
    "wfp_markset": ("is_use", "is_multimark", "repeatcheck", "regenerate", "contentchange", "delcodereserve", "delete_type"),
    "wfp_markdef": ("isuse", "disableinput", "ismaincode", "triggertype", "workflowseqalone", "startsequenceidtype", "delete_type"),
    "wfp_markfield": ("markfieldtype", "position", "seqalone", "caneditalone", "year_format", "delete_type"),
    "wf_multi_org_dt": ("opt_type", "orderid", "opt_value", "delete_type"),
    "form_field": ("title", "component_key", "component_type", "required", "data_type", "browser_type", "show_order", "is_delete", "delete_type"),
    "ebdd_page_layout": ("terminal_type", "virtual_layout", "config", "delete_type"),
}

CUSTOMER_BUSINESS_CATEGORIES = {
    "流转条件", "条件表达式", "条件取值", "节点操作者组", "节点操作者规则",
    "节点操作者", "发起人设置", "节点自定义操作", "节点附加动作",
    "子流程设置", "子流程触发规则", "关联表单", "流程字段映射",
    "流程变量与表单引用", "流程权限", "流程共享范围", "流程资源共享",
    "流程提醒", "流程超时处理", "退回原因设置", "流程阶段", "流程标题规则",
    "流程打印模板", "外部流程触发", "动作流绑定", "浏览数据范围",
    "应用与流程绑定", "系统字段权限", "节点表单绑定",
    "自动审批与后置处理", "节点操作者矩阵", "多组织适用范围",
    "关联事项显示设置",
    "流程编号规则",
    "外部接口服务",
    "工作流 SQL 数据源",
}
AUTO_NODE_DEFAULT_CATEGORIES = {"系统字段权限", "节点表单绑定"}


def sid(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def clean_text(value: Any, fallback: str = "") -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = re.sub(r"(?<!\d)\d{16,}(?!\d)", "", text)
    text = re.sub(r"[-_:：/\s]+$", "", text).strip()
    return text or fallback


def active_row(row: dict[str, Any]) -> bool:
    return str(row.get("delete_type", row.get("is_delete", "0"))).lower() not in {"1", "true"}


def clean_action_name(value: Any) -> str:
    text = clean_text(value, "流程动作")
    text = text.replace("//##split##//", "")
    return re.sub(r"-R\(20\d{2}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\)$", "", text).strip()


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def canonical(value: Any, key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {
            str(k): canonical(v, str(k))
            for k, v in sorted(value.items())
            if str(k).lower() not in NOISE_FIELDS
            and str(k).lower() not in ID_FIELDS
            and not str(k).lower().endswith("_id")
        }
    if isinstance(value, list):
        rows = [canonical(item, key) for item in value]
        return sorted(rows, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True))
    if isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r"\d{16,}", text):
            return "[关联对象]"
        return re.sub(r"(?<!\d)\d{16,}(?!\d)", "[关联对象]", text)
    if isinstance(value, int) and not isinstance(value, bool) and len(str(abs(value))) >= 16:
        return "[关联对象]"
    return value


def json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
    return {}


def optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "yes"}:
        return True
    if text in {"0", "false", "no"}:
        return False
    return None


def iter_records(ir: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for service, module in (ir.get("modules") or {}).items():
        for table, payload in (module.get("tables") or {}).items():
            sources = payload.get("recordSources") or []
            for index, row in enumerate(payload.get("records") or []):
                source = sources[index] if index < len(sources) else {}
                yield {
                    "service": service,
                    "table": str(table).lower(),
                    "row": row,
                    "unit": source.get("packageUnit"),
                    "recordKey": f"{service}|{str(table).lower()}|{index}",
                }


def lineage_map(ir: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    lineage = ir.get("migrationLineage") or {}
    for key in ("applicationAliases", "submoduleAliases"):
        for item in lineage.get(key) or []:
            current, source = sid(item.get("currentId")), sid(item.get("sourceId"))
            if current and source:
                result[current] = source
    return result


def idm_record_lineage(
    ir: dict[str, Any], records: list[dict[str, Any]], table: str
) -> dict[str, dict[str, Any]]:
    """Resolve unique KEYS_*.idm lineage for concrete current records."""
    aliases = lineage_map(ir)
    lookup: dict[tuple[str, str, str, str], list[str]] = defaultdict(list)
    record_by_key = {item["recordKey"]: item for item in records}
    for item in records:
        if item["table"] != table:
            continue
        current = sid(item["row"].get("id"))
        if current:
            lookup[(
                item.get("unitKey") or "__single__",
                item["service"].lower(), table.lower(), current,
            )].append(item["recordKey"])
    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for mapping in (ir.get("migrationLineage") or {}).get("idmMappings", []):
        if str(mapping.get("tableName") or "").lower() != table.lower():
            continue
        unit = mapping.get("packageUnit") or {}
        mapped_unit = unit_key(unit if unit else None, aliases)
        service = str(mapping.get("serviceName") or "").lower()
        source = sid(mapping.get("sourceId"))
        import_id, export_id = sid(mapping.get("importId")), sid(mapping.get("exportId"))
        import_hits = lookup.get((mapped_unit, service, table.lower(), import_id), []) if import_id else []
        export_hits = lookup.get((mapped_unit, service, table.lower(), export_id), []) if export_id else []
        if len(import_hits) > 1 or len(export_hits) > 1:
            continue
        if import_hits and export_hits and import_hits[0] != export_hits[0]:
            continue
        hit = (import_hits or export_hits)
        if hit and source:
            candidates[hit[0]].append(mapping)
    result = {}
    for record_key, items in candidates.items():
        sources = {sid(item.get("sourceId")) for item in items}
        if len(sources) != 1 or record_key not in record_by_key:
            continue
        source = next(iter(sources))
        scoped = (
            f"{record_by_key[record_key].get('unitKey')}|"
            f"{record_by_key[record_key]['service'].lower()}|{table.lower()}|{source}"
        )
        key_hash = hashlib.sha256(scoped.encode("utf-8")).hexdigest()[:24]
        result[record_key] = {
            "identityMethod": "MIGRATION_IDM_SOURCE_ID",
            "lineageKeyHash": key_hash,
            "stableToken": key_hash.translate(
                str.maketrans("0123456789abcdef", "ghijklmnopqrstuv")
            ),
            "lineageEvidencePath": sorted({
                str(item.get("evidencePath")) for item in items
                if item.get("evidencePath")
            })[0],
        }
    return result


def unit_key(unit: dict[str, Any] | None, aliases: dict[str, str]) -> str:
    if not unit:
        return "__single__"
    current = sid(unit.get("id")) or "__single__"
    return "source:" + aliases.get(current, current)


def load_config_semantics(knowledge: Path) -> tuple[dict[str, str], list[dict[str, str]]]:
    descriptions: dict[str, str] = {}
    relations: list[dict[str, str]] = []
    path = knowledge / "config-nodes.jsonl"
    if not path.is_file():
        return descriptions, relations
    relation_re = re.compile(r"([A-Za-z0-9_]+)\s*=\s*\$([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\$")
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        services = {str(x) for x in item.get("services") or []}
        table = str(item.get("table") or "").lower()
        if "weaver-workflow-pathdef-service" not in services and not table.startswith(WORKFLOW_PREFIXES):
            continue
        if item.get("description") and table not in descriptions:
            descriptions[table] = clean_text(item["description"], "流程配置")
        for field in ("foreignKey", "extraChainRelations"):
            for child_field, parent_table, parent_field in relation_re.findall(str(item.get(field) or "")):
                relations.append({
                    "childTable": table,
                    "childField": child_field,
                    "parentTable": parent_table.lower(),
                    "parentField": parent_field,
                })
    unique = {(x["childTable"], x["childField"], x["parentTable"], x["parentField"]): x for x in relations}
    return descriptions, list(unique.values())


def _row_name(table: str, row: dict[str, Any]) -> str:
    for key in (
        "workflowname", "nodename", "linkname", "groupname", "conditionname", "conditioncn",
        "action_name", "actionname", "menuname", "menu_name", "name", "title",
        "shortname",
    ):
        if row.get(key) not in (None, ""):
            if key in {"action_name", "actionname"}:
                return clean_action_name(row[key])
            return clean_text(row[key], "流程配置")
    return CATEGORIES.get(table, "流程配置")


def _summary(table: str, row: dict[str, Any]) -> dict[str, Any]:
    fields = SUMMARY_FIELDS.get(table)
    if fields:
        result = {key: canonical(row.get(key), key) for key in fields if row.get(key) not in (None, "")}
        for key in ("action_name", "actionname", "name"):
            if key in result:
                result[key] = clean_action_name(result[key])
        if table == "wf_multi_org_dt":
            result = {"opt_type": row.get("opt_type"), "orderid": row.get("orderid"), "delete_type": row.get("delete_type", 0)}
            value = row.get("opt_value")
            if value not in (None, "") and not re.fullmatch(r"\d{16,}", str(value)):
                result["opt_value"] = value
        return result
    return canonical(row)


def customized_menu(row: dict[str, Any]) -> bool:
    """Identify customer-configured menu semantics, excluding generated defaults."""
    return bool(
        str(row.get("menutype") or "").lower() == "custom"
        or str(row.get("title") or "").strip()
        or str(row.get("default_sign") or "").strip()
    )


MENU_LABELS = {
    "submit": "提交", "take_back": "收回", "reject": "退回", "forward": "转发",
    "consult": "征询", "circulate": "传阅", "save": "保存", "custom": "自定义操作",
}


def _menu_model(row: dict[str, Any], node_names: dict[str | None, str]) -> dict[str, Any]:
    menu_type = str(row.get("menutype") or "节点操作")
    title = clean_text(row.get("title") or row.get("default_sign") or "")
    label = title or MENU_LABELS.get(menu_type.lower(), "节点操作")
    node = node_names.get(sid(row.get("nodeid")), "未识别节点")
    return {
        "node": node,
        "name": f"{node}：{label}",
        "type": menu_type,
        "title": title,
        "enabled": str(row.get("useable", "1")) not in {"0", "false", "False"},
        "top": str(row.get("istop", "0")) in {"1", "true", "True"},
        "feedback": row.get("feedback_control"),
        "customized": customized_menu(row),
    }


def _rows(records: list[dict[str, Any]], table: str) -> list[dict[str, Any]]:
    return [item for item in records if item["table"] == table]


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _layout_component_model(row: dict[str, Any], field_names: dict[str, str]) -> dict[str, Any]:
    config = _json_object(row.get("config"))
    component_type = str(config.get("type") or row.get("type") or "布局组件")
    field_id = sid(config.get("fieldId") or config.get("associatedId"))
    title = clean_text(config.get("title") or config.get("name") or "")
    labels = {
        "ColumnTwo": "一行两列", "ColumnThree": "一行三列",
        "ColumnFour": "一行四列", "InternalContainer": "布局列容器",
    }
    name = field_names.get(field_id) or title or labels.get(component_type, "表单组件")
    return {
        "name": name,
        "type": component_type,
        "structure": labels.get(component_type, title or "表单组件"),
        "field": field_names.get(field_id),
        "readOnly": bool(config.get("readOnly")),
        "required": bool(config.get("required")),
        "hidden": bool((config.get("layout") or {}).get("hidden")),
    }


def _layout_name_map(
    multiples: list[dict[str, Any]],
    versions: list[dict[str, Any]],
    extended: list[dict[str, Any]],
    page_layouts: list[dict[str, Any]],
) -> dict[str, str]:
    def business_layout_name(value: Any) -> str:
        name = clean_text(value, "未命名布局")
        name = re.sub(r"(?i)MOBILE\d+$", "（移动端）", name)
        name = re.sub(r"(?i)(?:APP|H5)\d+$", "（移动端）", name)
        name = re.sub(r"(?i)PC\d+$", "（PC端）", name)
        return name

    version_to_name = {
        sid(item["row"].get("version_id")): business_layout_name(item["row"].get("name"))
        for item in multiples
    }
    version_to_name.update({
        sid(item["row"].get("id")): business_layout_name(item["row"].get("name"))
        for item in versions
    })
    extended_to_name = {
        sid(item["row"].get("id")): version_to_name.get(sid(item["row"].get("page_id")), "未命名布局")
        for item in extended
    }
    return {
        sid(item["row"].get("id")): extended_to_name.get(sid(item["row"].get("page_id")), "未命名布局")
        for item in page_layouts
    }


def _title_rule(rows: list[dict[str, Any]]) -> dict[str, Any]:
    parts: list[str] = []
    for item in sorted(rows, key=lambda x: (float(x["row"].get("sort") or 0), x["recordKey"])):
        row = item["row"]
        key = str(row.get("content_name") or "")
        value = str(row.get("content_value") or "")
        if key == "txtname":
            literal = re.sub(r"(?<!\d)\d{16,}(?!\d)", "", value).strip()
            if literal:
                parts.append(literal)
        elif key in {"txtusertitle", "txtuseryear", "txtusermouth", "txtuserdate"}:
            if value.lower() == "true":
                parts.append(TITLE_PART_LABELS[key])
        elif key in {"subtype", "depmarttype", "resourcetype"} and value not in {"", "0"}:
            parts.append(TITLE_PART_LABELS[key])
    return {"configured": bool(rows), "parts": parts, "display": "".join(parts) or "未配置"}


def _business_formula(value: Any) -> str:
    text = clean_text(value, "计算规则待确认")
    text = text.replace("{", "").replace("}", "")
    text = text.replace("*", " × ").replace("/", " ÷ ")
    text = re.sub(r"\s*=\s*", " = ", text)
    return re.sub(r"\s+", " ", text).strip()


def _effect_scope(
    root_id: str | None,
    effects: list[dict[str, Any]],
    effect_values: list[dict[str, Any]],
) -> list[str]:
    roots = [item for item in effects if sid(item["row"].get("ref_id")) == root_id]
    values_by_effect: dict[str | None, list[str]] = defaultdict(list)
    for item in effect_values:
        name = re.sub(r"【V\d+(?:\.\d+)*】$", "", clean_text(item["row"].get("effect_name")))
        if name:
            values_by_effect[sid(item["row"].get("effect_id"))].append(name)
    scopes: list[str] = []
    for item in roots:
        row = item["row"]
        effect_id = sid(row.get("id"))
        effect_name = clean_text(row.get("effect_name"))
        if effect_name == "当前工作流" or str(row.get("effect_type") or "").lower() == "workflow":
            scopes.append("当前工作流")
        else:
            scopes.extend(values_by_effect.get(effect_id) or ([effect_name] if effect_name else []))
    return sorted(set(scopes))


def _linkage_scope_text(scopes: list[str]) -> str:
    return "、".join(scopes) if scopes else "当前表单"


def build_workflow_linkage_model(
    form_ids: set[str | None],
    records: list[dict[str, Any]],
    field_names: dict[str | None, str],
) -> dict[str, Any]:
    """Restore customer-facing attribute, field and formula linkage semantics."""
    active = lambda table: [
        item for item in _rows(records, table) if active_row(item["row"])
    ]
    conditions = {sid(item["row"].get("id")): item for item in active("form_condition")}
    condition_details: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
    for item in active("form_condition_detail"):
        condition_details[sid(item["row"].get("condition_id"))].append(item)
    view_details: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
    for item in active("form_view_linkage_detail"):
        view_details[sid(item["row"].get("ref_linkage_id"))].append(item)
    effects, effect_values = active("fd_effect"), active("fd_effect_value")

    selected_rows: list[dict[str, Any]] = []
    attribute_linkages: list[dict[str, Any]] = []
    for root in active("form_view_linkage"):
        row = root["row"]
        if sid(row.get("form_id")) not in form_ids:
            continue
        root_id = sid(row.get("id"))
        condition = conditions.get(sid(row.get("condition_id")))
        details = condition_details.get(sid(row.get("condition_id"))) or []
        condition_phrases = []
        for detail in details:
            detail_row = detail["row"]
            field = field_names.get(sid(detail_row.get("target_id")), "业务字段")
            operator = CONDITION_OPERATOR_LABELS.get(
                str(detail_row.get("detail_symbol") or "").upper(), "满足设定条件"
            )
            source = clean_text(detail_row.get("source_content"))
            phrase = f"“{field}”{operator}"
            if source and operator not in {"为空", "不为空", "满足设定条件"}:
                phrase += f"“{source}”"
            condition_phrases.append(phrase)
        target_phrases = []
        targets = view_details.get(root_id) or []
        for detail in targets:
            detail_row = detail["row"]
            field = field_names.get(sid(detail_row.get("linkage_value")), "业务字段")
            prop = LINKAGE_PROPERTY_LABELS.get(
                str(detail_row.get("linkage_prop") or "").lower(), "调整显示属性"
            )
            target_phrases.append(f"{prop}“{field}”")
        scopes = _effect_scope(root_id, effects, effect_values)
        condition_text = "且".join(condition_phrases) or "满足设定条件"
        target_text = "、".join(target_phrases) or "调整表单显示属性"
        description = f"当{condition_text}时，{target_text}；适用范围：{_linkage_scope_text(scopes)}"
        name = clean_text(row.get("linkage_name")) or description
        attribute_linkages.append({
            "name": name,
            "description": description,
            "enabled": str(row.get("enable_state", "1")) not in {"0", "false", "False"},
            "conditions": sorted(condition_phrases),
            "effects": sorted(target_phrases),
            "scopes": scopes,
        })
        selected_rows.extend([root, *details, *targets])
        if condition:
            selected_rows.append(condition)
        selected_rows.extend(
            item for item in effects if sid(item["row"].get("ref_id")) == root_id
        )

    monitor_actions: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
    for item in active("fd_linkage_monitor_action"):
        monitor_actions[sid(item["row"].get("entity_id"))].append(item)
    monitor_fields: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
    for item in active("fd_linkage_monitor_field"):
        monitor_fields[sid(item["row"].get("entity_id"))].append(item)
    sources: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
    for item in active("fd_linkage_source"):
        sources[sid(item["row"].get("entity_id"))].append(item)
    source_excel = {
        sid(item["row"].get("entity_id")): item
        for item in active("fd_linkage_source_excel")
    }
    formulas = {
        sid(item["row"].get("id")): item for item in active("express_formula")
    }
    source_labels = {
        "esb": "动作流数据源", "excel": "计算公式", "sql": "数据库查询",
        "config": "配置数据", "mapping": "字段映射",
    }
    field_linkages: list[dict[str, Any]] = []
    function_linkages: list[dict[str, Any]] = []
    for root in active("fd_linkage"):
        row = root["row"]
        if sid(row.get("form_id")) not in form_ids:
            continue
        root_id = sid(row.get("id"))
        actions = monitor_actions.get(root_id) or []
        triggers: list[str] = []
        trigger_fields: list[str] = []
        for action in actions:
            action_row = action["row"]
            action_name = clean_text(action_row.get("action_name"), "触发时")
            fields = monitor_fields.get(sid(action_row.get("id"))) or []
            if fields:
                for field in fields:
                    field_row = field["row"]
                    field_name = clean_text(field_row.get("target_name")) or field_names.get(
                        sid(field_row.get("target_field")), "业务字段"
                    )
                    field_name = re.sub(r"^主表[.。]", "", field_name)
                    trigger_fields.append(field_name)
                    triggers.append(f"{field_name}{action_name}")
            else:
                triggers.append(action_name)
        root_sources = sources.get(root_id) or []
        source_types = sorted({
            source_labels.get(str(item["row"].get("linkage_type") or "").lower(), "业务数据源")
            for item in root_sources
        })
        scopes = _effect_scope(root_id, effects, effect_values)
        name = clean_text(row.get("linkage_name"), "未命名联动")
        name = re.sub(r"(对应)(?:对应)+", r"\1", name)
        common = {
            "name": name,
            "enabled": str(row.get("linkage_state", "1")) not in {"0", "false", "False"},
            "triggers": sorted(set(triggers)),
            "triggerFields": sorted(set(trigger_fields)),
            "sourceTypes": source_types,
            "scopes": scopes,
        }
        is_function = str(row.get("linkage_type") or "").lower() == "excel"
        if is_function:
            formula_texts = []
            custom_functions = []
            formula_rows: list[dict[str, Any]] = []
            for source in root_sources:
                excel = source_excel.get(sid(source["row"].get("id")))
                formula = formulas.get(sid((excel or {}).get("row", {}).get("excel_id")))
                if not formula:
                    continue
                formula_rows.extend([excel, formula])
                formula_value = _business_formula(formula["row"].get("formula"))
                formula_texts.append(formula_value)
                for function in active("custom_func"):
                    function_name = clean_text(function["row"].get("func_name"))
                    if function_name and re.search(rf"\b{re.escape(function_name)}\s*\(", str(formula["row"].get("formula") or "")):
                        custom_functions.append(function_name)
                        formula_rows.append(function)
            description = name
            if formula_texts:
                description += "（" + "；".join(sorted(set(formula_texts))) + "）"
            function_linkages.append({
                **common,
                "description": description,
                "formulas": sorted(set(formula_texts)),
                "customFunctions": sorted(set(custom_functions)),
            })
            selected_rows.extend(formula_rows)
        else:
            trigger_text = "、".join(sorted(set(triggers))) or "按配置触发"
            source_text = "、".join(source_types) or "业务数据源"
            field_linkages.append({
                **common,
                "description": f"{name}：{trigger_text}，调用{source_text}；适用范围：{_linkage_scope_text(scopes)}",
            })
        selected_rows.extend([root, *actions, *root_sources])
        selected_rows.extend(
            item for item in effects if sid(item["row"].get("ref_id")) == root_id
        )
        for action in actions:
            selected_rows.extend(monitor_fields.get(sid(action["row"].get("id"))) or [])

    selected_effect_ids = {
        sid(item["row"].get("id")) for item in selected_rows if item["table"] == "fd_effect"
    }
    selected_rows.extend(
        item for item in effect_values
        if sid(item["row"].get("effect_id")) in selected_effect_ids
    )
    return {
        "attributeLinkages": sorted(attribute_linkages, key=lambda item: (item["name"], stable_hash(item))),
        "fieldLinkages": sorted(field_linkages, key=lambda item: (item["name"], stable_hash(item))),
        "functionLinkages": sorted(function_linkages, key=lambda item: (item["name"], stable_hash(item))),
        "recordKeys": sorted({item["recordKey"] for item in selected_rows}),
    }


def build_workflow_form_model(
    active_id: str | None,
    records: list[dict[str, Any]],
    node_names: dict[str | None, str],
) -> dict[str, Any]:
    relate_rows = [
        item for item in _rows(records, "wfp_relateform")
        if sid(item["row"].get("workflowid")) == active_id
    ]
    form_ids = {
        sid(item["row"].get("relatekey")) for item in relate_rows
        if sid(item["row"].get("relatekey"))
    }
    forms = [item for item in _rows(records, "form") if sid(item["row"].get("id")) in form_ids and active_row(item["row"])]
    fields = [item for item in _rows(records, "form_field") if sid(item["row"].get("form_id")) in form_ids and active_row(item["row"])]
    field_names = {
        sid(item["row"].get("id")): re.sub(r"(?i)id$", "ID", clean_text(item["row"].get("title"), "未命名字段"))
        for item in fields
    }
    field_ids = set(field_names)
    table_fields = [
        item for item in _rows(records, "form_table_field")
        if sid(item["row"].get("field_id")) in field_ids and active_row(item["row"])
    ]
    storage_by_field = {
        sid(item["row"].get("field_id")): item["row"] for item in table_fields
    }

    def field_business_model(item: dict[str, Any]) -> dict[str, Any]:
        row = item["row"]
        field_id = sid(row.get("id"))
        properties = json_object(row.get("other_properties"))
        storage = storage_by_field.get(field_id) or {}
        component = str(row.get("component_type") or row.get("component_key") or "字段")
        single = optional_bool(row.get("single"))
        if single is None:
            single = optional_bool(properties.get("isSingle"))
        max_length = properties.get("maxLen")
        if max_length in (None, "") and component.lower() in {"text", "textarea", "input"}:
            max_length = storage.get("type_len")
        try:
            max_length = int(max_length) if max_length not in (None, "") else None
        except (TypeError, ValueError):
            max_length = None
        return {
            "key": clean_text(row.get("data_key") or storage.get("column_name"))
            or field_names.get(field_id, "未命名字段"),
            "name": field_names.get(field_id, "未命名字段"),
            "component": component,
            "required": optional_bool(row.get("required")) is True,
            "selectionMode": "单选" if single is True else "多选" if single is False else None,
            "maxLength": max_length,
            "detailViewEnabled": optional_bool(properties.get("viewDataDetail")),
            "deleted": str(row.get("is_delete", "0")) in {"1", "true", "True"},
        }
    field_model = sorted(({
        **field_business_model(item),
    } for item in fields), key=lambda x: (x["deleted"], x["key"], x["name"], x["component"]))
    linkage_model = build_workflow_linkage_model(form_ids, records, field_names)

    multiple = [item for item in _rows(records, "form_layout_multiple") if sid(item["row"].get("form_id")) in form_ids and active_row(item["row"])]
    multiple_ids = {sid(item["row"].get("id")) for item in multiple}
    versions = [
        item for item in _rows(records, "form_layout_version")
        if (sid(item["row"].get("form_id")) in form_ids
        or sid(item["row"].get("multiple_layout_id")) in multiple_ids)
        and active_row(item["row"])
    ]
    version_ids = {sid(item["row"].get("id")) for item in versions}
    extended = [item for item in _rows(records, "ebdd_page_extended") if sid(item["row"].get("page_id")) in version_ids and active_row(item["row"])]
    extended_ids = {sid(item["row"].get("id")) for item in extended}
    page_layouts = [item for item in _rows(records, "ebdd_page_layout") if sid(item["row"].get("page_id")) in extended_ids and active_row(item["row"])]
    page_layout_ids = {sid(item["row"].get("id")) for item in page_layouts}
    components = [item for item in _rows(records, "ebdd_layout_component") if sid(item["row"].get("layout_id")) in page_layout_ids and active_row(item["row"])]
    layout_names = _layout_name_map(multiple, versions, extended, page_layouts)
    component_model = sorted(
        ({**_layout_component_model(item["row"], field_names), "layout": layout_names.get(sid(item["row"].get("layout_id")), "未命名布局")} for item in components),
        key=lambda x: (x["structure"], x["name"], stable_hash(x)),
    )
    structure_model = [item for item in component_model if item["type"] != "InternalContainer"]

    permission_rows = [item for item in _rows(records, "field_permission") if sid(item["row"].get("form_id")) in form_ids and active_row(item["row"])]
    permission_ids = {sid(item["row"].get("id")) for item in permission_rows}
    node_form_rows = [
        item for item in _rows(records, "wfp_node_form_relate")
        if sid(item["row"].get("workflowid")) == active_id
        and sid(item["row"].get("permissionid")) in permission_ids
    ]
    permission_to_node = {
        sid(item["row"].get("permissionid")): node_names.get(sid(item["row"].get("nodeid")), "未识别节点")
        for item in node_form_rows
    }
    field_views = []
    view_rows = []
    for item in _rows(records, "form_view_relate_config"):
        row = item["row"]
        node = permission_to_node.get(sid(row.get("version_id")))
        field = field_names.get(sid(row.get("field_id")))
        if not node or not field:
            continue
        view_rows.append(item)
        field_views.append({
            "node": node,
            "field": field,
            "visible": str(row.get("display", "1")) not in {"0", "false", "False"},
            "readOnly": str(row.get("readonly", "0")) in {"1", "true", "True"},
            "required": str(row.get("required", "0")) in {"1", "true", "True"},
            "order": float(row.get("show_order") or 0),
        })

    list_tables = {
        item["table"] for item in records
        if item["table"].startswith(LIST_TABLE_PREFIXES)
    }
    list_roots = [
        item for item in _rows(records, "ebdf_list")
        if sid(item["row"].get("obj_id")) in form_ids
        or sid(item["row"].get("form_id")) in form_ids
    ]
    list_ids = {sid(item["row"].get("id")) for item in list_roots}
    list_columns = [
        item for item in _rows(records, "ebdf_list_field")
        if sid(item["row"].get("list_id")) in list_ids
    ]
    title_rows = [
        item for item in _rows(records, "wfp_deftitle_format_config")
        if sid(item["row"].get("workflowid")) == active_id
    ]
    record_keys = {
        item["recordKey"]
        for group in (
            relate_rows, forms, fields, table_fields, multiple, versions, extended, page_layouts,
            components, permission_rows, node_form_rows, view_rows, list_roots,
            list_columns, title_rows,
        )
        for item in group
    }
    record_keys.update(linkage_model["recordKeys"])
    return {
        "forms": sorted(clean_text(item["row"].get("name"), "未命名表单") for item in forms),
        "fields": field_model,
        "pcLayouts": sum(str(item["row"].get("terminal_type") or "").upper() == "PC" for item in multiple),
        "mobileLayouts": sum(str(item["row"].get("terminal_type") or "").upper() in {"MOBILE", "APP", "H5"} for item in multiple),
        "layoutComponents": component_model,
        "layoutStructures": structure_model,
        "nodeFieldViews": sorted(field_views, key=lambda x: (x["node"], x["order"], x["field"])),
        "listCoverage": "PRESENT" if list_tables else "NOT_PACKAGED",
        "lists": len(list_roots),
        "listColumns": len(list_columns),
        "titleRule": _title_rule(title_rows),
        "attributeLinkages": linkage_model["attributeLinkages"],
        "fieldLinkages": linkage_model["fieldLinkages"],
        "functionLinkages": linkage_model["functionLinkages"],
        "recordKeys": sorted(record_keys),
    }


DIRECT_OWNER_FIELDS = (
    "workflowid", "workflow_id", "business_id", "nodeid", "node_id",
    "srcnodeid", "destnodeid", "conditionid", "condition_id",
    "conditionkey", "targetconditionkey", "groupid", "groupdetailid",
    "actionid", "menuid", "foreign_key", "linkid", "mainid", "parent_id",
    "chartid", "chartId", "target_id", "ref_id", "subsetid", "cptbaseid",
    "optmatrixid", "optMatrixId", "markdefid", "markDefId",
)


def collect_chain(
    records: list[dict[str, Any]],
    seeds: list[dict[str, Any]],
    relation_specs: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Follow deterministic parent-to-child ownership until a fixed point."""
    owned = list(seeds)
    owned_keys = {item["recordKey"] for item in seeds}
    owned_ids = {
        sid(item["row"].get("id")) for item in seeds
        if sid(item["row"].get("id"))
    }
    owned_ids.update(
        sid(item["row"].get(key))
        for item in seeds
        for key in DIRECT_OWNER_FIELDS
        if sid(item["row"].get(key))
    )
    specs_by_child: dict[str, list[dict[str, str]]] = defaultdict(list)
    for spec in relation_specs:
        specs_by_child[spec["childTable"]].append(spec)
    changed = True
    while changed:
        changed = False
        for item in records:
            if item["recordKey"] in owned_keys:
                continue
            row, table = item["row"], item["table"]
            record_id = sid(row.get("id"))
            direct_values = {
                sid(row.get(key)) for key in DIRECT_OWNER_FIELDS
                if sid(row.get(key))
            }
            matched = bool((record_id and record_id in owned_ids) or direct_values & owned_ids)
            if not matched:
                for spec in specs_by_child.get(table, []):
                    value = sid(row.get(spec["childField"]))
                    if value and value in owned_ids:
                        matched = True
                        break
            if not matched:
                continue
            owned.append(item)
            owned_keys.add(item["recordKey"])
            if record_id and record_id not in owned_ids:
                owned_ids.add(record_id)
            owned_ids.update(direct_values)
            changed = True
    return owned


def build_integration_model(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Restore workflow-package interface resources as customer-facing dependencies."""
    active = [item for item in records if active_row(item["row"])]
    applications = {
        sid(item["row"].get("id")): re.sub(
            r"\(20\d{2}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\)",
            "",
            clean_action_name(item["row"].get("name")),
        ).strip(" -_")
        for item in active if item["table"] == "esb_application"
    }
    action_by_data = {
        sid(item["row"].get("data_id")): sid(item["row"].get("application_id"))
        for item in active if item["table"] == "esb_flow_action"
        and sid(item["row"].get("data_id"))
    }
    resource_names = {
        sid(item["row"].get("id")): clean_text(item["row"].get("name"), "外部接口服务")
        for item in active if item["table"] == "esb_resource"
    }
    endpoints = {
        sid(item["row"].get("id")): clean_text(item["row"].get("host"))
        for item in active if item["table"] == "esb_rest_resource"
    }
    calls: dict[str, list[str]] = defaultdict(list)
    for item in active:
        if item["table"] != "esb_component_http":
            continue
        resource_id = sid(item["row"].get("resource_id"))
        application_id = action_by_data.get(sid(item["row"].get("id")))
        if resource_id and application_id:
            calls[resource_id].append(applications.get(application_id, "关联动作流"))
    return sorted(({
        "name": resource_names.get(resource_id, "外部接口服务"),
        "endpoint": endpoint,
        "callCount": len(calls.get(resource_id) or []),
        "affectedActionFlows": sorted(set(calls.get(resource_id) or [])),
    } for resource_id, endpoint in endpoints.items()), key=lambda item: item["name"])


def build_workflow_sql_datasources(
    active_id: str | None,
    records: list[dict[str, Any]],
    dataset_lineage: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], set[str]]:
    """Attach SQL datasets through declared wfp_context parameters only."""

    contexts = {
        sid(item["row"].get("id")): item
        for item in records
        if item["table"] == "wfp_context"
        and sid(item["row"].get("workflowid")) == active_id
        and active_row(item["row"])
        and sid(item["row"].get("id"))
    }
    summaries: list[dict[str, Any]] = []
    record_keys: set[str] = set()
    for item in records:
        row = item["row"]
        if (
            item["table"] != "dataset"
            or str(row.get("source_module") or "").lower() != "workflow"
            or not active_row(row)
        ):
            continue
        config = json_object(row.get("dataset_sql"))
        fields = [field for field in config.get("fields") or [] if isinstance(field, dict)]
        parameter_ids = [sid(field.get("name")) for field in fields]
        if not parameter_ids or any(value not in contexts for value in parameter_ids):
            continue
        bindings = [
            {
                "name": clean_text(field.get("showname"), "查询参数"),
                "placeholderHash": hashlib.sha256(str(parameter_id).encode("utf-8")).hexdigest()[:16],
            }
            for field, parameter_id in zip(fields, parameter_ids)
        ]
        lineage = dataset_lineage.get(item["recordKey"]) or {}
        summaries.append(analyze_workflow_sql_dataset(
            config, bindings, lineage.get("lineageKeyHash")
        ))
        record_keys.add(item["recordKey"])
        record_keys.update(contexts[value]["recordKey"] for value in parameter_ids)
    summaries.sort(key=lambda value: (
        value.get("semanticHash") or "", value.get("identityHash") or ""
    ))
    return summaries, record_keys


def build_workflow_ir(ir: dict[str, Any], knowledge: Path) -> dict[str, Any]:
    aliases = lineage_map(ir)
    descriptions, relation_specs = load_config_semantics(knowledge)
    all_rows = list(iter_records(ir))
    all_by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unit_catalog: dict[str, dict[str, Any]] = {}
    for item in all_rows:
        key = unit_key(item.get("unit"), aliases)
        item["unitKey"] = key
        all_by_unit[key].append(item)
        if item.get("unit"):
            unit_catalog[key] = item["unit"]
    relevant = [
        item for item in all_rows
        if item["table"].startswith(WORKFLOW_PREFIXES)
        or item["table"] in EXTRA_TABLES
        or item["table"] in FORM_TABLES
        or item["table"].startswith(LIST_TABLE_PREFIXES)
    ]
    by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in relevant:
        key = item["unitKey"]
        by_unit[key].append(item)
    base_lineage = idm_record_lineage(ir, relevant, "wfp_base")
    dataset_lineage = idm_record_lineage(ir, relevant, "dataset")

    workflows: list[dict[str, Any]] = []
    assigned_record_keys: set[str] = set()
    ambiguous_record_keys: set[str] = set()
    for ukey, records in sorted(by_unit.items()):
        bases = [x for x in records if x["table"] == "wfp_base"]
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in bases:
            row = item["row"]
            fixed = sid(row.get("fixed_version_id")) or sid(row.get("id")) or _row_name("wfp_base", row)
            grouped[fixed].append(item)

        for fixed, versions in sorted(grouped.items()):
            versions.sort(key=lambda x: (int(x["row"].get("versionid") or 0), sid(x["row"].get("id")) or ""))
            version_ids = {sid(x["row"].get("id")) for x in versions}
            active_hint = sid(versions[-1]["row"].get("activewfid"))
            active = next((x for x in versions if sid(x["row"].get("id")) == active_hint), versions[-1])
            fixed_item = next(
                (x for x in versions if sid(x["row"].get("id")) == fixed),
                versions[0],
            )
            lineage = base_lineage.get(fixed_item["recordKey"])
            active_id = sid(active["row"].get("id"))
            node_rows = [x for x in records if x["table"] == "wfp_node" and sid(x["row"].get("workflowid")) == active_id and active_row(x["row"])]
            node_ids = {sid(x["row"].get("id")) for x in node_rows}
            link_rows = [x for x in records if x["table"] == "wfp_link" and sid(x["row"].get("workflowid")) == active_id and active_row(x["row"])]
            link_ids = {sid(x["row"].get("id")) for x in link_rows}
            condition_ids = {
                sid(x["row"].get("conditionkey")) for x in link_rows
                if sid(x["row"].get("conditionkey")) not in {None, "0", "-1"}
            }

            full_chain = collect_chain(records, versions, relation_specs)
            active_chain = collect_chain(records, [active], relation_specs)
            node_names = {sid(x["row"].get("id")): _row_name("wfp_node", x["row"]) for x in node_rows}
            form_model = build_workflow_form_model(active_id, records, node_names)
            integrations = build_integration_model(all_by_unit.get(ukey) or [])
            sql_datasources, sql_record_keys = build_workflow_sql_datasources(
                active_id, records, dataset_lineage
            )
            local_record_keys = {
                item["recordKey"] for item in full_chain
            } | set(form_model["recordKeys"]) | sql_record_keys
            for record_key in local_record_keys:
                if record_key in assigned_record_keys:
                    ambiguous_record_keys.add(record_key)
                assigned_record_keys.add(record_key)
            categories: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for item in active_chain:
                table, row = item["table"], item["row"]
                if not active_row(row):
                    continue
                category = CATEGORIES.get(table) or descriptions.get(table) or "其他流程设置"
                if category not in CUSTOMER_BUSINESS_CATEGORIES:
                    continue
                if table == "wfp_deftitle_format_config":
                    # Ten storage rows form one customer-facing title rule.
                    # It is rendered from form.titleRule below, not itemized.
                    continue
                if table == "wfp_node_menu" and not customized_menu(row):
                    continue
                categories[category].append({
                    "table": table,
                    "name": _row_name(table, row),
                    "summary": _summary(table, row),
                })

            menus = [
                _menu_model(item["row"], node_names)
                for item in active_chain
                if item["table"] == "wfp_node_menu" and active_row(item["row"]) and customized_menu(item["row"])
            ]

            links = []
            for item in link_rows:
                row = item["row"]
                links.append({
                    "name": _row_name("wfp_link", row),
                    "from": node_names.get(sid(row.get("srcnodeid")), "未识别节点"),
                    "to": node_names.get(sid(row.get("destnodeid")), "未识别节点"),
                    "default": row.get("isdefault"),
                    "reject": row.get("isreject"),
                    "conditional": sid(row.get("conditionkey")) not in {None, "0", "-1"},
                })
            nodes = [
                {
                    "name": _row_name("wfp_node", x["row"]),
                    "type": x["row"].get("nodetype"),
                    "attribute": x["row"].get("nodeattr"),
                    "order": x["row"].get("orderid"),
                    "deleted": str(x["row"].get("delete_type", "0")) in {"1", "true", "True"},
                }
                for x in node_rows
            ]
            category_model = {
                name: {
                    "count": len(items),
                    "items": sorted(items, key=lambda x: (x["name"], stable_hash(x["summary"]))),
                }
                for name, items in sorted(categories.items())
            }
            unit = unit_catalog.get(ukey) or {}
            name = clean_text(
                active["row"].get("workflowname") or active["row"].get("name"),
                "未命名流程",
            )
            identity = (
                f"{ukey}|workflow:lineage-{lineage['stableToken']}"
                if lineage else f"{ukey}|workflow:{aliases.get(fixed, fixed)}"
            )
            workflow = {
                "identity": identity,
                "identityMethod": (
                    lineage.get("identityMethod") if lineage
                    else "PROFILE_HOMOLOGY" if aliases.get(fixed) else "BUSINESS_KEY"
                ),
                "lineageKeyHash": lineage.get("lineageKeyHash") if lineage else None,
                "lineageEvidencePath": lineage.get("lineageEvidencePath") if lineage else None,
                "name": name,
                "packageUnit": {"name": clean_text(unit.get("name"), "未命名流程单元"), "identity": ukey} if unit else None,
                "description": clean_text(active["row"].get("workflowdesc") or ""),
                "versionCount": len(versions),
                "activeVersion": active["row"].get("versionid"),
                "status": active["row"].get("status"),
                "nodes": sorted(nodes, key=lambda x: (x.get("order") or 0, x["name"])),
                "links": sorted(links, key=lambda x: (x["from"], x["to"], x["name"])),
                "menus": sorted(menus, key=lambda x: (x["node"], x["type"], x["name"])),
                "categories": category_model,
                "form": form_model,
                "integrations": integrations,
                "sqlDataSources": sql_datasources,
                "activeRecordCount": len(active_chain),
                "versionGroupRecordCount": len(full_chain),
            }
            workflow["semanticHash"] = stable_hash({
                "name": workflow["name"],
                "description": workflow["description"],
                "status": workflow["status"],
                "nodes": workflow["nodes"],
                "links": workflow["links"],
                "menus": workflow["menus"],
                "categories": workflow["categories"],
                "form": {
                    key: value for key, value in workflow["form"].items()
                    if key != "recordKeys"
                },
                "integrations": workflow["integrations"],
                "sqlDataSources": workflow["sqlDataSources"],
            })
            workflows.append(workflow)

    unresolved = [item for item in relevant if item["recordKey"] not in assigned_record_keys]
    unresolved_counts = Counter(item["table"] for item in unresolved)
    core_tables = {"wfp_base", "wfp_node", "wfp_link"}
    core_unresolved = Counter(
        item["table"] for item in unresolved if item["table"] in core_tables
    )
    record_table = {item["recordKey"]: item["table"] for item in relevant}
    core_ambiguous = Counter(
        record_table[key] for key in ambiguous_record_keys
        if record_table.get(key) in core_tables
    )
    coverage = {
        "totalWorkflowRecords": len(relevant),
        "assignedRecordCount": len(assigned_record_keys),
        "unresolvedRecordCount": len(unresolved),
        "ambiguousRecordCount": len(ambiguous_record_keys),
        "coreUnresolvedRecordCount": sum(core_unresolved.values()),
        "coreAmbiguousRecordCount": sum(core_ambiguous.values()),
        "coreChainComplete": not core_unresolved and not core_ambiguous,
    }
    table_models: dict[str, list[Any]] = defaultdict(list)
    for item in relevant:
        table_models[item["table"]].append(canonical(item["row"]))
    for item in all_rows:
        if item["table"] == "esb_rest_resource":
            table_models[item["table"]].append(canonical(item["row"]))
    table_semantic_hashes = {
        table: stable_hash(sorted(rows, key=lambda row: stable_hash(row)))
        for table, rows in table_models.items()
    }
    packaged_table_names = sorted({item["table"] for item in relevant})

    return {
        "schemaVersion": "ebuilder-workflow-ir/v1.0",
        "package": ir.get("source") or {},
        "profile": ir.get("packageProfile") or {},
        "workflows": sorted(workflows, key=lambda x: (x["packageUnit"] or {}).get("name", "") + x["name"]),
        "summary": {
            "workflowCount": len(workflows),
            "versionCount": sum(x["versionCount"] for x in workflows),
            "nodeCount": sum(len(x["nodes"]) for x in workflows),
            "linkCount": sum(len(x["links"]) for x in workflows),
            "conditionCount": sum((x["categories"].get("流转条件") or {}).get("count", 0) for x in workflows),
            "operatorGroupCount": sum((x["categories"].get("节点操作者组") or {}).get("count", 0) for x in workflows),
            "menuCount": sum(
                sum(bool(menu.get("customized")) for menu in x["menus"])
                for x in workflows
            ),
            "actionCount": sum((x["categories"].get("节点附加动作") or {}).get("count", 0) for x in workflows),
            "subflowCount": sum((x["categories"].get("子流程触发规则") or {}).get("count", 0) for x in workflows),
            "mappingCount": sum((x["categories"].get("流程字段映射") or {}).get("count", 0) for x in workflows),
            "formCount": sum(len(x["form"]["forms"]) for x in workflows),
            "formFieldCount": sum(len(x["form"]["fields"]) for x in workflows),
            "pcLayoutCount": sum(x["form"]["pcLayouts"] for x in workflows),
            "mobileLayoutCount": sum(x["form"]["mobileLayouts"] for x in workflows),
            "layoutComponentCount": sum(len(x["form"]["layoutComponents"]) for x in workflows),
            "attributeLinkageCount": sum(len(x["form"].get("attributeLinkages") or []) for x in workflows),
            "fieldLinkageCount": sum(len(x["form"].get("fieldLinkages") or []) for x in workflows),
            "functionLinkageCount": sum(len(x["form"].get("functionLinkages") or []) for x in workflows),
            "listCount": sum(x["form"]["lists"] for x in workflows),
            "listColumnCount": sum(x["form"]["listColumns"] for x in workflows),
            "titleRuleCount": sum(bool(x["form"]["titleRule"]["configured"]) for x in workflows),
            "integrationCount": len({
                (
                    ((x.get("packageUnit") or {}).get("id") or (x.get("packageUnit") or {}).get("name") or "single"),
                    item.get("name") or "未命名接口服务",
                )
                for x in workflows
                for item in (x.get("integrations") or [])
            }),
            "sqlDataSourceCount": sum(len(x.get("sqlDataSources") or []) for x in workflows),
            "listCoverage": "PRESENT" if any(
                x["form"]["listCoverage"] == "PRESENT" for x in workflows
            ) else "NOT_PACKAGED",
        },
        "packagedTableNames": packaged_table_names,
        "tableSemanticHashes": table_semantic_hashes,
        "chainCoverage": coverage,
        "unresolvedTableCounts": dict(sorted(unresolved_counts.items())),
        "coreUnresolvedTableCounts": dict(sorted(core_unresolved.items())),
    }


def _match_workflows(old: list[dict[str, Any]], new: list[dict[str, Any]]) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], list[dict[str, Any]], list[dict[str, Any]]]:
    new_by_id = {x["identity"]: x for x in new}
    pairs, old_only = [], []
    used = set()
    for item in old:
        candidate = new_by_id.get(item["identity"])
        if candidate:
            pairs.append((item, candidate)); used.add(candidate["identity"])
        else:
            old_only.append(item)
    new_only = [x for x in new if x["identity"] not in used]
    # Conservative fallback: same package unit and unique exact business name.
    for old_item in list(old_only):
        old_unit = (old_item.get("packageUnit") or {}).get("identity")
        candidates = [
            x for x in new_only
            if x["name"] == old_item["name"]
            and (x.get("packageUnit") or {}).get("identity") == old_unit
        ]
        if len(candidates) == 1:
            pairs.append((old_item, candidates[0]))
            old_only.remove(old_item); new_only.remove(candidates[0])
    return pairs, old_only, new_only


def _category_diff(old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    names = sorted(set(old) | set(new))
    for name in names:
        before, after = old.get(name) or {"count": 0, "items": []}, new.get(name) or {"count": 0, "items": []}
        old_items = Counter(stable_hash(x) for x in before["items"])
        new_items = Counter(stable_hash(x) for x in after["items"])
        if old_items == new_items:
            continue
        if name == "关联事项显示设置" and len(before["items"]) == len(after["items"]) == 1:
            old_value = before["items"][0]["summary"].get("web_print_show")
            new_value = after["items"][0]["summary"].get("web_print_show")
            if old_value != new_value:
                state = lambda value: "开启" if str(value).lower() in {"1", "true"} else "关闭"
                result.append({
                    "category": name,
                    "beforeCount": 1,
                    "afterCount": 1,
                    "added": 0,
                    "removed": 0,
                    "beforeNames": [],
                    "afterNames": [],
                    "updatedNames": [f"网页版打印显示关联事项：{state(old_value)} → {state(new_value)}"],
                })
                continue
        if name == "流程编号规则":
            old_by_table = defaultdict(list)
            new_by_table = defaultdict(list)
            for item in before["items"]:
                old_by_table[item.get("table")].append(item)
            for item in after["items"]:
                new_by_table[item.get("table")].append(item)
            added_names = []
            removed_names = []
            updated_names = []
            old_set = (old_by_table.get("wfp_markset") or [None])[0]
            new_set = (new_by_table.get("wfp_markset") or [None])[0]
            if old_set and new_set:
                old_enabled = str(old_set["summary"].get("is_use", "0")).lower() in {"1", "true"}
                new_enabled = str(new_set["summary"].get("is_use", "0")).lower() in {"1", "true"}
                if old_enabled != new_enabled:
                    updated_names.append(
                        f"流程编号功能：{'开启' if old_enabled else '关闭'} → "
                        f"{'开启' if new_enabled else '关闭'}"
                    )
                old_multi = str(old_set["summary"].get("is_multimark", "0")).lower() in {"1", "true"}
                new_multi = str(new_set["summary"].get("is_multimark", "0")).lower() in {"1", "true"}
                if old_multi != new_multi:
                    updated_names.append(
                        f"多编号模式：{'开启' if old_multi else '关闭'} → "
                        f"{'开启' if new_multi else '关闭'}"
                    )
            for table, label in (("wfp_markdef", "编号生成规则"), ("wfp_markfield", "编号组成项")):
                old_count = len(old_by_table.get(table) or [])
                new_count = len(new_by_table.get(table) or [])
                if new_count > old_count:
                    added_names.append(f"{label}×{new_count - old_count}")
                elif old_count > new_count:
                    removed_names.append(f"{label}×{old_count - new_count}")
                elif old_count and stable_hash(old_by_table[table]) != stable_hash(new_by_table[table]):
                    updated_names.append(f"{label}已调整")
            if added_names or removed_names or updated_names:
                result.append({
                    "category": name,
                    "beforeCount": before["count"],
                    "afterCount": after["count"],
                    "added": max(0, after["count"] - before["count"]),
                    "removed": max(0, before["count"] - after["count"]),
                    "beforeNames": [],
                    "afterNames": [],
                    "addedNames": added_names,
                    "removedNames": removed_names,
                    "updatedNames": updated_names,
                })
                continue
        old_remaining = old_items - new_items
        new_remaining = new_items - old_items
        removed_names = []
        added_names = []
        for item in before["items"]:
            key = stable_hash(item)
            if old_remaining.get(key, 0):
                removed_names.append(item["name"])
                old_remaining[key] -= 1
        for item in after["items"]:
            key = stable_hash(item)
            if new_remaining.get(key, 0):
                added_names.append(item["name"])
                new_remaining[key] -= 1
        result.append({
            "category": name,
            "beforeCount": before["count"],
            "afterCount": after["count"],
            "added": sum((new_items - old_items).values()),
            "removed": sum((old_items - new_items).values()),
            "beforeNames": [x["name"] for x in before["items"][:12]],
            "afterNames": [x["name"] for x in after["items"][:12]],
            "addedNames": added_names,
            "removedNames": removed_names,
        })
    return result


def _suppress_new_node_defaults(
    details: list[dict[str, Any]],
    added_node_count: int,
    removed_node_count: int,
) -> list[dict[str, Any]]:
    if not (added_node_count or removed_node_count):
        return details
    result = []
    for detail in details:
        if detail["category"] not in AUTO_NODE_DEFAULT_CATEGORIES:
            result.append(detail)
            continue
        # A new node receives one form binding and the standard two system
        # field permissions. Do not report these generated defaults separately.
        expected_added = added_node_count * (2 if detail["category"] == "系统字段权限" else 1)
        expected_removed = removed_node_count * (2 if detail["category"] == "系统字段权限" else 1)
        if detail["added"] == expected_added and detail["removed"] == expected_removed:
            continue
        result.append(detail)
    return result


def _semantic_key(item: dict[str, Any]) -> str:
    return stable_hash({
        "name": item.get("name"),
        "type": item.get("type"),
        "attribute": item.get("attribute"),
        "deleted": item.get("deleted"),
    })


def _named_changes(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    old_by_key = {_semantic_key(item): item["name"] for item in before}
    new_by_key = {_semantic_key(item): item["name"] for item in after}
    added = sorted(new_by_key[key] for key in new_by_key.keys() - old_by_key.keys())
    removed = sorted(old_by_key[key] for key in old_by_key.keys() - new_by_key.keys())
    return added, removed


def _link_key(item: dict[str, Any]) -> str:
    return stable_hash({key: item.get(key) for key in ("from", "to", "default", "reject", "conditional")})


def _link_changes(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    old_by_key = {_link_key(item): item["name"] for item in before}
    new_by_key = {_link_key(item): item["name"] for item in after}
    added = sorted(new_by_key[key] for key in new_by_key.keys() - old_by_key.keys())
    removed = sorted(old_by_key[key] for key in old_by_key.keys() - new_by_key.keys())
    return added, removed


def _menu_changes(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
    added_nodes: list[str],
    removed_nodes: list[str],
) -> tuple[list[str], list[str]]:
    old = [item for item in before if item["node"] not in removed_nodes]
    new = [item for item in after if item["node"] not in added_nodes]
    old_by_key = {stable_hash(item): item["name"] for item in old}
    new_by_key = {stable_hash(item): item["name"] for item in new}
    added = sorted(new_by_key[key] for key in new_by_key.keys() - old_by_key.keys())
    removed = sorted(old_by_key[key] for key in old_by_key.keys() - new_by_key.keys())
    return added, removed


def _simple_named_changes(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    old = {stable_hash(item): item.get("name") or item.get("field") or "业务配置" for item in before}
    new = {stable_hash(item): item.get("name") or item.get("field") or "业务配置" for item in after}
    return (
        sorted(new[key] for key in new.keys() - old.keys()),
        sorted(old[key] for key in old.keys() - new.keys()),
    )


def _linkage_change_text(before: dict[str, Any], after: dict[str, Any]) -> str:
    changes: list[str] = []
    if before.get("enabled") != after.get("enabled"):
        changes.append(
            f"启用状态由{'启用' if before.get('enabled') else '停用'}调整为"
            f"{'启用' if after.get('enabled') else '停用'}"
        )
    for key, label in (
        ("triggers", "触发方式"), ("sourceTypes", "数据来源"),
        ("scopes", "适用范围"), ("formulas", "计算公式"),
        ("conditions", "生效条件"), ("effects", "联动效果"),
    ):
        old_values = before.get(key) or []
        new_values = after.get(key) or []
        if old_values != new_values:
            changes.append(
                f"{label}由{'、'.join(old_values) or '未配置'}调整为"
                f"{'、'.join(new_values) or '未配置'}"
            )
    return "；".join(changes) or "联动规则已调整"


def _linkage_detail(
    category: str,
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
    *,
    match_by_name: bool,
) -> dict[str, Any] | None:
    if match_by_name:
        old_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        new_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in before:
            old_groups[item.get("name") or item.get("description") or "未命名联动"].append(item)
        for item in after:
            new_groups[item.get("name") or item.get("description") or "未命名联动"].append(item)
        if all(len(items) == 1 for items in [*old_groups.values(), *new_groups.values()]):
            added_names = sorted(new_groups.keys() - old_groups.keys())
            removed_names = sorted(old_groups.keys() - new_groups.keys())
            updated_names = [
                f"{name}：{_linkage_change_text(old_groups[name][0], new_groups[name][0])}"
                for name in sorted(old_groups.keys() & new_groups.keys())
                if stable_hash(old_groups[name][0]) != stable_hash(new_groups[name][0])
            ]
        else:
            match_by_name = False
    if not match_by_name:
        old_by_hash = {stable_hash(item): item for item in before}
        new_by_hash = {stable_hash(item): item for item in after}
        added_names = sorted(
            new_by_hash[key].get("description") or new_by_hash[key].get("name") or "联动规则"
            for key in new_by_hash.keys() - old_by_hash.keys()
        )
        removed_names = sorted(
            old_by_hash[key].get("description") or old_by_hash[key].get("name") or "联动规则"
            for key in old_by_hash.keys() - new_by_hash.keys()
        )
        updated_names = []
    if not (added_names or removed_names or updated_names):
        return None
    return {
        "category": category,
        "beforeCount": len(before), "afterCount": len(after),
        "added": len(added_names), "removed": len(removed_names),
        "addedNames": added_names, "removedNames": removed_names,
        "updatedNames": updated_names,
    }


def _permission_label(item: dict[str, Any]) -> str:
    states = ["可见" if item.get("visible") else "隐藏"]
    states.append("只读" if item.get("readOnly") else "可编辑")
    if item.get("required"):
        states.append("必填")
    return f"{item.get('node')}：{item.get('field')}（{'、'.join(states)}）"


def _form_details(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    old_fields, new_fields = before.get("fields") or [], after.get("fields") or []
    old_by_key = {item.get("key") or item["name"]: item for item in old_fields}
    new_by_key = {item.get("key") or item["name"]: item for item in new_fields}
    added = sorted(new_by_key[key]["name"] for key in new_by_key.keys() - old_by_key.keys())
    removed = sorted(old_by_key[key]["name"] for key in old_by_key.keys() - new_by_key.keys())
    updated: list[str] = []
    for key in sorted(old_by_key.keys() & new_by_key.keys()):
        old_field, new_field = old_by_key[key], new_by_key[key]
        name = new_field["name"]
        if old_field.get("name") != name:
            updated.append(f"{old_field.get('name')}更名为{name}")
        old_mode, new_mode = old_field.get("selectionMode"), new_field.get("selectionMode")
        if old_mode and new_mode and old_mode != new_mode:
            updated.append(f"{name}：由{old_mode}调整为{new_mode}，可保存多个选择结果" if new_mode == "多选" else f"{name}：由{old_mode}调整为{new_mode}")
        old_length, new_length = old_field.get("maxLength"), new_field.get("maxLength")
        if old_length is not None and new_length is not None and old_length != new_length:
            verb = "扩展" if new_length > old_length else "收缩"
            updated.append(f"{name}：最大输入长度由{old_length}{verb}至{new_length}")
        if old_field.get("required") != new_field.get("required"):
            updated.append(f"{name}：{'调整为必填' if new_field.get('required') else '取消必填'}")
        old_detail = old_field.get("detailViewEnabled")
        new_detail = new_field.get("detailViewEnabled")
        if old_detail is not None and new_detail is not None and old_detail != new_detail:
            updated.append(
                f"{name}：查看数据详情由{'开启' if old_detail else '关闭'}调整为{'开启' if new_detail else '关闭'}"
            )
        if old_field.get("component") != new_field.get("component"):
            updated.append(f"{name}：录入方式发生调整")
    if added or removed or updated:
        result.append({
            "category": "关联表单字段",
            "beforeCount": len(old_fields), "afterCount": len(new_fields),
            "added": len(added), "removed": len(removed),
            "addedNames": added, "removedNames": removed,
            "updatedNames": updated,
        })

    old_views = {stable_hash(item): item for item in before.get("nodeFieldViews") or []}
    new_views = {stable_hash(item): item for item in after.get("nodeFieldViews") or []}
    added_views = [_permission_label(new_views[key]) for key in new_views.keys() - old_views.keys()]
    removed_views = [_permission_label(old_views[key]) for key in old_views.keys() - new_views.keys()]
    if added_views or removed_views:
        result.append({
            "category": "节点字段查看规则",
            "beforeCount": len(old_views), "afterCount": len(new_views),
            "added": len(added_views), "removed": len(removed_views),
            "addedNames": sorted(added_views), "removedNames": sorted(removed_views),
        })

    old_structures = before.get("layoutStructures") or []
    new_structures = after.get("layoutStructures") or []
    old_counter = Counter(stable_hash(item) for item in old_structures)
    new_counter = Counter(stable_hash(item) for item in new_structures)
    old_models = {stable_hash(item): item for item in old_structures}
    new_models = {stable_hash(item): item for item in new_structures}

    def component_label(item: dict[str, Any]) -> str:
        name = item.get("field") or item.get("name") or item.get("structure") or "表单组件"
        layout = item.get("layout")
        return f"{layout}：{name}" if layout and layout != "未命名布局" else name

    added_structures = sorted(
        component_label(new_models[key])
        for key, count in (new_counter - old_counter).items()
        for _ in range(count)
    )
    removed_structures = sorted(
        component_label(old_models[key])
        for key, count in (old_counter - new_counter).items()
        for _ in range(count)
    )
    updated_structures: list[str] = []
    old_components = before.get("layoutComponents") or []
    new_components = after.get("layoutComponents") or []
    if added_structures or removed_structures or updated_structures:
        result.append({
            "category": "表单布局",
            "beforeCount": len(old_structures), "afterCount": len(new_structures),
            "added": len(added_structures),
            "removed": len(removed_structures),
            "addedNames": added_structures,
            "removedNames": removed_structures,
            "updatedNames": sorted(updated_structures),
            "note": f"布局组件 {len(old_components)} → {len(new_components)}",
        })

    old_title, new_title = before.get("titleRule") or {}, after.get("titleRule") or {}
    if old_title != new_title:
        old_count, new_count = int(bool(old_title.get("configured"))), int(bool(new_title.get("configured")))
        result.append({
            "category": "流程标题组成",
            "beforeCount": old_count, "afterCount": new_count,
            "added": int(not old_count and new_count), "removed": int(old_count and not new_count),
            "addedNames": [new_title.get("display")] if new_count else [],
            "removedNames": [old_title.get("display")] if old_count else [],
            "updatedNames": [f"{old_title.get('display')} → {new_title.get('display')}"] if old_count and new_count else [],
        })

    if before.get("listCoverage") == "PRESENT" or after.get("listCoverage") == "PRESENT":
        if (before.get("lists"), before.get("listColumns")) != (after.get("lists"), after.get("listColumns")):
            result.append({
                "category": "表单列表",
                "beforeCount": before.get("lists", 0), "afterCount": after.get("lists", 0),
                "added": max(0, after.get("lists", 0) - before.get("lists", 0)),
                "removed": max(0, before.get("lists", 0) - after.get("lists", 0)),
                "addedNames": [], "removedNames": [],
            })
    for category, key, match_by_name in (
        ("属性联动", "attributeLinkages", False),
        ("字段联动", "fieldLinkages", True),
        ("函数联动", "functionLinkages", True),
    ):
        detail = _linkage_detail(
            category, before.get(key) or [], after.get(key) or [],
            match_by_name=match_by_name,
        )
        if detail:
            result.append(detail)
    return result


def _integration_details(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> list[dict[str, Any]]:
    old_by_name = {item["name"]: item for item in before}
    new_by_name = {item["name"]: item for item in after}
    added_names = sorted(new_by_name.keys() - old_by_name.keys())
    removed_names = sorted(old_by_name.keys() - new_by_name.keys())
    changed_names = sorted(
        name for name in old_by_name.keys() & new_by_name.keys()
        if old_by_name[name].get("endpoint") != new_by_name[name].get("endpoint")
    )
    if not (added_names or removed_names or changed_names):
        return []
    affected_flows = sorted({
        flow
        for name in changed_names
        for flow in new_by_name[name].get("affectedActionFlows") or []
    })
    call_count = sum(new_by_name[name].get("callCount") or 0 for name in changed_names)
    note = None
    if changed_names:
        note = f"共影响 {len(affected_flows)} 条动作流、{call_count} 个接口调用节点"
        if affected_flows:
            note += "，包括“" + "、".join(affected_flows) + "”"
    return [{
        "category": "外部接口服务",
        "beforeCount": len(before),
        "afterCount": len(after),
        "added": len(added_names),
        "removed": len(removed_names),
        "addedNames": [f"{name}：新增接口服务" for name in added_names],
        "removedNames": [f"{name}：停止随包提供接口服务" for name in removed_names],
        "updatedNames": [f"{name}：接口服务地址已切换" for name in changed_names],
        "note": note,
    }]


def _sql_static_check_text(summary: dict[str, Any]) -> str:
    checks = summary.get("staticChecks") or {}
    labels = (
        ("configurationParsed", "配置可解析"),
        ("singleStatement", "单语句"),
        ("readOnlyQuery", "只读查询"),
        ("parametersResolved", "参数引用闭合"),
        ("outputAliasesDeclared", "输出声明闭合"),
    )
    passed = [label for key, label in labels if checks.get(key)]
    failed = [label for key, label in labels if not checks.get(key)]
    text = "、".join(passed) or "无通过项"
    return text + ("；待复核：" + "、".join(failed) if failed else "")


def _sql_identity_text(value: str) -> str:
    return {
        "SAME_SOURCE": "同源配置更新",
        "RECREATED_OR_REBOUND": "非同源，疑似重建或重新绑定",
        "IDENTITY_UNCONFIRMED": "同源身份未确认，按配置重建候选处理",
        "ADDED": "新增数据源",
        "REMOVED": "删除数据源",
    }.get(value, "身份待确认")


def _sql_datasource_details(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    comparisons = pair_workflow_sql_summaries(before, after)
    if not comparisons:
        return []
    rows = []
    added = removed = 0
    updated_names = []
    for comparison in comparisons:
        old = comparison.get("before") or {}
        new = comparison.get("after") or {}
        identity = comparison.get("identityConclusion") or ""
        added += int(identity == "ADDED")
        removed += int(identity == "REMOVED")
        query_semantics = (
            f"{old.get('querySummary') or '无'} → {new.get('querySummary') or '无'}"
            if comparison.get("querySemanticsChanged")
            else "前后查询逻辑一致（格式差异已忽略）"
        )
        inputs = "、".join(new.get("inputs") or old.get("inputs") or []) or "未声明"
        old_types = "、".join(old.get("outputTypes") or []) or "无"
        new_types = "、".join(new.get("outputTypes") or []) or "无"
        output_types = old_types if old_types == new_types else f"{old_types} → {new_types}"
        current = new or old
        row = {
            "identity": _sql_identity_text(identity),
            "querySemantics": query_semantics,
            "inputs": inputs,
            "outputTypes": output_types,
            "staticChecks": _sql_static_check_text(current),
            "runtimePending": "；".join(current.get("runtimePending") or []) or "无",
        }
        rows.append(row)
        updated_names.append(
            f"{row['identity']}；{row['querySemantics']}；输入参数：{inputs}；"
            f"输出类型：{output_types}；离线静态校验：{row['staticChecks']}；运行待验证"
        )
    return [{
        "category": "工作流 SQL 数据源",
        "beforeCount": len(before),
        "afterCount": len(after),
        "added": added,
        "removed": removed,
        "addedNames": [],
        "removedNames": [],
        "updatedNames": updated_names,
        "validationRows": rows,
        "note": "数据库对象存在性、访问权限、真实执行结果和性能需在目标环境验证",
    }]


def _coverage_ledger(old_ir: dict[str, Any], new_ir: dict[str, Any]) -> dict[str, Any]:
    old_hashes, new_hashes = old_ir.get("tableSemanticHashes") or {}, new_ir.get("tableSemanticHashes") or {}
    changed = sorted(
        table for table in set(old_hashes) | set(new_hashes)
        if old_hashes.get(table) != new_hashes.get(table)
    )
    customer_core = {
        "wfp_base", "wfp_node", "wfp_link", "wfp_deftitle_format_config",
        "dataset", *FORM_TABLES, *INTEGRATION_TABLES,
    }
    derived = sorted(table for table in changed if table in DERIVED_WORKFLOW_TABLES)
    customer_tables = sorted(
        table for table in changed
        if table not in DERIVED_WORKFLOW_TABLES and (
            table in customer_core
            or table.startswith(LIST_TABLE_PREFIXES)
            or CATEGORIES.get(table) in CUSTOMER_BUSINESS_CATEGORIES
        )
    )
    unresolved = sorted(set(changed) - set(customer_tables) - set(derived))
    return {
        "changedTables": changed,
        "customerSemanticTables": customer_tables,
        "foldedDerivedTables": derived,
        "unresolvedChangedTables": unresolved,
        "complete": not unresolved,
    }


def compare_workflow_irs(old_ir: dict[str, Any], new_ir: dict[str, Any], direction: dict[str, Any]) -> dict[str, Any]:
    pairs, removed, added = _match_workflows(old_ir["workflows"], new_ir["workflows"])
    changes = []
    for item in added:
        changes.append({"changeType": "新增", "name": item["name"], "packageUnit": item.get("packageUnit"), "before": None, "after": item, "details": []})
    for item in removed:
        changes.append({"changeType": "删除", "name": item["name"], "packageUnit": item.get("packageUnit"), "before": item, "after": None, "details": []})
    for before, after in pairs:
        if before["semanticHash"] == after["semanticHash"]:
            continue
        details = _category_diff(before["categories"], after["categories"])
        added_nodes, removed_nodes = _named_changes(before["nodes"], after["nodes"])
        details = _suppress_new_node_defaults(details, len(added_nodes), len(removed_nodes))
        if before["nodes"] != after["nodes"]:
            details.append({"category": "流程节点", "beforeCount": len(before["nodes"]), "afterCount": len(after["nodes"]), "added": len(added_nodes), "removed": len(removed_nodes), "beforeNames": [x["name"] for x in before["nodes"]], "afterNames": [x["name"] for x in after["nodes"]], "addedNames": added_nodes, "removedNames": removed_nodes})
        if before["links"] != after["links"]:
            added_names, removed_names = _link_changes(before["links"], after["links"])
            details.append({"category": "节点连线与出口", "beforeCount": len(before["links"]), "afterCount": len(after["links"]), "added": len(added_names), "removed": len(removed_names), "beforeNames": [x["name"] for x in before["links"]], "afterNames": [x["name"] for x in after["links"]], "addedNames": added_names, "removedNames": removed_names})
        added_menus, removed_menus = _menu_changes(
            before.get("menus") or [], after.get("menus") or [], added_nodes, removed_nodes
        )
        if added_menus or removed_menus:
            details.append({
                "category": "节点操作菜单",
                "beforeCount": len(before.get("menus") or []),
                "afterCount": len(after.get("menus") or []),
                "added": len(added_menus),
                "removed": len(removed_menus),
                "beforeNames": [x["name"] for x in (before.get("menus") or [])],
                "afterNames": [x["name"] for x in (after.get("menus") or [])],
                "addedNames": added_menus,
                "removedNames": removed_menus,
            })
        details.extend(_form_details(before.get("form") or {}, after.get("form") or {}))
        details.extend(_integration_details(before.get("integrations") or [], after.get("integrations") or []))
        details.extend(_sql_datasource_details(
            before.get("sqlDataSources") or [], after.get("sqlDataSources") or []
        ))
        changes.append({"changeType": "更新", "name": after["name"], "packageUnit": after.get("packageUnit"), "before": before, "after": after, "details": sorted(details, key=lambda x: x["category"])})
    changes.sort(key=lambda x: ({"新增": 0, "删除": 1, "更新": 2}[x["changeType"]], (x.get("packageUnit") or {}).get("name", ""), x["name"]))
    counts = Counter(x["changeType"] for x in changes)
    test_points = []
    for change in changes:
        name = _scope_name(change)
        if change["changeType"] == "新增":
            test_points.append(f"验证新增流程“{name}”可以发起，并按节点顺序完成提交、审批、退回和结束。")
        elif change["changeType"] == "删除":
            test_points.append(f"确认流程“{name}”已按预期下线，历史实例查询和关联入口不受影响。")
        else:
            node_detail = next((x for x in change["details"] if x["category"] == "流程节点"), None)
            link_detail = next((x for x in change["details"] if x["category"] == "节点连线与出口"), None)
            focus = []
            if node_detail and node_detail.get("addedNames"):
                focus.append("新增节点“" + "、".join(node_detail["addedNames"]) + "”")
            if link_detail and link_detail.get("addedNames"):
                focus.append("新增路径“" + "、".join(link_detail["addedNames"][:4]) + "”")
            field_detail = next((x for x in change["details"] if x["category"] == "关联表单字段"), None)
            if field_detail and field_detail.get("addedNames"):
                focus.append("新增表单字段“" + "、".join(field_detail["addedNames"]) + "”")
            if field_detail and field_detail.get("updatedNames"):
                focus.append("表单字段能力调整“" + "、".join(field_detail["updatedNames"]) + "”")
            layout_detail = next((x for x in change["details"] if x["category"] == "表单布局"), None)
            if layout_detail:
                focus.append("表单布局调整")
            attribute_linkage_detail = next((x for x in change["details"] if x["category"] == "属性联动"), None)
            field_linkage_detail = next((x for x in change["details"] if x["category"] == "字段联动"), None)
            function_linkage_detail = next((x for x in change["details"] if x["category"] == "函数联动"), None)
            if attribute_linkage_detail:
                focus.append("属性联动调整")
            if field_linkage_detail:
                focus.append("字段联动调整")
            if function_linkage_detail:
                focus.append("函数联动调整")
            related_detail = next((x for x in change["details"] if x["category"] == "关联事项显示设置"), None)
            numbering_detail = next((x for x in change["details"] if x["category"] == "流程编号规则"), None)
            action_detail = next((x for x in change["details"] if x["category"] == "节点附加动作"), None)
            if related_detail:
                focus.append("关联事项打印显示调整")
            if numbering_detail:
                focus.append("流程编号规则调整")
            if action_detail:
                focus.append("节点附加动作调整")
            integration_detail = next((x for x in change["details"] if x["category"] == "外部接口服务"), None)
            if integration_detail:
                focus.append("外部接口服务地址切换")
            sql_detail = next((x for x in change["details"] if x["category"] == "工作流 SQL 数据源"), None)
            if sql_detail:
                focus.append("工作流 SQL 数据源调整")
            if not focus:
                focus = ["、".join(x["category"] for x in change["details"][:5]) or "流程设置"]
            test_points.append(f"回归流程“{name}”的{'及'.join(focus)}，覆盖路径可达性、正常通过、退回及异常路径。")
            view_detail = next((x for x in change["details"] if x["category"] == "节点字段查看规则"), None)
            if view_detail and view_detail.get("addedNames"):
                test_points.append(
                    f"在流程“{name}”中核对新增节点的表单字段："
                    + "、".join(view_detail["addedNames"])
                    + "，确认字段显示、只读和必填状态符合设计。"
                )
            if layout_detail:
                layout_focus = "、".join(
                    (layout_detail.get("addedNames") or []) + (layout_detail.get("updatedNames") or [])
                ) or "布局结构"
                test_points.append(
                    f"分别打开流程“{name}”的 PC 和移动端表单，核对{layout_focus}，并检查常用分辨率下无错位、遮挡或空白异常。"
                )
            for linkage_detail, label in (
                (attribute_linkage_detail, "属性联动"),
                (field_linkage_detail, "字段联动"),
                (function_linkage_detail, "函数联动"),
            ):
                if not linkage_detail:
                    continue
                rules = (
                    (linkage_detail.get("addedNames") or [])
                    + (linkage_detail.get("updatedNames") or [])
                )
                rule_text = "；".join(rules[:6]) or "本次调整的联动规则"
                test_points.append(
                    f"在流程“{name}”中验证{label}：{rule_text}。分别覆盖条件满足与不满足、"
                    "首次载入与字段值改变场景，确认显示属性、字段回填或计算结果符合设计。"
                )
            if related_detail:
                test_points.append(
                    f"在流程“{name}”中发起并关联一条事项后执行网页版打印，确认打印结果不再显示关联事项，同时正常办理页面不受影响。"
                )
            if numbering_detail:
                test_points.append(
                    f"连续发起两条流程“{name}”，确认新版自动生成流程编号，编号组成和顺序符合设计且不重复；退回后重新提交时按配置保留或重新生成。"
                )
            if action_detail:
                action_names = "、".join(action_detail.get("addedNames") or action_detail.get("updatedNames") or []) or "新增附加动作"
                test_points.append(
                    f"在流程“{name}”中完成审批并验证“{action_names}”：正常路径只执行一次、目标信息正确更新，重复提交不造成重复副作用，执行失败时有可确认的处理结果。"
                )
            if field_detail:
                for field_change in field_detail.get("updatedNames") or []:
                    field_name = field_change.split("：", 1)[0]
                    if "多选" in field_change:
                        test_points.append(
                            f"在流程“{name}”中为“{field_name}”选择多个值，保存后重新打开并提交；确认多值完整保留，且操作者、条件和后续动作读取结果正确。"
                        )
                    elif "最大输入长度" in field_change:
                        lengths = [int(value) for value in re.findall(r"\d+", field_change)]
                        boundary = "、".join(str(value) for value in sorted(set(lengths + [value + 1 for value in lengths])))
                        test_points.append(
                            f"在流程“{name}”中验证“{field_name}”的输入长度边界（{boundary} 个字符），保存并重新打开；确认范围内可完整保存，超限时按设计限制且不截断已有数据。"
                        )
                    elif "查看数据详情" in field_change:
                        expected = "不再提供数据详情入口" if "调整为关闭" in field_change else "可以打开关联数据详情"
                        test_points.append(
                            f"在流程“{name}”中定位“{field_name}”字段，完成选择、保存并尝试打开关联数据详情；确认新版{expected}，同时字段选择、展示和提交流转不受影响。"
                        )
            if integration_detail:
                resources = "、".join(
                    item.split("：", 1)[0] for item in integration_detail.get("updatedNames") or []
                ) or "相关中台接口"
                test_points.append(
                    f"验证流程“{name}”使用的{resources}连通性，覆盖初始化、查询、回写及失败提示的代表动作流；确认请求到达新服务地址，返回结果和异常处理符合设计。"
                )
            if sql_detail:
                test_points.append(
                    f"在目标环境验证流程“{name}”的 SQL 数据源：先核对数据库类型、连接、"
                    "对象和访问权限，再使用正常、空值和边界参数执行查询；确认结果字段类型、"
                    "返回数量、异常提示和执行耗时符合设计。"
                )
            title_detail = next((x for x in change["details"] if x["category"] == "流程标题组成"), None)
            if title_detail:
                test_points.append(
                    f"发起流程“{name}”，确认实例标题按“"
                    + "、".join(title_detail.get("addedNames") or title_detail.get("updatedNames") or [])
                    + "”生成。"
                )
    return {
        "schemaVersion": "ebuilder-workflow-diff/v1.0",
        "mode": "workflow",
        "direction": direction,
        "oldSummary": old_ir["summary"],
        "newSummary": new_ir["summary"],
        "changeSummary": {"新增": counts["新增"], "删除": counts["删除"], "更新": counts["更新"]},
        "changes": changes,
        "testPoints": test_points[:40],
        "coverageLedger": _coverage_ledger(old_ir, new_ir),
        "limitations": ["本报告基于离线保存态配置，不证明目标环境已迁入、启用或运行通过。", "组织、人员、角色、外部表单、动作流及子流程引用需在目标环境重新映射和验证。", "SQL 数据源只执行离线语义与静态配置检查；数据库连接、对象、权限、真实结果和性能必须在目标环境验证。", "两个包均未携带列表定义、列表字段、筛选、排序或行操作配置时，报告只标注“包内未提供”，不推断列表没有变化。"],
    }


def _scope_name(change: dict[str, Any]) -> str:
    unit = (change.get("packageUnit") or {}).get("name")
    comparable_unit = re.sub(r"\s*\(V\d+(?:\.\d+)*\)\s*$", "", unit or "", flags=re.IGNORECASE)
    return f"【{unit}】{change['name']}" if unit and comparable_unit != change["name"] else change["name"]


SUMMARY_LABELS = (
    ("workflowCount", "流程"), ("versionCount", "流程版本"),
    ("nodeCount", "节点"), ("linkCount", "连线"),
    ("conditionCount", "条件"), ("operatorGroupCount", "操作者组"),
    ("menuCount", "自定义节点菜单"), ("actionCount", "附加动作"),
    ("subflowCount", "子流程设置"), ("mappingCount", "字段映射"),
    ("formCount", "关联表单"), ("formFieldCount", "表单字段"),
    ("pcLayoutCount", "PC布局"), ("mobileLayoutCount", "移动布局"),
    ("layoutComponentCount", "布局组件"),
    ("attributeLinkageCount", "属性联动"),
    ("fieldLinkageCount", "字段联动"),
    ("functionLinkageCount", "函数联动"),
    ("titleRuleCount", "流程标题规则"),
    ("integrationCount", "外部接口服务"),
    ("sqlDataSourceCount", "工作流 SQL 数据源"),
)

SUMMARY_CATEGORY_KEYS = {
    "流程定义与版本": ("versionCount",),
    "流程节点": ("nodeCount",),
    "节点连线与出口": ("linkCount",),
    "流转条件": ("conditionCount",),
    "条件表达式": ("conditionCount",),
    "条件取值": ("conditionCount",),
    "节点操作者组": ("operatorGroupCount",),
    "节点操作者规则": ("operatorGroupCount",),
    "节点操作者": ("operatorGroupCount",),
    "发起人设置": ("operatorGroupCount",),
    "节点操作菜单": ("menuCount",),
    "节点自定义操作": ("menuCount",),
    "节点附加动作": ("actionCount",),
    "动作流绑定": ("actionCount",),
    "子流程设置": ("subflowCount",),
    "子流程触发规则": ("subflowCount",),
    "流程字段映射": ("mappingCount",),
    "关联表单": ("formCount",),
    "关联表单字段": ("formFieldCount",),
    "表单布局": ("layoutComponentCount",),
    "属性联动": ("attributeLinkageCount",),
    "字段联动": ("fieldLinkageCount",),
    "函数联动": ("functionLinkageCount",),
    "流程标题组成": ("titleRuleCount",),
    "流程标题规则": ("titleRuleCount",),
    "表单列表": ("listCount",),
    "外部接口服务": ("integrationCount",),
    "工作流 SQL 数据源": ("sqlDataSourceCount",),
}

SUMMARY_UPDATE_UNITS = {
    "workflowCount": "个流程", "versionCount": "处版本配置",
    "nodeCount": "处节点调整", "linkCount": "处路径调整",
    "conditionCount": "处条件调整", "operatorGroupCount": "处操作者调整",
    "menuCount": "处菜单调整", "actionCount": "处动作调整",
    "subflowCount": "处子流程调整", "mappingCount": "处映射调整",
    "formCount": "处表单调整", "formFieldCount": "处字段更新",
    "pcLayoutCount": "处布局更新", "mobileLayoutCount": "处布局更新",
    "layoutComponentCount": "处组件调整", "titleRuleCount": "处标题更新",
    "attributeLinkageCount": "处属性联动更新",
    "fieldLinkageCount": "处字段联动更新",
    "functionLinkageCount": "处函数联动更新",
    "listCount": "处列表更新", "listColumnCount": "处列表字段更新",
    "integrationCount": "个地址切换",
    "sqlDataSourceCount": "处 SQL 数据源更新",
}


def _detail_update_count(detail: dict[str, Any]) -> int:
    """Count retained configuration replacements, excluding pure net additions/removals."""
    updated = len(detail.get("updatedNames") or [])
    replaced = min(int(detail.get("added") or 0), int(detail.get("removed") or 0))
    return updated + replaced


def _summary_update_counts(diff: dict[str, Any]) -> dict[str, int]:
    counts = {key: 0 for key, _ in SUMMARY_LABELS}
    counts.update({"listCount": 0, "listColumnCount": 0})
    counts["workflowCount"] = int(diff.get("changeSummary", {}).get("更新") or 0)
    for change in diff.get("changes") or []:
        if change.get("changeType") != "更新":
            continue
        for detail in change.get("details") or []:
            amount = _detail_update_count(detail)
            for key in SUMMARY_CATEGORY_KEYS.get(detail.get("category"), ()):
                counts[key] += amount
    return counts


def _summary_rows(diff: dict[str, Any]) -> list[tuple[str, str]]:
    updates = _summary_update_counts(diff)
    old, new = diff.get("oldSummary") or {}, diff.get("newSummary") or {}
    indexed = list(enumerate(SUMMARY_LABELS))
    indexed.sort(key=lambda item: (
        -updates.get(item[1][0], 0),
        -abs(int(new.get(item[1][0], 0) or 0) - int(old.get(item[1][0], 0) or 0)),
        item[0],
    ))
    return [item for _, item in indexed]


def _update_text(key: str, count: int) -> str:
    return f"{count}{SUMMARY_UPDATE_UNITS.get(key, '处更新')}" if count else "—"


def _update_scope_text(diff: dict[str, Any], limit: int = 5) -> str:
    updates = _summary_update_counts(diff)
    scope_units = {"integrationCount": "个地址切换"}
    parts = []
    for key, label in _summary_rows(diff):
        if key == "workflowCount" or not updates.get(key):
            continue
        parts.append(f"{label}：{updates[key]}{scope_units.get(key, '处更新')}")
    return "、".join(parts[:limit])


def _linkage_overview(state: dict[str, Any] | None) -> list[str]:
    form = (state or {}).get("form") or {}
    groups = (
        ("属性联动", form.get("attributeLinkages") or []),
        ("字段联动", form.get("fieldLinkages") or []),
        ("函数联动", form.get("functionLinkages") or []),
    )
    result = []
    for label, items in groups:
        if not items:
            continue
        descriptions = [item.get("description") or item.get("name") or "联动规则" for item in items]
        shown = descriptions[:8]
        suffix = f"等{len(descriptions)}项" if len(descriptions) > len(shown) else ""
        result.append(f"{label}（{len(items)}项）：{'；'.join(shown)}{suffix}")
    return result


def render_report(diff: dict[str, Any]) -> str:
    old, new = diff["oldSummary"], diff["newSummary"]
    summary = diff["changeSummary"]
    update_counts = _summary_update_counts(diff)
    scope_text = _update_scope_text(diff)
    lines = ["# 流程版本功能差异报告", "", "## 1. 本次变化总览", "",
             "本报告按流程版本组还原并比较流程定义、活动版本、节点、连线、条件、操作者、菜单、动作、子流程、关联表单、表单字段、节点字段查看规则、属性联动、字段联动、函数联动、PC/移动布局、列表、流程标题、工作流 SQL 数据源和流程使用的外部接口服务。", "",
             f"> **变化提示：流程总数净变化 {new.get('workflowCount', 0)-old.get('workflowCount', 0):+d}，但有 {summary['更新']} 个流程发生配置更新"
             + (f"；涉及{scope_text}" if scope_text else "") + "。**", "",
             "| 流程视角 | 旧版 | 新版 | 数量净变化 | 配置更新 |", "|---|---:|---:|---:|---:|"]
    for key, label in _summary_rows(diff):
        update_text = _update_text(key, update_counts.get(key, 0))
        update_cell = f"**{update_text}**" if update_counts.get(key) else update_text
        lines.append(f"| {label} | {old.get(key,0)} | {new.get(key,0)} | {new.get(key,0)-old.get(key,0):+d} | {update_cell} |")
    if old.get("listCoverage") == "NOT_PACKAGED" and new.get("listCoverage") == "NOT_PACKAGED":
        lines += ["| 表单列表 | 包内未提供 | 包内未提供 | 无法判断 | 无法判断 |", "| 列表字段 | 包内未提供 | 包内未提供 | 无法判断 | 无法判断 |"]
    else:
        for key, label in (("listCount", "表单列表"), ("listColumnCount", "列表字段")):
            update_text = _update_text(key, update_counts.get(key, 0))
            update_cell = f"**{update_text}**" if update_counts.get(key) else update_text
            lines.append(f"| {label} | {old.get(key,0)} | {new.get(key,0)} | {new.get(key,0)-old.get(key,0):+d} | {update_cell} |")
    update_suffix = f"；存量更新涉及{scope_text}" if scope_text else ""
    lines += ["", f"共识别 {sum(summary.values())} 个变化流程：新增 {summary['新增']} 个、删除 {summary['删除']} 个、更新 {summary['更新']} 个{update_suffix}。", ""]
    section_numbers = {"新增": 2, "删除": 3, "更新": 4}
    for change_type in ("新增", "删除", "更新"):
        lines += [f"## {section_numbers[change_type]}. {change_type}流程", ""]
        items = [x for x in diff["changes"] if x["changeType"] == change_type]
        if not items:
            lines += [f"本次未识别到{change_type}流程。", ""]
            continue
        for index, item in enumerate(items, 1):
            lines += [f"### {section_numbers[change_type]}.{index} {_scope_name(item)}", ""]
            if change_type == "更新":
                related_forms = (item.get("after") or {}).get("form", {}).get("forms") or []
                if related_forms:
                    lines.append(f"- 对应表单：{'、'.join(related_forms)}。")
                for overview in _linkage_overview(item.get("after")):
                    lines.append(f"- {overview}。")
                for detail in item["details"]:
                    if detail["category"] == "工作流 SQL 数据源":
                        for row in detail.get("validationRows") or []:
                            lines.append(
                                "- 工作流 SQL 数据源："
                                f"{row['identity']}；{row['querySemantics']}；输入参数：{row['inputs']}；"
                                f"输出类型：{row['outputTypes']}；离线静态校验：{row['staticChecks']}；"
                                "数据库运行待目标环境验证。"
                            )
                        continue
                    delta = detail["afterCount"] - detail["beforeCount"]
                    added_names = "、".join(detail.get("addedNames") or [])
                    removed_names = "、".join(detail.get("removedNames") or [])
                    updated_names = "、".join(detail.get("updatedNames") or [])
                    note = detail.get("note")
                    if added_names or removed_names or updated_names:
                        actions = []
                        is_linkage = detail["category"] in {"属性联动", "字段联动", "函数联动"}
                        if added_names:
                            actions.append(f"新增规则：{added_names}" if is_linkage else f"新增“{added_names}”")
                        if removed_names:
                            actions.append(f"移除规则：{removed_names}" if is_linkage else f"移除“{removed_names}”")
                        if updated_names:
                            actions.append(f"调整规则：{updated_names}" if is_linkage else f"调整“{updated_names}”")
                        suffix = f"；{note}" if note else ""
                        lines.append(f"- {detail['category']}：{'；'.join(actions)}（{detail['beforeCount']} → {detail['afterCount']}，{delta:+d}{suffix}）。")
                    else:
                        lines.append(f"- {detail['category']}：配置发生调整（{detail['beforeCount']} → {detail['afterCount']}，{delta:+d}）。")
            else:
                state = item["after"] if change_type == "新增" else item["before"]
                lines.append(f"- 包含 {len(state['nodes'])} 个节点、{len(state['links'])} 条连线、{state['versionCount']} 个流程版本。")
                node_names = " → ".join(x["name"] for x in state["nodes"] if not x["deleted"])
                if node_names:
                    lines.append(f"- 主要节点：{node_names}。")
            lines.append("")
    lines += ["## 5. 重点验证清单", ""]
    if diff["testPoints"]:
        lines += [f"{i}. {text}" for i, text in enumerate(diff["testPoints"], 1)]
    else:
        lines += ["本次未识别到流程业务语义变化，因此不新增针对性验证点；迁入后仍建议执行流程发起、提交和结束的基础冒烟验证。"]
    lines += ["", "## 6. 结论边界", ""] + [f"- {x}" for x in diff["limitations"]] + [""]
    return "\n".join(lines)


def render_detail_report(diff: dict[str, Any]) -> str:
    lines = ["# 流程版本功能明细差异报告", "", "## 1. 流程对象变化汇总", "", "| 变化类型 | 数量 |", "|---|---:|"]
    for kind in ("新增", "删除", "更新"):
        lines.append(f"| {kind} | {diff['changeSummary'][kind]} |")
    lines += [""]
    if diff["oldSummary"].get("listCoverage") == "NOT_PACKAGED" and diff["newSummary"].get("listCoverage") == "NOT_PACKAGED":
        lines += ["> 列表覆盖说明：两个包均未携带列表定义、列表字段、筛选、排序或行操作配置，因此无法判断列表是否变化。", ""]
    for number, kind in enumerate(("新增", "删除", "更新"), 2):
        lines += [f"## {number}. {kind}流程明细", ""]
        items = [x for x in diff["changes"] if x["changeType"] == kind]
        if not items:
            lines += ["无。", ""]
            continue
        for item in items:
            lines += [f"### {_scope_name(item)}", ""]
            state = item["after"] or item["before"]
            lines += [f"- 流程版本数：{state['versionCount']}", f"- 对应表单：{'、'.join(state.get('form', {}).get('forms') or []) or '包内未识别'}", f"- 节点：{'、'.join(x['name'] for x in state['nodes']) or '无'}", f"- 连线：{'、'.join(x['name'] for x in state['links']) or '无'}"]
            lines.extend(f"- {overview}。" for overview in _linkage_overview(state))
            if kind == "更新":
                lines += ["", "| 变化区域 | 修改前 | 修改后 | 新增项 | 删除项 | 调整项 |", "|---|---:|---:|---:|---:|---:|"]
                for d in item["details"]:
                    lines.append(f"| {d['category']} | {d['beforeCount']} | {d['afterCount']} | {d['added']} | {d['removed']} | {len(d.get('updatedNames') or [])} |")
                for d in item["details"]:
                    if d["category"] == "工作流 SQL 数据源":
                        continue
                    statements = []
                    if d.get("addedNames"):
                        statements.append("新增：" + "、".join(d["addedNames"]))
                    if d.get("removedNames"):
                        statements.append("删除：" + "、".join(d["removedNames"]))
                    if d.get("updatedNames"):
                        statements.append("调整：" + "、".join(d["updatedNames"]))
                    if d.get("note"):
                        statements.append(d["note"])
                    if statements:
                        lines.append(f"- {d['category']}：{'；'.join(statements)}。")
                sql_rows = [
                    row for d in item["details"]
                    if d["category"] == "工作流 SQL 数据源"
                    for row in d.get("validationRows") or []
                ]
                if sql_rows:
                    lines += [
                        "", "#### 工作流 SQL 数据源离线校验", "",
                        "| 数据集身份 | 查询语义 | 输入参数 | 输出类型 | 离线静态校验 | 环境待验证 |",
                        "|---|---|---|---|---|---|",
                    ]
                    for row in sql_rows:
                        lines.append(
                            f"| {row['identity']} | {row['querySemantics']} | {row['inputs']} | "
                            f"{row['outputTypes']} | {row['staticChecks']} | {row['runtimePending']} |"
                        )
            lines.append("")
    return "\n".join(lines)


def render_html(diff: dict[str, Any]) -> str:
    summary_update_counts = _summary_update_counts(diff)
    customer_model = {
        "oldSummary": diff["oldSummary"],
        "newSummary": diff["newSummary"],
        "changeSummary": diff["changeSummary"],
        "summaryUpdateCounts": summary_update_counts,
        "testPoints": diff["testPoints"],
        "listCoverage": {
            "old": diff["oldSummary"].get("listCoverage"),
            "new": diff["newSummary"].get("listCoverage"),
        },
        "changes": [
            {
                "changeType": item["changeType"],
                "name": item["name"],
                "displayName": _scope_name(item),
                "linkageOverview": _linkage_overview(item.get("after") or item.get("before")),
                "details": [
                    {
                        "category": detail["category"],
                        "beforeCount": detail["beforeCount"],
                        "afterCount": detail["afterCount"],
                        "addedNames": detail.get("addedNames") or [],
                        "removedNames": detail.get("removedNames") or [],
                        "updatedNames": detail.get("updatedNames") or [],
                        "note": detail.get("note") or "",
                        "validationRows": detail.get("validationRows") or [],
                    }
                    for detail in item["details"]
                ],
            }
            for item in diff["changes"]
        ],
    }
    model = json.dumps(customer_model, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>流程版本功能差异可视化</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f4f7fb;color:#17213a;font:15px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif}}header{{background:linear-gradient(120deg,#173b85,#2868d8);color:white;padding:32px max(24px,6vw)}}main{{max-width:1200px;margin:auto;padding:24px}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px}}.card,.panel{{background:white;border:1px solid #dce5f2;border-radius:14px;padding:18px;box-shadow:0 8px 24px #173b8510}}.card strong{{display:block;font-size:28px}}.panel{{margin-top:18px}}.toolbar{{display:flex;gap:12px;flex-wrap:wrap;margin:14px 0}}select,input{{min-height:42px;border:1px solid #c8d5e8;border-radius:9px;padding:0 12px;background:white;min-width:190px}}table{{width:100%;border-collapse:collapse}}th,td{{padding:10px;border-bottom:1px solid #e7edf6;text-align:left;vertical-align:top}}tr.changed-row td{{background:#fff9ed}}.update-count{{display:inline-block;white-space:nowrap;color:#a34f00;background:#ffedcc;border:1px solid #f3bd65;border-radius:999px;padding:2px 9px;font-weight:800}}.summary-note{{margin:0 0 14px;padding:12px 14px;border-left:4px solid #ef8b17;background:#fff7e8;border-radius:8px;font-weight:700}}.tag{{display:inline-block;border-radius:999px;padding:2px 9px;font-weight:700}}.新增{{color:#137a3b;background:#e8f7ed}}.删除{{color:#b42318;background:#fff0ee}}.更新{{color:#b65b00;background:#fff5e7}}details{{border-top:1px solid #edf1f7;padding:12px 0}}summary{{cursor:pointer;font-weight:700}}.muted{{color:#66758f}}@media(max-width:700px){{header{{padding:24px}}main{{padding:14px}}table{{display:block;overflow:auto}}}}
</style></head><body><header><h1>流程版本功能差异可视化</h1><p>以流程版本组为单位，查看流程、节点、连线、关联表单、属性联动、字段联动、函数联动、布局、列表、SQL 数据源和审批规则变化</p></header><main><section class="cards" id="cards"></section><section class="panel"><h2>流程规模变化</h2><p class="summary-note" id="headline"></p><div id="summary"></div><p class="muted" id="coverage"></p></section><section class="panel"><h2>流程变化明细</h2><div class="toolbar"><select id="kind"><option value="">全部变化类型</option><option>新增</option><option>删除</option><option>更新</option></select><input id="q" placeholder="搜索流程名称"></div><div id="changes"></div></section><section class="panel"><h2>重点验证清单</h2><ol id="tests"></ol></section></main><script id="data" type="application/json">{model}</script><script>
const m=JSON.parse(document.getElementById('data').textContent),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const labels={{workflowCount:'流程',versionCount:'流程版本',nodeCount:'节点',linkCount:'连线',conditionCount:'条件',operatorGroupCount:'操作者组',menuCount:'自定义节点菜单',actionCount:'附加动作',subflowCount:'子流程设置',mappingCount:'字段映射',formCount:'关联表单',formFieldCount:'表单字段',pcLayoutCount:'PC布局',mobileLayoutCount:'移动布局',layoutComponentCount:'布局组件',attributeLinkageCount:'属性联动',fieldLinkageCount:'字段联动',functionLinkageCount:'函数联动',titleRuleCount:'流程标题规则',integrationCount:'外部接口服务',sqlDataSourceCount:'工作流 SQL 数据源'}};
const units={{workflowCount:'个流程',versionCount:'处版本配置',nodeCount:'处节点调整',linkCount:'处路径调整',conditionCount:'处条件调整',operatorGroupCount:'处操作者调整',menuCount:'处菜单调整',actionCount:'处动作调整',subflowCount:'处子流程调整',mappingCount:'处映射调整',formCount:'处表单调整',formFieldCount:'处字段更新',pcLayoutCount:'处布局更新',mobileLayoutCount:'处布局更新',layoutComponentCount:'处组件调整',attributeLinkageCount:'处属性联动更新',fieldLinkageCount:'处字段联动更新',functionLinkageCount:'处函数联动更新',titleRuleCount:'处标题更新',integrationCount:'个地址切换',sqlDataSourceCount:'处 SQL 数据源更新'}};
cards.innerHTML=['新增','删除','更新'].map(k=>`<div class="card"><span>${{k}}流程</span><strong class="${{k}}">${{m.changeSummary[k]}}</strong></div>`).join('');
const orderedKeys=Object.keys(labels).map((k,i)=>({{k,i}})).sort((a,b)=>(m.summaryUpdateCounts[b.k]||0)-(m.summaryUpdateCounts[a.k]||0)||Math.abs((m.newSummary[b.k]||0)-(m.oldSummary[b.k]||0))-Math.abs((m.newSummary[a.k]||0)-(m.oldSummary[a.k]||0))||a.i-b.i).map(x=>x.k);
const updateText=k=>m.summaryUpdateCounts[k]?`${{m.summaryUpdateCounts[k]}}${{units[k]||'处更新'}}`:'—';
const scope=orderedKeys.filter(k=>k!=='workflowCount'&&(m.summaryUpdateCounts[k]||0)).slice(0,5).map(k=>`${{labels[k]}}${{updateText(k)}}`).join('、');
headline.textContent=`流程总数净变化 ${{(m.newSummary.workflowCount||0)-(m.oldSummary.workflowCount||0)>=0?'+':''}}${{(m.newSummary.workflowCount||0)-(m.oldSummary.workflowCount||0)}}，但有 ${{m.changeSummary.更新}} 个流程发生配置更新${{scope?'；涉及'+scope:''}}。`;
summary.innerHTML=`<table><thead><tr><th>流程视角</th><th>旧版</th><th>新版</th><th>数量净变化</th><th>配置更新</th></tr></thead><tbody>${{orderedKeys.map(k=>{{const delta=(m.newSummary[k]||0)-(m.oldSummary[k]||0),updated=m.summaryUpdateCounts[k]||0;return `<tr class="${{delta||updated?'changed-row':''}}"><td>${{labels[k]}}</td><td>${{m.oldSummary[k]||0}}</td><td>${{m.newSummary[k]||0}}</td><td>${{delta>=0?'+':''}}${{delta}}</td><td>${{updated?`<span class="update-count">${{updateText(k)}}</span>`:'—'}}</td></tr>`}}).join('')}}</tbody></table>`;
coverage.textContent=m.listCoverage.old==='NOT_PACKAGED'&&m.listCoverage.new==='NOT_PACKAGED'?'列表覆盖说明：两个包均未携带列表定义、列表字段、筛选、排序或行操作配置，因此无法判断列表是否变化。':'';
function draw(){{const k=kind.value,s=q.value.trim().toLowerCase();const xs=m.changes.filter(x=>(!k||x.changeType===k)&&(!s||x.name.toLowerCase().includes(s)));changes.innerHTML=xs.length?xs.map(x=>`<details><summary><span class="tag ${{x.changeType}}">${{x.changeType}}</span> ${{esc(x.displayName)}}</summary>${{x.linkageOverview.length?`<ul>${{x.linkageOverview.map(v=>`<li>${{esc(v)}}</li>`).join('')}}</ul>`:''}}${{x.details.length?`<table><thead><tr><th>变化区域</th><th>修改前</th><th>修改后</th><th>具体内容</th></tr></thead><tbody>${{x.details.map(d=>`<tr><td>${{esc(d.category)}}</td><td>${{d.beforeCount}}</td><td>${{d.afterCount}}</td><td>${{esc([d.addedNames.length?'新增：'+d.addedNames.join('、'):'',d.removedNames.length?'删除：'+d.removedNames.join('、'):'',d.updatedNames.length?'调整：'+d.updatedNames.join('、'):'',d.note].filter(Boolean).join('；')||'配置调整')}}</td></tr>`).join('')}}</tbody></table>`:`<p class="muted">${{x.changeType==='新增'?'新增完整流程定义':'移除完整流程定义'}}</p>`}}</details>`).join(''):'<p class="muted">当前筛选条件下没有流程变化。</p>'}}kind.onchange=q.oninput=draw;draw();tests.innerHTML=m.testPoints.length?m.testPoints.map(x=>`<li>${{esc(x)}}</li>`).join(''):'<li>本次未识别到流程业务语义变化，建议执行流程发起、提交和结束的基础冒烟验证。</li>';
</script></body></html>'''
