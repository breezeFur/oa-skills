#!/usr/bin/env python3
"""渲染 V7 风格的全量对象明细差异报告，不生成可视化、风险或验证内容。"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from render_business_object_report import (
    CHANGE_LABELS,
    COMPONENT_LABELS,
    FLOW_NODE_LABELS,
    TYPE_LABELS,
    _change_text,
    _business_item_name,
    _escape,
    _flow_node_component_label,
    _flow_change_columns,
    _form_change_columns,
    _items,
    _page_change_columns,
    _short,
    _summary,
)


APPENDIX_ORDER = [
    "FORM", "PAGE", "EMBEDDED_VIEW", "ESB_ACTION_FLOW", "WORKFLOW", "MENU",
    "NAVIGATION", "REPORT", "MULTI_FILLING", "DATASET", "EXTERNAL_INTEGRATION",
    "PERMISSION", "APPLICATION_SHELL", "OTHER",
]


TECHNICAL_IDENTITY_RE = re.compile(
    r"(?:migration-source|profile-lineage|idm-lineage|idm-context|content|parent)="
    r"|undefined_迁出使用关联视图",
    flags=re.IGNORECASE,
)


def _customer_target(value: Any) -> str:
    """Keep internal identity placeholders out of customer menu targets."""
    text = str(value or "").strip()
    if not text:
        return "未设置"
    if TECHNICAL_IDENTITY_RE.search(text):
        return "目标关系待确认"
    return text


def _load_model(path: Path) -> dict[str, Any]:
    if path.suffix == ".gz":
        import gzip
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(path.read_text(encoding="utf-8"))


def _count_text(item: dict[str, Any], key: str) -> str:
    summary = item.get(key) or {}
    if not summary:
        return "未设置"
    values = []
    for name, label in (
        ("fieldCount", "字段"), ("componentCount", "组件"), ("nodeCount", "节点"),
        ("layoutCount", "布局"), ("listCount", "列表"), ("buttonActionCount", "按钮"),
    ):
        if name in summary:
            values.append(f"{label}{summary.get(name, 0)}")
    if summary.get("openTarget"):
        values.append(f"目标：{_customer_target(summary['openTarget'])}")
    return "、".join(values) or "已存在"


def _state(item: dict[str, Any], side: str) -> str:
    exists = item.get("oldExists" if side == "old" else "newExists")
    return "存在" if exists else "不存在"


def _added_detail(item: dict[str, Any]) -> str:
    return _short(_change_text(item), 420)


def _removed_detail(item: dict[str, Any]) -> str:
    return _short(_change_text(item), 420)


def _updated_detail(item: dict[str, Any]) -> tuple[str, str, str]:
    object_type = item.get("objectType")
    if object_type == "FORM":
        columns = _form_change_columns(item)
        return "；".join(columns[:3]), columns[3], _short(item.get("businessPurpose"), 220)
    if object_type == "PAGE":
        columns = _page_change_columns(item)
        return f"组件 {columns[0]}", "；".join(columns[1:4]), columns[4]
    if object_type == "ESB_ACTION_FLOW":
        columns = _flow_change_columns(item)
        return f"节点 {columns[0]}", "；".join(columns[1:4]), columns[4]
    if object_type == "MENU":
        old_target = _customer_target((item.get("oldSummary") or {}).get("openTarget"))
        new_target = _customer_target((item.get("newSummary") or {}).get("openTarget"))
        target_text = (
            f"打开目标：{_short(old_target)} → {_short(new_target)}"
            if old_target != new_target
            else f"打开目标保持为“{_short(old_target)}”"
        )
        return target_text, _short(_change_text(item), 360), _short(item.get("businessPurpose"), 220)
    return _short(_change_text(item), 520), "", _short(item.get("businessPurpose"), 220)


def _limited_names(values: list[str], *, limit: int = 8) -> str:
    names = list(dict.fromkeys(str(value) for value in values if value not in (None, "")))
    visible = "、".join(names[:limit])
    return visible + (f"等 {len(names)} 项" if len(names) > limit else "")


def _customer_child_name(value: Any, category: str) -> str:
    text = _business_item_name(value)
    if re.fullmatch(r"[a-z][a-z0-9_]{4,}", text, flags=re.IGNORECASE) or text.startswith(("uf_", "ebdf_", "ebdd_", "form_")):
        return {
            "布局结构": "布局子配置",
            "列表": "列表子配置",
            "按钮或动作": "按钮或动作子配置",
            "联动": "联动子配置",
        }.get(category, "表单基础配置")
    return text


def _component_counts(values: dict[str, Any], *, limit: int = 6) -> tuple[int, str]:
    counter = Counter({str(name): int(count) for name, count in (values or {}).items()})
    total = sum(counter.values())
    parts = [
        f"{COMPONENT_LABELS.get(name, name + '组件')}×{count}"
        for name, count in counter.most_common(limit)
    ]
    if len(counter) > limit:
        parts.append(f"另 {len(counter) - limit} 类")
    return total, "、".join(parts)


def _is_order_only(change: dict[str, Any]) -> bool:
    fields = change.get("fields") or []
    if not fields:
        return False
    return all(
        any(token in str(field.get("path") or "").lower() for token in ("show_order", "sort_order", "display_order", "sequence"))
        for field in fields
    )


def _form_profile(item: dict[str, Any]) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "fieldsAdded": [], "fieldsRemoved": [], "layoutsAdded": [], "layoutsRemoved": [],
        "layoutComponents": [], "listDeltas": [], "buttonDeltas": [], "linkageDeltas": [],
        "orderItems": [], "otherChildren": defaultdict(list),
    }
    for change in item.get("internalChanges") or []:
        kind = change.get("kind")
        if kind == "FIELD_ADDED":
            profile["fieldsAdded"].extend(change.get("items") or [])
        elif kind == "FIELD_REMOVED":
            profile["fieldsRemoved"].extend(change.get("items") or [])
        elif kind == "FORM_LAYOUT_ADDED":
            profile["layoutsAdded"].extend(change.get("items") or [])
        elif kind == "FORM_LAYOUT_REMOVED":
            profile["layoutsRemoved"].extend(change.get("items") or [])
        elif kind == "FORM_LAYOUT_COMPONENTS_CHANGED":
            profile["layoutComponents"].append(change)
        elif kind == "LIST":
            profile["listDeltas"].append(change)
        elif kind == "BUTTON_ACTION":
            profile["buttonDeltas"].append(change)
        elif kind == "LINKAGE":
            profile["linkageDeltas"].append(change)
        elif kind == "CHILD_CONFIGURATION_CHANGE":
            name = str(change.get("itemName") or "业务子配置")
            table = str(change.get("table") or "").lower()
            if _is_order_only(change):
                profile["orderItems"].append(
                    _customer_child_name(name, "按钮或动作")
                )
            elif "button" in table or "action" in table or "ecode" in table:
                profile["otherChildren"]["按钮或动作"].append(name)
            elif "linkage" in table or "relate" in table:
                profile["otherChildren"]["联动"].append(name)
            elif "list" in table:
                profile["otherChildren"]["列表"].append(name)
            elif "layout" in table or "component" in table:
                profile["otherChildren"]["布局结构"].append(name)
            else:
                profile["otherChildren"]["其他配置"].append(name)
    profile["orderItems"] = list(dict.fromkeys(profile["orderItems"]))
    return profile


def _delta_phrase(label: str, change: dict[str, Any]) -> str:
    old_count = int(change.get("oldCount", 0) or 0)
    new_count = int(change.get("newCount", 0) or 0)
    delta = new_count - old_count
    if delta > 0:
        return f"{label}增加 {delta} 项"
    if delta < 0:
        return f"{label}减少 {-delta} 项"
    return f"{label}内容调整"


def _form_conclusion(item: dict[str, Any]) -> str:
    profile = _form_profile(item)
    conclusions = []
    if profile["fieldsAdded"]:
        conclusions.append(f"新增 {len(profile['fieldsAdded'])} 个字段")
    if profile["fieldsRemoved"]:
        conclusions.append(f"删除 {len(profile['fieldsRemoved'])} 个字段")
    for name in profile["layoutsAdded"]:
        conclusions.append(f"新增“{name}”布局")
    for name in profile["layoutsRemoved"]:
        conclusions.append(f"删除“{name}”布局")
    added_layouts = set(profile["layoutsAdded"])
    removed_layouts = set(profile["layoutsRemoved"])
    for change in profile["layoutComponents"]:
        name = str(change.get("layoutName") or "未命名布局")
        if name in added_layouts or name in removed_layouts:
            continue
        added_total, _ = _component_counts(change.get("added") or {})
        removed_total, _ = _component_counts(change.get("removed") or {})
        if added_total and removed_total:
            conclusions.append(f"重新编排“{name}”布局")
        elif added_total or removed_total or change.get("updatedCount"):
            conclusions.append(f"调整“{name}”布局")
    list_conclusions = [_delta_phrase("列表配置", change) for change in profile["listDeltas"]]
    if profile["orderItems"]:
        conclusions.append(f"调整 {len(profile['orderItems'])} 个按钮或功能入口的显示顺序")
    for change in profile["buttonDeltas"]:
        conclusions.append(_delta_phrase("按钮或动作配置", change))
    for change in profile["linkageDeltas"]:
        conclusions.append(_delta_phrase("联动配置", change))
    for category, names in profile["otherChildren"].items():
        if names and category not in {"布局结构", "列表"}:
            conclusions.append(f"调整 {len(set(names))} 项{category}")
    # Field/layout headlines come first, followed by list changes. Minor layout
    # evidence and generic child changes remain in the object expansion layer.
    if list_conclusions:
        insert_at = min(2, len(conclusions))
        conclusions[insert_at:insert_at] = list_conclusions
    conclusions = list(dict.fromkeys(conclusions))
    if not conclusions:
        return "内部业务配置发生调整"
    visible = conclusions[:3]
    if len(conclusions) > 3:
        visible.append(f"另有 {len(conclusions) - 3} 类配置调整")
    return "；".join(visible)


def _form_impact(item: dict[str, Any]) -> str:
    profile = _form_profile(item)
    impacts = []
    if profile["fieldsAdded"] or profile["fieldsRemoved"]:
        impacts.append("影响表单录入字段")
    if profile["layoutsAdded"] or profile["layoutsRemoved"] or profile["layoutComponents"]:
        impacts.append("影响表单录入界面和组件排布")
    if profile["listDeltas"] or profile["otherChildren"].get("列表"):
        impacts.append("影响列表展示或操作")
    if profile["orderItems"]:
        impacts.append("影响按钮排列，不改变功能数量")
    elif profile["buttonDeltas"] or profile["otherChildren"].get("按钮或动作"):
        impacts.append("影响按钮位置或操作入口")
    if profile["linkageDeltas"] or profile["otherChildren"].get("联动"):
        impacts.append("影响字段联动或关联操作")
    return "；".join(impacts[:2]) or "影响对应表单的配置和操作入口"


def _form_detail_rows(item: dict[str, Any]) -> list[tuple[str, str, str]]:
    profile = _form_profile(item)
    rows: list[tuple[str, str, str]] = []
    if profile["fieldsAdded"]:
        rows.append(("字段", "新增", f"新增 {len(profile['fieldsAdded'])} 个字段：{_limited_names(profile['fieldsAdded'])}"))
    if profile["fieldsRemoved"]:
        rows.append(("字段", "删除", f"删除 {len(profile['fieldsRemoved'])} 个字段：{_limited_names(profile['fieldsRemoved'])}"))
    for name in profile["layoutsAdded"]:
        rows.append(("布局", "新增", f"新增“{name}”布局"))
    for name in profile["layoutsRemoved"]:
        rows.append(("布局", "删除", f"删除“{name}”布局"))
    for change in profile["layoutComponents"]:
        name = str(change.get("layoutName") or "未命名布局")
        added_total, added_text = _component_counts(change.get("added") or {})
        removed_total, removed_text = _component_counts(change.get("removed") or {})
        detail = []
        if added_total:
            detail.append(f"新增 {added_total} 个组件（{added_text}）")
        if removed_total:
            detail.append(f"删除 {removed_total} 个组件（{removed_text}）")
        if change.get("updatedCount"):
            detail.append(f"调整 {change['updatedCount']} 个组件配置")
        if added_total and removed_total:
            change_type = "结构重排"
        elif added_total:
            change_type = "组件新增"
        elif removed_total:
            change_type = "组件删除"
        else:
            change_type = "配置调整"
        rows.append((f"“{name}”布局", change_type, "；".join(detail) or "布局内部配置调整"))
    for change in profile["listDeltas"]:
        rows.append(("列表", "数量变化", _delta_phrase("列表配置", change)))
    if profile["orderItems"]:
        rows.append(("按钮/功能入口", "显示顺序调整", f"共 {len(profile['orderItems'])} 项：{_limited_names(profile['orderItems'])}"))
    for change in profile["buttonDeltas"]:
        rows.append(("按钮/动作", "数量变化", _delta_phrase("按钮或动作配置", change)))
    for change in profile["linkageDeltas"]:
        rows.append(("联动", "数量变化", _delta_phrase("联动配置", change)))
    for category, names in profile["otherChildren"].items():
        if not names:
            continue
        customer_names = [_customer_child_name(name, category) for name in names]
        rows.append((category, "配置调整", f"涉及 {len(set(customer_names))} 项：{_limited_names(customer_names)}"))
    return rows or [("其他配置", "调整", "内部业务配置发生调整，未观察到可进一步命名的子项")]


def _configuration_changes(item: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        change for change in item.get("internalChanges") or []
        if change.get("kind") == "CHILD_CONFIGURATION_CHANGE"
    ]


def _page_profile(item: dict[str, Any]) -> dict[str, Any]:
    added, removed, config_changes = [], [], _configuration_changes(item)
    for change in item.get("internalChanges") or []:
        if change.get("kind") == "COMPONENT_ADDED":
            added.extend(change.get("items") or [])
        elif change.get("kind") == "COMPONENT_REMOVED":
            removed.extend(change.get("items") or [])
    paths = [
        str(field.get("path") or "").lower()
        for change in config_changes for field in change.get("fields") or []
    ]
    tables = [str(change.get("table") or "").lower() for change in config_changes]
    names = [str(change.get("itemName") or "") for change in config_changes]
    operations = [
        str(change.get("changeType") or "")
        for change in config_changes
    ]
    child_added = []
    child_removed = []
    for change, name, operation in zip(config_changes, names, operations):
        readable_name = _business_item_name(name)
        component_match = re.search(r'type="([^"]+)"', name)
        component_name = component_match.group(1) if component_match else ""
        if operation == "ADDED":
            child_added.append(component_name or readable_name)
        elif operation == "REMOVED":
            child_removed.append(component_name or readable_name)
    added.extend(child_added)
    removed.extend(child_removed)
    list_name_count = sum("列表组件" in _business_item_name(name) for name in names)
    return {
        "added": added,
        "removed": removed,
        "changes": config_changes,
        "listCount": sum("list" in table for table in tables) + list_name_count,
        "interactionCount": sum(any(token in path for token in ("eventgroup", "event_group", "onclick", "action")) for path in paths),
        "dataCount": sum(any(token in path for token in ("fieldusage", "filter", "dataset", "query", "data")) for path in paths),
        "navigationCount": sum(any(token in path for token in ("target", "navigate", "navmenu", "open")) for path in paths),
        "structureCount": sum(any(token in path for token in ("flow", "layout", "nodes", "parent")) for path in paths),
    }


def _component_summary(values: list[str]) -> str:
    counter = Counter(str(value) for value in values if value not in (None, ""))
    def label(name: str) -> str:
        if name in FLOW_NODE_LABELS:
            return _flow_node_component_label(name)
        if name in COMPONENT_LABELS:
            return COMPONENT_LABELS[name]
        if name.endswith(("组件", "配置", "项", "节点", "面板", "容器")):
            return name
        return name + "组件"
    return "、".join(
        f"{label(name)}×{count}"
        for name, count in counter.most_common(6)
    )


def _page_conclusion(item: dict[str, Any]) -> str:
    profile = _page_profile(item)
    added, removed = Counter(profile["added"]), Counter(profile["removed"])
    if added and removed:
        conclusion = "页面结构与组件编排调整"
    elif added:
        conclusion = "新增页面组件"
    elif removed:
        conclusion = "删除页面组件"
    elif profile["listCount"] or profile["dataCount"]:
        conclusion = "列表展示或查询配置调整"
    elif profile["interactionCount"] or profile["navigationCount"]:
        conclusion = "页面交互或跳转配置调整"
    elif profile["structureCount"]:
        conclusion = "页面布局结构调整"
    else:
        conclusion = "页面业务配置调整"
    qualifiers = []
    if profile["listCount"] or profile["dataCount"]:
        qualifiers.append("涉及列表/数据")
    if profile["interactionCount"] or profile["navigationCount"]:
        qualifiers.append("涉及交互/跳转")
    return conclusion + ("（" + "、".join(qualifiers) + "）" if qualifiers else "")


def _page_specific_change(item: dict[str, Any]) -> str:
    profile = _page_profile(item)
    details = []
    if profile["added"]:
        details.append("新增" + _component_summary(profile["added"]))
    if profile["removed"]:
        details.append("删除" + _component_summary(profile["removed"]))
    if profile["listCount"] or profile["dataCount"]:
        count = max(profile["listCount"], profile["dataCount"])
        details.append(f"列表展示、查询条件或数据范围共 {count} 处调整")
    if profile["interactionCount"]:
        details.append(f"按钮或页面交互共 {profile['interactionCount']} 处调整")
    if profile["navigationCount"]:
        details.append(f"跳转或导航目标共 {profile['navigationCount']} 处调整")
    if not details and profile["changes"]:
        details.append(f"页面业务子配置共 {len(profile['changes'])} 处调整，具体行为待确认")
    return "；".join(details[:4]) or "页面结构或业务配置发生调整"


def _page_impact(item: dict[str, Any]) -> str:
    profile = _page_profile(item)
    impacts = []
    if profile["added"] or profile["removed"] or profile["structureCount"]:
        impacts.append("影响页面展示布局和操作区域")
    if profile["listCount"] or profile["dataCount"]:
        impacts.append("可能影响列表字段、筛选条件或数据范围")
    if profile["interactionCount"] or profile["navigationCount"]:
        impacts.append("可能影响点击、刷新或跳转行为")
    return "；".join(impacts[:2]) or "影响对应页面的展示或交互配置"


def _page_detail_rows(item: dict[str, Any]) -> list[tuple[str, str, str]]:
    profile = _page_profile(item)
    rows = []
    if profile["added"] or profile["removed"]:
        details = []
        if profile["added"]:
            details.append("新增" + _component_summary(profile["added"]))
        if profile["removed"]:
            details.append("删除" + _component_summary(profile["removed"]))
        rows.append(("页面结构", "组件调整", "；".join(details)))
    if profile["listCount"] or profile["dataCount"]:
        rows.append(("列表/数据", "配置调整", f"列表展示、查询条件或数据范围共 {max(profile['listCount'], profile['dataCount'])} 处调整"))
    if profile["interactionCount"]:
        rows.append(("页面交互", "参数调整", f"按钮或页面交互共 {profile['interactionCount']} 处调整；无法静态还原的具体行为标记为待确认"))
    if profile["navigationCount"]:
        rows.append(("跳转/导航", "目标调整", f"跳转或导航目标共 {profile['navigationCount']} 处调整"))
    if not rows:
        rows.append(("页面配置", "调整", f"共 {len(profile['changes'])} 处业务子配置变化，具体行为待确认"))
    return rows


def _flow_profile(item: dict[str, Any]) -> dict[str, Any]:
    node = next((change for change in item.get("internalChanges") or [] if change.get("kind") == "NODE_SET"), {})
    formula = next((change for change in item.get("internalChanges") or [] if change.get("kind") == "FORMULA_CHANGE"), {})
    mapping = next((change for change in item.get("internalChanges") or [] if change.get("kind") == "MAPPING_CHANGE"), {})
    name_change = next((change for change in item.get("internalChanges") or [] if change.get("kind") == "NAME_CHANGED"), {})
    status_change = next((change for change in item.get("internalChanges") or [] if change.get("kind") == "FLOW_STATUS_CHANGED"), {})
    root_settings = [
        change for change in item.get("internalChanges") or []
        if change.get("kind") == "FLOW_ROOT_SETTING_CHANGED"
    ]
    changes = _configuration_changes(item)
    names = []
    for change in changes:
        name = _customer_child_name(change.get("itemName") or "动作节点", "按钮或动作")
        name = re.sub(r"(?:-复制)+$", "", name).strip() or "动作节点"
        names.append(name)
    return {
        "oldCount": int(node.get("oldCount", 0) or 0),
        "newCount": int(node.get("newCount", 0) or 0),
        "added": list(node.get("addedComponents") or []),
        "removed": list(node.get("removedComponents") or []),
        "renamedNodes": list(node.get("renamedNodes") or []),
        "formulaCount": int(formula.get("factCount", 0) or 0),
        "mappingCount": int(mapping.get("factCount", 0) or 0),
        "changes": changes,
        "nodeNames": names,
        "nameChange": name_change,
        "statusChange": status_change,
        "rootSettings": root_settings,
    }


def _flow_conclusion(item: dict[str, Any]) -> str:
    profile = _flow_profile(item)
    if profile["added"] or profile["removed"] or profile["oldCount"] != profile["newCount"]:
        return "动作流节点结构调整"
    if profile["formulaCount"]:
        return "节点结构不变，公式或条件规则调整"
    if profile["mappingCount"]:
        return "节点结构不变，字段映射调整"
    if profile["renamedNodes"]:
        return "节点结构不变，节点业务名称调整"
    if profile["statusChange"]:
        return "动作流启用状态调整"
    if profile["rootSettings"]:
        return "动作流运行设置调整"
    if profile["changes"]:
        return "节点结构不变，节点参数调整"
    if profile["nameChange"]:
        return "动作流名称调整"
    return "未观察到可确认的动作流业务变化"


def _flow_nodes(item: dict[str, Any]) -> str:
    profile = _flow_profile(item)
    names = list(dict.fromkeys(profile["nodeNames"]))
    if names:
        return _limited_names(names, limit=5)
    renamed_names = [
        change.get("newName") or change.get("oldName")
        for change in profile["renamedNodes"]
    ]
    if renamed_names:
        return _limited_names(renamed_names, limit=5)
    types = [_flow_node_component_label(name) for name in profile["added"] + profile["removed"]]
    if types:
        return _limited_names(types, limit=5)
    if profile["rootSettings"]:
        return "动作流基础设置"
    return "相关配置节点"


def _flow_specific_change(item: dict[str, Any]) -> str:
    profile = _flow_profile(item)
    details = []
    if profile["added"]:
        details.append("新增" + _component_summary(profile["added"]))
    if profile["removed"]:
        details.append("删除" + _component_summary(profile["removed"]))
    if profile["formulaCount"]:
        details.append(f"公式或条件共 {profile['formulaCount']} 处调整")
    if profile["mappingCount"]:
        details.append(f"字段映射共 {profile['mappingCount']} 处调整")
    if profile["renamedNodes"]:
        renamed = []
        for change in profile["renamedNodes"][:4]:
            component = _flow_node_component_label(change.get("componentType"))
            renamed.append(
                f"{component}“{change.get('oldName')}”调整为“{change.get('newName')}”"
            )
        details.append("；".join(renamed))
    if profile["changes"]:
        details.append(f"节点参数共 {len(profile['changes'])} 处调整")
    if profile["nameChange"]:
        details.append(
            f"名称由“{profile['nameChange'].get('oldName')}”调整为"
            f"“{profile['nameChange'].get('newName')}”"
        )
    if profile["statusChange"]:
        labels = {"start_using": "启用", "forbidden": "停用"}
        before = labels.get(profile["statusChange"].get("before"), str(profile["statusChange"].get("before") or "未设置"))
        after = labels.get(profile["statusChange"].get("after"), str(profile["statusChange"].get("after") or "未设置"))
        details.append(f"启用状态由“{before}”调整为“{after}”")
    for setting in profile["rootSettings"]:
        details.append(
            f"{setting.get('settingName')}由“{setting.get('before')}”调整为“{setting.get('after')}”"
        )
    return "；".join(details[:4]) or "未观察到可确认的节点参数变化"


def _flow_impact(item: dict[str, Any]) -> str:
    profile = _flow_profile(item)
    names = "、".join(profile["nodeNames"])
    if profile["added"] or profile["removed"] or profile["oldCount"] != profile["newCount"]:
        return "可能影响动作流的调用方式、执行路径或处理结果"
    if "分支" in names or "条件" in names or profile["formulaCount"]:
        return "可能影响条件判断和后续执行路径"
    if "终止" in names:
        return "可能影响校验失败后的终止处理"
    if "变量赋值" in names or profile["mappingCount"]:
        return "可能影响变量取值、字段映射或数据处理结果"
    if "页面交互" in names:
        return "可能影响页面反馈或交互结果"
    if profile["statusChange"]:
        return "可能影响动作流能否继续从原入口触发执行"
    if profile["rootSettings"]:
        return "可能影响动作流运行记录的留存和后续排查"
    if profile["renamedNodes"]:
        return "组件类型和数量不变；节点业务名称已调整，需核对维护人员识别和后续配置引用"
    if profile["nameChange"] and not profile["changes"]:
        return "不改变已观察到的节点执行逻辑，需确认引用入口显示名称"
    return "可能影响动作执行结果或数据副作用"


def _flow_detail_rows(item: dict[str, Any]) -> list[tuple[str, str, str]]:
    profile = _flow_profile(item)
    rows = []
    if profile["added"] or profile["removed"] or profile["oldCount"] != profile["newCount"]:
        details = []
        if profile["added"]:
            details.append("新增" + _component_summary(profile["added"]))
        if profile["removed"]:
            details.append("删除" + _component_summary(profile["removed"]))
        rows.append(("节点结构", "调整", "；".join(details) or f"节点数量由 {profile['oldCount']} 调整为 {profile['newCount']}"))
    if profile["formulaCount"]:
        rows.append(("公式/条件", "规则调整", f"共 {profile['formulaCount']} 处；具体表达式保留在技术证据中"))
    if profile["mappingCount"]:
        rows.append(("字段映射", "映射调整", f"共 {profile['mappingCount']} 处；具体前后值保留在技术证据中"))
    if profile["renamedNodes"]:
        for change in profile["renamedNodes"]:
            component = _flow_node_component_label(change.get("componentType"))
            rows.append((
                component,
                "节点名称调整",
                f"由“{change.get('oldName')}”调整为“{change.get('newName')}”",
            ))
    if profile["changes"]:
        rows.append((_flow_nodes(item), "参数调整", f"共 {len(profile['changes'])} 处节点参数变化；无法静态还原的业务含义标记为待确认"))
    if profile["nameChange"]:
        rows.append((
            "动作流名称",
            "名称调整",
            f"由“{profile['nameChange'].get('oldName')}”调整为“{profile['nameChange'].get('newName')}”",
        ))
    if profile["statusChange"]:
        labels = {"start_using": "启用", "forbidden": "停用"}
        before = labels.get(profile["statusChange"].get("before"), str(profile["statusChange"].get("before") or "未设置"))
        after = labels.get(profile["statusChange"].get("after"), str(profile["statusChange"].get("after") or "未设置"))
        rows.append(("动作流状态", "状态调整", f"由“{before}”调整为“{after}”"))
    for setting in profile["rootSettings"]:
        rows.append((
            setting.get("settingName") or "动作流运行设置",
            "设置调整",
            f"由“{setting.get('before')}”调整为“{setting.get('after')}”",
        ))
    return rows or [("动作流", "无确认变化", "未观察到可确认的节点、公式、映射或参数变化")]


def _summary_table(model: dict[str, Any]) -> list[str]:
    lines = [
        "| 功能对象 | 旧版数量 | 新版数量 | 新增 | 删除 | 更新 | 疑似重命名/替代 | 净变化 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in model.get("summary") or []:
        net = row.get("netChange", 0)
        lines.append(
            f"| {row.get('label')} | {row.get('oldCount', 0)} | {row.get('newCount', 0)} | "
            f"{row.get('added', 0)} | {row.get('removed', 0)} | {row.get('updated', 0)} | "
            f"{row.get('possibleRename', 0)} | {'+' if net >= 0 else ''}{net} |"
        )
    return lines


def _form_table(model: dict[str, Any], change_type: str) -> list[str]:
    values = _items(model, "FORM", change_type)
    if change_type == "UPDATED":
        all_count = len(values)
        values = sorted(values, key=lambda item: (not any(token in str(item.get("businessName")) for token in ("学习", "考试", "成绩", "课程", "培训", "题库")), str(item.get("businessName"))))[:24]
        lines = [
            f"共有 {all_count} 个保留表单发生字段、布局、列表、按钮或联动变化；先展示每个表单的一句话结论，再按对象展开配置证据。正文最多展示 24 个代表对象，其余对象见附录。", "",
            "#### 表单变更摘要", "",
            "| 表单名称 | 变更结论 | 用户可见影响 |",
            "|---|---|---|",
        ]
        for item in values:
            lines.append(
                f"| {_escape(item.get('businessName'))} | {_short(_form_conclusion(item), 220)} | "
                f"{_short(_form_impact(item), 180)} |"
            )
        if not values:
            lines.append("| 无 | 本次未观察到表单更新 | — |")
        else:
            lines.extend(["", "#### 表单对象展开明细", ""])
            for item in values:
                name = _escape(item.get("businessName"))
                lines.extend([
                    f"##### {name}", "",
                    f"- 变更结论：{_form_conclusion(item)}。",
                    f"- 用户可见影响：{_form_impact(item)}。", "",
                    "| 变化区域 | 变化类型 | 具体变化 |",
                    "|---|---|---|",
                ])
                for area, kind, detail in _form_detail_rows(item):
                    lines.append(f"| {_escape(area)} | {_escape(kind)} | {_short(detail, 360)} |")
                lines.append("")
        return lines
    label = "新增" if change_type == "ADDED" else "删除"
    lines = [
        f"{label} {len(values)} 个表单。", "",
        "| 表单名称 | 前后状态 | 主要配置差异 | 业务说明 |",
        "|---|---|---|---|",
    ]
    for item in values:
        state = f"{_state(item, 'old')} → {_state(item, 'new')}"
        detail = _added_detail(item) if change_type == "ADDED" else _removed_detail(item)
        lines.append(f"| {_escape(item.get('businessName'))} | {state} | {detail} | {_short(item.get('businessPurpose'), 220)} |")
    if not values:
        lines.append(f"| 无 | — | 本次未观察到{label}表单 | — |")
    return lines


def _page_table(model: dict[str, Any], change_type: str) -> list[str]:
    values = _items(model, "PAGE", change_type)
    if change_type == "UPDATED":
        all_count = len(values)
        values = sorted(values, key=lambda item: (not any(token in str(item.get("businessName")) for token in ("学习", "考试", "成绩", "课程", "培训", "题库")), str(item.get("businessName"))))[:36]
        lines = [
            f"共有 {all_count} 个保留页面发生组件结构、数据或交互变化；先展示业务结论，再按页面展开结构化证据。正文最多展示 36 个代表对象，其余对象见附录。", "",
            "#### 页面变更摘要", "",
            "| 页面名称 | 变更结论 | 具体变化 | 影响判断 |",
            "|---|---|---|---|",
        ]
        for item in values:
            lines.append(
                f"| {_escape(item.get('businessName'))} | {_short(_page_conclusion(item), 150)} | "
                f"{_short(_page_specific_change(item), 260)} | {_short(_page_impact(item), 180)} |"
            )
        if not values:
            lines.append("| 无 | 本次未观察到页面更新 | — | — |")
        else:
            lines.extend(["", "#### 页面对象展开明细", ""])
            for item in values:
                lines.extend([
                    f"##### {_escape(item.get('businessName'))}", "",
                    f"- 变更结论：{_page_conclusion(item)}。",
                    f"- 影响判断：{_page_impact(item)}。", "",
                    "| 变化区域 | 变化类型 | 具体变化 |",
                    "|---|---|---|",
                ])
                for area, kind, detail in _page_detail_rows(item):
                    lines.append(f"| {_escape(area)} | {_escape(kind)} | {_short(detail, 320)} |")
                lines.append("")
        return lines
    label = "新增" if change_type == "ADDED" else "删除"
    lines = [
        f"{label} {len(values)} 个页面。", "",
        "| 页面名称 | 前后状态 | 主要组件或配置差异 | 页面功能 |",
        "|---|---|---|---|",
    ]
    for item in values:
        summary = item.get("newSummary") if change_type == "ADDED" else item.get("oldSummary")
        summary_text = _count_text({"newSummary": summary}, "newSummary")
        lines.append(f"| {_escape(item.get('businessName'))} | {_state(item, 'old')} → {_state(item, 'new')} | {_short(_change_text(item), 420)}（{summary_text}） | {_short(item.get('businessPurpose'), 220)} |")
    if not values:
        lines.append(f"| 无 | — | 本次未观察到{label}页面 | — |")
    return lines


def _flow_table(model: dict[str, Any], change_type: str) -> list[str]:
    values = _items(model, "ESB_ACTION_FLOW", change_type)
    if change_type == "UPDATED":
        all_count = len(values)
        values = sorted(values, key=lambda item: (not any(token in str(item.get("businessName")) for token in ("学习", "考试", "成绩", "课程", "培训", "题库")), str(item.get("businessName"))))[:24]
        lines = [
            f"共有 {all_count} 条保留动作流发生节点、公式、映射或分支配置变化；先展示业务结论，再按动作流展开结构化证据。正文最多展示 24 个代表对象，其余对象见附录。", "",
            "#### 动作流变更摘要", "",
            "| 动作流名称 | 变更结论 | 涉及节点 | 具体变化 | 业务影响 |",
            "|---|---|---|---|---|",
        ]
        for item in values:
            lines.append(
                f"| {_escape(item.get('businessName'))} | {_short(_flow_conclusion(item), 150)} | "
                f"{_short(_flow_nodes(item), 150)} | {_short(_flow_specific_change(item), 240)} | "
                f"{_short(_flow_impact(item), 180)} |"
            )
        if not values:
            lines.append("| 无 | 本次未观察到动作流更新 | — | — | — |")
        else:
            lines.extend(["", "#### 动作流对象展开明细", ""])
            for item in values:
                lines.extend([
                    f"##### {_escape(item.get('businessName'))}", "",
                    f"- 变更结论：{_flow_conclusion(item)}。",
                    f"- 业务影响：{_flow_impact(item)}。", "",
                    "| 变化区域/节点 | 变化类型 | 具体变化 |",
                    "|---|---|---|",
                ])
                for area, kind, detail in _flow_detail_rows(item):
                    lines.append(f"| {_escape(area)} | {_escape(kind)} | {_short(detail, 320)} |")
                lines.append("")
        return lines
    label = "新增" if change_type == "ADDED" else "删除"
    lines = [
        f"{label} {len(values)} 条动作流。", "",
        "| 动作流名称 | 前后状态 | 节点或配置差异 | 业务说明 |",
        "|---|---|---|---|",
    ]
    for item in values:
        lines.append(f"| {_escape(item.get('businessName'))} | {_state(item, 'old')} → {_state(item, 'new')} | {_short(_change_text(item), 500)} | {_short(item.get('businessPurpose'), 220)} |")
    if not values:
        lines.append(f"| 无 | — | 本次未观察到{label}动作流 | — |")
    return lines


def _menu_table(model: dict[str, Any], change_type: str) -> list[str]:
    values = _items(model, "MENU", change_type) + _items(model, "NAVIGATION", change_type)
    label = "新增" if change_type == "ADDED" else "删除" if change_type == "REMOVED" else "更新"
    lines = [f"{label} {len(values)} 个菜单或导航对象。", "", "| 名称 | 类型 | 前版目标 | 新版目标 | 业务差异 |", "|---|---|---|---|---|"]
    for item in values:
        old_target = _customer_target((item.get("oldSummary") or {}).get("openTarget"))
        new_target = _customer_target((item.get("newSummary") or {}).get("openTarget"))
        lines.append(f"| {_escape(item.get('businessName'))} | {TYPE_LABELS.get(item.get('objectType'), item.get('objectType'))} | {_short(old_target, 220)} | {_short(new_target, 220)} | {_short(_change_text(item), 420)} |")
    if not values:
        lines.append(f"| 无 | — | — | — | 本次未观察到{label}菜单或导航 |")
    return lines


def _other_summary(model: dict[str, Any], change_type: str) -> list[str]:
    values = []
    for object_type in ("EMBEDDED_VIEW", "WORKFLOW", "REPORT", "MULTI_FILLING", "DATASET", "EXTERNAL_INTEGRATION", "PERMISSION", "APPLICATION_SHELL", "OTHER"):
        values.extend(_items(model, object_type, change_type))
    label = "新增" if change_type == "ADDED" else "删除" if change_type == "REMOVED" else "更新"
    lines = [f"{label} {len(values)} 个其他功能对象。", ""]
    by_type = {}
    for item in values:
        by_type.setdefault(item.get("objectType"), []).append(item)
    if by_type:
        lines.extend(["| 对象类型 | 数量 | 代表对象 |", "|---|---:|---|"])
        for object_type in sorted(by_type, key=lambda value: str(value)):
            items = by_type[object_type]
            names = "、".join(_escape(item.get("businessName")) for item in items[:8])
            suffix = "等" if len(items) > 8 else ""
            lines.append(f"| {TYPE_LABELS.get(object_type, object_type)} | {len(items)} | {names}{suffix} |")
    else:
        lines.append(f"本次未观察到{label}其他功能对象。")
    sql_changes = [
        (item, change)
        for item in values if item.get("objectType") == "WORKFLOW"
        for change in item.get("internalChanges") or []
        if change.get("kind") == "WORKFLOW_SQL_DATASOURCE_CHANGED"
    ]
    if sql_changes:
        lines.extend([
            "",
            "#### 工作流 SQL 数据源离线校验",
            "",
            "这里区分“离线可确定”和“必须连接目标环境才能确定”的结论；报告不展示完整 SQL、物理表名或内部标识。",
            "",
            "| 所属流程 | 数据集身份 | 查询语义 | 输入参数 | 输出类型 | 离线静态校验 | 环境待验证 |",
            "|---|---|---|---|---|---|---|",
        ])
        for item, change in sql_changes:
            before = change.get("before") or {}
            after = change.get("after") or {}
            identity = {
                "SAME_SOURCE": "同源配置更新",
                "RECREATED_OR_REBOUND": "非同源，疑似重建或重新绑定",
                "IDENTITY_UNCONFIRMED": "同源身份未确认，按配置重建候选处理",
                "ADDED": "新增数据源",
                "REMOVED": "删除数据源",
            }.get(change.get("identityConclusion"), "身份待确认")
            if change.get("querySemanticsChanged"):
                semantics = f"{before.get('querySummary') or '无'} → {after.get('querySummary') or '无'}"
            else:
                semantics = "前后查询逻辑一致（空格、换行等格式差异已忽略）"
            inputs = "、".join(after.get("inputs") or before.get("inputs") or []) or "未声明"
            old_types = "、".join(before.get("outputTypes") or []) or "无"
            new_types = "、".join(after.get("outputTypes") or []) or "无"
            output_types = old_types if old_types == new_types else f"{old_types} → {new_types}"
            checks = after.get("staticChecks") or before.get("staticChecks") or {}
            check_labels = [
                ("configurationParsed", "配置可解析"),
                ("singleStatement", "单语句"),
                ("readOnlyQuery", "只读查询"),
                ("parametersResolved", "参数引用闭合"),
                ("outputAliasesDeclared", "输出声明闭合"),
            ]
            passed = "、".join(label for key, label in check_labels if checks.get(key)) or "无通过项"
            failed = "、".join(label for key, label in check_labels if not checks.get(key))
            static_text = passed + (f"；待复核：{failed}" if failed else "")
            pending = "；".join(after.get("runtimePending") or before.get("runtimePending") or []) or "无"
            lines.append(
                f"| {_escape(item.get('businessName'))} | {_escape(identity)} | {_escape(semantics)} | "
                f"{_escape(inputs)} | {_escape(output_types)} | {_escape(static_text)} | {_escape(pending)} |"
            )
    return lines


def _full_appendix(model: dict[str, Any]) -> list[str]:
    changed_count = sum(1 for item in model.get("objects") or [] if item.get("changeType") != "UNCHANGED")
    compact = changed_count > 250
    lines = ["## 附录：完整对象明细", "", "以下按对象类型和变化类型列出全部已计算对象；本附录只记录对象状态和配置前后差异。", ""]
    if compact:
        lines.extend(["本次对象量较大，附录按每行最多 6 个对象名称紧凑展示；完整字段前后值保留在 `business-object-diff.json`。", ""])
    for change_type, heading in (("ADDED", "新增"), ("REMOVED", "删除"), ("UPDATED", "更新"), ("POSSIBLE_RENAME", "疑似重命名/替代"), ("UNMATCHED", "无法稳定匹配")):
        lines.extend([f"### {heading}对象", "", "| 对象类型 | 对象名称 | 前版状态 | 新版状态 | 主要差异 |", "|---|---|---|---|---|"])
        values = [item for item in model.get("objects") or [] if item.get("changeType") == change_type]
        if compact:
            for offset in range(0, len(values), 6):
                batch = values[offset:offset + 6]
                names = "；".join(_escape(item.get("businessName")) for item in batch)
                lines.append(f"| 多类型明细 | {offset + 1}–{offset + len(batch)} | — | — | {names}。 |")
        else:
            for item in values:
                if item.get("objectType") == "FORM" and change_type == "UPDATED":
                    detail = _form_conclusion(item)
                elif item.get("objectType") == "PAGE" and change_type == "UPDATED":
                    detail = _page_conclusion(item)
                elif item.get("objectType") == "ESB_ACTION_FLOW" and change_type == "UPDATED":
                    detail = _flow_conclusion(item)
                else:
                    detail = _short(_change_text(item), 280)
                lines.append(f"| {TYPE_LABELS.get(item.get('objectType'), item.get('objectType'))} | {_escape(item.get('businessName'))} | {_state(item, 'old')} | {_state(item, 'new')} | {_short(detail, 280)} |")
        if not values:
            lines.append("| 无 | — | — | — | 本次未观察到该类对象 |")
        lines.append("")
    return lines


def render(model: dict[str, Any]) -> str:
    app_name = model.get("applicationName") or "eBuilder 应用"
    direction = model.get("direction") or {}
    old = direction.get("old") or {}
    new = direction.get("new") or {}
    rows = {item.get("label"): item for item in model.get("summary") or []}
    form, page, flow, menu = (_summary(model, key) for key in ("表单", "页面", "动作流", "菜单"))
    lines: list[str] = [
        f"# {app_name}应用版本功能明细差异报告", "",
        "## 1. 报告范围", "",
        f"- 对比方向：旧版“{_escape(old.get('name'))}” → 新版“{_escape(new.get('name'))}”。",
        f"- 旧包 SHA-256：`{str(old.get('sha256', ''))[:16]}…`；新包 SHA-256：`{str(new.get('sha256', ''))[:16]}…`。",
        "- 分析范围：表单、页面、嵌入式视图、动作流、工作流/审批流程、菜单、导航、报表、多级填报、独立数据集、业务资源绑定和权限。",
        "- 报告内容：对象数量、对象名称、前后状态、字段/组件/节点/目标等配置差异及业务功能说明。",
        "",
        "## 2. 总体结论", "",
        f"新版相对于旧版新增 {form.get('added', 0)} 个表单、{page.get('added', 0)} 个页面、{flow.get('added', 0)} 条动作流和 {menu.get('added', 0)} 个菜单；删除 {form.get('removed', 0)} 个表单、{page.get('removed', 0)} 个页面、{flow.get('removed', 0)} 条动作流和 {menu.get('removed', 0)} 个菜单；另有 {form.get('updated', 0)} 个表单、{page.get('updated', 0)} 个页面、{flow.get('updated', 0)} 条动作流和 {menu.get('updated', 0)} 个菜单发生配置变化。",
        "",
        "## 3. 功能对象变化汇总", "",
    ]
    lines.extend(_summary_table(model))
    lines.extend(["", "说明：净变化 = 新增 - 删除；更新不参与净数量计算；疑似重命名/替代和无法稳定匹配对象单独列示。", "", "## 4. 新增功能", "", "### 4.1 新增表单", ""])
    lines.extend(_form_table(model, "ADDED"))
    lines.extend(["", "### 4.2 新增页面", ""])
    lines.extend(_page_table(model, "ADDED"))
    lines.extend(["", "### 4.3 新增动作流", ""])
    lines.extend(_flow_table(model, "ADDED"))
    lines.extend(["", "### 4.4 新增菜单与导航", ""])
    lines.extend(_menu_table(model, "ADDED"))
    lines.extend(["", "### 4.5 新增其他功能", ""])
    lines.extend(_other_summary(model, "ADDED"))
    lines.extend(["", "## 5. 删除功能", "", "### 5.1 删除表单", ""])
    lines.extend(_form_table(model, "REMOVED"))
    lines.extend(["", "### 5.2 删除页面", ""])
    lines.extend(_page_table(model, "REMOVED"))
    lines.extend(["", "### 5.3 删除动作流", ""])
    lines.extend(_flow_table(model, "REMOVED"))
    lines.extend(["", "### 5.4 删除菜单与导航", ""])
    lines.extend(_menu_table(model, "REMOVED"))
    lines.extend(["", "### 5.5 删除其他功能", ""])
    lines.extend(_other_summary(model, "REMOVED"))
    lines.extend(["", "## 6. 更新功能", "", "### 6.1 表单更新", ""])
    lines.extend(_form_table(model, "UPDATED"))
    lines.extend(["", "### 6.2 页面更新", ""])
    lines.extend(_page_table(model, "UPDATED"))
    lines.extend(["", "### 6.3 动作流更新", ""])
    lines.extend(_flow_table(model, "UPDATED"))
    lines.extend(["", "### 6.4 菜单与导航更新", ""])
    lines.extend(_menu_table(model, "UPDATED"))
    lines.extend(["", "### 6.5 其他功能更新", ""])
    lines.extend(_other_summary(model, "UPDATED"))
    lines.extend(["", "## 7. 疑似重命名和功能替代", "", "| 旧对象 | 新对象候选 | 对象类型 | 相似依据 |", "|---|---|---|---|"])
    relations = model.get("possibleRenamesAndReplacements") or []
    for relation in relations:
        lines.append(f"| {_short(relation.get('oldObject'))} | {_short(relation.get('newObjectCandidate'))} | {_escape(relation.get('objectType'))} | {_short(relation.get('similarityBasis'), 420)} |")
    if not relations:
        lines.append("| 无 | 无 | — | 本次未形成满足保守门槛的候选关系 |")
    lines.extend(["", "说明：疑似重命名或替代对象不强行计入更新，保留为独立差异项。", ""])
    lines.extend(_full_appendix(model))
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("business_object_diff", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.business_object_diff.expanduser().resolve()
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(_load_model(source)), encoding="utf-8")
    print(json.dumps({"output": str(output), "bytes": output.stat().st_size}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
