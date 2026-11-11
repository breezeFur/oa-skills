#!/usr/bin/env python3
"""按已确认的业务功能对象结构渲染中文版本差异报告。"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from typing import Any


TYPE_LABELS = {
    "FORM": "表单",
    "PAGE": "页面",
    "EMBEDDED_VIEW": "嵌入式视图",
    "ESB_ACTION_FLOW": "动作流",
    "WORKFLOW": "工作流/审批流程",
    "MENU": "菜单",
    "NAVIGATION": "导航",
    "REPORT": "报表",
    "MULTI_FILLING": "多级填报",
    "DATASET": "独立数据集",
    "EXTERNAL_INTEGRATION": "业务资源绑定",
    "PERMISSION": "权限",
    "APPLICATION_SHELL": "应用壳",
    "OTHER": "其他功能",
}

CHANGE_LABELS = {
    "ADDED": "新增",
    "REMOVED": "删除",
    "UPDATED": "更新",
    "POSSIBLE_RENAME": "疑似重命名/替代",
    "UNMATCHED": "无法稳定匹配",
}

CORE_KEYWORDS = (
    "立项", "创建", "下发", "签收", "反馈", "审核", "催办", "延期", "办结",
    "拒收", "分派", "转办", "分解", "提交", "审批", "归档", "同步", "预警",
)


def _escape(value: Any) -> str:
    if value in (None, "", [], {}):
        return "未确认"
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)
    return text.replace("|", "｜").replace("\n", " ")


def _short(value: Any, limit: int = 180) -> str:
    text = _escape(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"


PATH_LABELS = {
    "record": "配置记录",
    "layout_id.$ref": "所属布局",
    "config.flow.parent.$ref": "组件父级",
    "languageid": "语言",
    "langid": "语言",
    "form_ecode_id.$ref": "扩展代码绑定",
    "ecode_install.name.$ref": "扩展代码名称绑定",
    "ecode_install.childCodes": "扩展代码内容",
    "target_id.$ref": "目标对象绑定",
    "page_id.$ref": "所属页面",
    "data_id.$ref": "数据对象绑定",
    "application_id.$ref": "动作流绑定",
    "app_id.$ref": "应用绑定",
    "form_id.$ref": "表单绑定",
    "version_id.$ref": "版本绑定",
    "obj_id.$ref": "业务对象绑定",
    "ref_comp_id.$ref": "引用组件",
    "button_id.$ref": "按钮绑定",
    "other_properties.secLevel": "安全级别",
    "other_properties.showFormat": "显示格式",
    "config.fieldUsage": "列表字段与查询配置",
    "config.eventGroup": "点击事件与交互动作",
    "config.flow.nodes": "组件子节点结构",
    "config.flow.parent.$ref": "组件父级",
}

COMPONENT_LABELS = {
    "NList": "列表组件",
    "GridContainer": "网格容器",
    "EbButton": "页面按钮",
    "CustomPage": "自定义页面组件",
    "InternalContainer": "内部容器",
    "TaskTree": "任务树组件",
    "ProjectTree": "项目树组件",
    "SimpleText": "文本组件",
    "EGantt": "甘特图组件",
    "Collapse": "折叠面板",
    "EBuilder": "eBuilder 组件",
    "SubLayout": "子布局组件",
    "Tree": "树形组件",
    "NewTab": "页签组件",
    "GridMultiColumn": "多列网格组件",
    "ColumnTwo": "双列布局组件",
    "ColumnThree": "三列布局组件",
    "Text": "文本组件",
    "TextArea": "多行文本组件",
    "Image": "图片组件",
    "Number": "数字组件",
    "RadioBox": "单选组件",
    "Drawer": "抽屉组件",
    "List": "列表组件",
    "FilterCondition": "筛选条件组件",
    "DigitalPanel": "数字指标组件",
    "PageHeader": "页面标题组件",
    "RotationPanel": "轮播面板组件",
    "Comment": "评论组件",
}

FLOW_NODE_LABELS = {
    "Assign": "变量赋值",
    "VariableAssign": "变量赋值",
    "AssignVar": "变量赋值",
    "IncrementVar": "变量增减",
    "Condition": "条件判断",
    "SingleCondition": "条件判断",
    "Branch": "分支",
    "Terminate": "终止",
    "Output": "输出",
    "DML": "数据写入",
    "DMLExecute": "数据库语句执行",
    "EnquiryForm": "表单/数据源查询",
    "PageInteraction": "页面交互",
    "Loop": "循环",
    "MultipleExecution": "循环执行",
    "InnerMQSend": "内部消息发送",
    "CustomTriggerAction": "自定义动作流调用",
    "ServerlessAction": "服务接口调用",
    "ActionEbAdd": "新建表单数据",
    "ActionEbUpdate": "更新表单数据",
    "ActionEbDelete": "删除表单数据",
    "AITextDataExtract": "AI文本内容提取",
    "AIVectorSearch": "AI知识向量检索",
    "AIAdvancedLLMChat": "AI大语言模型对话",
    "JsonXmlParsing": "JSON/XML文本解析",
}


def _flow_node_component_label(name: str) -> str:
    label = FLOW_NODE_LABELS.get(str(name), str(name))
    return label if label.endswith("组件") else label + "组件"

TABLE_LABELS = {
    "ebdd_page_layout": "页面布局",
    "ebdd_page_extended": "页面扩展配置",
    "ebdd_layout_component": "页面组件",
    "ebdd_list_button_item": "页面列表按钮项",
    "ebdd_navmenu_item": "页面导航项",
    "ebdd_button": "页面按钮",
    "form_ecode": "表单扩展代码",
    "form_field": "表单字段",
    "form_layout": "表单布局",
    "form_list": "表单列表",
    "esb_flow_action": "动作节点",
    "dataset": "数据集",
}

VALUE_LABELS = {
    "rightTopDropDown": "右上角下拉菜单",
    "rightTopBatch": "右上角批量操作区",
    "LineEndDropDown": "行尾下拉菜单",
    "rightTop": "右上角操作区",
    "lineEnd": "行尾操作区",
}


def _business_item_name(value: Any) -> str:
    text = str(value or "子配置")
    if text in TABLE_LABELS:
        return TABLE_LABELS[text]
    match = re.search(r'type="([^"]+)"', text)
    if match:
        return COMPONENT_LABELS.get(match.group(1), f"{match.group(1)} 组件")
    if any(token in text for token in ("migration-source=", "package-unit=", "content=", "parent=")):
        return "业务子配置"
    return text


def _display_value(value: Any) -> str:
    if value is None:
        return "未设置"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, dict):
        if value.get("truncated") and value.get("sha256"):
            return f"配置内容（长度 {value.get('length', '未确认')}）"
        if "$ref" in value:
            return _display_value(value["$ref"])
        if "$unresolvedId" in value:
            return "未解析目标（完整引用见技术证据）"
        return f"配置对象（{len(value)} 个字段）"
    if isinstance(value, list):
        refs = [item.get("$ref") for item in value if isinstance(item, dict) and item.get("$ref")]
        if refs:
            return f"{len(refs)} 项：" + "、".join(_display_value(item) for item in refs[:4])
        if all(not isinstance(item, (dict, list)) for item in value):
            return "、".join(VALUE_LABELS.get(str(item), str(item)) for item in value) or "空集合"
        return f"{len(value)} 项配置"
    text = str(value)
    if text in VALUE_LABELS:
        return VALUE_LABELS[text]
    if re.search(r"<[^>]+>", text):
        plain = re.sub(r"<[^>]+>", "", text)
        plain = re.sub(r"\s+", " ", plain).strip()
        return f"页面富文本内容（{len(plain)} 字）"
    if text.startswith("内容摘要 "):
        return "配置内容（完整摘要见技术证据）"
    if "::" in text or any(token in text for token in ("package-unit=", "migration-source=", "content=", "parent=", "$unresolvedId")):
        for pattern, label in (
            (r'type="([^"]+)"', "组件"),
            (r'name="([^"]+)"', "对象"),
            (r'form_name="([^"]+)"', "表单"),
            (r'page_name="([^"]+)"', "页面"),
            (r'table_name="([^"]+)"', "数据对象"),
        ):
            match = re.search(pattern, text)
            if match:
                name = match.group(1)
                if label == "组件":
                    return COMPONENT_LABELS.get(name, f"{name} 组件")
                return f"{label}“{name}”"
        table_match = re.search(r"::([^:]+)::", text)
        if table_match:
            table = table_match.group(1)
            return TABLE_LABELS.get(table, "业务配置对象")
        return "绑定对象（完整引用见技术证据）"
    return _short(text, 80)


def _field_change_text(field: dict[str, Any]) -> str:
    path = str(field.get("path") or "配置")
    label = PATH_LABELS.get(path)
    if not label:
        if path.startswith("show_position."):
            label = "按钮显示位置"
        elif path.startswith("config."):
            suffix = path.removeprefix("config.")
            if "linkedNodes" in suffix:
                label = "组件关联节点"
            elif "nodes" in suffix:
                label = "组件内部节点结构"
            else:
                label = "组件内部配置"
        elif path.startswith("ecode_install."):
            label = "扩展代码配置"
        elif path.endswith(".$ref") or path.endswith("_id"):
            label = "对象绑定"
        else:
            label = "业务配置"
    before_raw = field.get("before")
    after_raw = field.get("after")
    if path == "record":
        if before_raw is None and after_raw is not None:
            return "新增组件或子配置"
        if before_raw is not None and after_raw is None:
            return "移除组件或子配置"
        return "组件或子配置内容已替换"
    before = _display_value(before_raw)
    after = _display_value(after_raw)
    if before == after and field.get("before") != field.get("after"):
        after += "（对象实例或内部配置已切换）"
    return f"{label}：{before} → {after}"


def _configuration_change_text(item: dict[str, Any], *, limit: int = 5) -> str:
    parts = []
    for change in item.get("internalChanges") or []:
        if change.get("kind") != "CHILD_CONFIGURATION_CHANGE":
            continue
        raw_name = change.get("itemName")
        if not raw_name or "技术名称未还原" in str(raw_name):
            raw_name = change.get("table") or "业务子配置"
        name = _business_item_name(raw_name)
        fields = change.get("fields") or []
        detail = "；".join(_field_change_text(field) for field in fields[:2])
        parts.append(f"{name}：{detail}")
        if len(parts) >= limit:
            break
    return "；".join(parts) or "未观察到可展示的字段前后值"


def _items(model: dict[str, Any], object_type: str, change_type: str) -> list[dict[str, Any]]:
    return [
        item for item in model.get("objects") or []
        if item.get("objectType") == object_type and item.get("changeType") == change_type
    ]


def _summary(model: dict[str, Any], label: str) -> dict[str, Any]:
    return next(
        (item for item in model.get("summary") or [] if item.get("label") == label),
        {
            "oldCount": 0,
            "newCount": 0,
            "added": 0,
            "removed": 0,
            "updated": 0,
            "possibleRename": 0,
            "netChange": 0,
        },
    )


def _change_text(item: dict[str, Any]) -> str:
    changes = item.get("internalChanges") or []
    parts = []
    for change in changes:
        kind = change.get("kind")
        if kind == "NAME_CHANGED":
            parts.append(
                f"名称由“{_short(change.get('oldName'))}”调整为"
                f"“{_short(change.get('newName'))}”"
            )
        elif kind == "FIELD_ADDED":
            names = "、".join(change.get("items") or [])
            parts.append(f"新增 {change.get('count', 0)} 个字段" + (f"：{names}" if names else ""))
        elif kind == "FIELD_REMOVED":
            names = "、".join(change.get("items") or [])
            parts.append(f"删除 {change.get('count', 0)} 个字段" + (f"：{names}" if names else ""))
        elif kind == "FORM_LAYOUT_ADDED":
            parts.append("新增布局：" + "、".join(change.get("items") or []))
        elif kind == "FORM_LAYOUT_REMOVED":
            parts.append("删除布局：" + "、".join(change.get("items") or []))
        elif kind == "FORM_LAYOUT_COMPONENTS_CHANGED":
            detail = []
            if change.get("added"):
                detail.append("新增" + "、".join(f"{COMPONENT_LABELS.get(name, name + '组件')}×{count}" for name, count in change["added"].items()))
            if change.get("removed"):
                detail.append("删除" + "、".join(f"{COMPONENT_LABELS.get(name, name + '组件')}×{count}" for name, count in change["removed"].items()))
            if change.get("updatedCount"):
                detail.append(f"调整{change['updatedCount']}个组件配置")
            parts.append(f"“{change.get('layoutName')}”布局：" + "，".join(detail))
        elif kind == "NODE_POST_VALIDATION_CHANGED":
            node_name = _short(change.get("nodeName") or "未命名流程节点")
            detail = [
                f"规则 {change.get('oldRuleCount', 0)}→{change.get('newRuleCount', 0)} 条",
                f"启用 {change.get('oldEnabledCount', 0)}→{change.get('newEnabledCount', 0)} 条",
            ]
            before_rules = change.get("effectiveBefore") or []
            after_rules = change.get("effectiveAfter") or []
            before_conditions = list(dict.fromkeys(
                str(rule.get("condition")) for rule in before_rules if rule.get("condition")
            ))
            after_conditions = list(dict.fromkeys(
                str(rule.get("condition")) for rule in after_rules if rule.get("condition")
            ))
            if before_conditions != after_conditions:
                before_text = "；".join(before_conditions) or "无启用规则"
                after_text = "；".join(after_conditions) or "无启用规则"
                detail.append(f"有效校验条件由“{_short(before_text, 180)}”调整为“{_short(after_text, 180)}”")
            removed_names = [
                str(rule.get("name")) for rule in change.get("removedRules") or []
                if rule.get("name")
            ]
            if removed_names:
                detail.append("删除规则：“" + "、".join(removed_names[:4]) + "”")
            updated = change.get("updatedRules") or []
            if updated:
                detail.append(f"调整 {len(updated)} 条同源规则的名称、启用状态或条件")
            parts.append(f"“{node_name}”节点后校验：" + "，".join(detail))
        elif kind == "WORKFLOW_SQL_DATASOURCE_CHANGED":
            before = change.get("before") or {}
            after = change.get("after") or {}
            identity = change.get("identityConclusion")
            detail = []
            if identity == "RECREATED_OR_REBOUND":
                detail.append("数据集记录不是同源记录，按重建或重新绑定处理")
            elif identity == "IDENTITY_UNCONFIRMED":
                detail.append("同源身份未确认，按配置重建候选处理")
            elif identity == "ADDED":
                detail.append("新增 SQL 数据源")
            elif identity == "REMOVED":
                detail.append("删除 SQL 数据源")
            if change.get("querySemanticsChanged"):
                detail.append(
                    f"查询语义由“{_short(before.get('querySummary') or '无', 140)}”调整为"
                    f"“{_short(after.get('querySummary') or '无', 140)}”"
                )
            elif before and after:
                detail.append("查询逻辑一致（仅格式差异不计为业务变化）")
            old_types = "、".join(before.get("outputTypes") or []) or "无"
            new_types = "、".join(after.get("outputTypes") or []) or "无"
            if old_types != new_types:
                detail.append(f"输出类型由“{old_types}”调整为“{new_types}”")
            checks = (after or before).get("staticChecks") or {}
            passed = [
                label for key, label in (
                    ("configurationParsed", "配置可解析"),
                    ("singleStatement", "单语句"),
                    ("readOnlyQuery", "只读查询"),
                    ("parametersResolved", "参数引用闭合"),
                    ("outputAliasesDeclared", "输出声明闭合"),
                ) if checks.get(key)
            ]
            if passed:
                detail.append("离线静态校验通过：" + "、".join(passed))
            pending = (after or before).get("runtimePending") or []
            if pending:
                detail.append("环境待验：" + "；".join(pending))
            parts.append("工作流 SQL 数据源：" + "，".join(detail))
        elif kind in {"LAYOUT", "LIST", "BUTTON_ACTION", "LINKAGE"}:
            if "oldCount" in change:
                label = {"LAYOUT": "布局配置", "LIST": "列表配置", "BUTTON_ACTION": "按钮/动作配置", "LINKAGE": "联动配置"}.get(kind, kind)
                parts.append(f"{label} {change.get('oldCount', 0)}→{change.get('newCount', 0)}")
            else:
                parts.append(kind)
        elif kind == "NODE_SET":
            added = Counter(change.get("addedComponents") or [])
            removed = Counter(change.get("removedComponents") or [])
            if (
                change.get("oldCount", 0) == change.get("newCount", 0)
                and not added
                and not removed
            ):
                continue
            detail = [f"节点 {change.get('oldCount', 0)}→{change.get('newCount', 0)}"]
            if added:
                detail.append("新增" + "、".join(f"{_flow_node_component_label(name)}×{count}" for name, count in added.most_common(5)))
            if removed:
                detail.append("删除" + "、".join(f"{_flow_node_component_label(name)}×{count}" for name, count in removed.most_common(5)))
            parts.append("，".join(detail))
        elif kind == "COMPONENT_ADDED" and change.get("items"):
            parts.append("新增组件：" + "、".join(change["items"][:8]))
        elif kind == "COMPONENT_REMOVED" and change.get("items"):
            parts.append("删除组件：" + "、".join(change["items"][:8]))
        elif kind == "COMPONENT_SET":
            parts.append(f"包含 {change.get('componentCount', 0)} 个可识别组件")
        elif kind == "MENU_TARGET_OR_NAME":
            parts.append(f"打开目标由“{_short(change.get('oldTarget'))}”调整为“{_short(change.get('newTarget'))}”")
        elif kind == "MENU_CONFIGURATION_CHANGE":
            label = str(change.get("label") or "菜单入口配置")
            parts.append(f"{label}发生变化")
        elif kind == "FLOW_STATUS_CHANGED":
            status_labels = {"start_using": "启用", "forbidden": "停用"}
            before = status_labels.get(change.get("before"), str(change.get("before") or "未设置"))
            after = status_labels.get(change.get("after"), str(change.get("after") or "未设置"))
            parts.append(f"启用状态由“{before}”调整为“{after}”")
        elif kind == "BUSINESS_RESOURCE_BINDING":
            parts.append(f"业务资源绑定：{change.get('module')} / {change.get('businessObject')}")
        elif kind == "POSSIBLE_REBUILD":
            parts.append(change.get("description") or "疑似同名重建")
        elif kind == "CHILD_CONFIGURATION_CHANGE":
            fields = change.get("fields") or []
            detail = "；".join(_field_change_text(field) for field in fields[:2])
            raw_name = change.get("itemName")
            if not raw_name or "技术名称未还原" in str(raw_name):
                raw_name = change.get("table") or "业务子配置"
            parts.append(f"{_business_item_name(raw_name)}：{detail}")
        elif change.get("description"):
            parts.append(str(change["description"]))
    return "；".join(parts[:5]) or "对象配置发生新增、删除或业务调整"


def _form_change_columns(item: dict[str, Any]) -> tuple[str, str, str, str]:
    field_parts = []
    layout_parts = []
    action_parts = []
    for change in item.get("internalChanges") or []:
        kind = change.get("kind")
        if kind in {"FIELD_ADDED", "FIELD_REMOVED"}:
            label = "新增" if kind == "FIELD_ADDED" else "删除"
            names = "、".join((change.get("items") or [])[:12])
            field_parts.append(f"{label}{change.get('count', 0)}个" + (f"（{names}）" if names else ""))
        elif kind in {"FORM_LAYOUT_ADDED", "FORM_LAYOUT_REMOVED", "FORM_LAYOUT_COMPONENTS_CHANGED", "LAYOUT", "LIST"}:
            layout_parts.append(_change_text({"internalChanges": [change]}))
        elif kind in {"BUTTON_ACTION", "LINKAGE", "PLATFORM_FORM_CHILD_SET"}:
            action_parts.append(_change_text({"internalChanges": [change]}))
        elif kind == "CHILD_CONFIGURATION_CHANGE":
            table = str(change.get("table") or "").lower()
            text = _change_text({"internalChanges": [change]})
            if table == "form_field":
                field_parts.append(text)
            elif "button" in table or "linkage" in table or "action" in table or "ecode" in table:
                action_parts.append(text)
            else:
                layout_parts.append(text)
    impact_parts = []
    all_paths = [
        str(field.get("path") or "")
        for change in item.get("internalChanges") or []
        if change.get("kind") == "CHILD_CONFIGURATION_CHANGE"
        for field in change.get("fields") or []
    ]
    if any("show_position" in path for path in all_paths):
        impact_parts.append("按钮出现位置和可操作入口发生变化")
    if any("ecode" in path for path in all_paths):
        impact_parts.append("表单扩展代码或运行逻辑发生变化")
    if any("layout" in path or "flow" in path for path in all_paths):
        impact_parts.append("表单布局或嵌入组件关系发生变化")
    return (
        "；".join(field_parts) or "未观察到可命名字段增删",
        "；".join(layout_parts) or "布局/列表变化见业务对象明细",
        "；".join(action_parts) or "按钮/联动变化见业务对象明细",
        "；".join(impact_parts[:3]) or item.get("businessPurpose") or "需按实际入口验证",
    )


def _page_change_columns(item: dict[str, Any]) -> tuple[str, str, str, str, str]:
    old_summary = item.get("oldSummary") or {}
    new_summary = item.get("newSummary") or {}
    added, removed = [], []
    for change in item.get("internalChanges") or []:
        if change.get("kind") == "COMPONENT_ADDED":
            added.extend(change.get("items") or [])
        elif change.get("kind") == "COMPONENT_REMOVED":
            removed.extend(change.get("items") or [])
    old_count = old_summary.get("componentCount", 0)
    new_count = new_summary.get("componentCount", 0)
    count_text = (
        "组件关系未完整解析"
        if old_count == 0 and new_count == 0 and _configuration_change_text(item) != "未观察到可展示的字段前后值"
        else f"{old_count}→{new_count}"
    )
    paths = [
        str(field.get("path") or "")
        for change in item.get("internalChanges") or []
        if change.get("kind") == "CHILD_CONFIGURATION_CHANGE"
        for field in change.get("fields") or []
    ]
    impacts = []
    if any("fieldUsage" in path for path in paths):
        impacts.append("列表展示字段、查询条件或数据范围可能变化")
    if any("eventGroup" in path for path in paths):
        impacts.append("点击、刷新或跳转交互发生变化")
    if any("flow" in path or "layout" in path for path in paths):
        impacts.append("组件层级或页面布局绑定发生变化")
    if any(path == "record" for path in paths):
        impacts.append("页面组件或导航子配置发生新增、删除或替换")
    return (
        count_text,
        "、".join(added[:8]) or "无",
        "、".join(removed[:8]) or "无",
        _configuration_change_text(item),
        "；".join(impacts[:3]) or item.get("businessPurpose") or "页面入口或交互发生调整",
    )


def _flow_change_columns(item: dict[str, Any]) -> tuple[str, str, str, str, str]:
    node = next(
        (change for change in item.get("internalChanges") or [] if change.get("kind") == "NODE_SET"),
        {},
    )
    formula = next(
        (change for change in item.get("internalChanges") or [] if change.get("kind") == "FORMULA_CHANGE"),
        {},
    )
    mapping = next(
        (change for change in item.get("internalChanges") or [] if change.get("kind") == "MAPPING_CHANGE"),
        {},
    )
    name_change = next(
        (
            change
            for change in item.get("internalChanges") or []
            if change.get("kind") == "NAME_CHANGED"
        ),
        {},
    )
    status_change = next(
        (change for change in item.get("internalChanges") or [] if change.get("kind") == "FLOW_STATUS_CHANGED"),
        {},
    )
    added = Counter(node.get("addedComponents") or [])
    removed = Counter(node.get("removedComponents") or [])
    details = []
    if formula.get("factCount", 0):
        details.append(f"公式或条件 {formula.get('factCount', 0)} 处")
    if mapping.get("factCount", 0):
        details.append(f"字段映射 {mapping.get('factCount', 0)} 处")
    if name_change:
        details.append(
            f"名称由“{_short(name_change.get('oldName'))}”调整为"
            f"“{_short(name_change.get('newName'))}”"
        )
    if status_change:
        details.append(_change_text({"internalChanges": [status_change]}))
    configuration = _configuration_change_text(item, limit=3)
    if configuration != "未观察到可展示的字段前后值":
        details.append(configuration)
    if not details and (added or removed):
        details.append("节点类型或结构发生变化")
    return (
        f"{node.get('oldCount', 0)}→{node.get('newCount', 0)}",
        "、".join(f"{_flow_node_component_label(name)}×{count}" for name, count in added.most_common(6)) or "无",
        "、".join(f"{_flow_node_component_label(name)}×{count}" for name, count in removed.most_common(6)) or "无",
        "；".join(details) or "未观察到可确认的节点参数变化",
        item.get("businessPurpose") or "动作执行结果或数据副作用可能变化",
    )


def _test_operation(item: dict[str, Any]) -> str:
    object_type = item.get("objectType")
    change_type = item.get("changeType")
    name = item.get("businessName")
    if change_type == "REMOVED":
        return f"检查“{name}”原入口、收藏、上游调用和历史记录，并确认替代路径"
    if object_type == "FORM":
        return f"使用代表数据新增、编辑、查看“{name}”，再执行关联按钮或流程"
    if object_type == "PAGE":
        return f"从实际菜单进入“{name}”，验证加载、筛选、交互、空数据和无权限场景"
    if object_type == "ESB_ACTION_FLOW":
        return f"从真实触发入口执行“{name}”的正常、边界和失败分支，并核对数据前后值"
    if object_type == "MENU":
        return f"分别使用有权和无权角色从 PC/H5 访问“{name}”"
    if object_type == "DATASET":
        return f"通过关联页面查询“{name}”，覆盖代表数据、空数据、筛选和分页"
    if object_type == "EXTERNAL_INTEGRATION":
        return f"从关联动作流触发“{name}”，核对目标资源、输入输出和异常处理"
    if object_type == "PERMISSION":
        return f"使用有权、无权和不同数据范围角色验证“{name}”"
    return f"从实际业务入口执行“{name}”并保留操作前后截图、日志或数据证据"


def _test_expected(item: dict[str, Any]) -> str:
    change_type = item.get("changeType")
    object_type = item.get("objectType")
    if change_type == "REMOVED":
        return "旧入口已清理或明确跳转到替代能力；历史数据仍按约定可查，不残留无效引用"
    if object_type == "FORM":
        return "字段、布局、按钮和联动符合新版配置，历史数据可查看，新写入数据完整"
    if object_type == "PAGE":
        return "页面组件、数据、跳转和权限符合新版配置，PC/H5 无越权或无效入口"
    if object_type == "ESB_ACTION_FLOW":
        return "节点顺序、分支、公式、映射和数据副作用符合新版配置，失败路径有明确结果"
    if object_type == "MENU":
        return "菜单层级、打开目标和角色可见范围正确，无源环境引用残留"
    if object_type == "DATASET":
        return "查询字段、数据范围、筛选、汇总和空数据行为符合预期"
    if object_type == "EXTERNAL_INTEGRATION":
        return "目标资源可解析，输入输出和错误处理符合约定，未配置时产生可定位证据"
    if object_type == "PERMISSION":
        return "授权用户可见可用，未授权用户不可越权，数据范围正确"
    return "业务结果与新版静态配置一致，异常时可通过截图、请求、日志或数据前后值定位"


def build_test_scenarios(model: dict[str, Any]) -> list[dict[str, Any]]:
    active = [
        item for item in model.get("objects") or []
        if item.get("changeType") in {"ADDED", "REMOVED", "UPDATED"}
    ]
    used = set()
    scenarios = []

    def take(candidates: list[dict[str, Any]], limit: int, priority: str, group: str) -> None:
        for item in candidates:
            marker = (group, item.get("logicalKey"), item.get("changeType"))
            if marker in used:
                continue
            used.add(marker)
            scenarios.append(
                {
                    "priority": priority,
                    "group": group,
                    "name": item.get("businessName"),
                    "relatedChange": f"{CHANGE_LABELS.get(item.get('changeType'))}{TYPE_LABELS.get(item.get('objectType'), item.get('objectType'))}",
                    "operation": _test_operation(item),
                    "expected": _test_expected(item),
                    "objectType": item.get("objectType"),
                    "logicalKey": item.get("logicalKey"),
                }
            )
            if sum(value["group"] == group for value in scenarios) >= limit:
                break

    core = sorted(
        [
            item for item in active
            if item.get("objectType") in {"ESB_ACTION_FLOW", "FORM", "WORKFLOW"}
            and any(token in item.get("businessName", "") for token in CORE_KEYWORDS)
        ],
        key=lambda item: (
            item.get("objectType") != "ESB_ACTION_FLOW",
            item.get("changeType") != "UPDATED",
            item.get("businessName"),
        ),
    )
    take(core, 12, "P0", "核心业务链路")
    take(
        sorted([item for item in active if item.get("changeType") == "ADDED"], key=lambda item: (item.get("objectType"), item.get("businessName"))),
        8,
        "P1",
        "新增功能",
    )
    take(
        sorted([item for item in active if item.get("changeType") == "UPDATED"], key=lambda item: (item.get("objectType"), item.get("businessName"))),
        7,
        "P1",
        "更新功能",
    )
    take(
        sorted([item for item in active if item.get("changeType") == "REMOVED"], key=lambda item: (item.get("objectType"), item.get("businessName"))),
        5,
        "P2",
        "删除与兼容性",
    )
    target = min(32, max(1, min(20, len(active))) if len(active) < 20 else 32)
    if len(scenarios) < target:
        fallback = sorted(active, key=lambda item: (item.get("objectType"), item.get("changeType"), item.get("businessName")))
        for item in fallback:
            marker = ("补充业务场景", item.get("logicalKey"), item.get("changeType"))
            if any(
                value.get("logicalKey") == item.get("logicalKey")
                and value.get("relatedChange") == f"{CHANGE_LABELS.get(item.get('changeType'))}{TYPE_LABELS.get(item.get('objectType'), item.get('objectType'))}"
                for value in scenarios
            ):
                continue
            used.add(marker)
            scenarios.append(
                {
                    "priority": "P1",
                    "group": "补充业务场景",
                    "name": item.get("businessName"),
                    "relatedChange": f"{CHANGE_LABELS.get(item.get('changeType'))}{TYPE_LABELS.get(item.get('objectType'), item.get('objectType'))}",
                    "operation": _test_operation(item),
                    "expected": _test_expected(item),
                    "objectType": item.get("objectType"),
                    "logicalKey": item.get("logicalKey"),
                }
            )
            if len(scenarios) >= target:
                break
    return scenarios[:40]


def render_report(model: dict[str, Any], analysis: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    app_name = model.get("applicationName") or "eBuilder 应用"
    rows = {item["label"]: item for item in model.get("summary") or []}
    scenarios = build_test_scenarios(model)
    lines: list[str] = []

    def add(*values: str) -> None:
        lines.extend(values)

    old_meta = model["direction"]["old"]
    new_meta = model["direction"]["new"]
    direction = analysis.get("analysisDirection") or {}
    if direction.get("directionSource") == "PROFILE_EXPORT_TIME":
        direction_text = (
            f"- 对比方向：旧版“{_escape(old_meta.get('name'))}”"
            f"（exportTime：{_escape((direction.get('oldProfile') or {}).get('raw'))}） → "
            f"新版“{_escape(new_meta.get('name'))}”"
            f"（exportTime：{_escape((direction.get('newProfile') or {}).get('raw'))}）；"
            "方向由两个包最外层 `profile.json.exportTime` 自动识别，"
            "没有根据文件名或文件属性推断。"
        )
    else:
        direction_text = (
            f"- 对比方向：旧版“{_escape(old_meta.get('name'))}” → "
            f"新版“{_escape(new_meta.get('name'))}”；方向来自明确的 "
            "`--old`、`--new` 参数，没有根据文件名或文件属性推断。"
        )
    form = _summary(model, "表单")
    page = _summary(model, "页面")
    flow = _summary(model, "动作流")
    menu = _summary(model, "菜单")
    permission = _summary(model, "权限")

    add(
        f"# {app_name}应用版本功能差异报告",
        "",
        "## 1. 报告范围",
        "",
        direction_text,
        f"- 旧包 SHA-256：`{str(old_meta.get('sha256', ''))[:16]}…`；新包 SHA-256：`{str(new_meta.get('sha256', ''))[:16]}…`。",
        "- 分析范围：表单、页面、嵌入式视图、动作流、工作流/审批流程、菜单、导航、报表、多级填报、独立数据集、业务资源绑定和权限。",
        "- 报告性质：迁入前离线包静态对比。报告中的风险解释和测试建议不是实际迁入或运行验收结果。",
        "",
        "## 2. 总体结论",
        "",
        f"新版在保留核心业务链路的基础上，新增了 {form['added']} 个表单、{page['added']} 个页面、{flow['added']} 条动作流和 {menu['added']} 个菜单；删除了 {form['removed']} 个表单、{page['removed']} 个页面、{flow['removed']} 条动作流和 {menu['removed']} 个菜单；另有 {form['updated']} 个保留表单、{page['updated']} 个页面、{flow['updated']} 条动作流和 {menu['updated']} 个菜单发生功能调整。",
        "",
    )
    highlights = [
        item for item in model.get("objects") or []
        if item.get("changeType") in {"ADDED", "REMOVED", "UPDATED"}
        and item.get("objectType") in {"FORM", "PAGE", "ESB_ACTION_FLOW", "MENU", "REPORT"}
    ]
    for item in highlights[:7]:
        add(f"- {CHANGE_LABELS[item['changeType']]}{TYPE_LABELS[item['objectType']]}“{item['businessName']}”：{_short(_change_text(item), 150)}。")
    if not highlights:
        add("- 未观察到可确认的一级业务功能新增、删除或更新；疑似替代和未确认项见后文。")

    add(
        "",
        "## 3. 功能对象变化汇总",
        "",
        "| 功能对象 | 旧版数量 | 新版数量 | 新增 | 删除 | 更新 | 净变化 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    )
    for row in model.get("summary") or []:
        net = row["netChange"]
        add(
            f"| {row['label']} | {row['oldCount']} | {row['newCount']} | {row['added']} | {row['removed']} | {row['updated']} | {'+' if net >= 0 else ''}{net} |"
        )
    unit_summary = model.get("packageUnitSummary") or []
    if unit_summary:
        add(
            "",
            "### 3.1 批量包子应用变化汇总",
            "",
            "以下数量按顶层应用 ZIP 隔离计算；同名对象不会跨子应用匹配。",
            "",
            "| 子应用 | 新增 | 删除 | 更新 | 疑似重命名/替代 |",
            "|---|---:|---:|---:|---:|",
        )
        for unit in unit_summary:
            add(
                f"| {_escape(unit.get('name'))} | {unit.get('added', 0)} | "
                f"{unit.get('removed', 0)} | {unit.get('updated', 0)} | "
                f"{unit.get('possibleRename', 0)} |"
            )
    add(
        "",
        "说明：这里统计的是可独立使用或配置的业务功能对象，不是底层配置记录。净变化 = 新增 - 删除，更新不参与净数量计算；疑似重命名和疑似重建单独列示，不强行计入更新。",
        "",
        "## 4. 新增功能",
        "",
        "### 4.1 新增表单",
        "",
        f"新版新增 {form['added']} 个表单。",
        "",
        "| 表单名称 | 主要新增内容 | 实现的业务功能 | 相关入口或依赖 |",
        "|---|---|---|---|",
    )
    for item in _items(model, "FORM", "ADDED"):
        add(f"| {_escape(item['businessName'])} | {_short(_change_text(item))} | {_short(item['businessPurpose'])} | {_short(item['userEntry'])} |")
    if not _items(model, "FORM", "ADDED"):
        add("| 无 | 本次未观察到新增表单 | — | — |")

    add(
        "",
        "### 4.2 新增页面",
        "",
        f"新版新增 {page['added']} 个页面。",
        "",
        "| 页面名称 | 终端 | 主要组件 | 页面功能 | 关联数据或入口 |",
        "|---|---|---|---|---|",
    )
    for item in _items(model, "PAGE", "ADDED"):
        summary = item.get("newSummary") or {}
        component_types = summary.get("componentTypes") or {}
        components = "、".join(f"{name}×{count}" for name, count in list(component_types.items())[:8])
        component_count = summary.get("componentCount", 0)
        component_summary = (
            components
            or f"可识别组件 {component_count} 个"
            if component_count
            else "组件关系待确认（未解析到可归属组件）"
        )
        add(f"| {_escape(item['businessName'])} | PC/H5 以包内配置为准 | {_short(component_summary)} | {_short(item['businessPurpose'])} | {_short(item['userEntry'])} |")
    if not _items(model, "PAGE", "ADDED"):
        add("| 无 | — | 本次未观察到新增页面 | — | — |")

    add(
        "",
        "### 4.3 新增动作流",
        "",
        f"新版新增 {flow['added']} 条动作流。完整名称均在本节和附录保留，未简写为技术统计。",
        "",
        "| 动作流名称 | 触发方式 | 主要节点或组件 | 实现的功能 | 关联表单/页面 |",
        "|---|---|---|---|---|",
    )
    for item in _items(model, "ESB_ACTION_FLOW", "ADDED"):
        node = next((value for value in item.get("internalChanges") or [] if value.get("kind") == "NODE_SET"), {})
        components = Counter(node.get("addedComponents") or [])
        component_text = "、".join(
            f"{_flow_node_component_label(name)}×{count}"
            for name, count in components.most_common(8)
        )
        trigger = "定时触发" if any(token in item["businessName"] for token in ("定时", "周期", "预警")) else "按钮、流程事件、联动或子动作流"
        node_summary = component_text or f"节点 {node.get('newCount', 0)} 个"
        add(f"| {_escape(item['businessName'])} | {trigger} | {_short(node_summary)} | {_short(item['businessPurpose'])} | 关联对象以包内引用和目标映射为准 |")
    if not _items(model, "ESB_ACTION_FLOW", "ADDED"):
        add("| 无 | — | 本次未观察到新增动作流 | — | — |")

    add(
        "",
        "### 4.4 新增菜单与导航",
        "",
        "| 菜单名称 | 终端 | 父级路径 | 打开目标 | 业务作用 |",
        "|---|---|---|---|---|",
    )
    for item in _items(model, "MENU", "ADDED"):
        add(f"| {_escape(item['businessName'])} | PC/H5 以包内配置为准 | 应用导航路径 | {_short((item.get('newSummary') or {}).get('openTarget'))} | {_short(item['businessPurpose'])} |")
    if not _items(model, "MENU", "ADDED"):
        add("| 无 | — | — | 本次未观察到新增菜单 | — |")
    nav_added = _items(model, "NAVIGATION", "ADDED")
    if nav_added:
        add("", "新增导航：" + "、".join(item["businessName"] for item in nav_added) + "。")

    add(
        "",
        "### 4.5 新增工作流、报表、数据集与集成",
        "",
    )
    for object_type in ("WORKFLOW", "REPORT", "MULTI_FILLING", "DATASET", "EXTERNAL_INTEGRATION", "PERMISSION"):
        values = _items(model, object_type, "ADDED")
        add(f"- {TYPE_LABELS[object_type]}：新增 {len(values)} 项。" + ("主要包括“" + "”“".join(item["businessName"] for item in values[:8]) + "”。" if values else ""))

    add(
        "",
        "## 5. 删除功能",
        "",
        "### 5.1 删除表单",
        "",
        "| 表单名称 | 旧版功能 | 原入口或调用方 | 删除影响 |",
        "|---|---|---|---|",
    )
    for item in _items(model, "FORM", "REMOVED"):
        add(f"| {_escape(item['businessName'])} | {_short(item['businessPurpose'])} | {_short(item['userEntry'])} | 需确认替代能力、历史数据查看和残余引用 |")
    if not _items(model, "FORM", "REMOVED"):
        add("| 无 | 本次未观察到删除表单 | — | — |")

    add(
        "",
        "### 5.2 删除页面",
        "",
        "| 页面名称 | 原页面功能 | 原入口 | 删除影响 |",
        "|---|---|---|---|",
    )
    for item in _items(model, "PAGE", "REMOVED"):
        add(f"| {_escape(item['businessName'])} | {_short(item['businessPurpose'])} | {_short(item['userEntry'])} | 需确认菜单、跳转、权限和历史访问路径已清理 |")
    if not _items(model, "PAGE", "REMOVED"):
        add("| 无 | 本次未观察到删除页面 | — | — |")

    add(
        "",
        "### 5.3 删除动作流",
        "",
        "| 动作流名称 | 原触发方式 | 原功能 | 新版替代方式 | 删除影响 |",
        "|---|---|---|---|---|",
    )
    for item in _items(model, "ESB_ACTION_FLOW", "REMOVED"):
        add(f"| {_escape(item['businessName'])} | 按钮、流程事件、联动或子动作流 | {_short(item['businessPurpose'])} | 未确认；疑似替代见第 7 节 | 需确认上游调用和数据回写没有残留引用 |")
    if not _items(model, "ESB_ACTION_FLOW", "REMOVED"):
        add("| 无 | — | 本次未观察到删除动作流 | — | — |")

    add(
        "",
        "### 5.4 删除菜单与导航",
        "",
        "| 名称 | 类型 | 原目标或作用 | 删除影响 |",
        "|---|---|---|---|",
    )
    for object_type in ("MENU", "NAVIGATION"):
        for item in _items(model, object_type, "REMOVED"):
            add(f"| {_escape(item['businessName'])} | {TYPE_LABELS[object_type]} | {_short((item.get('oldSummary') or {}).get('openTarget') or item['businessPurpose'])} | 需确认替代入口、收藏和权限引用 |")
    if not any(_items(model, value, "REMOVED") for value in ("MENU", "NAVIGATION")):
        add("| 无 | — | 本次未观察到删除菜单或导航 | — |")

    add("", "### 5.5 删除其他功能", "")
    for object_type in ("WORKFLOW", "REPORT", "MULTI_FILLING", "DATASET", "EXTERNAL_INTEGRATION", "PERMISSION"):
        values = _items(model, object_type, "REMOVED")
        add(f"- {TYPE_LABELS[object_type]}：删除 {len(values)} 项。" + ("需确认“" + "”“".join(item["businessName"] for item in values[:8]) + "”的替代与历史兼容。" if values else ""))

    add(
        "",
        "## 6. 更新功能",
        "",
        "### 6.1 表单更新",
        "",
        f"共有 {form['updated']} 个保留表单的字段、布局、列表、按钮或联动发生业务调整。",
        "",
        "| 表单名称 | 字段变化 | 布局/列表变化 | 按钮或动作变化（旧值→新值） | 功能影响 |",
        "|---|---|---|---|---|",
    )
    form_updates = _items(model, "FORM", "UPDATED")
    important_forms = sorted(form_updates, key=lambda item: (not any(token in item["businessName"] for token in CORE_KEYWORDS), item["businessName"]))[:24]
    for item in important_forms:
        columns = _form_change_columns(item)
        add(f"| {_escape(item['businessName'])} | {_short(columns[0])} | {_short(columns[1])} | {_short(columns[2])} | {_short(columns[3])} |")
    if not form_updates:
        add("| 无 | 本次未观察到确认的表单更新 | — | — | — |")

    add(
        "",
        "### 6.2 页面更新",
        "",
        f"共有 {page['updated']} 个保留页面发生组件结构、数据或交互变化；纯样式和缓存差异没有计为业务逻辑更新。",
        "",
        "| 页面名称 | 组件数旧→新 | 新增组件 | 删除组件 | 数据/交互变化 | 功能影响 |",
        "|---|---:|---|---|---|---|",
    )
    page_updates = _items(model, "PAGE", "UPDATED")
    detailed_page_limit = 36 if len(page_updates) > 60 else len(page_updates)
    important_pages = sorted(
        page_updates,
        key=lambda item: (
            not any(token in item["businessName"] for token in CORE_KEYWORDS),
            item["businessName"],
        ),
    )[:detailed_page_limit]
    for item in important_pages:
        columns = _page_change_columns(item)
        add(f"| {_escape(item['businessName'])} | {columns[0]} | {_short(columns[1])} | {_short(columns[2])} | {_short(columns[3])} | {_short(columns[4])} |")
    if len(page_updates) > detailed_page_limit:
        add(
            f"| 其余 {len(page_updates) - detailed_page_limit} 个更新页面 | — | — | — | "
            "完整名称见附录C，字段前后值及证据见 `business-object-diff.json` | — |"
        )
    if not page_updates:
        add("| 无 | — | 本次未观察到确认的页面业务更新 | — | — | — |")

    add(
        "",
        "### 6.3 动作流更新",
        "",
        f"共有 {flow['updated']} 条保留动作流的节点、公式、映射或分支配置发生业务变化。",
        "",
        "| 动作流名称 | 节点数旧→新 | 新增节点/组件 | 删除节点/组件 | 公式/映射变化 | 功能影响 |",
        "|---|---:|---|---|---|---|",
    )
    flow_updates = _items(model, "ESB_ACTION_FLOW", "UPDATED")
    important_flows = sorted(flow_updates, key=lambda item: (not any(token in item["businessName"] for token in CORE_KEYWORDS), item["businessName"]))[:24]
    for item in important_flows:
        columns = _flow_change_columns(item)
        add(f"| {_escape(item['businessName'])} | {columns[0]} | {_short(columns[1])} | {_short(columns[2])} | {_short(columns[3])} | {_short(columns[4])} |")
    if not flow_updates:
        add("| 无 | — | 本次未观察到确认的动作流更新 | — | — | — |")

    add(
        "",
        "### 6.4 菜单与权限更新",
        "",
        f"确认 {menu['updated']} 个保留菜单发生目标、打开方式、入口参数或访问识别配置调整；权限对象净变化 {permission['netChange']:+d} 项。",
        "",
        "| 菜单名称 | 修改前目标 | 修改后目标 | 路径/权限变化 | 用户影响 |",
        "|---|---|---|---|---|",
    )
    for item in _items(model, "MENU", "UPDATED"):
        add(f"| {_escape(item['businessName'])} | {_short((item.get('oldSummary') or {}).get('openTarget'))} | {_short((item.get('newSummary') or {}).get('openTarget'))} | {_short(_change_text(item), 260)} | 需确认 PC/H5 入口、打开行为和授权后可达性 |")
    if not _items(model, "MENU", "UPDATED"):
        add("| 无 | 本次未观察到确认的菜单目标更新 | — | — | — |")
    add("", "| 权限类型 | 旧版 | 新版 | 新增 | 删除 |", "|---|---:|---:|---:|---:|")
    for label, values in (model.get("permissionBreakdown") or {}).items():
        add(f"| {label} | {values.get('old', 0)} | {values.get('new', 0)} | {values.get('added', 0)} | {values.get('removed', 0)} |")

    add(
        "",
        "### 6.5 报表、工作流和集成更新",
        "",
    )
    for object_type in ("REPORT", "WORKFLOW", "NAVIGATION", "DATASET", "EXTERNAL_INTEGRATION", "APPLICATION_SHELL"):
        values = _items(model, object_type, "UPDATED")
        possible = _items(model, object_type, "POSSIBLE_RENAME")
        add(f"- {TYPE_LABELS[object_type]}：确认更新 {len(values)} 项，疑似重命名或重建 {len(possible)} 项。" + ("确认更新包括“" + "”“".join(item["businessName"] for item in values[:6]) + "”。" if values else ""))

    add(
        "",
        "### 6.6 跨模块变化、待确认项与非功能性变化",
        "",
        "本节确保无法稳定归属到单个一级对象的变化也不会从客户报告中消失；"
        "已归属到表单、页面或动作流的变化可能在此按业务链路再次汇总，不重复计入一级对象数量。",
        "",
        "| 业务变化链路 | 模块 | 底层变化统计 | 关键配置旧值→新值 | 影响判断 |",
        "|---|---|---|---|---|",
    )
    feature_summaries = model.get("featureChangeSummaries") or []
    for feature in feature_summaries:
        counts = "、".join(
            f"{CHANGE_LABELS.get(kind, kind)} {count}"
            for kind, count in sorted((feature.get("rawChangeCounts") or {}).items())
        ) or "未确认"
        path_text = "；".join(
            _field_change_text(item)
            for item in (feature.get("changedPaths") or [])[:5]
        )
        if not path_text:
            path_text = "记录集合发生变化，具体前后记录见机器可读明细"
        impact = feature.get("userVisibleChange") or feature.get("businessPurpose")
        if feature.get("reportingStatus") == "EXCLUDED_NON_BUSINESS":
            impact = "已排除：" + str(impact)
        elif feature.get("evidenceLevel") == "UNKNOWN" and not str(impact or "").startswith("待确认"):
            impact = "待确认：" + str(impact or "需要结合目标环境确认业务影响")
        add(
            f"| {_short(feature.get('businessFunction'), 120)} | "
            f"{_short(feature.get('moduleKind') or feature.get('module'), 60)} | "
            f"{_short(counts, 100)} | {_short(path_text, 260)} | {_short(impact, 160)} |"
        )
    if not feature_summaries:
        add("| 无 | — | 本次未观察到业务变化链路 | — | — |")

    add(
        "",
        "## 7. 疑似重命名和功能替代",
        "",
        "| 旧对象 | 新对象候选 | 对象类型 | 相似依据 | 结论 |",
        "|---|---|---|---|---|",
    )
    for relation in model.get("possibleRenamesAndReplacements") or []:
        add(f"| {_short(relation.get('oldObject'))} | {_short(relation.get('newObjectCandidate'))} | {_escape(relation.get('objectType'))} | {_short(relation.get('similarityBasis'))} | {_escape(relation.get('conclusion'))} |")
    if not model.get("possibleRenamesAndReplacements"):
        add("| 无 | 无 | — | 本次未形成满足保守门槛的候选关系 | 无法确认 |")
    add("", "疑似替代不会为了减少新增和删除数量而强行改成更新；只有业务负责人或更强证据确认后，才能裁决为同一对象。")

    add(
        "",
        "## 8. 业务影响评估",
        "",
        "| 影响方面 | 真实变化 | 可能影响 |",
        "|---|---|---|",
        f"| 用户入口 | 页面新增 {page['added']}、删除 {page['removed']}、更新 {page['updated']}；菜单新增 {menu['added']}、删除 {menu['removed']}、更新 {menu['updated']} | 访问路径、角色可见范围、PC/H5 和替代入口需要验证 |",
        f"| 表单录入 | 表单新增 {form['added']}、删除 {form['removed']}、更新 {form['updated']} | 字段录入、历史数据、布局、列表、按钮和联动可能变化 |",
        f"| 数据写入 | 动作流新增 {flow['added']}、删除 {flow['removed']}、更新 {flow['updated']} | 状态、记录、次数、映射结果和失败回滚需要重点验证 |",
        f"| 页面展示 | 页面组件和数据集发生对象级变化 | 指标、列表、图表、筛选、跳转、空数据和权限行为需要验证 |",
        f"| 工作流流转 | 工作流确认更新 {_summary(model, '工作流/审批流程')['updated']} 项；动作流可能连接流程事件 | 节点前后置动作、操作者、分支和在途流程兼容需要核对 |",
        f"| 权限 | 权限净变化 {permission['netChange']:+d} 项 | 新功能可能因漏授权不可见，也可能扩大查看或操作范围 |",
        f"| 报表与集成 | 一级报表和外部集成均未确认更新；跨模块汇总保留待确认的多语言或目标绑定线索 | 仅在取得目标映射或运行证据后判断是否影响查询、菜单链接或外部调用 |",
        f"| 历史数据 | 存在 {form['removed']} 个表单和 {flow['removed']} 条动作流删除 | 旧记录查看、旧任务继续办理和历史引用兼容需要验证 |",
        "",
        "风险规则、ID 替换和外部引用只用于解释为什么需要这些测试；完整技术风险实例保留在 `风险与验证点.jsonl`，不作为本报告主叙事。",
        "",
        "## 9. 重点测试建议",
        "",
        "通用前置条件：准备正常、空值、边界、失败和权限代表数据；按 PC/H5、角色和流程分支执行；保留页面截图、请求响应、动作流/服务日志、字段前后值或映射报告。",
        "",
    )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for scenario in scenarios:
        grouped[scenario["group"]].append(scenario)
    group_order = ["核心业务链路", "新增功能", "更新功能", "删除与兼容性", "补充业务场景"]
    priorities = {
        "核心业务链路": "P0",
        "新增功能": "P1",
        "更新功能": "P1",
        "删除与兼容性": "P2",
        "补充业务场景": "P1",
    }
    for group in group_order:
        values = grouped.get(group) or []
        if not values:
            continue
        add(
            f"### {priorities[group]}：{group}",
            "",
            "| 测试场景 | 关联变化 | 操作要点 | 预期结果 |",
            "|---|---|---|---|",
        )
        for scenario in values:
            add(f"| {_escape(scenario['name'])} | {_escape(scenario['relatedChange'])} | {_short(scenario['operation'], 220)} | {_short(scenario['expected'], 220)} |")
        add("")

    add(
        "## 10. 未确认项和能力边界",
        "",
    )
    unknowns = analysis.get("unknownItems") or []
    relations = model.get("possibleRenamesAndReplacements") or []
    identity = analysis.get("identityResolution") or {}
    add(
        f"1. 疑似重命名、疑似替代或同名重建候选共 {len(relations)} 项，均未强行认定为更新。",
        f"2. 计算分析层保留 {len(unknowns)} 条无法稳定匹配、包外引用或证据不足事项；完整明细见 `无法确认项.jsonl`。",
        "3. 外部连接、组织、人员、角色、流程和其他包外资源是否已在目标环境配置，需要结合映射报告和运行证据确认。",
        "4. 报告没有执行迁入、接口调用、数据库核验或运行时验收；所有预期结果都必须在目标环境实际执行。",
        "5. OBSERVED 表示离线包或内置 Codex 知识直接证据；INFERRED 表示关系传播或业务语义推断；UNKNOWN 表示需要目标映射、数据库或运行证据确认。",
        (
            "6. 新旧环境当前 ID 不一致时，优先按迁入同源 ID 识别同一对象；"
            f"本次共有 {identity.get('matchesByMigrationSourceId', 0)} 个技术对象"
            "由该关系直接匹配。缺失、冲突或超出表/模块作用域的映射不会强行使用。"
        ),
        "",
        "## 附录A：完整新增对象",
        "",
    )
    appendix_order = [
        "FORM", "PAGE", "EMBEDDED_VIEW", "ESB_ACTION_FLOW", "WORKFLOW", "MENU",
        "NAVIGATION", "REPORT", "MULTI_FILLING", "DATASET", "EXTERNAL_INTEGRATION",
        "PERMISSION", "OTHER",
    ]
    active_object_count = sum(
        item.get("changeType") in {"ADDED", "REMOVED", "UPDATED"}
        for item in model.get("objects") or []
    )
    compact_appendix = active_object_count > 250
    if compact_appendix:
        add(
            "批量包变化对象较多；以下附录保留全部业务对象名称，"
            "每行合并展示多个名称。内部变化、用途和证据仍完整保存在 "
            "`business-object-diff.json`。",
            "",
        )

    def add_appendix_items(values: list[dict[str, Any]], change_type: str) -> None:
        if compact_appendix:
            for offset in range(0, len(values), 6):
                batch = values[offset: offset + 6]
                names = "；".join(_escape(item["businessName"]) for item in batch)
                add(f"{offset + 1}–{offset + len(batch)}. {names}。")
            return
        for index, item in enumerate(values, 1):
            detail = _change_text(item) if change_type == "UPDATED" else item.get("businessPurpose")
            add(f"{index}. {item['businessName']}：{_short(detail, 220)}。")
    for object_type in appendix_order:
        values = _items(model, object_type, "ADDED")
        if not values:
            continue
        add(f"### 新增{TYPE_LABELS[object_type]}（{len(values)}）", "")
        add_appendix_items(values, "ADDED")

    add("## 附录B：完整删除对象", "")
    for object_type in appendix_order:
        values = _items(model, object_type, "REMOVED")
        if not values:
            continue
        add(f"### 删除{TYPE_LABELS[object_type]}（{len(values)}）", "")
        add_appendix_items(values, "REMOVED")

    add("## 附录C：完整更新对象", "")
    for object_type in appendix_order + ["APPLICATION_SHELL"]:
        values = _items(model, object_type, "UPDATED")
        if not values:
            continue
        add(f"### 更新{TYPE_LABELS[object_type]}（{len(values)}）", "")
        add_appendix_items(values, "UPDATED")

    add(
        "## 附录D：技术证据索引",
        "",
        "| 证据文件 | 用途 |",
        "|---|---|",
        "| `comparison-facts.jsonl` | 字段级事实、对象存在性和变化类型 |",
        "| `comparison-analysis.json` | 影响、风险、验证点、未知项和分析边界 |",
        "| `business-object-diff.json` | 表单、页面、动作流等一级业务对象差异 |",
        "| `应用版本功能差异明细.json` | 完整机器可读变化与分析结果 |",
        "| `应用版本差异可视化.html` | 离线查看版本总览、业务链路、字段勾稽、影响风险与验证场景 |",
        "| `visual-diff-model.json` | 可视化使用的确定性业务节点、关系、字段和验证模型；大包可能为 `.json.gz` |",
        "| `影响传播明细.jsonl` | 直接影响和最多三层的间接影响 |",
        "| `风险与验证点.jsonl` | 原始风险实例、配置检查点和业务验证点 |",
        "| `无法确认项.jsonl` | 疑似重命名、无法匹配和包外未知项 |",
        "| `执行与完整性校验.json` | 输入方向、事实层哈希和全部质量门禁 |",
        "",
        "正文不展示大段原始 JSON、完整 SQL、数据库流水、风险总账或逐条技术验证记录。每个业务对象在 `business-object-diff.json` 中保留逻辑键、变化编号、模块、表和记录序号，可继续追溯到事实层。",
        "",
    )
    return "\n".join(lines).rstrip() + "\n", scenarios
