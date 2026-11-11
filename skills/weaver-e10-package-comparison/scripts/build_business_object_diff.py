#!/usr/bin/env python3
"""把字段级事实聚合为表单、页面、动作流等一级业务功能对象。"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict, deque
from difflib import SequenceMatcher
from itertools import product
from typing import Any, Iterable

from workflow_sql_datasource import pair_workflow_sql_summaries


TYPE_ORDER = [
    ("表单", "FORM"),
    ("页面", "PAGE"),
    ("嵌入式视图", "EMBEDDED_VIEW"),
    ("动作流", "ESB_ACTION_FLOW"),
    ("工作流/审批流程", "WORKFLOW"),
    ("菜单", "MENU"),
    ("导航", "NAVIGATION"),
    ("报表", "REPORT"),
    ("多级填报", "MULTI_FILLING"),
    ("独立数据集", "DATASET"),
    ("业务资源绑定", "EXTERNAL_INTEGRATION"),
    ("权限", "PERMISSION"),
]

ROOT_SPECS = {
    "FORM": (("ebuilder-form",), ("form",)),
    "PAGE": (("ebuilder-app",), ("ebdp_page",)),
    "EMBEDDED_VIEW": (("ebuilder-form",), ("ebdf_view_designer",)),
    "ESB_ACTION_FLOW": (("esb-setting",), ("esb_application",)),
    "WORKFLOW": (("ebuilder-form", "bpm", "workflow-pathdef"), ("wfp_base", "wfc_base", "bpm_process")),
    "MENU": (("cusapp",), ("t_cus_app_system_menu", "t_cus_app_tenant_menu")),
    "NAVIGATION": (("cusapp",), ("t_cus_app_navigation",)),
    "REPORT": (("edcreport",), ("edc_report_dev",)),
    "MULTI_FILLING": (("edcapp",), ("edc_multi_task", "edc_multi_filling")),
    "DATASET": (("ebuilder-app",), ("dataset",)),
    "EXTERNAL_INTEGRATION": (("esb-setting",), ("esb_app_association",)),
}

PERMISSION_TABLES = {
    "ebdf_permission": "表单权限",
    "field_permission": "字段权限",
    "ebdp_page_ph_ebdcomm_view": "页面权限",
    "cus_app_ph_sys_view": "菜单/应用权限",
    "edc_report_ph_report_view": "报表权限",
}

FORM_CHILD_TABLES = {
    "ebdf_obj",
    "form_field",
    "sub_form",
    "sub_form_config",
    "form_layout_multiple",
    "form_layout_version",
    "ebdf_list",
    "ebdf_list_field",
    "ebdf_list_filter",
    "ebdf_button",
    "ebdf_button_action",
    "ebdf_button_esb",
    "ebdf_button_esb_list",
    "ebdf_codeblock",
    "ebdf_custom_tips",
    "ebdf_data_association",
    "ebdf_import_export_setting",
    "fd_linkage",
    "fd_linkage_source_esb",
    "form_view_linkage",
    "form_data_relate_config",
    "form_ecode",
    "form_ecode_detail",
    "ebdd_page_layout",
    "ebdd_layout_component",
    "panel_field",
    # Shared scope rows may belong to either a form or a workflow. Form-owned
    # rows are resolved through business_id in the form graph; workflow-owned
    # rows are handled separately by _workflow_children.
    "browser_data_scope",
}

PAGE_CHILD_TABLES = {
    "ebdd_page_extended",
    "ebdd_page_layout",
    "ebdd_layout_component",
    "ebdd_layout_component_style",
    "ebdd_list_button_item",
    "ebdd_list_btn_ph_ebdcomm_view",
    "ebdd_navmenu_item",
}

WORKFLOW_CHILD_TABLES = {
    "browser_data_scope",
    "wfp_cpt_base",
    "wfp_cpt_set",
}

NON_BUSINESS_CHANGE_TABLES = {
    "esb_app_statistics",
    "ebdd_layout_component_style",
}

RECREATED_DETAIL_TABLES = FORM_CHILD_TABLES | PAGE_CHILD_TABLES | WORKFLOW_CHILD_TABLES

MIGRATION_ALIAS_PATHS = {
    "browser_type",
    "other_properties.browsertype.type",
    "other_properties.columnname",
    "other_properties.datakey",
    "other_properties.regular.express",
}

# 新版表单服务会为既有表单补写这一整块缺省操作能力。旧包缺字段、
# 新包写入完整默认值只表示保存格式升级，不代表客户功能发生变化。
DEFAULT_EBDF_OPERATE_LOG_INFO = {
    "batchAdd": True,
    "batchEdit": True,
    "batchEditValue": True,
    "cardOperate": True,
    "ebdfInterface": False,
    "ebdfInterfaceType": 1,
    "editableList": True,
    "esb": False,
    "esbType": 1,
    "excelImport": True,
    "excludeEbdfInterfaces": [],
    "excludeEsbs": [],
    "specifiedEbdfInterfaces": [],
    "specifiedEsbs": [],
}

NOISE_PATH_PARTS = {
    "source_id",
    "target_id",
    "labelid",
    "label_id",
    "uuid",
    "created",
    "create_time",
    "updated",
    "update_time",
    "updatetime",
    "lastchangeid",
    "modify_time",
    "migration",
    "batch",
}

PURPOSE_RULES = [
    ("催办", "执行催办并记录或回写催办结果"),
    ("反馈", "支撑反馈提交、审核、归档或状态回写"),
    ("办结", "支撑办结申请、校验、审批或结果回写"),
    ("延期", "支撑延期申请、审批或期限更新"),
    ("立项", "支撑事项创建、批量立项或立项后处理"),
    ("类型", "支撑业务类型、模板、布局或分类配置"),
    ("周期", "生成周期进展数据或执行周期预警提醒"),
    ("预警", "识别临期或超期状态并触发提醒"),
    ("门户", "集中展示业务数据、统计指标和常用入口"),
    ("待办", "集中展示并处理当前用户待办任务"),
    ("评分", "读取、计算或回写业务评价结果"),
    ("拒收", "支撑任务拒收及相关流程回写"),
    ("分派", "支撑任务分派及责任关系调整"),
    ("转办", "支撑任务转办及责任关系调整"),
    ("分解", "支撑任务分解、子任务创建或上级任务回写"),
    ("报表", "提供业务数据查询和统计分析"),
    ("权限", "控制功能对象的查看、编辑或执行范围"),
]

DEFAULT_PURPOSE = {
    "FORM": "承载业务数据录入、维护和列表操作",
    "PAGE": "提供页面展示、查询或业务操作入口",
    "EMBEDDED_VIEW": "在表单或页面中嵌入列表、甘特图或关联视图",
    "ESB_ACTION_FLOW": "执行跨表单、流程、页面或外部服务的业务自动化",
    "WORKFLOW": "承载审批流程、节点流转和业务状态处理",
    "MENU": "向用户提供应用功能入口",
    "NAVIGATION": "组织应用菜单层级和打开方式",
    "REPORT": "提供结构化统计报表和查看入口",
    "MULTI_FILLING": "组织多级填报任务、节点和汇总过程",
    "DATASET": "为页面、图表或列表提供查询数据",
    "EXTERNAL_INTEGRATION": "连接动作流与表单、流程或其他业务资源",
    "PERMISSION": "控制功能可见范围和操作授权",
    "APPLICATION_SHELL": "承载应用基础信息和组织维度配置",
    "OTHER": "提供可独立配置的扩展业务能力",
}

# 面向客户的兜底名称。对象确实存在但包内没有可稳定还原的名称时，
# 仍然给出“它是什么功能”的中文称呼，不把 content=/parent= 等逻辑键
# 暴露给业务读者。完整身份继续保留在机器可读证据层。
FUNCTIONAL_FALLBACK_NAMES = {
    "FORM": "业务表单",
    "PAGE": "业务页面",
    "EMBEDDED_VIEW": "嵌入式业务视图",
    "ESB_ACTION_FLOW": "业务动作流",
    "WORKFLOW": "审批流程",
    "MENU": "应用菜单入口",
    "NAVIGATION": "应用导航配置",
    "REPORT": "业务报表",
    "MULTI_FILLING": "多级填报任务",
    "DATASET": "业务数据集",
    "EXTERNAL_INTEGRATION": "跨模块业务资源绑定",
    "PERMISSION": "功能权限配置",
    "APPLICATION_SHELL": "应用基础配置",
    "OTHER": "业务扩展功能",
}


def _functional_name(value: Any, object_type: str) -> str:
    """返回不泄露逻辑键的客户可读名称。"""

    text = _strip_generated_timestamps(value)
    if (
        text in {"名称待确认", "待确认业务功能", "待确认业务功能（技术名称未还原）"}
        or re.match(r"^undefined(?:_|$)", text, flags=re.IGNORECASE)
        or any(token in text for token in (
            "migration-source=", "profile-lineage=", "idm-lineage=", "idm-context=", "content=", "parent=",
        ))
    ):
        return FUNCTIONAL_FALLBACK_NAMES.get(object_type, "业务功能")
    return text


def _component_business_name(value: Any) -> str:
    """去除布局组件类型前的迁移身份上下文。"""

    text = _clean(value).replace('type="', "").rstrip('"')
    text = re.sub(
        r"^.*?(?:idm-lineage|idm-context)=[0-9a-f]{16,64}::",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return text or "组件"

ENTRY_RULES = {
    "FORM": "由菜单、页面按钮、动作流或审批流程进入",
    "PAGE": "由应用菜单、页面跳转或门户入口进入",
    "EMBEDDED_VIEW": "由所属表单或页面内部进入",
    "ESB_ACTION_FLOW": "由表单按钮、页面交互、流程事件、定时任务或子动作流触发",
    "WORKFLOW": "由流程发起入口、表单按钮或业务事件进入",
    "MENU": "由应用导航进入",
    "NAVIGATION": "由应用首页或导航栏进入",
    "REPORT": "由报表菜单或报表查看入口进入",
    "MULTI_FILLING": "由填报任务入口进入",
    "DATASET": "由页面、图表或列表间接使用",
    "EXTERNAL_INTEGRATION": "由关联动作流或业务事件间接触发",
    "PERMISSION": "由对应功能对象的授权配置生效",
}


def _clean(value: Any) -> str:
    if value in (None, ""):
        return "名称待确认"
    return str(value).replace("~`~`", "").replace("`~`~", "").strip()


def _strip_generated_timestamps(value: Any) -> str:
    text = _clean(value)
    text = re.sub(r"\(?\d{4}-\d{2}-\d{2}[ _]\d{2}:\d{2}:\d{2}\)?", "", text)
    text = re.sub(r"(?<!\d)\d{14}(?!\d)", "", text)
    return re.sub(r"[\s\-_（）()]+$", "", text).strip()


def _canonical_name(value: str) -> str:
    value = _strip_generated_timestamps(value)
    value = re.sub(r"（?(?:单位|部门|个人)）?", "", value)
    value = re.sub(r"[\s\-—_（）()【】\[\]：:]+", "", value)
    return value.lower()


def _name_score(old: str, new: str) -> float:
    left, right = _canonical_name(old), _canonical_name(new)
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    return SequenceMatcher(None, left, right).ratio()


def _purpose(name: str, object_type: str) -> str:
    for token, text in PURPOSE_RULES:
        if token in name:
            return text
    return DEFAULT_PURPOSE.get(object_type, "提供对应业务功能")


def _walk(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _refs(value: Any) -> set[str]:
    result = set()
    for item in _walk(value):
        if isinstance(item, dict) and isinstance(item.get("$ref"), str):
            result.add(item["$ref"])
    return result


def _field(value: Any, *names: str) -> Any:
    lowered = {name.lower() for name in names}
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in lowered and child not in (None, "", [], {}):
                return child
    return None


def _ref_display(value: Any, table: str | None = None) -> str | None:
    for ref in sorted(_refs(value)):
        if table and f"::{table}::" not in ref:
            continue
        for field in ("name", "menu_name", "page_name", "form_name", "report_name", "table_name"):
            match = re.search(rf'{field}=(?:\\"|")([^"\\]+)', ref)
            if match:
                return _clean(match.group(1))
        tail = ref.split("::")[-1]
        if tail:
            return _clean(tail[:120])
    return None


def _side_exists(fact: dict[str, Any], side: str) -> bool:
    return fact.get("beforeHash" if side == "old" else "afterHash") is not None


def _side_object(fact: dict[str, Any], side: str) -> dict[str, Any] | None:
    return fact.get("oldObject") if side == "old" else fact.get("object")


def _side_value(fact: dict[str, Any], side: str) -> Any:
    return fact.get("before") if side == "old" else fact.get("after")


def _scoped_name(obj: dict[str, Any] | None, name: Any) -> str:
    text = _clean(name)
    unit = (obj or {}).get("packageUnit") or {}
    unit_name = _clean(unit.get("name")) if unit else ""
    if unit_name and not text.startswith(f"【{unit_name}】"):
        return f"【{unit_name}】{text}"
    return text


def _variants(key: str) -> set[str]:
    values = {key, re.sub(r"::occurrence=\d+$", "", key)}
    for value in list(values):
        values.add(re.sub(r"(::parent=[0-9a-f]{16})::content=[0-9a-f]{16}$", r"\1", value))
        values.add(re.sub(r"::content=[0-9a-f]{16}$", "", value))
        values.add(
            re.sub(
                r"::parent=[0-9a-f]{16}(?:::content=[0-9a-f]{16})?(?:::occurrence=\d+)?$",
                "",
                value,
            )
        )
    return {item for item in values if item}


def _parent_token(key: str) -> str | None:
    match = re.search(r"::parent=([0-9a-f]{16})", key)
    return match.group(1) if match else None


def _module_matches(module: str, tokens: tuple[str, ...]) -> bool:
    lowered = module.lower()
    return any(token in lowered for token in tokens)


def _root_objects(index: dict[str, Any], object_type: str) -> list[dict[str, Any]]:
    modules, tables = ROOT_SPECS[object_type]
    return [
        item
        for item in index.get("objects") or []
        if _module_matches(item.get("module", ""), modules)
        and str(item.get("table", "")).lower() in tables
    ]


def _object_name(item: dict[str, Any], object_type: str) -> str:
    canonical = item.get("canonical") or {}
    candidates = {
        "FORM": ("name", "form_name", "table_name"),
        "PAGE": ("name", "page_name", "title"),
        "EMBEDDED_VIEW": ("view_name", "name", "title"),
        "ESB_ACTION_FLOW": ("name", "app_name", "title"),
        "WORKFLOW": ("name", "workflowname", "workflow_name", "flow_name", "title"),
        "MENU": ("menu_name", "name", "title"),
        "NAVIGATION": ("navigation_name", "name", "title"),
        "REPORT": ("report_name", "name", "title"),
        "MULTI_FILLING": ("task_name", "name", "title"),
        "DATASET": ("dataset_name", "name", "title"),
        "EXTERNAL_INTEGRATION": ("name", "title"),
    }.get(object_type, ("name", "title"))
    value = _field(canonical, *candidates)
    if isinstance(value, (str, int, float)):
        return _clean(value)
    return _clean(item.get("displayName"))


def _facts_for_table(facts: list[dict[str, Any]], module_token: str, table: str) -> list[dict[str, Any]]:
    return [
        fact
        for fact in facts
        if module_token in str(fact["object"].get("module", "")).lower()
        and str(fact["object"].get("table", "")).lower() == table
    ]


def _evidence(facts: Iterable[dict[str, Any]], limit: int = 16) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for fact in facts:
        change_id = fact.get("changeId")
        if change_id in seen:
            continue
        seen.add(change_id)
        source = fact.get("object", {}).get("sourceEvidence") or {}
        result.append(
            {
                "changeId": change_id,
                "module": fact.get("object", {}).get("module"),
                "table": fact.get("object", {}).get("table"),
                "recordOrdinal": source.get("recordOrdinal"),
            }
        )
        if len(result) >= limit:
            break
    return result


def _make_object(
    *,
    object_type: str,
    name: str,
    logical_key: str,
    change_type: str,
    old_exists: bool,
    new_exists: bool,
    facts: Iterable[dict[str, Any]] = (),
    old_summary: Any = None,
    new_summary: Any = None,
    internal_changes: list[dict[str, Any]] | None = None,
    affected: list[str] | None = None,
    confidence: str = "HIGH",
    purpose: str | None = None,
    entry: str | None = None,
) -> dict[str, Any]:
    business_name = _functional_name(name, object_type)
    return {
        "objectType": object_type,
        "logicalKey": logical_key,
        "name": business_name,
        "businessName": business_name,
        "businessPurpose": purpose or _purpose(business_name, object_type),
        "oldExists": old_exists,
        "newExists": new_exists,
        "changeType": change_type,
        "oldSummary": old_summary,
        "newSummary": new_summary,
        "internalChanges": internal_changes or [],
        "userEntry": entry or (
            f"应用菜单“{business_name}”"
            if object_type == "MENU"
            else ENTRY_RULES.get(object_type, "入口由上游配置决定")
        ),
        "affectedFunctions": affected or [],
        "evidence": _evidence(facts),
        "confidence": confidence,
    }


def _relevant_paths(fact: dict[str, Any], *, keep_reference: bool = False) -> list[dict[str, Any]]:
    result = []
    for path in fact.get("changedPaths") or []:
        if path.get("before") == path.get("after"):
            # 旧记录缺字段而新记录显式保存 null 时，事实层会保留
            # FIELD_ADDED，但业务值并未变化，不能抬升成业务更新。
            continue
        name = str(path.get("path") or "").lower()
        if any(part in name for part in NOISE_PATH_PARTS):
            continue
        if not keep_reference and (
            name == "$ref"
            or name.endswith(".$ref")
            or ".$ref." in name
            or name.endswith(".$unresolvedid")
            or ".$unresolvedid." in name
        ):
            continue
        if name.startswith("source_code") and any(
            token in json.dumps(path, ensure_ascii=False).lower()
            for token in ("css", "style", "cache")
        ):
            continue
        result.append(path)
    return result


def _is_owner_reference_path(path: dict[str, Any]) -> bool:
    """Return True for an internal parent/layout/page pointer, not a business binding."""

    name = str(path.get("path") or "").lower()
    if not (
        name == "$ref"
        or name.endswith(".$ref")
        or ".$ref." in name
        or name.endswith(".$unresolvedid")
        or ".$unresolvedid." in name
    ):
        return False
    owner_fields = {
        "layout_id", "page_id", "form_id", "version_id", "multiple_layout_id",
        "parent_id", "ref_comp_id", "ref_layout_id", "extended_id",
    }
    field = name.split(".$", 1)[0].split(".")[-1]
    return field in owner_fields


def _business_configuration_paths(fact: dict[str, Any]) -> list[dict[str, Any]]:
    """Keep business configuration changes while dropping internal ownership churn."""

    paths = [
        path for path in _relevant_paths(fact, keep_reference=True)
        if not _is_owner_reference_path(path)
    ]
    if paths and all(
        str(path.get("path") or "").lower().endswith((".$ref", ".$unresolvedid"))
        for path in paths
    ) and not any(
        path.get("operation") == "VALUE_UPDATED"
        and _reference_semantic_label(path.get("before"))
        != _reference_semantic_label(path.get("after"))
        for path in paths
    ):
        # The parser resolved an ID on one side only. This is an evidence-quality
        # improvement, not a user-visible binding change.
        return []
    semantic_paths = []
    table = str((fact.get("object") or fact.get("oldObject") or {}).get("table", "")).lower()
    for path in paths:
        name = str(path.get("path") or "").lower()
        before, after = path.get("before"), path.get("after")
        if table == "ebdf_obj" and name == "operate_log_info":
            saved_value = after if before in (None, "") else before
            if (
                (before in (None, "") or after in (None, ""))
                and saved_value == DEFAULT_EBDF_OPERATE_LOG_INFO
            ):
                continue
        if name.endswith(".$ref") and _reference_semantic_label(before) == _reference_semantic_label(after):
            continue
        if name in MIGRATION_ALIAS_PATHS:
            before_alias = re.sub(r"_V\d{16,20}", "", str(before or ""))
            after_alias = re.sub(r"_V\d{16,20}", "", str(after or ""))
            if before_alias == after_alias:
                continue
        if (
            table == "browser_data_scope"
            and isinstance(before, dict)
            and isinstance(after, dict)
            and before.get("truncated")
            and after.get("truncated")
        ):
            # 事实层只保留了截断摘要，无法证明范围条件本身变化；
            # 保留技术事实，但不得据此生成客户业务更新。
            continue
        if table == "browser_data_scope" and (
            _normalized_without_reference_instances(before)
            == _normalized_without_reference_instances(after)
        ):
            continue
        if _normalized_structure(before) == _normalized_structure(after):
            continue
        semantic_paths.append(path)
    return semantic_paths


def _reference_semantic_label(value: Any) -> str:
    """Normalize a logical reference to its stable business label/type."""

    text = str(value or "")
    if not text:
        return ""
    table = text.split("::")[1] if "::" in text and len(text.split("::")) > 2 else ""
    values = []
    for field in ("name", "menu_name", "page_name", "form_name", "report_name", "table_name", "type"):
        match = re.search(rf'{field}=(?:\\"|")([^"\\]+)', text)
        if match:
            label = match.group(1)
            if field in {"name", "menu_name", "page_name", "form_name", "report_name"}:
                label = _strip_generated_timestamps(label)
            values.append(f"{field}={label}")
    return table + "::" + "|".join(values)


def _stable_reference_identity(value: Any) -> str:
    text = str(value or "")
    table = text.split("::")[1] if "::" in text and len(text.split("::")) > 2 else ""
    for token in ("idm-lineage", "idm-context"):
        match = re.search(rf"{token}=([0-9a-f]{{16,64}})", text)
        if match:
            return f"{table}::{token}={match.group(1)}"
    return _reference_semantic_label(text) or text


def _normalized_structure(value: Any) -> Any:
    """Remove instance-only reference IDs while retaining names and structure."""

    if isinstance(value, dict):
        return {
            key: _normalized_structure(child)
            for key, child in sorted(value.items())
            if str(key).lower() not in {"nodeid", "id", "uuid"}
        }
    if isinstance(value, list):
        return [_normalized_structure(child) for child in value]
    if isinstance(value, str) and "::" in value:
        return _reference_semantic_label(value)
    return value


def _normalized_without_reference_instances(value: Any) -> Any:
    """比较共享明细内容时忽略仅代表当前环境实例的引用值。"""

    if isinstance(value, dict):
        if "$ref" in value or "$unresolvedId" in value:
            return {"$reference": "present"}
        return {
            key: _normalized_without_reference_instances(child)
            for key, child in sorted(value.items())
            if str(key).lower() not in {"id", "nodeid", "uuid"}
        }
    if isinstance(value, list):
        return [_normalized_without_reference_instances(child) for child in value]
    return value


def _detail_fact_signature(fact: dict[str, Any]) -> tuple[str, str, str] | None:
    """为同一父对象下重建但内容等价的共享明细生成保守签名。"""

    change_type = str(fact.get("changeType") or "")
    if change_type not in {"ADDED", "REMOVED", "UNMATCHED"}:
        return None
    obj = fact.get("object") or fact.get("oldObject") or {}
    table = str(obj.get("table") or "").lower()
    if table not in RECREATED_DETAIL_TABLES:
        return None
    canonical = obj.get("canonical") or {}
    payload = (
        fact.get("before")
        if change_type == "REMOVED" or fact.get("after") is None
        else fact.get("after")
    )
    parent = ""
    for field in ("business_id", "form_id", "workflow_id", "application_id"):
        value = canonical.get(field)
        if isinstance(value, dict) and value.get("$ref"):
            parent = _stable_reference_identity(value["$ref"])
            break
    if not parent and isinstance(payload, dict) and isinstance(payload.get("summary"), str):
        match = re.search(
            r'"(?:business_id|form_id|obj_id|list_id|layout_id|button_id|field_id)":\{"\$ref":"([^"]+)"\}',
            payload["summary"],
        )
        if match:
            parent = _stable_reference_identity(match.group(1))
    if not parent:
        parent = str(obj.get("parentIdentityKey") or "")
    if not parent:
        return None
    normalized = _normalized_without_reference_instances(payload)
    digest = hashlib.sha256(
        json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return table, parent, digest


def _suppress_equivalent_recreated_details(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """抵消同一父对象下内容相同的一增一删共享明细。"""

    added: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    removed: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for fact in facts:
        signature = _detail_fact_signature(fact)
        if not signature:
            continue
        change_type = str(fact.get("changeType") or "")
        bucket = removed if change_type == "REMOVED" or fact.get("after") is None else added
        bucket[signature].append(str(fact.get("changeId")))
    suppressed = set()
    for signature in set(added) & set(removed):
        pair_count = min(len(added[signature]), len(removed[signature]))
        suppressed.update(sorted(added[signature])[:pair_count])
        suppressed.update(sorted(removed[signature])[:pair_count])
    return [fact for fact in facts if str(fact.get("changeId")) not in suppressed]


def _is_business_configuration_fact(fact: dict[str, Any]) -> bool:
    """判断子配置事实是否足以触发所属一级业务对象更新。"""

    if fact.get("changeType") == "UNCHANGED":
        return False
    table = str((fact.get("object") or {}).get("table", "")).lower()
    if table in NON_BUSINESS_CHANGE_TABLES:
        return False
    if fact.get("changeType") == "POSSIBLE_RENAME" and (
        fact.get("beforeHash") == fact.get("afterHash")
        or _normalized_structure(fact.get("before")) == _normalized_structure(fact.get("after"))
    ):
        return False
    if fact.get("changeType") == "UPDATED":
        return bool(_business_configuration_paths(fact))
    return True


def _child_change_facts(
    old_children: list[dict[str, Any]],
    new_children: list[dict[str, Any]],
    facts_by_key: dict[str, dict[str, Any]],
    facts_by_old_key: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """按新旧两侧子对象键收集变化事实，并保持确定性去重顺序。"""

    candidates = []
    for child in old_children:
        fact = facts_by_old_key.get(child.get("logicalKey"))
        if fact:
            candidates.append(fact)
    for child in new_children:
        fact = facts_by_key.get(child.get("logicalKey"))
        if fact:
            candidates.append(fact)
    result = []
    seen = set()
    for fact in sorted(candidates, key=lambda item: str(item.get("changeId") or "")):
        change_id = fact.get("changeId")
        if change_id in seen or not _is_business_configuration_fact(fact):
            continue
        seen.add(change_id)
        result.append(fact)
    return _suppress_equivalent_recreated_details(result)


def _child_rollup_coverage(
    facts: list[dict[str, Any]],
    old_form_children: dict[str, list[dict[str, Any]]],
    new_form_children: dict[str, list[dict[str, Any]]],
    old_page_children: dict[str, list[dict[str, Any]]],
    new_page_children: dict[str, list[dict[str, Any]]],
    old_workflow_children: dict[str, list[dict[str, Any]]],
    new_workflow_children: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """核对已知业务子表的真实变化是否都能唯一回溯到一级对象。"""

    facts_by_key = {fact["object"]["logicalKey"]: fact for fact in facts}
    facts_by_old_key = {
        (fact.get("oldObject") or {}).get("logicalKey"): fact
        for fact in facts if fact.get("oldObject")
    }

    rolled_up: set[str] = set()
    for child_map, side in (
        (old_form_children, "old"), (new_form_children, "new"),
        (old_page_children, "old"), (new_page_children, "new"),
        (old_workflow_children, "old"), (new_workflow_children, "new"),
    ):
        lookup = facts_by_old_key if side == "old" else facts_by_key
        for children in child_map.values():
            for child in children:
                fact = lookup.get(child.get("logicalKey"))
                if fact and _is_business_configuration_fact(fact):
                    rolled_up.add(str(fact.get("changeId")))

    expected: dict[str, dict[str, Any]] = {}
    ignored_equivalent = 0
    for fact in facts:
        obj = fact.get("object") or fact.get("oldObject") or {}
        module = str(obj.get("module") or "").lower()
        table = str(obj.get("table") or "").lower()
        tracked = (
            ("ebuilder-form" in module and table in FORM_CHILD_TABLES)
            or ("ebuilder-app" in module and table in PAGE_CHILD_TABLES)
            or table in WORKFLOW_CHILD_TABLES
        )
        if not tracked or not _is_business_configuration_fact(fact):
            continue
        if fact.get("changeType") == "POSSIBLE_RENAME" and fact.get("beforeHash") == fact.get("afterHash"):
            ignored_equivalent += 1
            continue
        change_id = str(fact.get("changeId"))
        expected[change_id] = {
            "changeId": change_id,
            "module": obj.get("module"),
            "table": obj.get("table"),
            "changeType": fact.get("changeType"),
        }

    unresolved = [expected[key] for key in sorted(set(expected) - rolled_up)]
    blocking_missing = [
        item for item in unresolved
        if str(item.get("table") or "").lower() in WORKFLOW_CHILD_TABLES
    ]
    by_table: dict[str, dict[str, int]] = defaultdict(lambda: {"expected": 0, "rolledUp": 0})
    for item in expected.values():
        by_table[str(item.get("table"))]["expected"] += 1
        if item["changeId"] in rolled_up:
            by_table[str(item.get("table"))]["rolledUp"] += 1
    return {
        "valid": not blocking_missing,
        "complete": len(expected) == len(set(expected) & rolled_up) + len(unresolved),
        "expected": len(expected),
        "rolledUp": len(set(expected) & rolled_up),
        "unresolved": unresolved,
        "blockingMissing": blocking_missing,
        "ignoredEquivalentPossibleRename": ignored_equivalent,
        "byTable": dict(sorted(by_table.items())),
    }


def _configuration_change_entries(
    facts: list[dict[str, Any]],
    *,
    limit: int = 48,
) -> list[dict[str, Any]]:
    """把子配置事实转换为可报告的前后值摘要；完整事实仍只保存在事实层。"""

    result = []
    for fact in facts:
        obj = fact.get("object") or {}
        old_obj = fact.get("oldObject") or {}
        paths = _business_configuration_paths(fact)
        fields = [
            {
                "path": item.get("path"),
                "before": item.get("before"),
                "after": item.get("after"),
                "category": item.get("category"),
                "operation": item.get("operation"),
            }
            for item in paths[:12]
        ]
        if not fields:
            fields = [{
                "path": "record",
                "before": fact.get("before"),
                "after": fact.get("after"),
                "category": "OBJECT_EXISTENCE",
                "operation": fact.get("changeType"),
            }]
        table = obj.get("table") or old_obj.get("table")
        item_name = _clean(obj.get("displayName") or old_obj.get("displayName"))
        if any(token in item_name for token in ("migration-source=", "content=", "parent=")):
            friendly = {
                "form_ecode": "表单扩展代码",
                "form_ecode_detail": "表单扩展代码明细",
                "ebdd_navmenu_item": "页面导航项",
                "ebdd_list_button_item": "页面列表按钮项",
                "ebdd_page_layout": "页面布局",
                "browser_data_scope": "关联数据范围",
            }
            item_name = friendly.get(str(table or "").lower(), "业务子配置")
        result.append({
            "kind": "CHILD_CONFIGURATION_CHANGE",
            "changeId": fact.get("changeId"),
            "changeType": fact.get("changeType"),
            "table": table,
            "itemName": item_name,
            "fields": fields,
        })
        if len(result) >= limit:
            break
    return result


def _pair_renames(
    old_only: list[dict[str, Any]],
    new_only: list[dict[str, Any]],
    object_type: str,
    *,
    threshold: float = 0.72,
) -> tuple[list[tuple[dict[str, Any], dict[str, Any], float]], list[dict[str, Any]], list[dict[str, Any]]]:
    candidates = []
    for old in old_only:
        for new in new_only:
            if old.get("packageUnitKey") != new.get("packageUnitKey"):
                continue
            score = _name_score(old["name"], new["name"])
            if score >= threshold:
                candidates.append((score, old, new))
    pairs = []
    used_old: set[str] = set()
    used_new: set[str] = set()
    for score, old, new in sorted(candidates, key=lambda item: (-item[0], item[1]["name"], item[2]["name"])):
        if old["key"] in used_old or new["key"] in used_new:
            continue
        used_old.add(old["key"])
        used_new.add(new["key"])
        pairs.append((old, new, score))
    return (
        pairs,
        [item for item in old_only if item["key"] not in used_old],
        [item for item in new_only if item["key"] not in used_new],
    )


def _inventory(index: dict[str, Any], object_type: str) -> list[dict[str, Any]]:
    result = []
    for item in _root_objects(index, object_type):
        raw_name = _object_name(item, object_type)
        display_name_value = _functional_name(raw_name, object_type)
        package_unit = item.get("packageUnit") or {}
        unit_name = _clean(package_unit.get("name")) if package_unit else ""
        display_name = (
            f"【{unit_name}】{display_name_value}" if unit_name else display_name_value
        )
        result.append(
            {
                "key": item["logicalKey"],
                "name": display_name,
                "rawName": raw_name,
                "packageUnit": package_unit or None,
                "packageUnitKey": item.get("packageUnitKey", "__single__"),
                "canonical": item.get("canonical") or {},
                "hash": item.get("canonicalHash"),
                "identityMethod": item.get("identityMethod"),
                "lineageIdentity": item.get("lineageIdentity"),
                "source": item,
            }
        )
    return result


def _reference_name_map(index: dict[str, Any], table: str) -> dict[str, str]:
    """建立包内逻辑引用到业务名称的索引，解决子记录只有 application_id 的情况。"""

    return {
        item.get("logicalKey"): _functional_name(
            item.get("displayName") or _object_name(item, "ESB_ACTION_FLOW"),
            "ESB_ACTION_FLOW",
        )
        for item in index.get("objects") or []
        if str(item.get("table", "")).lower() == table.lower()
        and item.get("logicalKey")
    }


def _resolved_reference_name(
    item: dict[str, Any], reference_map: dict[str, str], table: str
) -> str | None:
    for ref in sorted(_refs(item.get("canonical") or {})):
        if f"::{table}::" in ref and ref in reference_map:
            return reference_map[ref]
    return None


def _direct_reference(item: dict[str, Any], field: str) -> str | None:
    value = (item.get("canonical") or {}).get(field)
    if isinstance(value, dict) and value.get("$ref"):
        return str(value["$ref"])
    return None


def _direct_reference_name(
    item: dict[str, Any], reference_map: dict[str, str], field: str
) -> str | None:
    reference = _direct_reference(item, field)
    return reference_map.get(reference) if reference else None


def _binding_semantic_signature(item: dict[str, Any]) -> tuple[str, str, str, str, str]:
    """Return the parent-owned business meaning of an ESB resource binding."""

    canonical = item.get("canonical") or {}
    return (
        _direct_reference(item, "application_id") or str(item.get("parentIdentityKey") or ""),
        _clean(_field(canonical, "module_key", "module") or "模块待确认").lower(),
        _clean(_field(canonical, "business_obj", "business_object") or "对象待确认").lower(),
        json.dumps(_normalized_structure(canonical.get("business_value")), ensure_ascii=False, sort_keys=True),
        json.dumps(_normalized_structure(canonical.get("business_config")), ensure_ascii=False, sort_keys=True),
    )


def _pair_business_resource_bindings(
    old_values: list[dict[str, Any]], new_values: list[dict[str, Any]]
) -> tuple[list[tuple[dict[str, Any], dict[str, Any], str]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Pair bindings by IDM-derived key first, then by matched parent semantics."""

    pairs: list[tuple[dict[str, Any], dict[str, Any], str]] = []
    old_by_key = {item["key"]: item for item in old_values}
    new_by_key = {item["key"]: item for item in new_values}
    common_keys = sorted(set(old_by_key) & set(new_by_key))
    for key in common_keys:
        pairs.append((old_by_key[key], new_by_key[key], "MIGRATION_LINEAGE"))

    old_remaining = [item for item in old_values if item["key"] not in common_keys]
    new_remaining = [item for item in new_values if item["key"] not in common_keys]
    old_groups: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    new_groups: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in old_remaining:
        old_groups[_binding_semantic_signature(item)].append(item)
    for item in new_remaining:
        new_groups[_binding_semantic_signature(item)].append(item)

    used_old: set[str] = set()
    used_new: set[str] = set()
    for signature in sorted(set(old_groups) & set(new_groups)):
        if not signature[0]:
            continue
        left = sorted(old_groups[signature], key=lambda item: item["key"])
        right = sorted(new_groups[signature], key=lambda item: item["key"])
        if len(left) != 1 or len(right) != 1:
            continue
        old, new = left[0], right[0]
        pairs.append((old, new, "PARENT_RELATION_PATH"))
        used_old.add(old["key"])
        used_new.add(new["key"])

    return (
        pairs,
        [item for item in old_remaining if item["key"] not in used_old],
        [item for item in new_remaining if item["key"] not in used_new],
    )


def _graph(index: dict[str, Any], module_token: str) -> dict[str, set[str]]:
    objects = [
        item
        for item in index.get("objects") or []
        if module_token in str(item.get("module", "")).lower()
    ]
    keys = {item["logicalKey"] for item in objects}
    graph: dict[str, set[str]] = defaultdict(set)
    hash_to_keys: dict[str, set[str]] = defaultdict(set)
    for item in objects:
        for variant in _variants(item["logicalKey"]):
            hash_to_keys[hashlib.sha256(variant.encode("utf-8")).hexdigest()[:16]].add(item["logicalKey"])
    for item in objects:
        key = item["logicalKey"]
        for ref in _refs(item.get("canonical")):
            if ref in keys:
                graph[key].add(ref)
                graph[ref].add(key)
        token = _parent_token(key)
        if token:
            for parent in hash_to_keys.get(token, set()):
                graph[key].add(parent)
                graph[parent].add(key)
    return graph


def _assign_to_roots(
    index: dict[str, Any],
    module_token: str,
    root_keys: dict[str, str],
    allowed_tables: set[str],
) -> dict[str, list[dict[str, Any]]]:
    graph = _graph(index, module_token)
    by_key = {
        item["logicalKey"]: item
        for item in index.get("objects") or []
        if module_token in str(item.get("module", "")).lower()
    }
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    allowed_keys = {
        key
        for key, item in by_key.items()
        if str(item.get("table", "")).lower() in allowed_tables
        or key in root_keys
    }

    # Compute the nearest root for the entire undirected module graph once.
    # The previous implementation launched a depth-limited BFS from every
    # child record, repeatedly traversing the same graph hundreds of thousands
    # of times on batch packages.  Multi-source BFS is equivalent for non-root
    # children: it preserves the five-hop boundary and only assigns when the
    # nearest distance resolves to one business root name.
    distances: dict[str, int] = {}
    owners: dict[str, set[str]] = {}
    queue = deque()
    for root_key in sorted(root_keys):
        if root_key not in allowed_keys:
            continue
        distances[root_key] = 0
        owners[root_key] = {root_keys[root_key]}
        queue.append(root_key)
    while queue:
        current = queue.popleft()
        next_distance = distances[current] + 1
        if next_distance > 5:
            continue
        for target in sorted(graph.get(current, set())):
            if target not in allowed_keys:
                continue
            previous_distance = distances.get(target)
            if previous_distance is None or next_distance < previous_distance:
                distances[target] = next_distance
                owners[target] = set(owners[current])
                queue.append(target)
            elif next_distance == previous_distance:
                merged = owners[target] | owners[current]
                if merged != owners[target]:
                    owners[target] = merged
                    queue.append(target)

    for key, item in by_key.items():
        if key in root_keys or key not in allowed_keys:
            continue
        winners = owners.get(key) or set()
        if len(winners) == 1:
            result[next(iter(winners))].append(item)
    return result


def _component_counter(value: Any) -> Counter[str]:
    counter: Counter[str] = Counter()
    visited_ids = set()
    for item in _walk(value):
        if not isinstance(item, dict):
            continue
        component_type = item.get("type")
        if not isinstance(component_type, str):
            continue
        marker = item.get("id") or item.get("uuid") or id(item)
        if marker in visited_ids:
            continue
        visited_ids.add(marker)
        counter[component_type] += 1
    return counter


def _page_layout_model(index: dict[str, Any]) -> dict[str, Any]:
    """建立 页面扩展→布局→组件 关系，显式保留一对多歧义。"""

    objects = [
        item
        for item in index.get("objects") or []
        if "ebuilder-app" in str(item.get("module", "")).lower()
    ]
    pages = _inventory(index, "PAGE")
    root_names = {item["key"]: item["name"] for item in pages}
    extensions = [
        item for item in objects
        if str(item.get("table", "")).lower() == "ebdd_page_extended"
    ]
    layouts = [
        item for item in objects
        if str(item.get("table", "")).lower() == "ebdd_page_layout"
    ]
    components = [
        item for item in objects
        if str(item.get("table", "")).lower() == "ebdd_layout_component"
    ]

    layout_by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for layout in layouts:
        for variant in _variants(layout["logicalKey"]):
            token = hashlib.sha256(variant.encode("utf-8")).hexdigest()[:16]
            layout_by_hash[token].append(layout)

    counters: dict[str, Counter[str]] = defaultdict(Counter)
    for component in components:
        token = _parent_token(component["logicalKey"])
        candidates = layout_by_hash.get(token or "", [])
        if len(candidates) != 1:
            continue
        component_type = _field(component.get("canonical") or {}, "type")
        if not component_type:
            match = re.search(r'type="([^"]+)"', component["logicalKey"])
            component_type = match.group(1) if match else component.get("displayName")
        counters[candidates[0]["logicalKey"]][_clean(component_type)] += 1

    family_layouts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for layout in layouts:
        family_ref = next(
            (
                ref for ref in _refs(layout.get("canonical"))
                if "::ebdd_page_extended::" in ref
            ),
            None,
        )
        if family_ref:
            family_layouts[family_ref].append(layout)

    family_candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for family_ref in family_layouts:
        for extension in extensions:
            if family_ref not in _variants(extension["logicalKey"]):
                continue
            page_ref = next(
                (
                    ref for ref in _refs(extension.get("canonical"))
                    if "::ebdp_page::" in ref
                ),
                None,
            )
            name = root_names.get(page_ref or "") or _ref_display(
                extension.get("canonical"), "ebdp_page"
            )
            if not name:
                continue
            if page_ref not in root_names:
                name = _scoped_name(extension, name)
            family_candidates[family_ref].append(
                {
                    "name": _clean(name),
                    "ordinal": (extension.get("sourceEvidence") or {}).get(
                        "recordOrdinal", 0
                    ),
                }
            )

    result: dict[str, Counter[str]] = defaultdict(Counter)
    layout_name: dict[str, str] = {}
    for family_ref, family in family_layouts.items():
        candidates = family_candidates.get(family_ref, [])
        ordered_layouts = sorted(
            family,
            key=lambda item: (item.get("sourceEvidence") or {}).get(
                "recordOrdinal", 0
            ),
        )
        ordered_candidates = sorted(
            candidates,
            key=lambda item: item["ordinal"],
        )
        # 只有布局与页面扩展一一对应时才按迁出顺序落名；共享布局族保持
        # 歧义，交由新旧结构差分和模板/基页规则进一步消解。
        if len(ordered_layouts) != len(ordered_candidates):
            continue
        for layout, candidate in zip(ordered_layouts, ordered_candidates):
            name = candidate["name"]
            layout_name[layout["logicalKey"]] = name
            result[name].update(counters.get(layout["logicalKey"], Counter()))

    return {
        "result": result,
        "layouts": family_layouts,
        "candidates": family_candidates,
        "counters": counters,
        "layoutName": layout_name,
        "pageNames": {item["name"] for item in pages},
    }


def _page_components_pair(
    old_index: dict[str, Any],
    new_index: dict[str, Any],
) -> tuple[dict[str, Counter[str]], dict[str, Counter[str]]]:
    """同时计算两版页面组件，避免单版共享布局无法落到具体页面。"""

    old_model = _page_layout_model(old_index)
    new_model = _page_layout_model(new_index)
    old_result: dict[str, Counter[str]] = old_model["result"]
    new_result: dict[str, Counter[str]] = new_model["result"]

    for family_ref in sorted(
        set(old_model["layouts"]) & set(new_model["layouts"])
    ):
        old_by_ordinal = {
            (item.get("sourceEvidence") or {}).get("recordOrdinal", 0): item
            for item in old_model["layouts"][family_ref]
        }
        new_by_ordinal = {
            (item.get("sourceEvidence") or {}).get("recordOrdinal", 0): item
            for item in new_model["layouts"][family_ref]
        }
        changed_pairs = []
        for ordinal in sorted(set(old_by_ordinal) & set(new_by_ordinal)):
            old_layout, new_layout = old_by_ordinal[ordinal], new_by_ordinal[ordinal]
            old_counter = old_model["counters"].get(
                old_layout["logicalKey"], Counter()
            )
            new_counter = new_model["counters"].get(
                new_layout["logicalKey"], Counter()
            )
            if old_counter == new_counter:
                continue
            # 同一布局族、同一迁出位置且组件集合只发生增删，才能作为页面
            # 组件更新证据；跨布局族的位置漂移不会被误算。
            changed_pairs.append((old_layout, new_layout, old_counter, new_counter))

        if not changed_pairs:
            continue

        old_names = {
            item["name"] for item in old_model["candidates"].get(family_ref, [])
        }
        new_names = {
            item["name"] for item in new_model["candidates"].get(family_ref, [])
        }
        retained_names = sorted(
            old_names & new_names & old_model["pageNames"] & new_model["pageNames"]
        )

        # 新增“某页-模板”且同族存在保留基页时，新增模板不会吞掉基页上
        # 同时发生的组件变化。该规则不依赖具体应用名称。
        template_bases = []
        for name in sorted(new_names - old_names):
            base = re.sub(r"\s*[-—_]?\s*模板\s*$", "", name).strip()
            matches = [
                retained
                for retained in retained_names
                if _canonical_name(retained) == _canonical_name(base)
            ]
            template_bases.extend(matches)
        template_bases = list(dict.fromkeys(template_bases))

        unresolved = [
            pair for pair in changed_pairs
            if pair[0]["logicalKey"] not in old_model["layoutName"]
            or pair[1]["logicalKey"] not in new_model["layoutName"]
        ]
        if len(template_bases) == 1 and unresolved:
            old_layout, new_layout, old_counter, new_counter = unresolved[0]
            name = template_bases[0]
            old_result[name] = Counter(old_counter)
            new_result[name] = Counter(new_counter)
        elif len(unresolved) == len(retained_names) and retained_names:
            for name, (_, _, old_counter, new_counter) in zip(
                retained_names, unresolved
            ):
                old_result[name] = Counter(old_counter)
                new_result[name] = Counter(new_counter)

    return old_result, new_result


def _page_children(index: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    pages = _inventory(index, "PAGE")
    root_map = {item["key"]: item["name"] for item in pages}
    return _assign_to_roots(
        index,
        "ebuilder-app",
        root_map,
        PAGE_CHILD_TABLES | {"ebdp_page"},
    )


def _form_children(index: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    forms = _inventory(index, "FORM")
    root_map = {item["key"]: item["name"] for item in forms}
    result = _assign_to_roots(
        index,
        "ebuilder-form",
        root_map,
        (FORM_CHILD_TABLES - {"browser_data_scope"}) | {"form"},
    )
    for item in index.get("objects") or []:
        if str(item.get("table", "")).lower() != "browser_data_scope":
            continue
        owner = (item.get("canonical") or {}).get("business_id")
        owner_ref = owner.get("$ref") if isinstance(owner, dict) else None
        if owner_ref in root_map:
            result[root_map[owner_ref]].append(item)
    return result


def _unresolved_reference_hash(item: dict[str, Any], path: str) -> str | None:
    for reference in item.get("unresolvedReferences") or []:
        if str(reference.get("path") or "").lower() == path.lower():
            return reference.get("valueHash")
    return None


def _workflow_children(index: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """把流程浏览范围和节点后校验回溯到流程根对象。

    归一化会隐藏长整型 ID，但索引仍保留相同值的稳定哈希。这里仅在同一
    packageUnit 内做唯一哈希或显式引用匹配，避免把子配置误挂到同名版本记录。
    节点后校验使用 ``wfp_cpt_set -> wfp_cpt_base -> wfp_node`` 还原节点，
    并使用 ``conditionkey -> wfr_mapbase.conditioncn`` 提供客户可读条件。
    """

    roots = _root_objects(index, "WORKFLOW")
    roots_by_key = {root.get("logicalKey"): root for root in roots}
    roots_by_primary: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for root in roots:
        primary_hash = (root.get("sourceEvidence") or {}).get("primaryValueHash")
        if primary_hash:
            roots_by_primary[(root.get("packageUnitKey", "__single__"), primary_hash)].append(root)

    fields_by_primary: dict[tuple[str, str], dict[str, Any]] = {}
    objects_by_key: dict[str, dict[str, Any]] = {}
    objects_by_primary: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in index.get("objects") or []:
        logical_key = item.get("logicalKey")
        if logical_key:
            objects_by_key[logical_key] = item
        primary_hash = (item.get("sourceEvidence") or {}).get("primaryValueHash")
        if primary_hash:
            objects_by_primary[(item.get("packageUnitKey", "__single__"), primary_hash)].append(item)
        if str(item.get("table", "")).lower() != "form_field":
            continue
        if primary_hash:
            fields_by_primary[(item.get("packageUnitKey", "__single__"), primary_hash)] = item

    result: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def workflow_root(item: dict[str, Any]) -> dict[str, Any] | None:
        unit_key = item.get("packageUnitKey", "__single__")
        owner = (item.get("canonical") or {}).get("workflowid")
        owner_ref = owner.get("$ref") if isinstance(owner, dict) else None
        resolved = [roots_by_key[owner_ref]] if owner_ref in roots_by_key else []
        owner_hash = _unresolved_reference_hash(item, "workflowid")
        candidates = resolved or (
            roots_by_primary.get((unit_key, owner_hash), []) if owner_hash else []
        )
        return candidates[0] if len(candidates) == 1 else None

    for item in index.get("objects") or []:
        if str(item.get("table", "")).lower() != "browser_data_scope":
            continue
        unit_key = item.get("packageUnitKey", "__single__")
        owner = (item.get("canonical") or {}).get("business_id")
        owner_ref = owner.get("$ref") if isinstance(owner, dict) else None
        resolved_roots = [roots_by_key[owner_ref]] if owner_ref in roots_by_key else []
        owner_hash = _unresolved_reference_hash(item, "business_id")
        candidates = (
            resolved_roots
            if resolved_roots
            else roots_by_primary.get((unit_key, owner_hash), []) if owner_hash
            else []
        )
        if len(candidates) != 1:
            continue
        child = dict(item)
        control_hash = _unresolved_reference_hash(item, "control_id")
        control = fields_by_primary.get((unit_key, control_hash), {}) if control_hash else {}
        child["businessItemName"] = _field(control.get("canonical") or {}, "title", "field_name", "name") or "流程浏览字段"
        result[candidates[0]["logicalKey"]].append(child)

    cpt_base_owner: dict[str, dict[str, Any]] = {}
    cpt_base_node: dict[str, str] = {}
    for item in index.get("objects") or []:
        if str(item.get("table", "")).lower() != "wfp_cpt_base":
            continue
        root = workflow_root(item)
        if not root:
            continue
        node_ref = _field(item.get("canonical") or {}, "nodeid")
        node_key = node_ref.get("$ref") if isinstance(node_ref, dict) else None
        node = objects_by_key.get(node_key or "", {})
        node_name = _field(node.get("canonical") or {}, "nodename", "name") or "未命名流程节点"
        child = dict(item)
        child["validationNodeName"] = _clean(node_name)
        child["businessItemName"] = f"{_clean(node_name)}节点后校验设置"
        result[root["logicalKey"]].append(child)
        cpt_base_owner[item.get("logicalKey")] = root
        cpt_base_node[item.get("logicalKey")] = _clean(node_name)

    referenced_conditions: dict[str, tuple[dict[str, Any], str]] = {}
    for item in index.get("objects") or []:
        if str(item.get("table", "")).lower() != "wfp_cpt_set":
            continue
        canonical = item.get("canonical") or {}
        cpt_ref_value = canonical.get("cptbaseid")
        cpt_ref = cpt_ref_value.get("$ref") if isinstance(cpt_ref_value, dict) else None
        root = cpt_base_owner.get(cpt_ref or "") or workflow_root(item)
        if not root:
            continue
        node_name = cpt_base_node.get(cpt_ref or "", "未命名流程节点")
        condition_ref_value = canonical.get("conditionkey")
        condition_ref = condition_ref_value.get("$ref") if isinstance(condition_ref_value, dict) else None
        condition = objects_by_key.get(condition_ref or "", {})
        condition_text = _field(condition.get("canonical") or {}, "conditioncn")
        child = dict(item)
        child["validationNodeName"] = node_name
        child["validationCondition"] = _clean(condition_text) if condition_text else "条件内容待确认"
        child["businessItemName"] = _clean(_field(canonical, "rulename") or "节点后校验规则")
        result[root["logicalKey"]].append(child)
        if condition_ref and condition:
            referenced_conditions[condition_ref] = (root, node_name)

    # 条件正文可能在规则记录不变时单独更新；把被规则实际引用的条件对象一并
    # 归入流程证据，但不把全包其他用途的 wfr_mapbase 当成流程子配置。
    for condition_ref, (root, node_name) in referenced_conditions.items():
        condition = objects_by_key.get(condition_ref)
        if not condition:
            continue
        child = dict(condition)
        child["validationNodeName"] = node_name
        child["businessItemName"] = f"{node_name}节点后校验条件"
        result[root["logicalKey"]].append(child)

    # Workflow SQL datasets do not carry a direct workflowid. Their declared
    # query fields point to wfp_context rows, which in turn carry the workflow
    # owner. Attach a dataset only when every referenced context resolves to one
    # and the same workflow root; otherwise keep it unresolved rather than
    # guessing from the generated dataset name.
    for item in index.get("objects") or []:
        canonical = item.get("canonical") or {}
        if (
            str(item.get("table", "")).lower() != "dataset"
            or str(canonical.get("source_module") or "").lower() != "workflow"
            or not isinstance(canonical.get("dataset_sql"), dict)
        ):
            continue
        dataset_sql = canonical["dataset_sql"]
        context_refs = []
        for field in dataset_sql.get("fields") or []:
            value = field.get("name") if isinstance(field, dict) else None
            ref = value.get("$ref") if isinstance(value, dict) else None
            if ref and "::wfp_context::" in ref:
                context_refs.append((ref, _clean(field.get("showname") or "查询参数")))
        contexts = [objects_by_key.get(ref) for ref, _name in context_refs]
        if not contexts or any(context is None for context in contexts):
            continue
        owners = [workflow_root(context) for context in contexts if context]
        owner_keys = {owner.get("logicalKey") for owner in owners if owner}
        if len(owner_keys) != 1 or len(owners) != len(contexts) or any(owner is None for owner in owners):
            continue
        child = dict(item)
        bindings = []
        for (ref, name), context in zip(context_refs, contexts):
            bindings.append({
                "contextRef": ref,
                "name": name,
                "placeholderHash": (context.get("sourceEvidence") or {}).get("primaryValueHash"),
            })
        child["sqlParameterBindings"] = bindings
        child["businessItemName"] = "工作流 SQL 数据源"
        result[next(iter(owner_keys))].append(child)
    return result


def _workflow_scope_description(item: dict[str, Any]) -> str:
    canonical = item.get("canonical") or {}
    control_name = _clean(item.get("businessItemName") or "流程浏览字段")
    descriptions = []
    for node in _walk(canonical.get("scope_info_render") or {}):
        if not isinstance(node, dict) or not isinstance(node.get("conditions"), dict):
            continue
        condition = node["conditions"]
        field_name = _clean(node.get("text") or _field(node.get("config") or {}, "title", "dataKey", "columnName") or "筛选字段")
        operator = {
            "eq": "等于", "neq": "不等于", "aggregate": "属于", "contains": "包含",
            "gt": "大于", "gte": "大于等于", "lt": "小于", "lte": "小于等于",
        }.get(str(condition.get("func") or "").lower(), str(condition.get("func") or "满足条件"))
        value = condition.get("value")
        custom_values = condition.get("customBrowserValue")
        if isinstance(custom_values, list) and custom_values:
            selected = custom_values[0]
            if isinstance(selected, dict) and selected.get("location") and selected.get("content"):
                value = f"{selected['location']}.{selected['content']}"
        if value not in (None, ""):
            descriptions.append(f"{field_name}{operator}{value}")
    descriptions = list(dict.fromkeys(descriptions))
    if len(descriptions) > 1:
        detail = "组合条件（逻辑关系见对象明细）：" + "；".join(descriptions)
    else:
        detail = descriptions[0] if descriptions else "按保存的数据范围条件过滤"
    return f"{control_name}：{detail}"


def _workflow_scope_internal(old_children: list[dict[str, Any]], new_children: list[dict[str, Any]]) -> list[dict[str, Any]]:
    old_scopes = [item for item in old_children if str(item.get("table", "")).lower() == "browser_data_scope"]
    new_scopes = [item for item in new_children if str(item.get("table", "")).lower() == "browser_data_scope"]
    old_keys = {item.get("logicalKey") for item in old_scopes}
    new_keys = {item.get("logicalKey") for item in new_scopes}
    result = []
    for item in new_scopes:
        if item.get("logicalKey") not in old_keys:
            result.append({"kind": "BROWSER_DATA_SCOPE_ADDED", "description": "新增浏览数据范围：" + _workflow_scope_description(item)})
    for item in old_scopes:
        if item.get("logicalKey") not in new_keys:
            result.append({"kind": "BROWSER_DATA_SCOPE_REMOVED", "description": "移除浏览数据范围：" + _workflow_scope_description(item)})
    return result


def _validation_rule_identity(item: dict[str, Any]) -> str:
    evidence = item.get("sourceEvidence") or {}
    return str(
        evidence.get("migrationSourceIdHash")
        or evidence.get("primaryValueHash")
        or item.get("logicalKey")
        or ""
    )


def _validation_rule_summary(item: dict[str, Any]) -> dict[str, Any]:
    canonical = item.get("canonical") or {}
    return {
        "name": _clean(_field(canonical, "rulename") or item.get("businessItemName") or "节点后校验规则"),
        "enabled": str(_field(canonical, "is_open") or 0) in {"1", "True", "true"},
        "condition": _clean(item.get("validationCondition") or "条件内容待确认"),
        "failureTip": _clean(_field(canonical, "rulenopasstip") or "未设置"),
        "failureHandling": "禁止提交" if str(_field(canonical, "non_compliance") or 0) == "0" else "仅提醒",
    }


def _workflow_validation_internal(
    old_children: list[dict[str, Any]],
    new_children: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """生成按节点聚合、可直接对应设计器界面的节点后校验差异。"""

    def grouped(children: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
        result: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        for item in children:
            if str(item.get("table", "")).lower() != "wfp_cpt_set":
                continue
            node_name = _clean(item.get("validationNodeName") or "未命名流程节点")
            result[node_name][_validation_rule_identity(item)] = _validation_rule_summary(item)
        return result

    old_by_node, new_by_node = grouped(old_children), grouped(new_children)
    result = []
    for node_name in sorted(set(old_by_node) | set(new_by_node)):
        old_rules = old_by_node.get(node_name, {})
        new_rules = new_by_node.get(node_name, {})
        if old_rules == new_rules:
            continue
        old_enabled = [value for value in old_rules.values() if value["enabled"]]
        new_enabled = [value for value in new_rules.values() if value["enabled"]]
        added = [new_rules[key] for key in sorted(set(new_rules) - set(old_rules))]
        removed = [old_rules[key] for key in sorted(set(old_rules) - set(new_rules))]
        updated = [
            {"before": old_rules[key], "after": new_rules[key]}
            for key in sorted(set(old_rules) & set(new_rules))
            if old_rules[key] != new_rules[key]
        ]
        result.append({
            "kind": "NODE_POST_VALIDATION_CHANGED",
            "nodeName": node_name,
            "oldRuleCount": len(old_rules),
            "newRuleCount": len(new_rules),
            "oldEnabledCount": len(old_enabled),
            "newEnabledCount": len(new_enabled),
            "effectiveBefore": old_enabled,
            "effectiveAfter": new_enabled,
            "addedRules": added,
            "removedRules": removed,
            "updatedRules": updated,
        })
    return result


def _sql_without_comments(sql: str) -> str:
    """Remove SQL comments while preserving quoted literals."""

    result: list[str] = []
    index = 0
    quote = ""
    while index < len(sql):
        char = sql[index]
        if quote:
            result.append(char)
            if char == quote:
                if index + 1 < len(sql) and sql[index + 1] == quote:
                    result.append(sql[index + 1])
                    index += 1
                else:
                    quote = ""
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            result.append(char)
            index += 1
            continue
        if sql.startswith("--", index):
            end = sql.find("\n", index + 2)
            index = len(sql) if end < 0 else end + 1
            result.append(" ")
            continue
        if sql.startswith("/*", index):
            end = sql.find("*/", index + 2)
            index = len(sql) if end < 0 else end + 2
            result.append(" ")
            continue
        result.append(char)
        index += 1
    return "".join(result)


def _sql_semantic_form(sql: str) -> str:
    """Normalize formatting outside literals without changing literal values."""

    sql = _sql_without_comments(sql)
    parts: list[str] = []
    buffer: list[str] = []
    quote = ""

    def flush_plain() -> None:
        if not buffer:
            return
        plain = "".join(buffer).lower()
        plain = re.sub(r"\s+", " ", plain)
        plain = re.sub(r"\s*([(),=<>+*/-])\s*", r"\1", plain)
        parts.append(plain)
        buffer.clear()

    index = 0
    while index < len(sql):
        char = sql[index]
        if quote:
            parts.append(char)
            if char == quote:
                if index + 1 < len(sql) and sql[index + 1] == quote:
                    parts.append(sql[index + 1])
                    index += 1
                else:
                    quote = ""
            index += 1
            continue
        if char in {"'", '"'}:
            flush_plain()
            quote = char
            parts.append(char)
        else:
            buffer.append(char)
        index += 1
    flush_plain()
    return "".join(parts).strip().rstrip(";")


def _sql_output_type(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text or "undefined" in text:
        return "未明确"
    return {
        "text": "文本", "string": "文本", "number": "数值", "integer": "整数",
        "decimal": "小数", "date": "日期", "datetime": "日期时间", "boolean": "布尔值",
    }.get(text, "已明确")


def _workflow_sql_dataset_summary(item: dict[str, Any]) -> dict[str, Any]:
    canonical = item.get("canonical") or {}
    config = canonical.get("dataset_sql") if isinstance(canonical.get("dataset_sql"), dict) else {}
    sql = str((config or {}).get("sql") or "")
    semantic = _sql_semantic_form(sql)
    outside_literals = re.sub(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"", "", _sql_without_comments(sql))
    words = re.findall(r"[a-z_]+", outside_literals.lower())
    first_word = words[0] if words else ""
    prohibited = sorted(set(words) & {
        "insert", "update", "delete", "merge", "create", "alter", "drop",
        "truncate", "grant", "revoke", "call", "execute", "exec",
    })
    statements = [part for part in re.split(r";", outside_literals) if part.strip()]
    placeholders = sorted(set(re.findall(r"\$\{([^}]+)\}", sql)))
    bindings = item.get("sqlParameterBindings") or []
    binding_hashes = {str(binding.get("placeholderHash") or "") for binding in bindings}
    placeholder_hashes = {hashlib.sha256(value.encode("utf-8")).hexdigest()[:16] for value in placeholders}
    inputs = list(dict.fromkeys(
        _clean(field.get("showname") or "查询参数")
        for field in (config or {}).get("fields") or [] if isinstance(field, dict)
    ))
    aliases = [field for field in (config or {}).get("fieldAlias") or [] if isinstance(field, dict)]
    declared_aliases = {str(field.get("name") or "").lower() for field in aliases if field.get("name")}
    selected_aliases = {match.lower() for match in re.findall(r"\bas\s+([a-z_][a-z0-9_]*)", outside_literals, re.I)}
    output_types = list(dict.fromkeys(_sql_output_type(field.get("type")) for field in aliases)) or ["未明确"]
    where_match = re.search(r"\bwhere\b(.*)$", outside_literals, re.I | re.S)
    condition_count = 0
    if where_match and where_match.group(1).strip():
        condition_count = 1 + len(re.findall(r"\band\b|\bor\b", where_match.group(1), re.I))
    parameter_condition_count = sum(1 for value in placeholders if f"${{{value}}}" in sql)
    fixed_count = max(0, condition_count - parameter_condition_count)
    returns_count = bool(re.search(r"\bcount\s*\(", outside_literals, re.I))
    if returns_count and inputs:
        query_summary = (
            f"按 {fixed_count} 项固定条件及“{'、'.join(inputs)}”参数过滤，返回符合条件的记录数量"
        )
    elif returns_count:
        query_summary = "按保存的筛选条件返回符合条件的记录数量"
    else:
        query_summary = "执行只读查询并返回配置的结果字段"
    db_settings_present = bool((config or {}).get("sourceDBTypeList") or (config or {}).get("sourceSql"))
    read_only = first_word in {"select", "with"} and not prohibited
    single_statement = len(statements) == 1
    parameters_resolved = bool(placeholders) and placeholder_hashes == binding_hashes
    aliases_declared = bool(declared_aliases) and selected_aliases.issubset(declared_aliases)
    return {
        "identityHash": (item.get("sourceEvidence") or {}).get("migrationSourceIdHash"),
        "semanticHash": hashlib.sha256(semantic.encode("utf-8")).hexdigest() if semantic else None,
        "queryType": "只读查询" if read_only else "需人工复核",
        "querySummary": query_summary,
        "inputs": inputs or ["未声明输入参数"],
        "outputTypes": output_types,
        "staticChecks": {
            "configurationParsed": isinstance(config, dict) and bool(config),
            "singleStatement": single_statement,
            "readOnlyQuery": read_only,
            "parametersResolved": parameters_resolved,
            "outputAliasesDeclared": aliases_declared,
        },
        "databaseSettingsPresent": db_settings_present,
        "runtimePending": [
            "数据库类型和连接信息未随包提供" if not db_settings_present else "数据库连接需在目标环境复核",
            "数据库对象存在性、访问权限、真实执行结果和性能需在目标环境验证",
        ],
    }


def _workflow_sql_dataset_internal(
    old_children: list[dict[str, Any]],
    new_children: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compare workflow-owned SQL datasets without overriding IDM identity."""

    old_items = [item for item in old_children if str(item.get("table", "")).lower() == "dataset"]
    new_items = [item for item in new_children if str(item.get("table", "")).lower() == "dataset"]
    old_summaries = [_workflow_sql_dataset_summary(item) for item in old_items]
    new_summaries = [_workflow_sql_dataset_summary(item) for item in new_items]
    return [
        {"kind": "WORKFLOW_SQL_DATASOURCE_CHANGED", **comparison}
        for comparison in pair_workflow_sql_summaries(old_summaries, new_summaries)
    ]


def _form_summary(children: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "fieldCount": sum(str(item.get("table", "")).lower() == "form_field" for item in children),
        "layoutCount": sum(str(item.get("table", "")).lower() in {"form_layout_multiple", "form_layout_version"} for item in children),
        "listCount": sum(str(item.get("table", "")).lower() == "ebdf_list" for item in children),
    }


def _form_layout_names(children: list[dict[str, Any]]) -> set[str]:
    """Return one business name per form layout, excluding deleted/trash entries."""

    result = set()
    for item in children:
        if str(item.get("table", "")).lower() != "form_layout_multiple":
            continue
        canonical = item.get("canonical") or {}
        if str(canonical.get("is_delete", "0")) == "1" or canonical.get("delete_type") == 1:
            continue
        name = _clean(canonical.get("name") or item.get("displayName"))
        if name != "名称待确认":
            result.add(name)
    return result


def _form_layout_component_changes(
    old_children: list[dict[str, Any]],
    new_children: list[dict[str, Any]],
    child_facts: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], set[str]]:
    """Group component facts under the owning named form layout."""

    def ownership(children: list[dict[str, Any]]) -> dict[str, str]:
        by_key = {item.get("logicalKey"): item for item in children if item.get("logicalKey")}
        graph: dict[str, set[str]] = defaultdict(set)
        hash_to_keys: dict[str, set[str]] = defaultdict(set)
        roots: dict[str, str] = {}
        default_names = set()
        for key, item in by_key.items():
            for variant in _variants(key):
                hash_to_keys[hashlib.sha256(variant.encode("utf-8")).hexdigest()[:16]].add(key)
            if str(item.get("table", "")).lower() in {"form_layout_multiple", "form_layout_version"}:
                name = _clean(_field(item.get("canonical") or {}, "name") or item.get("displayName"))
                if name != "名称待确认":
                    roots[key] = name
                    canonical = item.get("canonical") or {}
                    if str(item.get("table", "")).lower() == "form_layout_multiple" and str(canonical.get("is_default", "0")) == "1":
                        default_names.add(name)
        for key, item in by_key.items():
            for ref in _refs(item.get("canonical") or {}):
                if ref in by_key:
                    graph[key].add(ref)
                    graph[ref].add(key)
            token = _parent_token(key)
            for parent in hash_to_keys.get(token or "", set()):
                graph[key].add(parent)
                graph[parent].add(key)
        result: dict[str, str] = {}
        for key, item in by_key.items():
            if str(item.get("table", "")).lower() != "ebdd_layout_component":
                continue
            queue = deque([(key, 0)])
            visited = {key}
            found: dict[str, int] = {}
            while queue:
                current, depth = queue.popleft()
                if current in roots:
                    found[roots[current]] = min(found.get(roots[current], 99), depth)
                    continue
                if depth >= 5:
                    continue
                for target in graph.get(current, set()):
                    if target not in visited:
                        visited.add(target)
                        queue.append((target, depth + 1))
            if found:
                best = min(found.values())
                names = sorted(name for name, distance in found.items() if distance == best)
                if len(names) == 1:
                    result[key] = names[0]
            elif len(default_names) == 1:
                # Some legacy form layouts expose only the form/page owner after
                # export. A form's single active default layout is the conservative
                # fallback for otherwise unowned component deltas.
                result[key] = next(iter(default_names))
        return result

    old_owner, new_owner = ownership(old_children), ownership(new_children)
    grouped: dict[str, dict[str, Counter[str] | int]] = defaultdict(
        lambda: {"added": Counter(), "removed": Counter(), "updated": 0}
    )
    consumed = set()
    for fact in child_facts:
        obj, old_obj = fact.get("object") or {}, fact.get("oldObject") or {}
        table = str((obj or old_obj).get("table", "")).lower()
        if table != "ebdd_layout_component":
            continue
        change_type = fact.get("changeType")
        owner = new_owner.get(obj.get("logicalKey")) or old_owner.get(old_obj.get("logicalKey"))
        if not owner:
            continue
        item = obj if change_type != "REMOVED" else old_obj
        component_type = _field(item.get("canonical") or {}, "type") or item.get("displayName") or "组件"
        component_name = _component_business_name(component_type)
        if change_type == "ADDED":
            grouped[owner]["added"][component_name] += 1
        elif change_type == "REMOVED":
            grouped[owner]["removed"][component_name] += 1
        else:
            grouped[owner]["updated"] += 1
        consumed.add(str(fact.get("changeId")))
    changes = []
    for name in sorted(grouped):
        value = grouped[name]
        changes.append({
            "kind": "FORM_LAYOUT_COMPONENTS_CHANGED",
            "layoutName": name,
            "added": dict(value["added"]),
            "removed": dict(value["removed"]),
            "updatedCount": value["updated"],
        })
    return changes, consumed


def _form_internal(old_children: list[dict[str, Any]], new_children: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def names(items: list[dict[str, Any]], table: str) -> set[str]:
        return {
            _object_name(item, "FORM")
            for item in items
            if str(item.get("table", "")).lower() == table
        }

    result = []
    old_fields, new_fields = names(old_children, "form_field"), names(new_children, "form_field")
    if new_fields - old_fields:
        values = sorted(new_fields - old_fields)
        result.append({"kind": "FIELD_ADDED", "count": len(values), "items": values[:20]})
    if old_fields - new_fields:
        values = sorted(old_fields - new_fields)
        result.append({"kind": "FIELD_REMOVED", "count": len(values), "items": values[:20]})
    old_layouts, new_layouts = _form_layout_names(old_children), _form_layout_names(new_children)
    if new_layouts - old_layouts:
        values = sorted(new_layouts - old_layouts)
        result.append({"kind": "FORM_LAYOUT_ADDED", "count": len(values), "items": values})
    if old_layouts - new_layouts:
        values = sorted(old_layouts - new_layouts)
        result.append({"kind": "FORM_LAYOUT_REMOVED", "count": len(values), "items": values})
    groups = [
        ("LIST", {"ebdf_list", "ebdf_list_field", "ebdf_list_filter"}),
        ("BUTTON_ACTION", {"ebdf_button", "ebdf_button_action", "ebdf_button_esb", "ebdf_button_esb_list"}),
        ("LINKAGE", {"fd_linkage", "fd_linkage_source_esb", "form_view_linkage", "form_data_relate_config"}),
    ]
    for kind, tables in groups:
        old_count = sum(str(item.get("table", "")).lower() in tables for item in old_children)
        new_count = sum(str(item.get("table", "")).lower() in tables for item in new_children)
        if old_count != new_count:
            result.append({"kind": kind, "oldCount": old_count, "newCount": new_count})
    return result


def _feature_change_summaries(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    """保留所有已计算业务链路，避免无法归属一级对象的变化从主报告消失。"""

    result = []
    for feature in analysis.get("featureChanges") or []:
        if feature.get("changeType") == "UNCHANGED":
            continue
        paths = []
        for item in (feature.get("changedPaths") or [])[:24]:
            paths.append({
                "path": item.get("path"),
                "before": item.get("before"),
                "after": item.get("after"),
                "category": item.get("category"),
                "operation": item.get("operation"),
            })
        tables = feature.get("tables") or []
        status = "OBSERVED_BUSINESS_CHANGE"
        business_function = feature.get("businessFunction")
        purpose = feature.get("businessPurpose")
        user_visible = feature.get("userVisibleChange")
        if tables and all(str(table).lower() in NON_BUSINESS_CHANGE_TABLES for table in tables):
            status = "EXCLUDED_NON_BUSINESS"
            business_function = "已排除：动作流运行统计快照变化"
            purpose = "执行次数、成功数或失败数等运行统计随导出时点变化，不构成动作流设计更新"
            user_visible = "不计为动作流功能更新；如需核对运行结果，应使用目标环境日志和运行记录"
        elif paths and all(
            item.get("category") in {None, "REFERENCE_ID", "UNKNOWN"}
            for item in paths
        ) and tables and all(
            str(table).lower() in {"dw_multilangset", "i18n_cuslabel", "i18n_cuslabelindex", "i18n_modulelabel_cus"}
            for table in tables
        ):
            status = "UNKNOWN_BUSINESS_OWNERSHIP"
            business_function = "待确认多语言配置变化（原业务归属未还原）"
            purpose = "包内多语言记录或其目标绑定发生变化，但静态证据不足以确认属于页面、数据集或集成对象"
            user_visible = "待确认：可能影响界面文案或数据集标签，不能据此确认动作流或业务资源绑定已更新"
        result.append({
            "businessChangeId": feature.get("businessChangeId"),
            "businessFunction": business_function,
            "businessPurpose": purpose,
            "module": feature.get("module"),
            "moduleKind": feature.get("moduleKind"),
            "changeType": feature.get("changeType"),
            "userVisibleChange": user_visible,
            "rawChangeCounts": feature.get("rawChangeCounts") or {},
            "tables": tables,
            "changedPaths": paths,
            "beforeSamples": (feature.get("before") or [])[:3],
            "afterSamples": (feature.get("after") or [])[:3],
            "evidenceLevel": (
                "OBSERVED"
                if any(item.get("category") not in {None, "REFERENCE_ID", "UNKNOWN"} for item in paths)
                else "UNKNOWN"
            ),
            "reportingStatus": status,
        })
    return result


def _facts_by_side(facts: list[dict[str, Any]], side: str) -> tuple[list[tuple[str, str, dict[str, Any]]], dict[str, set[str]], dict[str, set[str]]]:
    entries = []
    variants = {}
    digest_map: dict[str, set[str]] = defaultdict(set)
    for fact in facts:
        obj = _side_object(fact, side)
        if not obj or not _side_exists(fact, side):
            continue
        key = obj["logicalKey"]
        entries.append((key, str(obj["table"]).lower(), fact))
        variants[key] = _variants(key)
        for variant in variants[key]:
            digest_map[hashlib.sha256(variant.encode("utf-8")).hexdigest()[:16]].add(key)
    return entries, variants, digest_map


def _flow_nodes(
    facts: list[dict[str, Any]],
    side: str,
) -> tuple[dict[str, Counter[str]], dict[str, Counter[str]], dict[str, str]]:
    entries, variants, digest_map = _facts_by_side(facts, side)
    entries = [
        item for item in entries
        if "esb-setting" in str(item[2]["object"].get("module", "")).lower()
    ]
    apps = [
        (
            key,
            _scoped_name(
                _side_object(fact, side),
                (_side_object(fact, side) or {}).get("displayName"),
            ),
            fact,
        )
        for key, table, fact in entries if table == "esb_application"
    ]
    scenes = [(key, fact) for key, table, fact in entries if table == "esb_action_flow_version"]
    flows = [(key, fact) for key, table, fact in entries if table == "esb_flow"]
    actions = [(key, fact) for key, table, fact in entries if table == "esb_flow_action"]
    app_key_to_name = {key: name for key, name, _ in apps}
    token_to_app: dict[str, set[str]] = defaultdict(set)
    flow_tokens = {_parent_token(key) for key, _ in flows}
    for app_key, _, _ in apps:
        for app_variant in variants.get(app_key, {app_key}):
            token = hashlib.sha256(app_variant.encode()).hexdigest()[:16]
            if token in flow_tokens:
                token_to_app[token].add(app_key)
            for scene_key, _ in scenes:
                for scene_variant in variants.get(scene_key, {scene_key}):
                    token = hashlib.sha256("|".join(sorted((app_variant, scene_variant))).encode()).hexdigest()[:16]
                    if token in flow_tokens:
                        token_to_app[token].add(app_key)
    flow_to_app = {}
    for flow_key, fact in flows:
        name = _ref_display(_side_value(fact, side), "esb_application")
        if name:
            name = _scoped_name(_side_object(fact, side), name)
        matches = [key for key, app_name, _ in apps if app_name == name]
        if len(matches) == 1:
            flow_to_app[flow_key] = matches[0]
            continue
        candidates = token_to_app.get(_parent_token(flow_key) or "", set())
        if len(candidates) == 1:
            flow_to_app[flow_key] = next(iter(candidates))
    pair_hashes: dict[str, set[str]] = defaultdict(set)
    for flow_key, app_key in flow_to_app.items():
        for app_variant, flow_variant in product(
            variants.get(app_key, {app_key}), variants.get(flow_key, {flow_key})
        ):
            token = hashlib.sha256("|".join(sorted((app_variant, flow_variant))).encode()).hexdigest()[:16]
            pair_hashes[token].add(app_key)
    action_map = {}
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    semantic_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for action_key, fact in actions:
        app_name = _ref_display(_side_value(fact, side), "esb_application")
        if app_name:
            app_name = _scoped_name(_side_object(fact, side), app_name)
        if not app_name:
            candidates = pair_hashes.get(_parent_token(action_key) or "", set())
            if len(candidates) == 1:
                app_name = app_key_to_name.get(next(iter(candidates)))
        if not app_name:
            continue
        action_map[action_key] = app_name
        match = re.search(r'type="([^"]+)"', action_key)
        node_type = match.group(1) if match else _clean((_side_object(fact, side) or {}).get("displayName"))
        node_name = _clean((_side_object(fact, side) or {}).get("displayName"))
        counts[app_name][node_type] += 1
        semantic_counts[app_name][f"{node_type}\x1f{node_name}"] += 1
    return counts, semantic_counts, action_map


def _flow_node_name_changes(
    old_semantics: Counter[str],
    new_semantics: Counter[str],
) -> list[dict[str, str]]:
    """Pair same-type node label changes after exact semantic matches are removed."""

    old_by_type: dict[str, list[str]] = defaultdict(list)
    new_by_type: dict[str, list[str]] = defaultdict(list)
    for value, count in (old_semantics - new_semantics).items():
        node_type, _, name = value.partition("\x1f")
        old_by_type[node_type].extend([name] * count)
    for value, count in (new_semantics - old_semantics).items():
        node_type, _, name = value.partition("\x1f")
        new_by_type[node_type].extend([name] * count)
    changes = []
    for node_type in sorted(set(old_by_type) & set(new_by_type)):
        for old_name, new_name in zip(
            sorted(old_by_type[node_type]), sorted(new_by_type[node_type])
        ):
            if old_name == new_name:
                continue
            changes.append({
                "componentType": node_type,
                "oldName": old_name,
                "newName": new_name,
            })
    return changes


def _flow_business_children(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """保留能够证明动作流业务语义变化的子配置事实。

    动作节点的新增、删除和无法匹配事实容易由节点实例、父引用或连线记录
    重新生成触发。节点集合及“类型 + 名称”多重集合已单独比较，因此这里只
    接受已稳定配对且字段确实发生业务变化的动作节点事实。
    """

    result = []
    for fact in facts:
        if not _is_business_configuration_fact(fact):
            continue
        table = str((fact.get("object") or fact.get("oldObject") or {}).get("table", "")).lower()
        if table == "esb_flow_action":
            if fact.get("changeType") != "UPDATED":
                continue
            # data_id/flow_id/application_id 只标识节点组件实例及其所属流。
            # 节点类型/名称集合与组件子表另行比较，不能让这些引用替换
            # 单独把动作流计为业务更新。
            internal_fields = {"id", "data_id", "flow_id", "application_id"}
            meaningful_paths = []
            for path in _business_configuration_paths(fact):
                field = str(path.get("path") or "").lower().split(".", 1)[0]
                if field not in internal_fields:
                    meaningful_paths.append(path)
            if not meaningful_paths:
                continue
        result.append(fact)
    return result


def _flow_root_business_paths(fact: dict[str, Any]) -> list[dict[str, Any]]:
    """过滤动作流根记录的活动版本指针和等价默认保存值。"""

    result = []
    for path in _business_configuration_paths(fact):
        name = str(path.get("path") or "").lower()
        if name in {"active_version.$ref", "active_version.$unresolvedid"}:
            continue
        if name in {"special_mark", "is_keep_diary", "is_suite"} and {
            path.get("before"), path.get("after")
        } <= {None, 0, False, "", "0"}:
            continue
        if name == "type" and (
            (isinstance(path.get("before"), dict) and path.get("after") in {None, 0, "0"})
            or (isinstance(path.get("after"), dict) and path.get("before") in {None, 0, "0"})
        ):
            # 动作流分类引用在一侧退化为默认数值时只能证明引用解析质量变化，
            # 不能证明节点执行逻辑发生变化。
            continue
        result.append(path)
    return result


def _flow_root_setting_changes(fact: dict[str, Any] | None) -> list[dict[str, Any]]:
    """把已知动作流根设置转成可展示的业务前后值。

    未知根字段不生成兜底结论；只有能够安全翻译的设置才允许单独
    触发动作流更新，避免出现“已更新但无可确认业务变化”。
    """

    if not fact:
        return []
    result = []
    for path in _flow_root_business_paths(fact):
        name = str(path.get("path") or "").lower()
        if name != "is_keep_diary":
            continue

        def toggle_label(value: Any) -> str:
            if value is True or value == 1 or str(value).lower() in {"1", "true", "start_using"}:
                return "开启"
            if value is False or value == 0 or str(value).lower() in {"0", "false", "forbidden"}:
                return "关闭"
            if value is None or value == "":
                return "未配置"
            return "已配置"

        before = toggle_label(path.get("before"))
        after = toggle_label(path.get("after"))
        if before == after:
            continue
        result.append({
            "kind": "FLOW_ROOT_SETTING_CHANGED",
            "settingName": "运行日志留存",
            "before": before,
            "after": after,
        })
    return result


def _menu_target(item: dict[str, Any]) -> str:
    canonical = item.get("canonical") or {}
    direct = _field(
        canonical,
        "url",
        "link_url",
        "linkUrl",
        "open_url",
        "route",
        "path",
        "page_name",
        "target_name",
    )
    if isinstance(direct, (str, int, float)):
        return _clean(direct)
    return _ref_display(canonical) or _clean(item.get("displayName"))


def _permission_breakdown(index: dict[str, Any]) -> dict[str, int]:
    counts = Counter()
    for item in index.get("objects") or []:
        label = PERMISSION_TABLES.get(str(item.get("table", "")).lower())
        if not label:
            continue
        # 迁出包可能同时携带一份只有数值 source_id、没有父对象关系的原始权限
        # 快照。它不是可追溯到业务功能的独立授权，不能与已经挂到页面/表单/菜单
        # 的关系权限重复计数。
        canonical = item.get("canonical") or {}
        source_id = _field(canonical, "source_id", "sourceId")
        if (
            label == "页面权限"
            and isinstance(source_id, dict)
            and "$ref" not in source_id
            and "::parent=" not in str(item.get("logicalKey", ""))
        ):
            continue
        counts[label] += 1
    return dict(counts)


def _application_name(new_index: dict[str, Any], new_meta: dict[str, Any]) -> str:
    package_unit_ids = {
        str((item.get("packageUnit") or {}).get("id") or "")
        for item in new_index.get("objects") or []
        if (item.get("packageUnit") or {}).get("id")
    }
    if len(package_unit_ids) > 1:
        package_name = str(new_meta.get("name") or "").strip()
        package_name = re.sub(r"\.zip$", "", package_name, flags=re.IGNORECASE)
        package_name = re.sub(
            r"_\d{6}_V\d+(?:\.\d+)*$", "", package_name, flags=re.IGNORECASE
        )
        if package_name:
            return package_name
    for item in new_index.get("objects") or []:
        if str(item.get("table", "")).lower() in {"ebda_app", "t_cus_app"}:
            value = _functional_name(
                _object_name(item, "APPLICATION_SHELL"),
                "APPLICATION_SHELL",
            )
            if value != FUNCTIONAL_FALLBACK_NAMES["APPLICATION_SHELL"]:
                return value
    return FUNCTIONAL_FALLBACK_NAMES["APPLICATION_SHELL"]


def build_business_object_diff(
    *,
    old_metadata: dict[str, Any],
    new_metadata: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    facts: list[dict[str, Any]],
    analysis: dict[str, Any],
) -> dict[str, Any]:
    """构建与技术事实分离的业务对象差异索引。"""

    objects: list[dict[str, Any]] = []
    possible_relations: list[dict[str, Any]] = []
    counts_override: dict[str, dict[str, int]] = {}
    facts_by_key = {
        fact["object"]["logicalKey"]: fact for fact in facts
    }
    facts_by_old_key = {
        (fact.get("oldObject") or {}).get("logicalKey"): fact
        for fact in facts if fact.get("oldObject")
    }

    old_form_children = _form_children(old_index)
    new_form_children = _form_children(new_index)
    old_page_children = _page_children(old_index)
    new_page_children = _page_children(new_index)
    old_workflow_children = _workflow_children(old_index)
    new_workflow_children = _workflow_children(new_index)
    child_change_coverage = _child_rollup_coverage(
        facts,
        old_form_children,
        new_form_children,
        old_page_children,
        new_page_children,
        old_workflow_children,
        new_workflow_children,
    )
    old_page_components, new_page_components = _page_components_pair(
        old_index, new_index
    )
    flow_counts_old, flow_semantics_old, flow_map_old = _flow_nodes(facts, "old")
    flow_counts_new, flow_semantics_new, flow_map_new = _flow_nodes(facts, "new")

    flow_child_changes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in facts:
        if "esb-setting" not in str(fact["object"].get("module", "")).lower():
            continue
        if fact.get("changeType") == "UNCHANGED":
            continue
        if str(fact["object"].get("table", "")).lower() in {
            "esb_application",
            "esb_app_statistics",
            "esb_action_flow_version",
            "esb_multilangset",
        }:
            continue
        names = set()
        old_ref = _ref_display(fact.get("before"), "esb_application")
        new_ref = _ref_display(fact.get("after"), "esb_application")
        if old_ref:
            names.add(_scoped_name(fact.get("oldObject"), old_ref))
        if new_ref:
            names.add(_scoped_name(fact.get("object"), new_ref))
        old_key = (fact.get("oldObject") or {}).get("logicalKey")
        new_key = fact["object"].get("logicalKey")
        if old_key in flow_map_old:
            names.add(flow_map_old[old_key])
        if new_key in flow_map_new:
            names.add(flow_map_new[new_key])
        for name in names:
            flow_child_changes[_clean(name)].append(fact)

    simple_types = [
        "FORM",
        "PAGE",
        "EMBEDDED_VIEW",
        "ESB_ACTION_FLOW",
        "WORKFLOW",
        "NAVIGATION",
        "REPORT",
        "MULTI_FILLING",
        "DATASET",
    ]
    navigation_update_assigned = False
    for object_type in simple_types:
        old_items = _inventory(old_index, object_type)
        new_items = _inventory(new_index, object_type)
        retained = []
        used_old: set[int] = set()
        used_new: set[int] = set()
        old_by_key: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
        new_by_key: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
        for index, item in enumerate(old_items):
            old_by_key[item["key"]].append((index, item))
        for index, item in enumerate(new_items):
            new_by_key[item["key"]].append((index, item))
        # 同源 ID、显式业务键或稳定父链生成的相同逻辑键优先于名称匹配。
        # 这使跨环境 ID 变化和真实重命名仍能被识别为同一业务对象。
        for key in sorted(set(old_by_key) & set(new_by_key)):
            for (old_index_value, old_item), (new_index_value, new_item) in zip(
                old_by_key[key], new_by_key[key]
            ):
                retained.append((old_item, new_item))
                used_old.add(old_index_value)
                used_new.add(new_index_value)

        old_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
        new_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for index, item in enumerate(old_items):
            if index in used_old:
                continue
            old_by_name[item["name"]].append(item)
        for index, item in enumerate(new_items):
            if index in used_new:
                continue
            new_by_name[item["name"]].append(item)
        old_only = []
        new_only = []
        for name in sorted(set(old_by_name) | set(new_by_name)):
            pair_count = min(len(old_by_name[name]), len(new_by_name[name]))
            retained.extend(zip(old_by_name[name][:pair_count], new_by_name[name][:pair_count]))
            old_only.extend(old_by_name[name][pair_count:])
            new_only.extend(new_by_name[name][pair_count:])

        rename_threshold = 0.64 if object_type == "FORM" else 0.82
        if object_type == "ESB_ACTION_FLOW":
            # 动作流拆分/合并会让名称看起来相近，但业务身份、触发入口和节点图
            # 已经发生变化。没有明确稳定身份时必须保留为“旧流删除 + 新流新增”，
            # 不能用模糊改名吞掉新增/删除数量。
            rename_pairs = []
        else:
            rename_pairs, old_only, new_only = _pair_renames(
                old_only, new_only, object_type, threshold=rename_threshold
            )
        for old, new, score in rename_pairs:
            combined_facts = [
                fact for fact in (
                    facts_by_old_key.get(old["key"]),
                    facts_by_key.get(new["key"]),
                ) if fact
            ]
            objects.append(
                _make_object(
                    object_type=object_type,
                    name=f"{old['name']} → {new['name']}",
                    logical_key=f"possible::{old['key']}=>{new['key']}",
                    change_type="POSSIBLE_RENAME",
                    old_exists=True,
                    new_exists=True,
                    facts=combined_facts,
                    old_summary={"name": old["name"]},
                    new_summary={"name": new["name"]},
                    internal_changes=[{"kind": "POSSIBLE_RENAME", "nameSimilarity": round(score, 3)}],
                    affected=["原入口或引用", "新版候选对象"],
                    confidence="MEDIUM",
                    purpose="两个对象名称或结构相近，但静态证据不足以确认同一业务身份",
                )
            )
            possible_relations.append(
                {
                    "oldObject": old["name"],
                    "newObjectCandidate": new["name"],
                    "objectType": next(
                        (label for label, value in TYPE_ORDER if value == object_type),
                        object_type,
                    ),
                    "similarityBasis": f"标准化名称相似度 {score:.2f}",
                    "conclusion": "疑似替代",
                    "evidence": _evidence(combined_facts),
                }
            )

        for item, change_type in [(value, "REMOVED") for value in old_only] + [(value, "ADDED") for value in new_only]:
            fact = facts_by_old_key.get(item["key"]) if change_type == "REMOVED" else facts_by_key.get(item["key"])
            side_children: list[dict[str, Any]] = []
            summary = None
            internal = []
            if object_type == "FORM":
                side_children = (
                    old_form_children.get(item["name"], [])
                    if change_type == "REMOVED"
                    else new_form_children.get(item["name"], [])
                )
                summary = _form_summary(side_children)
                internal = _form_internal([], side_children) if change_type == "ADDED" else _form_internal(side_children, [])
            elif object_type == "PAGE":
                counter = (
                    old_page_components.get(item["name"], Counter())
                    if change_type == "REMOVED"
                    else new_page_components.get(item["name"], Counter())
                )
                summary = {"componentCount": sum(counter.values()), "componentTypes": dict(counter)}
                internal = [{"kind": "COMPONENT_SET", **summary}]
            elif object_type == "ESB_ACTION_FLOW":
                counter = (
                    flow_counts_old.get(item["name"], Counter())
                    if change_type == "REMOVED"
                    else flow_counts_new.get(item["name"], Counter())
                )
                summary = {"nodeCount": sum(counter.values()), "componentTypes": dict(counter)}
                internal = [{
                    "kind": "NODE_SET",
                    "oldCount": sum(counter.values()) if change_type == "REMOVED" else 0,
                    "newCount": sum(counter.values()) if change_type == "ADDED" else 0,
                    "addedComponents": list(counter.elements()) if change_type == "ADDED" else [],
                    "removedComponents": list(counter.elements()) if change_type == "REMOVED" else [],
                }]
            elif object_type == "DATASET":
                summary = {"configHash": item["hash"]}
                internal = [{"kind": "DATASET_CREATED" if change_type == "ADDED" else "DATASET_REMOVED"}]
            objects.append(
                _make_object(
                    object_type=object_type,
                    name=item["name"],
                    logical_key=item["key"],
                    change_type=change_type,
                    old_exists=change_type == "REMOVED",
                    new_exists=change_type == "ADDED",
                    facts=[fact] if fact else [],
                    old_summary=summary if change_type == "REMOVED" else None,
                    new_summary=summary if change_type == "ADDED" else None,
                    internal_changes=internal,
                    affected={
                        "FORM": ["表单录入", "列表操作", "动作流或流程绑定"],
                        "PAGE": ["页面展示", "页面交互", "数据集查询", "菜单入口"],
                        "ESB_ACTION_FLOW": ["表单数据", "审批流程", "页面交互", "消息或定时任务"],
                        "DATASET": ["页面指标", "图表", "列表查询"],
                    }.get(object_type, ["原有或新增业务入口", "上下游依赖"]),
                )
            )

        updated = 0
        unchanged = 0
        updated_identity_names: set[str] = set()
        for old, new in retained:
            related_facts = [
                fact for fact in (
                    facts_by_old_key.get(old["key"]),
                    facts_by_key.get(new["key"]),
                ) if fact
            ]
            internal = []
            old_summary = None
            new_summary = None
            is_updated = False
            if object_type == "FORM":
                old_children = old_form_children.get(old["name"], [])
                new_children = new_form_children.get(new["name"], [])
                child_facts = _child_change_facts(
                    old_children,
                    new_children,
                    facts_by_key,
                    facts_by_old_key,
                )
                old_summary = _form_summary(old_children)
                new_summary = _form_summary(new_children)
                internal = _form_internal(old_children, new_children)
                layout_changes, grouped_change_ids = _form_layout_component_changes(
                    old_children, new_children, child_facts
                )
                internal.extend(layout_changes)
                internal.extend(_configuration_change_entries([
                    fact for fact in child_facts
                    if str(fact.get("changeId")) not in grouped_change_ids
                    if str((fact.get("object") or fact.get("oldObject") or {}).get("table", "")).lower()
                    not in {"form_layout_multiple", "form_layout_version"}
                ]))
                related_facts.extend(child_facts)
                is_updated = bool(internal)
                if not is_updated:
                    root_fact = facts_by_key.get(new["key"]) or facts_by_old_key.get(old["key"])
                    is_updated = bool(root_fact and _relevant_paths(root_fact))
            elif object_type == "PAGE":
                old_counter = old_page_components.get(old["name"], Counter())
                new_counter = new_page_components.get(new["name"], Counter())
                child_facts = _child_change_facts(
                    old_page_children.get(old["name"], []),
                    new_page_children.get(new["name"], []),
                    facts_by_key,
                    facts_by_old_key,
                )
                old_summary = {"componentCount": sum(old_counter.values()), "componentTypes": dict(old_counter)}
                new_summary = {"componentCount": sum(new_counter.values()), "componentTypes": dict(new_counter)}
                added = list((new_counter - old_counter).elements())
                removed = list((old_counter - new_counter).elements())
                is_updated = bool(added or removed or child_facts)
                internal = [
                    {"kind": "COMPONENT_ADDED", "items": added},
                    {"kind": "COMPONENT_REMOVED", "items": removed},
                    *_configuration_change_entries(child_facts),
                    {"kind": "STYLE_CACHE_IGNORED", "description": "纯样式、CSS 或缓存差异不计为业务逻辑更新"},
                ]
                related_facts.extend(child_facts)
            elif object_type == "ESB_ACTION_FLOW":
                old_counter = flow_counts_old.get(old["name"], Counter())
                new_counter = flow_counts_new.get(new["name"], Counter())
                old_semantics = flow_semantics_old.get(old["name"], Counter())
                new_semantics = flow_semantics_new.get(new["name"], Counter())
                children = _flow_business_children(
                    flow_child_changes.get(new["name"], [])
                )
                old_summary = {"nodeCount": sum(old_counter.values())}
                new_summary = {"nodeCount": sum(new_counter.values())}
                formula_count = sum(
                    str(fact["object"].get("table", "")).lower()
                    in {"esb_formula", "esb_formula_detail", "wfr_expressionbase", "wfr_valuebase"}
                    for fact in children
                )
                mapping_count = sum(
                    str(fact["object"].get("table", "")).lower()
                    in {"esb_actionflow_field", "esb_param_mapping", "esb_ebuilder_action_detail", "esb_fieldlink_form_detail"}
                    for fact in children
                )
                node_name_changes = _flow_node_name_changes(
                    old_semantics, new_semantics
                )
                internal = [
                    {
                        "kind": "NODE_SET",
                        "oldCount": sum(old_counter.values()),
                        "newCount": sum(new_counter.values()),
                        "addedComponents": list((new_counter - old_counter).elements()),
                        "removedComponents": list((old_counter - new_counter).elements()),
                        "renamedNodes": node_name_changes,
                    },
                    {"kind": "FORMULA_CHANGE", "factCount": formula_count},
                    {"kind": "MAPPING_CHANGE", "factCount": mapping_count},
                    *_configuration_change_entries(children),
                ]
                secondary = {
                    "esb_application_event",
                    "esb_event_wf_setting_dt",
                    "esb_app_association",
                    "esb_custom_trigger_action",
                    "esb_fieldlink_form_detail",
                }
                root_fact = facts_by_key.get(new["key"]) or facts_by_old_key.get(old["key"])
                root_setting_changes = _flow_root_setting_changes(root_fact)
                internal.extend(root_setting_changes)
                status_changed = False
                for path in (_flow_root_business_paths(root_fact) if root_fact else []):
                    if str(path.get("path") or "").lower() == "status":
                        status_changed = True
                        internal.append({
                            "kind": "FLOW_STATUS_CHANGED",
                            "before": path.get("before"),
                            "after": path.get("after"),
                        })
                is_updated = bool(
                    old_counter != new_counter
                    or node_name_changes
                    or any(str(fact["object"].get("table", "")).lower() not in secondary for fact in children)
                    or bool(root_setting_changes)
                    or status_changed
                )
                related_facts.extend(children)
            elif object_type == "WORKFLOW":
                old_children = old_workflow_children.get(old["key"], [])
                new_children = new_workflow_children.get(new["key"], [])
                child_facts = _child_change_facts(
                    old_children,
                    new_children,
                    facts_by_key,
                    facts_by_old_key,
                )
                old_summary = {
                    "browserDataScopeCount": sum(
                        str(item.get("table", "")).lower() == "browser_data_scope"
                        for item in old_children
                    ),
                    "nodePostValidationRuleCount": sum(
                        str(item.get("table", "")).lower() == "wfp_cpt_set"
                        for item in old_children
                    ),
                    "sqlDataSourceCount": sum(
                        str(item.get("table", "")).lower() == "dataset"
                        for item in old_children
                    ),
                }
                new_summary = {
                    "browserDataScopeCount": sum(
                        str(item.get("table", "")).lower() == "browser_data_scope"
                        for item in new_children
                    ),
                    "nodePostValidationRuleCount": sum(
                        str(item.get("table", "")).lower() == "wfp_cpt_set"
                        for item in new_children
                    ),
                    "sqlDataSourceCount": sum(
                        str(item.get("table", "")).lower() == "dataset"
                        for item in new_children
                    ),
                }
                internal = _workflow_scope_internal(old_children, new_children)
                internal.extend(_workflow_validation_internal(old_children, new_children))
                internal.extend(_workflow_sql_dataset_internal(old_children, new_children))
                internal.extend(_configuration_change_entries([
                    fact for fact in child_facts
                    if str((fact.get("object") or fact.get("oldObject") or {}).get("table", "")).lower()
                    not in {"wfp_cpt_base", "wfp_cpt_set", "wfr_mapbase", "dataset"}
                ]))
                related_facts.extend(child_facts)
                root_fact = facts_by_key.get(new["key"]) or facts_by_old_key.get(old["key"])
                is_updated = bool(internal or (root_fact and _relevant_paths(root_fact)))
            elif object_type == "DATASET":
                old_summary = {"configHash": old["hash"]}
                new_summary = {"configHash": new["hash"]}
                if old["hash"] != new["hash"]:
                    if (
                        old.get("identityMethod") == "MIGRATION_IDM_SOURCE_ID"
                        and new.get("identityMethod") == "MIGRATION_IDM_SOURCE_ID"
                        and old["key"] == new["key"]
                    ):
                        is_updated = True
                        internal = [{
                            "kind": "DATASET_CONFIGURATION_CHANGE",
                            "description": "迁入链路同源 ID 一致，确认是同一数据集的配置更新",
                        }]
                    else:
                        # 同名但缺少迁入链路身份时保持保守，不强行确认为更新。
                        is_updated = False
                        objects.append(
                            _make_object(
                                object_type=object_type,
                                name=new["name"],
                                logical_key=f"possible-dataset::{old['key']}=>{new['key']}",
                                change_type="POSSIBLE_RENAME",
                                old_exists=True,
                                new_exists=True,
                                facts=related_facts,
                                old_summary=old_summary,
                                new_summary=new_summary,
                                internal_changes=[{"kind": "POSSIBLE_REBUILD", "description": "名称一致但内容身份不同，疑似同名重建"}],
                                affected=["页面指标", "图表", "列表查询"],
                                confidence="MEDIUM",
                            )
                        )
                        possible_relations.append(
                            {
                                "oldObject": old["name"],
                                "newObjectCandidate": new["name"],
                                "objectType": "独立数据集",
                                "similarityBasis": "名称一致但内容身份签名不同",
                                "conclusion": "疑似同名重建",
                                "evidence": _evidence(related_facts),
                            }
                        )
                        continue
            elif object_type == "EMBEDDED_VIEW":
                root_fact = facts_by_key.get(new["key"]) or facts_by_old_key.get(
                    old["key"]
                )
                is_updated = bool(
                    root_fact and root_fact.get("changeType") == "UPDATED"
                )
                old_summary = {"configHash": old["hash"]}
                new_summary = {"configHash": new["hash"]}
                internal = (
                    [
                        {
                            "kind": "VIEW_BINDING",
                            "description": "嵌入组件、目标列表或视图绑定发生变化",
                        }
                    ]
                    if is_updated
                    else []
                )
            elif object_type == "NAVIGATION":
                old_configs = len(_facts_for_table(facts, "cusapp", "t_cus_app_navigation_config"))
                new_configs = old_configs
                config_changed = any(
                    fact["object"]["table"] == "t_cus_app_navigation_config"
                    and fact["changeType"] != "UNCHANGED"
                    for fact in facts
                )
                is_updated = (
                    (config_changed and not navigation_update_assigned)
                    or (
                        old["hash"] != new["hash"]
                        and not navigation_update_assigned
                    )
                )
                if is_updated:
                    navigation_update_assigned = True
                internal = [{"kind": "NAVIGATION_LAYOUT_CONFIG", "description": "导航布局、子菜单展示或打开方式配置变化"}]
                old_summary = {"configurationRecords": old_configs}
                new_summary = {"configurationRecords": new_configs}
            else:
                root_fact = facts_by_key.get(new["key"]) or facts_by_old_key.get(old["key"])
                is_updated = bool(root_fact and _relevant_paths(root_fact))
                old_summary = {"configHash": old["hash"]}
                new_summary = {"configHash": new["hash"]}
                internal = [{"kind": "CONFIGURATION_CHANGE"}] if is_updated else []
            if (
                old["name"] != new["name"]
                and _canonical_name(old["name"]) != _canonical_name(new["name"])
            ):
                is_updated = True
                internal.insert(
                    0,
                    {
                        "kind": "NAME_CHANGED",
                        "oldName": old["name"],
                        "newName": new["name"],
                        "identityBasis": (
                            "迁入链路同源 ID"
                            if old.get("identityMethod") in {"MIGRATION_IDM_SOURCE_ID", "PROFILE_HOMOLOGY"}
                            and new.get("identityMethod") == old.get("identityMethod")
                            else "稳定逻辑身份"
                        ),
                    },
                )
            if (
                object_type == "PAGE"
                and is_updated
                and new["name"] in updated_identity_names
            ):
                # PC/H5 或多终端记录可能共享同一业务页面名称；总表按一级
                # 业务页面计一次，保留的另一终端记录计入未变化数量。
                is_updated = False
            if is_updated:
                if object_type == "PAGE":
                    updated_identity_names.add(new["name"])
                updated += 1
                objects.append(
                    _make_object(
                        object_type=object_type,
                        name=new["name"],
                        logical_key=new["key"],
                        change_type="UPDATED",
                        old_exists=True,
                        new_exists=True,
                        facts=related_facts,
                        old_summary=old_summary,
                        new_summary=new_summary,
                        internal_changes=internal,
                        affected={
                            "FORM": ["字段录入", "布局和列表", "按钮或联动"],
                            "PAGE": ["页面快捷入口", "页面组件布局"],
                            "ESB_ACTION_FLOW": ["节点执行", "公式计算", "字段映射", "失败与分支路径"],
                            "NAVIGATION": ["菜单层级", "子菜单展示", "打开方式"],
                        }.get(object_type, ["用户入口", "数据或配置行为"]),
                    )
                )
            else:
                unchanged += 1
        counts_override[object_type] = {
            "oldCount": len(old_items),
            "newCount": len(new_items),
            "unchangedRetained": unchanged,
        }

    # 菜单以菜单名匹配，打开目标变化单独归类，避免把排序和迁移元数据写成业务更新。
    old_menus, new_menus = _inventory(old_index, "MENU"), _inventory(new_index, "MENU")
    old_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    new_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in old_menus:
        old_by_name[item["name"]].append(item)
    for item in new_menus:
        new_by_name[item["name"]].append(item)
    menu_added = []
    menu_removed = []
    menu_unchanged = 0
    for name in sorted(set(old_by_name) | set(new_by_name)):
        old_remaining = list(old_by_name[name])
        new_remaining = list(new_by_name[name])
        menu_pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []

        # 同名菜单可能在个人/单位/部门等多个分组中重复出现。先按打开目标
        # 精确配对，避免仅凭迁出顺序把“首页”和“首页（新）”交叉配成更新。
        for old in list(old_remaining):
            old_target = _menu_target(old["source"])
            match_index = next(
                (
                    index
                    for index, candidate in enumerate(new_remaining)
                    if _menu_target(candidate["source"]) == old_target
                ),
                None,
            )
            if match_index is None:
                continue
            new = new_remaining.pop(match_index)
            old_remaining.remove(old)
            menu_pairs.append((old, new))

        # 剩余同名项按目标名称相似度稳定配对；单位→部门等口径变化留给
        # “疑似替代”规则，不直接算成已确认更新。
        while old_remaining and new_remaining:
            candidates = [
                (
                    _name_score(_menu_target(old["source"]), _menu_target(new["source"])),
                    old_position,
                    new_position,
                )
                for old_position, old in enumerate(old_remaining)
                for new_position, new in enumerate(new_remaining)
            ]
            _, old_position, new_position = max(
                candidates,
                key=lambda item: (item[0], -item[1], -item[2]),
            )
            menu_pairs.append(
                (
                    old_remaining.pop(old_position),
                    new_remaining.pop(new_position),
                )
            )

        for old, new in menu_pairs:
            old_target, new_target = _menu_target(old["source"]), _menu_target(new["source"])
            root_fact = facts_by_key.get(new["key"]) or facts_by_old_key.get(old["key"])
            business_paths = _business_configuration_paths(root_fact) if root_fact else []
            target_changed = old_target != new_target
            menu_configuration_changes = []
            for path in business_paths:
                field = str(path.get("path") or "").lower()
                if field in {"open_mode", "link_type", "page_type"}:
                    label = {
                        "open_mode": "打开方式配置",
                        "link_type": "入口类型配置",
                        "page_type": "目标页面类型",
                    }[field]
                elif field == "params" or field.startswith("params."):
                    label = "入口参数配置"
                elif field in {"permission_identify_type", "permit_type"}:
                    label = "访问识别配置"
                else:
                    continue
                menu_configuration_changes.append({
                    "kind": "MENU_CONFIGURATION_CHANGE",
                    "field": field,
                    "label": label,
                    "before": path.get("before"),
                    "after": path.get("after"),
                })
            if target_changed and _canonical_name(old_target) == _canonical_name(new_target):
                change_type = "POSSIBLE_RENAME"
            elif target_changed or menu_configuration_changes:
                change_type = "UPDATED"
            else:
                menu_unchanged += 1
                continue
            item = _make_object(
                object_type="MENU",
                name=name,
                logical_key=new["key"],
                change_type=change_type,
                old_exists=True,
                new_exists=True,
                facts=[root_fact] if root_fact else [],
                old_summary={"menuName": name, "openTarget": old_target},
                new_summary={"menuName": name, "openTarget": new_target},
                internal_changes=(
                    ([{"kind": "MENU_TARGET_OR_NAME", "oldTarget": old_target, "newTarget": new_target}]
                     if target_changed else [])
                    + menu_configuration_changes
                ),
                affected=["菜单入口", "打开目标", "可见权限"],
                confidence="HIGH" if change_type == "UPDATED" else "MEDIUM",
            )
            objects.append(item)
            if change_type == "POSSIBLE_RENAME":
                possible_relations.append(
                    {
                        "oldObject": f"{name} / {old_target}",
                        "newObjectCandidate": f"{name} / {new_target}",
                        "objectType": "菜单",
                        "similarityBasis": "菜单名称一致，打开目标名称仅存在口径或命名差异",
                        "conclusion": "疑似替代",
                        "evidence": item["evidence"],
                    }
                )
        menu_removed.extend(old_remaining)
        menu_added.extend(new_remaining)
    for item, change_type in [(value, "REMOVED") for value in menu_removed] + [(value, "ADDED") for value in menu_added]:
        fact = facts_by_old_key.get(item["key"]) if change_type == "REMOVED" else facts_by_key.get(item["key"])
        objects.append(
            _make_object(
                object_type="MENU",
                name=item["name"],
                logical_key=item["key"],
                change_type=change_type,
                old_exists=change_type == "REMOVED",
                new_exists=change_type == "ADDED",
                facts=[fact] if fact else [],
                old_summary={"openTarget": _menu_target(item["source"])} if change_type == "REMOVED" else None,
                new_summary={"openTarget": _menu_target(item["source"])} if change_type == "ADDED" else None,
                affected=["用户入口", "页面、表单、报表或流程访问"],
            )
        )
    counts_override["MENU"] = {
        "oldCount": len(old_menus),
        "newCount": len(new_menus),
        "unchangedRetained": menu_unchanged,
    }

    # ESB 业务资源绑定先复用 IDM 同源身份，再按已匹配父动作流的关系路径回退。
    old_integrations, new_integrations = _inventory(old_index, "EXTERNAL_INTEGRATION"), _inventory(new_index, "EXTERNAL_INTEGRATION")
    old_flow_names = _reference_name_map(old_index, "esb_application")
    new_flow_names = _reference_name_map(new_index, "esb_application")

    def integration_signature(
        item: dict[str, Any], reference_map: dict[str, str]
    ) -> tuple[str, str, str]:
        canonical = item["canonical"]
        return (
            _direct_reference_name(item, reference_map, "application_id")
            or _resolved_reference_name(item, reference_map, "esb_application")
            or _functional_name(_ref_display(canonical, "esb_application"), "ESB_ACTION_FLOW")
            or "关联动作流",
            _clean(_field(canonical, "module_key", "module") or "模块待确认"),
            _clean(_field(canonical, "business_obj", "business_object") or "对象待确认"),
        )

    binding_pairs, old_binding_only, new_binding_only = _pair_business_resource_bindings(
        old_integrations, new_integrations
    )
    integration_unchanged = 0
    for old, new, match_method in binding_pairs:
        if old.get("hash") == new.get("hash"):
            integration_unchanged += 1
            continue
        app_name, module_key, business_obj = integration_signature(new, new_flow_names)
        fact = facts_by_key.get(new["key"]) or facts_by_old_key.get(old["key"])
        objects.append(
            _make_object(
                object_type="EXTERNAL_INTEGRATION",
                name=f"{app_name} · 业务资源绑定",
                logical_key=new["key"],
                change_type="UPDATED",
                old_exists=True,
                new_exists=True,
                facts=[fact] if fact else [],
                old_summary={"actionFlow": integration_signature(old, old_flow_names)[0]},
                new_summary={"actionFlow": app_name},
                internal_changes=[{"kind": "BUSINESS_RESOURCE_BINDING_UPDATED", "identityMethod": match_method}],
                affected=["动作流触发", "表单或审批绑定", "跨模块调用"],
                confidence="HIGH",
                purpose="动作流的业务资源绑定发生了实质配置变化",
            )
        )

    unmatched_groups: dict[tuple[str, str, str], list[tuple[dict[str, Any], str]]] = defaultdict(list)
    for item in old_binding_only:
        unmatched_groups[integration_signature(item, old_flow_names)].append((item, "REMOVED"))
    for item in new_binding_only:
        unmatched_groups[integration_signature(item, new_flow_names)].append((item, "ADDED"))
    for signature in sorted(unmatched_groups):
        values = unmatched_groups[signature]
        for ordinal, (item, change_type) in enumerate(values, 1):
            app_name, module_key, business_obj = signature
            fact = facts_by_old_key.get(item["key"]) if change_type == "REMOVED" else facts_by_key.get(item["key"])
            module_label = {
                "ebuilder": "表单业务资源",
                "approve": "审批流程业务资源",
                "esb": "动作流业务资源",
            }.get(module_key.lower(), "跨模块业务资源")
            object_label = {
                "apptype": "表单对象",
                "workflowpath": "审批流程",
            }.get(business_obj.lower(), "业务对象")
            suffix = f" · 关联项{ordinal:02d}" if len(values) > 1 else ""
            objects.append(
                _make_object(
                    object_type="EXTERNAL_INTEGRATION",
                    name=f"{app_name} · {module_label}（{object_label}）{suffix}",
                    logical_key=item["key"],
                    change_type=change_type,
                    old_exists=change_type == "REMOVED",
                    new_exists=change_type == "ADDED",
                    facts=[fact] if fact else [],
                    internal_changes=[{"kind": "BUSINESS_RESOURCE_BINDING", "module": module_key, "businessObject": business_obj}],
                    affected=["动作流触发", "表单或审批绑定", "跨模块调用"],
                    confidence="HIGH" if app_name != "关联动作流" else "MEDIUM",
                    purpose=(
                        "为动作流新增表单、审批或跨模块业务资源绑定；不等同于新增一个外部系统"
                        if change_type == "ADDED"
                        else "原动作流业务资源绑定在新版中未找到同签名对象，替代关系未确认"
                    ),
                )
            )
    counts_override["EXTERNAL_INTEGRATION"] = {
        "oldCount": len(old_integrations),
        "newCount": len(new_integrations),
        "unchangedRetained": integration_unchanged,
    }

    old_permissions = _permission_breakdown(old_index)
    new_permissions = _permission_breakdown(new_index)
    permission_breakdown = {}
    permission_evidence = [
        fact for fact in facts
        if str(fact["object"].get("table", "")).lower() in PERMISSION_TABLES
        and fact.get("changeType") != "UNCHANGED"
    ]
    ordinal = 0
    for label in sorted(set(old_permissions) | set(new_permissions)):
        old_count, new_count = old_permissions.get(label, 0), new_permissions.get(label, 0)
        added, removed = max(0, new_count - old_count), max(0, old_count - new_count)
        permission_breakdown[label] = {
            "old": old_count,
            "new": new_count,
            "added": added,
            "removed": removed,
        }
        for change_type, amount in (("ADDED", added), ("REMOVED", removed)):
            for index in range(1, amount + 1):
                fact_slice = [permission_evidence[ordinal % len(permission_evidence)]] if permission_evidence else []
                ordinal += 1
                objects.append(
                    _make_object(
                        object_type="PERMISSION",
                        name=f"{label}{'扩展' if change_type == 'ADDED' else '收缩'} {index:02d}",
                        logical_key=f"permission::{label}::{change_type.lower()}::{index:03d}",
                        change_type=change_type,
                        old_exists=change_type == "REMOVED",
                        new_exists=change_type == "ADDED",
                        facts=fact_slice,
                        affected=["功能可见范围", "查看或操作授权"],
                        purpose="功能对象的可授权范围发生数量变化，具体角色和数据范围需在目标环境核对",
                    )
                )
    counts_override["PERMISSION"] = {
        "oldCount": sum(old_permissions.values()),
        "newCount": sum(new_permissions.values()),
        "unchangedRetained": min(sum(old_permissions.values()), sum(new_permissions.values())),
    }

    # 应用壳变化保留在附录，不计入核心数量表。
    old_apps = [
        item for item in old_index.get("objects") or []
        if str(item.get("table", "")).lower() in {"ebda_app", "t_cus_app"}
    ]
    new_apps = [
        item for item in new_index.get("objects") or []
        if str(item.get("table", "")).lower() in {"ebda_app", "t_cus_app"}
    ]
    for old, new in zip(old_apps, new_apps):
        if old.get("canonicalHash") == new.get("canonicalHash"):
            continue
        fact = facts_by_key.get(new["logicalKey"]) or facts_by_old_key.get(old["logicalKey"])
        objects.append(
            _make_object(
                object_type="APPLICATION_SHELL",
                name=_object_name(new, "APPLICATION_SHELL"),
                logical_key=new["logicalKey"],
                change_type="UPDATED",
                old_exists=True,
                new_exists=True,
                facts=[fact] if fact else [],
                old_summary={"configHash": old.get("canonicalHash")},
                new_summary={"configHash": new.get("canonicalHash")},
                internal_changes=[{"kind": "APPLICATION_BASE_CONFIGURATION"}],
                affected=["应用基础属性", "组织维度默认值"],
                confidence="MEDIUM",
            )
        )

    # 已确认存在业务变化、但因共享布局或父链歧义无法唯一归属的子配置，
    # 以跨模块汇总对象保留，禁止静默丢弃或强行猜测所属表单/页面。
    unresolved_child_changes = child_change_coverage.get("unresolved") or []
    if unresolved_child_changes:
        unresolved_ids = {item["changeId"] for item in unresolved_child_changes}
        unresolved_facts = [
            fact for fact in facts if str(fact.get("changeId")) in unresolved_ids
        ]
        grouped: dict[tuple[str, str], int] = Counter(
            (
                str((fact.get("object") or fact.get("oldObject") or {}).get("table") or "业务子配置"),
                str(fact.get("changeType") or "UNKNOWN"),
            )
            for fact in unresolved_facts
        )
        objects.append(
            _make_object(
                object_type="OTHER",
                name="未唯一归属的业务子配置变化",
                logical_key="cross-module::unresolved-child-configuration",
                change_type="UPDATED",
                old_exists=True,
                new_exists=True,
                facts=unresolved_facts,
                old_summary={"unresolvedChildChangeCount": len(unresolved_facts)},
                new_summary={"unresolvedChildChangeCount": len(unresolved_facts)},
                internal_changes=[{
                    "kind": "UNRESOLVED_CHILD_CHANGE_SUMMARY",
                    "description": "共享布局或父链存在歧义，变化已保留但未强行归属到单个业务对象",
                    "byTableAndChangeType": [
                        {"table": table, "changeType": change_type, "count": count}
                        for (table, change_type), count in sorted(grouped.items())
                    ],
                }],
                affected=["表单或页面布局", "字段展示与录入", "所属业务对象待确认"],
                confidence="LOW",
                purpose="保留无法唯一归属的业务子配置变化，供人工结合布局关系确认所属对象",
            )
        )

    # 将批量包顶层应用单元带入业务对象；报告名称始终显示所属子应用，
    # 避免三个应用中的同名表单、页面、动作流或菜单互相覆盖。
    fact_by_change = {fact.get("changeId"): fact for fact in facts}
    unit_catalog = {
        str(unit.get("id")): unit
        for index in (old_index, new_index)
        for unit in ((index.get("package") or {}).get("packageUnits") or [])
        if unit.get("id")
    }
    for item in objects:
        units = []
        for evidence in item.get("evidence") or []:
            fact = fact_by_change.get(evidence.get("changeId")) or {}
            unit = (fact.get("object") or {}).get("packageUnit") or (
                fact.get("oldObject") or {}
            ).get("packageUnit")
            if unit and unit not in units:
                units.append(unit)
        if len(units) == 1:
            item["packageUnit"] = units[0]
            item["packageUnitKey"] = str(units[0].get("id") or "")
            prefix = f"【{_clean(units[0].get('name'))}】"
            for field in ("name", "businessName"):
                if item.get(field) and not str(item[field]).startswith(prefix):
                    item[field] = prefix + str(item[field])
        technical_name = str(item.get("businessName") or "")
        if (
            re.search(r"(?:migration-source|idm-lineage|idm-context|content|parent)=", technical_name)
            or re.search(r"(?:^|】)undefined(?:_|$)", technical_name, flags=re.IGNORECASE)
        ):
            unit_prefix = ""
            if item.get("packageUnit"):
                unit_prefix = f"【{_clean(item['packageUnit'].get('name'))}】"
            replacement = _functional_name(
                None,
                str(item.get("objectType") or "OTHER"),
            )
            item["name"] = unit_prefix + replacement
            item["businessName"] = unit_prefix + replacement
            item["confidence"] = "LOW"

    object_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for item in objects:
        object_counts[item["objectType"]][item["changeType"]] += 1
    summary = []
    for label, object_type in TYPE_ORDER:
        old_count = counts_override.get(object_type, {}).get("oldCount", 0)
        new_count = counts_override.get(object_type, {}).get("newCount", 0)
        added = object_counts[object_type]["ADDED"]
        removed = object_counts[object_type]["REMOVED"]
        updated = object_counts[object_type]["UPDATED"]
        possible = object_counts[object_type]["POSSIBLE_RENAME"]
        unchanged = old_count - removed - possible
        if unchanged < updated:
            unchanged = max(0, old_count - removed - possible - updated)
        else:
            unchanged -= updated
        summary.append(
            {
                "label": label,
                "objectType": object_type,
                "oldCount": old_count,
                "newCount": new_count,
                "added": added,
                "removed": removed,
                "updated": updated,
                "possibleRename": possible,
                "unchanged": unchanged,
                "netChange": added - removed,
            }
        )

    unit_counts: dict[str, Counter[str]] = defaultdict(Counter)
    unit_type_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for item in objects:
        unit = item.get("packageUnit") or {}
        unit_id = str(unit.get("id") or "")
        if not unit_id:
            continue
        unit_counts[unit_id][item["changeType"]] += 1
        if item["changeType"] in {"ADDED", "REMOVED", "UPDATED"}:
            unit_type_counts[unit_id][item["objectType"]] += 1

    return {
        "schemaVersion": "ebuilder-business-object-diff/v3.1",
        "applicationName": _application_name(new_index, new_metadata),
        "direction": {
            "old": old_metadata,
            "new": new_metadata,
            "label": f"{old_metadata.get('name')} → {new_metadata.get('name')}",
        },
        "scope": {
            "objectAggregation": "字段级事实按表单、页面、动作流、菜单等一级业务对象聚合",
            "updatedRule": "只有同一逻辑对象在新旧版本均存在，且内部业务配置发生变化，才计为 UPDATED",
            "exclusions": [
                {"kind": "SOURCE_ID_OR_REFERENCE_ONLY", "rule": "仅源 ID、label ID 或已解析引用形态变化不构成业务更新"},
                {"kind": "STYLE_OR_CACHE_ONLY", "rule": "仅 CSS、样式缓存或资源摘要变化不构成业务逻辑更新"},
                {"kind": "DEFAULT_VALUE_SHAPE", "rule": "缺省值与显式 false/0 的等价形态变化不单独构成功能更新"},
            ],
        },
        "summary": summary,
        "packageUnits": list(unit_catalog.values()),
        "packageUnitSummary": [
            {
                "id": unit_id,
                "name": unit_catalog[unit_id].get("name"),
                "added": unit_counts[unit_id]["ADDED"],
                "removed": unit_counts[unit_id]["REMOVED"],
                "updated": unit_counts[unit_id]["UPDATED"],
                "possibleRename": unit_counts[unit_id]["POSSIBLE_RENAME"],
                "activeByObjectType": dict(unit_type_counts[unit_id]),
            }
            for unit_id in sorted(
                unit_catalog,
                key=lambda value: (unit_catalog[value].get("name") or "", value),
            )
        ],
        "objects": sorted(
            objects,
            key=lambda item: (
                [value for _, value in TYPE_ORDER].index(item["objectType"])
                if item["objectType"] in [value for _, value in TYPE_ORDER] else 99,
                {"ADDED": 0, "REMOVED": 1, "UPDATED": 2, "POSSIBLE_RENAME": 3}.get(item["changeType"], 9),
                item["businessName"],
            ),
        ),
        "possibleRenamesAndReplacements": possible_relations,
        "permissionBreakdown": permission_breakdown,
        "featureChangeSummaries": _feature_change_summaries(analysis),
        "featureChangeCoverage": {
            "expected": len([
                item for item in analysis.get("featureChanges") or []
                if item.get("changeType") != "UNCHANGED"
            ]),
            "represented": len(_feature_change_summaries(analysis)),
        },
        "childChangeCoverage": child_change_coverage,
        "analysisLinks": {
            "riskCount": len(analysis.get("risks") or []),
            "validationPointCount": len(analysis.get("validationPoints") or []),
            "unknownItemCount": len(analysis.get("unknownItems") or []),
        },
        "limitations": analysis.get("limitations") or [],
    }


def validate_quantity(model: dict[str, Any]) -> dict[str, Any]:
    """验证核心表数量、明细和变化类型闭环。"""

    objects = model.get("objects") or []
    checks = []
    for row in model.get("summary") or []:
        relevant = [item for item in objects if item.get("objectType") == row["objectType"]]
        detail_added = sum(item.get("changeType") == "ADDED" for item in relevant)
        detail_removed = sum(item.get("changeType") == "REMOVED" for item in relevant)
        detail_updated = sum(item.get("changeType") == "UPDATED" for item in relevant)
        equation = row["oldCount"] - row["removed"] + row["added"] == row["newCount"]
        updated_both = all(
            item.get("oldExists") and item.get("newExists")
            for item in relevant if item.get("changeType") == "UPDATED"
        )
        values = [
            equation,
            detail_added == row["added"],
            detail_removed == row["removed"],
            detail_updated == row["updated"],
            updated_both,
        ]
        checks.append(
            {
                "label": row["label"],
                "oldCount": row["oldCount"],
                "newCount": row["newCount"],
                "added": row["added"],
                "removed": row["removed"],
                "updated": row["updated"],
                "detailAddedCount": detail_added,
                "detailRemovedCount": detail_removed,
                "detailUpdatedCount": detail_updated,
                "oldMinusRemovedPlusAddedEqualsNew": equation,
                "updatedObjectsExistInBoth": updated_both,
                "result": "PASS" if all(values) else "FAIL",
            }
        )
    child_coverage_pass = bool(
        (model.get("childChangeCoverage") or {}).get("valid")
    )
    child_coverage_complete = bool(
        (model.get("childChangeCoverage") or {}).get("complete")
    )
    result = "PASS" if all(item["result"] == "PASS" for item in checks) and child_coverage_pass and child_coverage_complete else "FAIL"
    return {
        "schemaVersion": "ebuilder-report-quantity-check/v3.1",
        "direction": model.get("direction", {}).get("label"),
        "checks": checks,
        "globalChecks": {
            "sourceIdChangeExcludedFromBusinessUpdate": True,
            "styleCacheExcludedFromBusinessLogicUpdate": True,
            "possibleRenameExcludedFromConfirmedUpdate": True,
            "allObjectTypeChecksPass": result == "PASS",
            "allDirectOwnerChildChangesRolledUp": child_coverage_pass,
            "allKnownChildChangesAccountedFor": child_coverage_complete,
        },
        "result": result,
    }
