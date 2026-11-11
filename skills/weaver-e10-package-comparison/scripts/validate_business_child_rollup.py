#!/usr/bin/env python3
"""Self-test child configuration roll-up and customer-visible before/after values."""

from __future__ import annotations

import copy
import json

from build_business_object_diff import (
    _flow_business_children,
    build_business_object_diff,
    validate_quantity,
)
from compare_reconstructed_application import (
    workflow_post_validation_delta,
    workflow_sql_datasource_delta,
)
from render_business_object_report import _change_text, render_report
from render_detail_diff_report import (
    _flow_conclusion, _flow_detail_rows, _flow_impact, _flow_nodes,
    _flow_specific_change,
    _form_conclusion, _form_detail_rows, _form_impact,
    _page_conclusion, _page_detail_rows, _page_impact, _page_specific_change,
)
from validate_report_readability import validate_readability


MODULE_FORM = "weaver-ebuilder-form-service"
MODULE_PAGE = "weaver-ebuilder-app-service"


def object_record(module: str, table: str, key: str, name: str, canonical: dict) -> dict:
    return {
        "module": module,
        "table": table,
        "logicalKey": key,
        "displayName": name,
        "canonical": canonical,
        "canonicalHash": "stable-" + key,
        "sourceEvidence": {"recordOrdinal": 1},
    }


def main() -> None:
    form_key = f'{MODULE_FORM}::form::name="项目基础"'
    form_obj_key = f'{MODULE_FORM}::ebdf_obj::table_name="uf_proj"'
    button_key = f'{MODULE_FORM}::ebdf_button::name="个性化设置"'
    page_key = f'{MODULE_PAGE}::ebdp_page::name="项目首页"|type="PAGE"'
    component_key = f'{MODULE_PAGE}::ebdd_layout_component::type="NList"'
    owner_noise_key = f'{MODULE_PAGE}::ebdd_layout_component::type="Bar"'
    layout_component_key = f'{MODULE_FORM}::ebdd_layout_component::type="Text"::parent=aaaaaaaaaaaaaaaa'
    layout_key = f'{MODULE_FORM}::form_layout_multiple::name="项目基础-CPQ"'
    workflow_key = f'{MODULE_FORM}::wfp_base::workflowname="工时填报"'
    scope_key = f'{MODULE_FORM}::browser_data_scope::content="项目任务范围"'
    node_key = f'{MODULE_FORM}::wfp_node::name="档案组录入"'
    cpt_base_key = f'{MODULE_FORM}::wfp_cpt_base::node="档案组录入"'
    old_condition_key = f'{MODULE_FORM}::wfr_mapbase::condition="old-active"'
    new_condition_key = f'{MODULE_FORM}::wfr_mapbase::condition="new-active"'
    retained_rule_key = f'{MODULE_FORM}::wfp_cpt_set::source="retained"'
    removed_rule_key = f'{MODULE_FORM}::wfp_cpt_set::source="removed"'
    context_key = f'{MODULE_FORM}::wfp_context::source="shop-context"'
    old_dataset_key = f'{MODULE_FORM}::dataset::idm-lineage="old-dataset"'
    new_dataset_key = f'{MODULE_FORM}::dataset::idm-lineage="new-dataset"'

    old_objects = [
        object_record(MODULE_FORM, "form", form_key, "项目基础", {"name": "项目基础"}),
        object_record(MODULE_FORM, "ebdf_obj", form_obj_key, "项目基础对象", {"form_id": {"$ref": form_key}}),
        object_record(MODULE_FORM, "ebdf_button", button_key, "个性化设置", {"obj_id": {"$ref": form_obj_key}}),
        object_record(MODULE_PAGE, "ebdp_page", page_key, "项目首页", {"name": "项目首页", "type": "PAGE"}),
        object_record(MODULE_PAGE, "ebdd_layout_component", component_key, 'type="NList"', {"page_id": {"$ref": page_key}, "type": "NList", "config": {"filter": "old"}}),
        object_record(MODULE_PAGE, "ebdd_layout_component", owner_noise_key, 'type="Bar"', {"page_id": {"$ref": page_key}, "layout_id": {"$ref": "layout-old"}, "type": "Bar"}),
        object_record(MODULE_FORM, "wfp_base", workflow_key, "工时填报", {"workflowname": "工时填报"}),
        object_record(MODULE_FORM, "wfp_node", node_key, "档案组录入", {"nodename": "档案组录入"}),
        object_record(MODULE_FORM, "wfp_cpt_base", cpt_base_key, "节点后校验设置", {
            "workflowid": {"$unresolvedId": "NUMERIC"},
            "nodeid": {"$ref": node_key},
            "opennodecheck": 1,
        }),
        object_record(MODULE_FORM, "wfr_mapbase", old_condition_key, "旧条件", {
            "conditioncn": "((店铺是否直销区 大于 '0') AND (身份 包含 '经销商'))",
        }),
        object_record(MODULE_FORM, "wfr_mapbase", new_condition_key, "新条件", {
            "conditioncn": "((直销区 大于 '0') AND (身份 包含 '经销商'))",
        }),
        object_record(MODULE_FORM, "wfp_cpt_set", retained_rule_key, "非直销区规则（报错的）", {
            "workflowid": {"$unresolvedId": "NUMERIC"},
            "cptbaseid": {"$ref": cpt_base_key},
            "conditionkey": {"$ref": old_condition_key},
            "rulename": "非直销区规则（报错的）",
            "rulenopasstip": "非直销区的经销商不允许提交。",
            "is_open": 0,
            "non_compliance": 0,
        }),
        object_record(MODULE_FORM, "wfp_cpt_set", removed_rule_key, "非直销区规则", {
            "workflowid": {"$unresolvedId": "NUMERIC"},
            "cptbaseid": {"$ref": cpt_base_key},
            "conditionkey": {"$ref": new_condition_key},
            "rulename": "非直销区规则",
            "rulenopasstip": "非直销区的经销商不允许提交。",
            "is_open": 1,
            "non_compliance": 0,
        }),
        object_record(MODULE_FORM, "wfp_context", context_key, "所属店铺流程参数", {
            "workflowid": {"$unresolvedId": "NUMERIC"},
        }),
        object_record(MODULE_FORM, "dataset", old_dataset_key, "工作流 SQL 数据源", {
            "source_module": "workflow",
            "dataset_type": "out_sql_tool",
            "dataset_sql": {
                "fields": [{
                    "name": {"$ref": context_key}, "showname": "所属店铺", "usage": "query",
                }],
                "fieldAlias": [{"name": "total", "type": "undefined,undefined", "usage": "measure"}],
                "sql": "select\n count(1) as total from business_source where enabled='Y' and shop=substring([${1230026196365860865}],3,2)",
                "sourceDBTypeList": [], "sourceSql": {}, "viewType": "sql",
            },
        }),
    ]
    old_objects[6]["sourceEvidence"]["primaryValueHash"] = "workflow-owner-hash"
    old_objects[8]["unresolvedReferences"] = [{
        "path": "workflowid", "valueHash": "workflow-owner-hash",
    }]
    for index in (11, 12):
        old_objects[index]["sourceEvidence"]["migrationSourceIdHash"] = (
            "retained-rule" if index == 11 else "removed-rule"
        )
    old_objects[13]["sourceEvidence"].update({
        "primaryValueHash": "9f2a0bfbf2b365f0",
    })
    old_objects[13]["unresolvedReferences"] = [{
        "path": "workflowid", "valueHash": "workflow-owner-hash",
    }]
    old_objects[14]["sourceEvidence"]["migrationSourceIdHash"] = "old-dataset-source"
    new_objects = copy.deepcopy(old_objects)
    new_objects = [
        item for item in new_objects
        if item.get("logicalKey") not in {removed_rule_key, old_dataset_key}
    ]
    new_dataset = object_record(MODULE_FORM, "dataset", new_dataset_key, "工作流 SQL 数据源", {
        "source_module": "workflow",
        "dataset_type": "out_sql_tool",
        "dataset_sql": {
            "fields": [{
                "name": {"$ref": context_key}, "showname": "所属店铺", "usage": "query",
            }],
            "fieldAlias": [{"name": "total", "type": "Text", "usage": "measure"}],
            "sql": "select count(1) as total from business_source where enabled = 'Y' and shop = substring([${1230026196365860865}], 3, 2)",
            "sourceDBTypeList": [], "sourceSql": {}, "viewType": "sql",
        },
    })
    new_dataset["sourceEvidence"]["migrationSourceIdHash"] = "new-dataset-source"
    new_objects.append(new_dataset)
    new_retained_rule = next(
        item for item in new_objects if item.get("logicalKey") == retained_rule_key
    )
    old_retained_rule = next(
        item for item in old_objects if item.get("logicalKey") == retained_rule_key
    )
    new_retained_rule["canonical"].update({
        "rulename": "非直销区规则",
        "is_open": 1,
    })
    layout = object_record(MODULE_FORM, "form_layout_multiple", layout_key, "项目基础-CPQ", {
        "form_id": {"$ref": form_key},
        "name": "项目基础-CPQ",
        "is_delete": "0",
        "delete_type": 0,
    })
    new_objects.append(layout)
    layout_component = object_record(MODULE_FORM, "ebdd_layout_component", layout_component_key, 'type="Text"', {
        "layout_id": {"$ref": layout_key},
        "type": "Text",
    })
    new_objects.append(layout_component)
    old_button, new_button = old_objects[2], new_objects[2]
    old_component, new_component = old_objects[4], new_objects[4]
    old_owner_noise, new_owner_noise = old_objects[5], new_objects[5]
    new_button["canonical"]["show_position"] = {"table": ["rightTopDropDown"]}
    new_component["canonical"]["config"]["filter"] = "new"
    new_owner_noise["canonical"]["layout_id"] = {"$ref": "layout-new"}
    scope = object_record(MODULE_FORM, "browser_data_scope", scope_key, "项目任务范围", {
        "business_module": "ebuildercard",
        "scope_info_render": {
            "datas": [{
                "text": "所属项目编码",
                "conditions": {"func": "eq", "value": "工时明细.项目编码"},
            }]
        },
    })
    scope["unresolvedReferences"] = [{
        "field": "business_id",
        "path": "business_id",
        "shape": "NUMERIC_19",
        "valueHash": "workflow-owner-hash",
    }]
    new_objects.append(scope)

    facts = [
        {
            "changeId": "CHG-LAYOUT-COMPONENT-ADDED",
            "changeType": "ADDED",
            "object": layout_component,
            "oldObject": None,
            "beforeHash": None,
            "afterHash": "new-layout-component",
            "before": None,
            "after": layout_component["canonical"],
            "changedPaths": [],
        },
        {
            "changeId": "CHG-PAGE-OWNER-REFERENCE",
            "changeType": "UPDATED",
            "object": new_owner_noise,
            "oldObject": old_owner_noise,
            "beforeHash": "old-owner-reference",
            "afterHash": "new-owner-reference",
            "before": old_owner_noise["canonical"],
            "after": new_owner_noise["canonical"],
            "changedPaths": [{
                "path": "layout_id.$ref",
                "before": "layout-old",
                "after": "layout-new",
                "category": "NAVIGATION_DISPLAY",
                "operation": "VALUE_UPDATED",
            }],
        },
        {
            "changeId": "CHG-LAYOUT-ADDED",
            "changeType": "ADDED",
            "object": layout,
            "oldObject": None,
            "beforeHash": None,
            "afterHash": "new-layout",
            "before": None,
            "after": layout["canonical"],
            "changedPaths": [],
        },
        {
            "changeId": "CHG-BUTTON",
            "changeType": "UPDATED",
            "object": new_button,
            "oldObject": old_button,
            "beforeHash": "old-button",
            "afterHash": "new-button",
            "before": old_button["canonical"],
            "after": new_button["canonical"],
            "changedPaths": [{
                "path": "show_position.table",
                "before": None,
                "after": ["rightTopDropDown"],
                "category": "DATA_SEMANTICS",
                "operation": "FIELD_ADDED",
            }],
        },
        {
            "changeId": "CHG-WORKFLOW-SCOPE",
            "changeType": "ADDED",
            "object": scope,
            "oldObject": None,
            "beforeHash": None,
            "afterHash": "new-workflow-scope",
            "before": None,
            "after": scope["canonical"],
            "changedPaths": [],
        },
        {
            "changeId": "CHG-COMPONENT",
            "changeType": "UPDATED",
            "object": new_component,
            "oldObject": old_component,
            "beforeHash": "old-component",
            "afterHash": "new-component",
            "before": old_component["canonical"],
            "after": new_component["canonical"],
            "changedPaths": [{
                "path": "config.filter",
                "before": "old",
                "after": "new",
                "category": "FUNCTION_BEHAVIOR",
                "operation": "VALUE_UPDATED",
            }],
        },
        {
            "changeId": "CHG-NODE-VALIDATION-RETAINED",
            "changeType": "UPDATED",
            "object": new_retained_rule,
            "oldObject": old_retained_rule,
            "beforeHash": "old-retained-rule",
            "afterHash": "new-retained-rule",
            "before": old_retained_rule["canonical"],
            "after": new_retained_rule["canonical"],
            "changedPaths": [
                {
                    "path": "rulename",
                    "before": "非直销区规则（报错的）",
                    "after": "非直销区规则",
                    "category": "FUNCTION_BEHAVIOR",
                    "operation": "VALUE_UPDATED",
                },
                {
                    "path": "is_open",
                    "before": 0,
                    "after": 1,
                    "category": "FUNCTION_BEHAVIOR",
                    "operation": "VALUE_UPDATED",
                },
            ],
        },
        {
            "changeId": "CHG-NODE-VALIDATION-REMOVED",
            "changeType": "REMOVED",
            "object": old_objects[12],
            "oldObject": old_objects[12],
            "beforeHash": "old-removed-rule",
            "afterHash": None,
            "before": old_objects[12]["canonical"],
            "after": None,
            "changedPaths": [],
        },
        {
            "changeId": "CHG-WORKFLOW-SQL-DATASET-REMOVED",
            "changeType": "REMOVED",
            "object": old_objects[14],
            "oldObject": old_objects[14],
            "beforeHash": "old-sql-dataset",
            "afterHash": None,
            "before": old_objects[14]["canonical"],
            "after": None,
            "changedPaths": [],
        },
        {
            "changeId": "CHG-WORKFLOW-SQL-DATASET-ADDED",
            "changeType": "ADDED",
            "object": new_dataset,
            "oldObject": None,
            "beforeHash": None,
            "afterHash": "new-sql-dataset",
            "before": None,
            "after": new_dataset["canonical"],
            "changedPaths": [],
        },
    ]
    analysis = {
        "analysisDirection": {"directionSource": "EXPLICIT_ARGUMENTS"},
        "featureChanges": [],
        "unknownItems": [],
        "identityResolution": {},
    }
    model = build_business_object_diff(
        old_metadata={"name": "old.zip", "role": "old", "sha256": "old"},
        new_metadata={"name": "new.zip", "role": "new", "sha256": "new"},
        old_index={"objects": old_objects, "package": {}},
        new_index={"objects": new_objects, "package": {}},
        facts=facts,
        analysis=analysis,
    )
    report, scenarios = render_report(model, analysis)
    model["testScenarios"] = scenarios
    form = next(item for item in model["objects"] if item["objectType"] == "FORM")
    page = next(item for item in model["objects"] if item["objectType"] == "PAGE")
    workflow_object = next(item for item in model["objects"] if item["objectType"] == "WORKFLOW")
    assert form["changeType"] == "UPDATED"
    assert page["changeType"] == "UPDATED"
    assert workflow_object["changeType"] == "UPDATED"
    assert workflow_object["oldSummary"]["browserDataScopeCount"] == 0
    assert workflow_object["newSummary"]["browserDataScopeCount"] == 1
    assert any(item.get("kind") == "BROWSER_DATA_SCOPE_ADDED" for item in workflow_object["internalChanges"])
    assert any(item.get("changeId") == "CHG-WORKFLOW-SCOPE" for item in workflow_object["internalChanges"])
    node_validation = next(
        item for item in workflow_object["internalChanges"]
        if item.get("kind") == "NODE_POST_VALIDATION_CHANGED"
    )
    assert node_validation["nodeName"] == "档案组录入"
    assert node_validation["oldRuleCount"] == 2
    assert node_validation["newRuleCount"] == 1
    assert node_validation["oldEnabledCount"] == 1
    assert node_validation["newEnabledCount"] == 1
    assert "直销区" in node_validation["effectiveBefore"][0]["condition"]
    assert "店铺是否直销区" in node_validation["effectiveAfter"][0]["condition"]
    assert "“档案组录入”节点后校验" in report
    assert "有效校验条件由" in report
    sql_datasource = next(
        item for item in workflow_object["internalChanges"]
        if item.get("kind") == "WORKFLOW_SQL_DATASOURCE_CHANGED"
    )
    assert sql_datasource["identityConclusion"] == "RECREATED_OR_REBOUND"
    assert sql_datasource["querySemanticsChanged"] is False
    assert sql_datasource["before"]["staticChecks"]["parametersResolved"] is True
    assert sql_datasource["after"]["staticChecks"]["readOnlyQuery"] is True
    assert sql_datasource["before"]["outputTypes"] == ["未明确"]
    assert sql_datasource["after"]["outputTypes"] == ["文本"]
    workflow_change_text = _change_text(workflow_object)
    assert "查询逻辑一致" in workflow_change_text
    assert "数据集记录不是同源记录" in workflow_change_text
    panorama_delta = workflow_post_validation_delta(
        {"workflows": ["workflow:hours"]},
        {"workflows": ["workflow:hours"]},
        {"workflowMap": {"workflow:hours": {"name": "工时填报"}}},
        {"workflowMap": {"workflow:hours": {"name": "工时填报"}}},
        {"工时填报": [node_validation]},
    )
    assert panorama_delta
    assert "档案组录入节点" in panorama_delta["delta"]["added"][0]
    assert "店铺是否直销区" in panorama_delta["delta"]["added"][0]
    assert "直销区" in panorama_delta["delta"]["removed"][0]
    sql_panorama_delta = workflow_sql_datasource_delta(
        {"workflows": ["workflow:hours"]},
        {"workflows": ["workflow:hours"]},
        {"workflowMap": {"workflow:hours": {"name": "工时填报"}}},
        {"workflowMap": {"workflow:hours": {"name": "工时填报"}}},
        {"工时填报": [sql_datasource]},
    )
    assert sql_panorama_delta
    assert "疑似重建或重新绑定" in sql_panorama_delta["delta"]["added"][0]
    assert "输出类型：文本" in sql_panorama_delta["delta"]["added"][0]
    assert model["childChangeCoverage"] == {
        "valid": True,
        "complete": True,
        "expected": 7,
        "rolledUp": 7,
        "unresolved": [],
        "blockingMissing": [],
        "ignoredEquivalentPossibleRename": 0,
        "byTable": {
            "browser_data_scope": {"expected": 1, "rolledUp": 1},
            "ebdd_layout_component": {"expected": 2, "rolledUp": 2},
            "ebdf_button": {"expected": 1, "rolledUp": 1},
            "form_layout_multiple": {"expected": 1, "rolledUp": 1},
            "wfp_cpt_set": {"expected": 2, "rolledUp": 2},
        },
    }
    assert any(item.get("changeId") == "CHG-BUTTON" for item in form["internalChanges"])
    assert any(item.get("kind") == "FORM_LAYOUT_ADDED" and "项目基础-CPQ" in item.get("items", []) for item in form["internalChanges"])
    assert "新增布局：项目基础-CPQ" in report
    assert "“项目基础-CPQ”布局：新增文本组件×1" in report
    assert any(item.get("changeId") == "CHG-COMPONENT" for item in page["internalChanges"])
    assert not any(item.get("changeId") == "CHG-PAGE-OWNER-REFERENCE" for item in page["internalChanges"])
    assert "个性化设置" in report and "右上角下拉菜单" in report
    assert "项目首页" in report and "old → new" in report
    assert "留白仅用于保持报告章节间距" not in report
    assert 'type="' not in report and "内容摘要 " not in report
    assert validate_quantity(model)["result"] == "PASS"
    assert validate_readability(report, model, scenarios)["result"] == "PASS"
    order_only_form = {
        "objectType": "FORM",
        "businessName": "AI应用设置",
        "internalChanges": [
            {
                "kind": "CHILD_CONFIGURATION_CHANGE",
                "itemName": name,
                "table": "ebdf_button",
                "fields": [{"path": "show_order", "before": old, "after": new}],
            }
            for name, old, new in (
                ("自助式分析", 1050, 1046),
                ("个性化设置", 999999, 1051),
                ("还原数据", 1047, 1044),
            )
        ],
    }
    assert _form_conclusion(order_only_form) == "调整 3 个按钮或功能入口的显示顺序"
    assert _form_impact(order_only_form) == "影响按钮排列，不改变功能数量"
    assert "1050" not in json.dumps(_form_detail_rows(order_only_form), ensure_ascii=False)
    summary_form = {
        "objectType": "FORM",
        "businessName": "项目基础",
        "internalChanges": [
            {"kind": "FORM_LAYOUT_ADDED", "items": ["项目基础-CPQ"]},
            {"kind": "LIST", "oldCount": 4, "newCount": 5},
            {
                "kind": "FORM_LAYOUT_COMPONENTS_CHANGED",
                "layoutName": "项目基础",
                "added": {"ColumnTwo": 4, "InternalContainer": 10},
                "removed": {"ColumnTwo": 4, "InternalContainer": 9},
                "updatedCount": 0,
            },
        ],
    }
    assert _form_conclusion(summary_form) == "新增“项目基础-CPQ”布局；重新编排“项目基础”布局；列表配置增加 1 项"
    assert any(row[1] == "结构重排" for row in _form_detail_rows(summary_form))
    assert _form_conclusion(summary_form).split("；")[:3] == [
        "新增“项目基础-CPQ”布局", "重新编排“项目基础”布局", "列表配置增加 1 项"
    ]
    readable_page = {
        "objectType": "PAGE",
        "businessName": "外勤打卡",
        "internalChanges": [
            {"kind": "COMPONENT_ADDED", "items": ["TextArea", "NList"]},
            {"kind": "COMPONENT_REMOVED", "items": ["Drawer"]},
            {
                "kind": "CHILD_CONFIGURATION_CHANGE",
                "itemName": "页面按钮",
                "table": "ebdd_layout_component",
                "fields": [{"path": "config.eventGroup", "before": {"truncated": True, "length": 1067, "sha256": "old"}, "after": {"truncated": True, "length": 1067, "sha256": "new"}}],
            },
            {
                "kind": "CHILD_CONFIGURATION_CHANGE",
                "changeType": "ADDED",
                "itemName": 'type="Text"',
                "table": "ebdd_layout_component",
                "fields": [{"path": "record", "before": None, "after": {"type": "Text"}}],
            },
        ],
    }
    assert _page_conclusion(readable_page) == "页面结构与组件编排调整（涉及交互/跳转）"
    assert "新增多行文本组件×1、列表组件×1、文本组件×1" in _page_specific_change(readable_page)
    assert "配置内容（长度" not in json.dumps(_page_detail_rows(readable_page), ensure_ascii=False)
    assert "影响页面展示布局和操作区域" in _page_impact(readable_page)
    readable_flow = {
        "objectType": "ESB_ACTION_FLOW",
        "businessName": "保存必填校验",
        "internalChanges": [
            {"kind": "NODE_SET", "oldCount": 6, "newCount": 6, "addedComponents": [], "removedComponents": []},
            {"kind": "FORMULA_CHANGE", "factCount": 0},
            {"kind": "MAPPING_CHANGE", "factCount": 0},
            {"kind": "CHILD_CONFIGURATION_CHANGE", "itemName": "终止", "table": "esb_flow_action", "fields": [{"path": "config", "before": "old", "after": "new"}]},
            {"kind": "CHILD_CONFIGURATION_CHANGE", "itemName": "终止", "table": "esb_flow_action", "fields": [{"path": "config", "before": "old2", "after": "new2"}]},
        ],
    }
    assert _flow_conclusion(readable_flow) == "节点结构不变，节点参数调整"
    assert _flow_nodes(readable_flow) == "终止"
    assert _flow_impact(readable_flow) == "可能影响校验失败后的终止处理"
    flow_details = json.dumps(_flow_detail_rows(readable_flow), ensure_ascii=False)
    assert "公式事实 0" not in flow_details and "映射事实 0" not in flow_details and "6→6" not in flow_details

    esb_action = object_record(
        "weaver-esb-setting-service",
        "esb_flow_action",
        'weaver-esb-setting-service::esb_flow_action::type="Output"',
        "终止",
        {"type": "Output", "display_order": 1},
    )
    owner_only = {
        "changeId": "CHG-ESB-OWNER-ONLY",
        "changeType": "UPDATED",
        "object": esb_action,
        "oldObject": esb_action,
        "before": {"data_id": {"$ref": "service::esb_component_output::parent=old"}},
        "after": {"data_id": {"$ref": "service::esb_enquiryform::parent=new"}},
        "changedPaths": [{
            "path": "data_id.$ref",
            "before": "service::esb_component_output::parent=old",
            "after": "service::esb_enquiryform::parent=new",
            "operation": "VALUE_UPDATED",
        }],
    }
    instance_recreated = {
        "changeId": "CHG-ESB-INSTANCE-RECREATED",
        "changeType": "ADDED",
        "object": esb_action,
        "oldObject": None,
        "before": None,
        "after": esb_action["canonical"],
        "changedPaths": [],
    }
    display_order_changed = copy.deepcopy(owner_only)
    display_order_changed.update({
        "changeId": "CHG-ESB-DISPLAY-ORDER",
        "before": {"display_order": 1},
        "after": {"display_order": 2},
        "changedPaths": [{
            "path": "display_order",
            "before": 1,
            "after": 2,
            "operation": "VALUE_UPDATED",
        }],
    })
    assert _flow_business_children([owner_only, instance_recreated]) == []
    assert _flow_business_children([display_order_changed]) == [display_order_changed]

    removed_flow = {
        "objectType": "ESB_ACTION_FLOW",
        "businessName": "月报新建验证",
        "internalChanges": [{
            "kind": "NODE_SET",
            "oldCount": 4,
            "newCount": 0,
            "addedComponents": [],
            "removedComponents": ["Condition", "EnquiryForm", "Output", "PageInteraction"],
        }],
    }
    expected_components = (
        "删除条件判断组件×1、表单/数据源查询组件×1、"
        "输出组件×1、页面交互组件×1"
    )
    assert expected_components in _change_text(removed_flow)
    assert expected_components in _flow_specific_change(removed_flow)
    print(json.dumps({
        "status": "PASS",
        "formChildUpdateRolledUp": True,
        "pageChildUpdateRolledUp": True,
        "workflowScopeChildUpdateRolledUp": True,
        "workflowNodePostValidationRolledUp": True,
        "workflowNodePostValidationInPanorama": True,
        "workflowSqlDatasourceRolledUp": True,
        "workflowSqlDatasourceInPanorama": True,
        "knownChildChangeCoverage": "7/7",
        "beforeAfterVisible": True,
        "artificialPaddingAbsent": True,
        "standardLibraryOnly": True,
        "formSummaryThenEvidence": True,
        "buttonOrderValuesCollapsed": True,
        "pageSummaryThenEvidence": True,
        "flowSummaryThenEvidence": True,
        "flowTechnicalNoiseSuppressed": True,
        "flowComponentsLocalizedWithSuffix": True,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
