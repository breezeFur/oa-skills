#!/usr/bin/env python3
"""验证客户报告不会把迁移保存态噪声抬升成业务更新。"""

from __future__ import annotations

import json

from build_business_object_diff import (
    _business_configuration_paths,
    _component_business_name,
    _functional_name,
    _suppress_equivalent_recreated_details,
    build_business_object_diff,
)
from render_detail_diff_report import (
    _customer_target,
    _flow_conclusion,
    _flow_detail_rows,
    _flow_specific_change,
)


ANALYSIS = {
    "analysisDirection": {"directionSource": "EXPLICIT_ARGUMENTS"},
    "featureChanges": [],
    "unknownItems": [],
    "identityResolution": {},
}


def record(module: str, table: str, key: str, name: str, canonical: dict) -> dict:
    return {
        "module": module,
        "table": table,
        "logicalKey": key,
        "displayName": name,
        "canonical": canonical,
        "canonicalHash": key,
        "sourceEvidence": {"recordOrdinal": 1},
    }


def fact(change_id: str, old: dict, new: dict, paths: list[dict]) -> dict:
    return {
        "changeId": change_id,
        "changeType": "UPDATED",
        "object": new,
        "oldObject": old,
        "before": old["canonical"],
        "after": new["canonical"],
        "beforeHash": "old",
        "afterHash": "new",
        "changedPaths": paths,
    }


def build(old_objects: list[dict], new_objects: list[dict], facts: list[dict]) -> dict:
    return build_business_object_diff(
        old_metadata={"name": "old.zip", "role": "old", "sha256": "old"},
        new_metadata={"name": "new.zip", "role": "new", "sha256": "new"},
        old_index={"objects": old_objects, "package": {}},
        new_index={"objects": new_objects, "package": {}},
        facts=facts,
        analysis=ANALYSIS,
    )


def main() -> None:
    menu_key = 'weaver-cusapp-service::t_cus_app_system_menu::idm-lineage=menu'
    old_menu = record(
        "weaver-cusapp-service", "t_cus_app_system_menu", menu_key, "全部流程",
        {"menu_name": "全部流程", "url": "/sp/workflow/list/all?disableNewFlow=1"},
    )
    new_menu = record(
        "weaver-cusapp-service", "t_cus_app_system_menu", menu_key, "全部流程",
        {"menu_name": "全部流程", "url": "/sp/workflow/list/all?disableNewFlow=1", "menu_url": None},
    )
    null_paths = [
        {"path": name, "before": None, "after": None, "operation": "FIELD_ADDED"}
        for name in ("menu_desc", "menu_desc_labelid", "menu_url")
    ]
    menu_model = build([old_menu], [new_menu], [fact("CHG-MENU-NULL", old_menu, new_menu, null_paths)])
    assert not [item for item in menu_model["objects"] if item["objectType"] == "MENU"]
    menu_summary = next(item for item in menu_model["summary"] if item["objectType"] == "MENU")
    assert menu_summary["unchanged"] == 1 and menu_summary["updated"] == 0

    changed_menu = record(
        "weaver-cusapp-service", "t_cus_app_system_menu", menu_key, "全部流程",
        {"menu_name": "全部流程", "url": "/sp/workflow/list/all?disableNewFlow=1", "open_mode": 1},
    )
    open_mode = {"path": "open_mode", "before": 2, "after": 1, "operation": "VALUE_UPDATED"}
    old_menu["canonical"]["open_mode"] = 2
    changed_model = build([old_menu], [changed_menu], [fact("CHG-MENU-MODE", old_menu, changed_menu, [open_mode])])
    changed = next(item for item in changed_model["objects"] if item["objectType"] == "MENU")
    assert changed["changeType"] == "UPDATED"
    assert changed["oldSummary"] == changed["newSummary"]
    assert changed["internalChanges"] == [{
        "kind": "MENU_CONFIGURATION_CHANGE",
        "field": "open_mode",
        "label": "打开方式配置",
        "before": 2,
        "after": 1,
    }]

    flow_key = 'weaver-esb-setting-service::esb_application::idm-lineage=flow'
    old_flow = record(
        "weaver-esb-setting-service", "esb_application", flow_key,
        "DML更新释放时间-联动设置1", {"app_name": "DML更新释放时间-联动设置1"},
    )
    new_flow = record(
        "weaver-esb-setting-service", "esb_application", flow_key,
        "DML更新释放时间-联动设置1(2026-04-03 02:05:47)",
        {"app_name": "DML更新释放时间-联动设置1(2026-04-03 02:05:47)"},
    )
    flow_name_path = {
        "path": "app_name",
        "before": old_flow["displayName"],
        "after": new_flow["displayName"],
        "operation": "VALUE_UPDATED",
    }
    flow_paths = [
        flow_name_path,
        {
            "path": "active_version.$ref",
            "before": "service::esb_action_flow_version::parent=old",
            "after": "service::esb_action_flow_version::parent=new",
            "operation": "VALUE_UPDATED",
        },
        {"path": "special_mark", "before": None, "after": 0, "operation": "FIELD_ADDED"},
        {"path": "type", "before": {"$ref": 'service::esb_application_type::name="UC集成"'}, "after": 0, "operation": "VALUE_UPDATED"},
    ]
    flow_model = build([old_flow], [new_flow], [fact("CHG-FLOW-TIMESTAMP", old_flow, new_flow, flow_paths)])
    flow_summary = next(item for item in flow_model["summary"] if item["objectType"] == "ESB_ACTION_FLOW")
    assert flow_summary["unchanged"] == 1 and flow_summary["updated"] == 0

    status_path = {"path": "status", "before": "start_using", "after": "forbidden", "operation": "VALUE_UPDATED"}
    status_model = build([old_flow], [new_flow], [fact("CHG-FLOW-STATUS", old_flow, new_flow, flow_paths + [status_path])])
    status_flow = next(item for item in status_model["objects"] if item["objectType"] == "ESB_ACTION_FLOW")
    assert status_flow["changeType"] == "UPDATED"
    assert any(change.get("kind") == "FLOW_STATUS_CHANGED" for change in status_flow["internalChanges"])
    assert _flow_conclusion(status_flow) == "动作流启用状态调整"
    assert "启用状态由“启用”调整为“停用”" in _flow_specific_change(status_flow)

    old_diary_flow = record(
        "weaver-esb-setting-service", "esb_application", flow_key,
        "档案-回单文件分割（step2）", {"name": "档案-回单文件分割（step2）"},
    )
    new_diary_flow = record(
        "weaver-esb-setting-service", "esb_application", flow_key,
        "档案-回单文件分割（step2）", {"name": "档案-回单文件分割（step2）", "is_keep_diary": 1},
    )
    diary_path = {"path": "is_keep_diary", "before": None, "after": 1, "operation": "FIELD_ADDED"}
    diary_model = build(
        [old_diary_flow], [new_diary_flow],
        [fact("CHG-FLOW-DIARY", old_diary_flow, new_diary_flow, [diary_path])],
    )
    diary_flow = next(item for item in diary_model["objects"] if item["objectType"] == "ESB_ACTION_FLOW")
    assert diary_flow["changeType"] == "UPDATED"
    assert any(change.get("kind") == "FLOW_ROOT_SETTING_CHANGED" for change in diary_flow["internalChanges"])
    assert _flow_conclusion(diary_flow) == "动作流运行设置调整"
    assert "运行日志留存由“未配置”调整为“开启”" in _flow_specific_change(diary_flow)

    name_only = {
        "internalChanges": [{
            "kind": "NAME_CHANGED", "oldName": "旧名称", "newName": "新名称",
        }],
    }
    assert _flow_conclusion(name_only) == "动作流名称调整"
    assert "名称由" in _flow_specific_change(name_only)
    assert "参数发生变化" not in json.dumps(_flow_detail_rows(name_only), ensure_ascii=False)

    form_key = 'weaver-ebuilder-form-service::form::idm-lineage=form'
    field_key = 'weaver-ebuilder-form-service::form_field::idm-lineage=field'
    old_form = record("weaver-ebuilder-form-service", "form", form_key, "优惠顾客申请（PC）录入", {"name": "优惠顾客申请（PC）录入"})
    new_form = record("weaver-ebuilder-form-service", "form", form_key, "优惠顾客申请（PC）录入", {"name": "优惠顾客申请（PC）录入"})
    old_field = record(
        "weaver-ebuilder-form-service", "form_field", field_key, "省",
        {"form_id": {"$ref": form_key}, "browser_type": "customBrowser_s", "other_properties": {"columnName": "s"}},
    )
    new_field = record(
        "weaver-ebuilder-form-service", "form_field", field_key, "省",
        {"form_id": {"$ref": form_key}, "browser_type": "customBrowser_s_V1253924880434061317", "other_properties": {"columnName": "s_V1253924880434061317"}},
    )
    alias_paths = [
        {"path": "browser_type", "before": "customBrowser_s", "after": "customBrowser_s_V1253924880434061317", "operation": "VALUE_UPDATED"},
        {"path": "other_properties.columnName", "before": "s", "after": "s_V1253924880434061317", "operation": "VALUE_UPDATED"},
        {"path": "other_properties.regular.express", "before": r"^[A-Z\s·]+$", "after": r"^[A-Z\s_V1253924880434061317·]+$", "operation": "VALUE_UPDATED"},
    ]
    field_fact = fact("CHG-FORM-ALIAS", old_field, new_field, alias_paths)
    assert _business_configuration_paths(field_fact) == []
    form_model = build([old_form, old_field], [new_form, new_field], [field_fact])
    form_summary = next(item for item in form_model["summary"] if item["objectType"] == "FORM")
    assert form_summary["unchanged"] == 1 and form_summary["updated"] == 0

    unresolved_template = fact(
        "CHG-TEMPLATE-RESOLUTION", old_field, new_field,
        [
            {"path": "data_template_id.$ref", "before": 'service::template::name="资料审核(2026-03-17 16:17:18)"', "after": None, "operation": "FIELD_REMOVED"},
            {"path": "data_template_id.$unresolvedId", "before": None, "after": "NUMERIC", "operation": "FIELD_ADDED"},
            {"path": "other_properties.fieldId.$ref", "before": 'service::field::name="审核不通过原因"::parent=old', "after": 'service::field::name="审核不通过原因"::parent=new', "operation": "VALUE_UPDATED"},
        ],
    )
    assert _business_configuration_paths(unresolved_template) == []

    truncated_scope = fact(
        "CHG-SCOPE-TRUNCATED", old_field, new_field,
        [{
            "path": "scope_info_render.datas",
            "before": {"length": 2860, "sha256": "old", "summary": "old", "truncated": True},
            "after": {"length": 2644, "sha256": "new", "summary": "new", "truncated": True},
            "operation": "LIST_UPDATED",
        }],
    )
    truncated_scope["object"]["table"] = "browser_data_scope"
    truncated_scope["oldObject"]["table"] = "browser_data_scope"
    assert _business_configuration_paths(truncated_scope) == []

    parent = "same-parent"
    old_scope = record("weaver-ebuilder-form-service", "browser_data_scope", "scope-old", "范围", {"business_id": {"$ref": form_key}, "rule": "same"})
    new_scope = record("weaver-ebuilder-form-service", "browser_data_scope", "scope-new", "范围", {"business_id": {"$ref": form_key}, "rule": "same"})
    old_scope["parentIdentityKey"] = parent
    new_scope["parentIdentityKey"] = parent
    removed = {"changeId": "CHG-SCOPE-REMOVED", "changeType": "UNMATCHED", "object": old_scope, "oldObject": old_scope, "before": old_scope["canonical"], "after": None}
    added = {"changeId": "CHG-SCOPE-ADDED", "changeType": "UNMATCHED", "object": new_scope, "oldObject": None, "before": None, "after": new_scope["canonical"]}
    assert _suppress_equivalent_recreated_details([removed, added]) == []

    assert _functional_name(
        "idm-lineage=39e765ff2f76f0d63d6fb11d", "NAVIGATION"
    ) == "应用导航配置"
    assert _functional_name(
        "undefined_迁出使用关联视图", "EMBEDDED_VIEW"
    ) == "嵌入式业务视图"
    assert _functional_name(
        "档案室综合年报-20260617175058", "REPORT"
    ) == "档案室综合年报"
    assert _component_business_name(
        "idm-context=074c1c13b08dd6f04c2af03d::Select"
    ) == "Select"
    assert _customer_target("idm-lineage=39637e9a1003e12fc25dbc66") == "目标关系待确认"
    assert _customer_target("档案授权页面") == "档案授权页面"

    print(json.dumps({
        "status": "PASS",
        "equivalentNullMenuSuppressed": True,
        "realMenuConfigurationPreserved": True,
        "timestampOnlyActionFlowSuppressed": True,
        "unsupportedFlowFallbackRemoved": True,
        "flowRootBusinessSettingRendered": True,
        "migrationAliasFormNoiseSuppressed": True,
        "equivalentSharedDetailsPaired": True,
        "technicalObjectNamesSanitized": True,
        "generatedNameTimestampsRemoved": True,
        "componentIdentityContextRemoved": True,
        "menuTechnicalTargetSanitized": True,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
