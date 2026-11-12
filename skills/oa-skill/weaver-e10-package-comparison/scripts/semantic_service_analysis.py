#!/usr/bin/env python3
"""AI 应用与 Workflow PathDef 的专用语义解析。"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict

from ir_common import first_value, logical_key, redact, sid, slug, source_ref


AI_SERVICE = "weaver-ai-application-service"
WORKFLOW_SERVICE = "weaver-workflow-pathdef-service"


def records_any(ir, table):
    """返回表的全部包内记录，并保留其物理服务容器。"""
    result = []
    for container_service, module in ir.get("modules", {}).items():
        payload = module.get("tables", {}).get(table)
        if not payload:
            continue
        for record in payload.get("records", []):
            result.append((container_service, record))
    return result


def rows(ir, table):
    return [record for _, record in records_any(ir, table)]


def group(rows_, *fields):
    result = defaultdict(list)
    for row in rows_:
        value = sid(first_value(row, *fields))
        if value:
            result[value].append(row)
    return result


def compact_rows(rows_, fields):
    return [
        {key: redact(row.get(key)) for key in fields if row.get(key) is not None}
        for row in rows_
    ]


def _scope_render(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _scope_conditions(value):
    operator_labels = {
        "eq": "等于",
        "neq": "不等于",
        "aggregate": "属于",
        "contains": "包含",
        "notcontains": "不包含",
        "gt": "大于",
        "gte": "大于等于",
        "lt": "小于",
        "lte": "小于等于",
    }
    result = []

    def walk(node):
        if isinstance(node, dict):
            condition = node.get("conditions")
            if isinstance(condition, dict):
                config = node.get("config") if isinstance(node.get("config"), dict) else {}
                field = first_value(node, "text", default=None) or first_value(
                    config, "title", "dataKey", "columnName", default="筛选字段"
                )
                operator = str(condition.get("func") or "条件")
                value_ = condition.get("value")
                custom_values = condition.get("customBrowserValue")
                if isinstance(custom_values, list) and custom_values:
                    selected = custom_values[0]
                    if isinstance(selected, dict) and selected.get("location") and selected.get("content"):
                        value_ = f"{selected['location']}.{selected['content']}"
                if value_ not in (None, ""):
                    result.append({
                        "field": str(field),
                        "operator": operator_labels.get(operator.lower(), operator),
                        "value": str(value_),
                    })
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(_scope_render(value))
    seen = set()
    unique = []
    for item in result:
        marker = (item["field"], item["operator"], item["value"])
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(item)
    return unique


def _workflow_browser_scope(row, field_by_id):
    field = field_by_id.get(sid(row.get("control_id")), {})
    control_name = first_value(field, "title", "field_name", "name", default="流程浏览字段")
    control_key = first_value(field, "data_key", "field_key", default=None)
    conditions = _scope_conditions(row.get("scope_info_render"))
    condition_parts = [
        f"{item['field']}{item['operator']}{item['value']}" for item in conditions
    ]
    if len(condition_parts) > 1:
        condition_text = "组合条件（逻辑关系见对象明细）：" + "；".join(condition_parts)
    else:
        condition_text = condition_parts[0] if condition_parts else "按保存的数据范围条件过滤"
    return {
        "controlName": control_name,
        "controlDataKey": control_key,
        "browserType": first_value(row, "browser_type", default="未标注浏览类型"),
        "scopeType": first_value(row, "scope_type", default="未标注范围类型"),
        "conditions": conditions,
        "businessDescription": f"{control_name}：{condition_text}",
    }


def _dependency(key, from_key, kind, table, record_id, target, status="unresolved"):
    return {
        "logicalKey": key,
        "from": from_key,
        "to": None,
        "kind": kind,
        "status": status,
        "sourceTarget": target,
        "sourceRef": source_ref(AI_SERVICE, table, record_id),
    }


def build_ai_applications(ir):
    roots = rows(ir, "ai_application_config")
    if not roots:
        return [], [], [], []

    direct_tables = {
        "contexts": "ai_application_context",
        "initMessages": "ai_app_init_msg_config",
        "knowledge": "ai_app_knowlege_config",
        "memories": "ai_memory_var_config",
        "memoryExpiry": "ai_memory_expire_config",
        "memoryFragments": "ai_memory_fragment_config",
        "memoryFields": "ai_memory_fragment_cus_fields",
        "promptVariables": "ai_app_prompt_variable",
        "home": "ai_app_home_config",
        "accessLimits": "ai_app_access_limit",
        "customConfig": "ai_app_custom_config",
        "guides": "ai_app_guide_config",
        "notices": "ai_app_notice_config",
        "otherConfig": "ai_app_other_config",
        "mcp": "ai_app_mcp_config",
        "files": "ai_file_upload_config",
        "fileParsing": "ai_file_parse_method_config",
        "sensitiveRules": "ai_sensitive_config",
        "authorization": "ai_authconfig",
        "subAgents": "ai_sub_agent_config",
    }
    grouped = {name: group(rows(ir, table), "application_id", "applicationId") for name, table in direct_tables.items()}
    models = group(rows(ir, "ai_model_app"), "appid", "app_id", "application_id")
    functions_by_subapp = group(rows(ir, "ai_function_config"), "sub_application_id", "application_id")
    multi_data = group(rows(ir, "ai_multi_data"), "application_id", "appid")
    prompt_options = group(rows(ir, "ai_app_prompt_var_option"), "var_id")
    cross_by_id = {sid(x.get("id")): x for x in rows(ir, "ai_app_cross_config")}
    vector_by_id = {sid(x.get("id")): x for x in rows(ir, "ai_vertor_data_group")}
    context_by_id = {sid(x.get("id")): x for x in rows(ir, "ai_chat_context_config")}
    functions_by_id = {sid(x.get("id")): x for x in rows(ir, "ai_function_config")}

    applications, dependencies, integrations, unresolved = [], [], [], []
    used = set()
    for root in roots:
        source_id = sid(root.get("id"))
        name = first_value(root, "app_name", "appName", "name", default="未命名 AI 应用")
        stable = first_value(root, "app_unique_key", "appUniqueKey", default=name)
        key = logical_key("ai-application", stable=stable)
        if key in used:
            key = f"{key}-{slug(source_id, 'source')}"
        used.add(key)

        sections = {section: list(mapping.get(source_id, [])) for section, mapping in grouped.items()}
        contexts = list(sections.pop("contexts", []))
        context_ref = sid(first_value(root, "context_id", "contextId"))
        if context_ref and context_ref in context_by_id:
            contexts.append(context_by_id[context_ref])
        functions = list(functions_by_subapp.get(source_id, []))
        function_ids = {sid(x.get("id")) for x in functions}
        for item in multi_data.get(source_id, []):
            value = sid(first_value(item, "datavalue", "data_value", "value"))
            if value in functions_by_id and value not in function_ids:
                functions.append(functions_by_id[value])
                function_ids.add(value)

        prompt_variables = []
        for variable in sections.pop("promptVariables", []):
            var_id = sid(variable.get("id"))
            default_value = first_value(variable, "def_value", "default_value", "defaultValue")
            hidden_id_risk = bool(isinstance(default_value, str) and re.search(r"(?<!\d)\d{16,}(?!\d)", default_value))
            prompt_variables.append({
                "sourceId": var_id,
                "key": first_value(variable, "var_key", "variable_key", "key"),
                "name": first_value(variable, "var_name", "variable_name", "name"),
                "type": first_value(variable, "var_type", "type"),
                "required": first_value(variable, "required", "is_required"),
                "defaultValue": redact(default_value),
                "optionCount": len(prompt_options.get(var_id, [])),
                "embeddedSourceIdRisk": hidden_id_risk,
            })
            if hidden_id_risk:
                unresolved.append({
                    "kind": "ai-prompt-default-embedded-source-id",
                    "service": AI_SERVICE,
                    "table": "ai_app_prompt_variable",
                    "sourceId": var_id,
                    "status": "UNRESOLVED",
                    "reason": "def_value 是不透明文本；迁入处理器没有确认其中嵌入 ID 的专用替换逻辑。",
                })

        knowledge = []
        for item in sections.pop("knowledge", []):
            vector_id = sid(first_value(item, "data_group_id", "vector_group_id", "group_id"))
            cross_id = sid(first_value(item, "cross_config_id", "crossConfigId"))
            knowledge.append({
                "sourceId": sid(item.get("id")),
                "name": first_value(item, "knowledge_name", "name", "title"),
                "type": first_value(item, "knowledge_type", "type"),
                "vectorGroup": redact(vector_by_id.get(vector_id, {})),
                "crossConfig": redact(cross_by_id.get(cross_id, {})),
                "configuration": redact(item),
            })

        normalized_functions = []
        for function in functions:
            function_id = sid(function.get("id"))
            action_id = sid(first_value(function, "action_id", "actionId"))
            eb_app_id = sid(first_value(function, "eb_app_id", "ebAppId"))
            sub_app_id = sid(first_value(function, "sub_application_id", "subApplicationId"))
            normalized_functions.append({
                "sourceId": function_id,
                "name": first_value(function, "function_name", "fun_name", "name", default="未命名函数"),
                "type": first_value(function, "function_type", "type"),
                "actionFlowSourceId": action_id,
                "eBuilderApplicationSourceId": eb_app_id,
                "subApplicationSourceId": sub_app_id,
                "enabled": first_value(function, "enable", "status", "enabled"),
                "configuration": redact(function),
            })
            if action_id:
                dependencies.append(_dependency(
                    f"dependency:{slug(key)}:ai-function-action:{slug(function_id, 'source')}",
                    key, "ai-function-action-flow", "ai_function_config", function_id,
                    {"actionFlowSourceId": action_id},
                ))
            if eb_app_id:
                dependencies.append(_dependency(
                    f"dependency:{slug(key)}:ai-function-eb-app:{slug(function_id, 'source')}",
                    key, "ai-function-ebuilder-application", "ai_function_config", function_id,
                    {"eBuilderApplicationSourceId": eb_app_id},
                ))

        for config in sections.get("initMessages", []):
            for field, kind in (
                ("q_source_action_id", "ai-question-source-action-flow"),
                ("guide_esb_id", "ai-guide-action-flow"),
                ("input_guide_esb_id", "ai-input-guide-action-flow"),
            ):
                target_id = sid(config.get(field))
                if target_id and target_id not in {"0", "-1"}:
                    dependencies.append(_dependency(
                        f"dependency:{slug(key)}:{slug(kind)}:{slug(config.get('id'), 'source')}",
                        key, kind, "ai_app_init_msg_config", config.get("id"),
                        {"actionFlowSourceId": target_id, "sourceField": field},
                    ))

        integration_refs = []
        for section in ("mcp",):
            for item in sections.get(section, []):
                integration_key = f"integration:{slug(key)}:{section}:{slug(item.get('id'), 'source')}"
                integration_refs.append(integration_key)
                integrations.append({
                    "logicalKey": integration_key,
                    "name": first_value(item, "name", "mcp_name", "server_name", default="AI MCP 配置"),
                    "type": "ai-mcp",
                    "aiApplicationRef": key,
                    "configuration": redact(item),
                    "sourceRef": source_ref(AI_SERVICE, direct_tables[section], item.get("id")),
                })

        applications.append({
            "logicalKey": key,
            "name": name,
            "uniqueKey": first_value(root, "app_unique_key", "appUniqueKey"),
            "type": first_value(root, "app_type", "appType"),
            "configType": first_value(root, "config_type", "configType"),
            "status": first_value(root, "app_status", "status"),
            "scene": root.get("scene"),
            "eBuilderApplicationSourceId": sid(first_value(root, "eb_app_id", "ebAppId")),
            "modelBindings": [redact(x) for x in models.get(source_id, [])],
            "contexts": [redact(x) for x in contexts],
            "promptVariables": prompt_variables,
            "knowledge": knowledge,
            "functions": normalized_functions,
            "memory": {
                "variables": [redact(x) for x in sections.get("memories", [])],
                "expiry": [redact(x) for x in sections.get("memoryExpiry", [])],
                "fragments": [redact(x) for x in sections.get("memoryFragments", [])],
                "customFields": [redact(x) for x in sections.get("memoryFields", [])],
            },
            "initialExperience": [redact(x) for x in sections.get("initMessages", [])],
            "home": [redact(x) for x in sections.get("home", [])],
            "accessLimits": [redact(x) for x in sections.get("accessLimits", [])],
            "files": [redact(x) for x in sections.get("files", [])],
            "fileParsing": [redact(x) for x in sections.get("fileParsing", [])],
            "sensitiveRules": [redact(x) for x in sections.get("sensitiveRules", [])],
            "authorization": [redact(x) for x in sections.get("authorization", [])],
            "subAgents": [redact(x) for x in sections.get("subAgents", [])],
            "integrationRefs": integration_refs,
            "migrationSemantics": {
                "importedDisabled": True,
                "modelBindingDeduplicatedByApplication": True,
                "functionIdsRecoveredFromMultiData": True,
                "cacheResetAfterImport": True,
            },
            "sourceRef": source_ref(AI_SERVICE, "ai_application_config", source_id),
        })
    return applications, integrations, dependencies, unresolved


def build_workflow_pathdefs(ir, form_source_map=None):
    bases = rows(ir, "wfp_base")
    if not bases:
        return [], {}, [], []
    form_source_map = form_source_map or {}
    by_fixed = group(bases, "fixed_version_id", "id")
    nodes_by_wf = group(rows(ir, "wfp_node"), "workflowid", "workflow_id")
    links_by_wf = group(rows(ir, "wfp_link"), "workflowid", "workflow_id")
    menus_by_wf = group(rows(ir, "wfp_node_menu"), "workflowid", "workflow_id")
    actions_by_wf = group(rows(ir, "wfp_add_action"), "workflowid", "workflow_id")
    auth_by_wf = group(rows(ir, "wfp_auth"), "workflowid", "workflow_id")
    charts_by_wf = group(rows(ir, "wfp_chart"), "workflowid", "workflow_id")
    relate_forms_by_wf = group(rows(ir, "wfp_relateform"), "workflowid", "workflow_id")
    node_forms_by_wf = group(rows(ir, "wfp_node_form_relate"), "workflowid", "workflow_id")
    operator_groups_by_wf = group(rows(ir, "wfp_opt_group"), "workflowid", "workflow_id")
    operators_by_wf = group(rows(ir, "wfp_opt_operator"), "workflowid", "workflow_id")
    subflows_by_wf = group(rows(ir, "wfp_subsetdetail"), "workflowid", "workflow_id")
    variables_by_wf = group(rows(ir, "wfp_variables"), "workflowid", "workflow_id")
    bindings_by_wf = group(rows(ir, "ebdf_app_ref_workflow"), "workflowid")
    browser_scopes_by_wf = group(rows(ir, "browser_data_scope"), "business_id")
    field_by_id = {sid(row.get("id")): row for row in rows(ir, "form_field") if sid(row.get("id"))}
    conditions = {sid(x.get("id")): x for x in rows(ir, "wfr_conditionbase")}
    expressions = group(rows(ir, "wfr_expressionbase"), "conditionid", "condition_id")
    values = group(rows(ir, "wfr_valuebase"), "conditionid", "condition_id")

    workflows, source_map, dependencies, unresolved = [], {}, [], []
    used = set()
    for fixed_id, versions in sorted(by_fixed.items()):
        ordered = sorted(versions, key=lambda x: int(first_value(x, "versionid", default=0) or 0))
        active_id = sid(first_value(ordered[-1], "activewfid", default=fixed_id))
        active = next((x for x in ordered if sid(x.get("id")) == active_id), ordered[-1])
        name = first_value(active, "workflowname", "name", default="未命名审批流程")
        key = logical_key("workflow-pathdef", stable=fixed_id or name)
        if key in used:
            key = f"{key}-{slug(active.get('id'), 'source')}"
        used.add(key)
        for version in ordered:
            source_map[sid(version.get("id"))] = key
        source_map[fixed_id] = key

        wf_id = sid(active.get("id"))
        menu_counter = Counter(sid(row.get("nodeid")) for row in menus_by_wf.get(wf_id, []))
        nodes = [{
            "logicalKey": f"{key}/node:{slug(node.get('id'), 'source')}",
            "name": first_value(node, "nodename", "name", default="未命名节点"),
            "type": node.get("nodetype"),
            "attribute": node.get("nodeattr"),
            "order": node.get("orderid"),
            "deleted": str(node.get("delete_type", "0")) in {"1", "true", "True"},
            "menuCount": menu_counter.get(sid(node.get("id")), 0),
            "sourceRef": source_ref(WORKFLOW_SERVICE, "wfp_node", node.get("id")),
        } for node in nodes_by_wf.get(wf_id, [])]

        links = []
        condition_ids = set()
        for link in links_by_wf.get(wf_id, []):
            condition_id = sid(first_value(link, "conditionkey", "condition_key"))
            if condition_id not in {None, "0", "-1"}:
                condition_ids.add(condition_id)
            links.append({
                "sourceId": sid(link.get("id")),
                "name": first_value(link, "linkname", "name"),
                "fromSourceId": sid(first_value(link, "srcnodeid", "source_node_id")),
                "toSourceId": sid(first_value(link, "destnodeid", "target_node_id")),
                "default": first_value(link, "isdefault", "is_default"),
                "reject": first_value(link, "isreject", "is_reject"),
                "conditionSourceId": condition_id,
                "sourceRef": source_ref(WORKFLOW_SERVICE, "wfp_link", link.get("id")),
            })
        normalized_conditions = [{
            "sourceId": condition_id,
            "name": first_value(conditions.get(condition_id, {}), "conditionname", "name"),
            "description": first_value(conditions.get(condition_id, {}), "conditiondesc", "conditioncn"),
            "expressionCount": len(expressions.get(condition_id, [])),
            "valueCount": len(values.get(condition_id, [])),
            "configuration": redact(conditions.get(condition_id, {})),
        } for condition_id in sorted(condition_ids)]

        for variable in variables_by_wf.get(wf_id, []):
            form_id = sid(first_value(variable, "ebuilder_sform_id", "ebuilderSformId"))
            if not form_id or form_id in {"0", "-1"}:
                continue
            resolved = form_source_map.get(form_id)
            dependencies.append({
                "logicalKey": f"dependency:{slug(key)}:workflow-variable-form:{slug(variable.get('id'), 'source')}",
                "from": key,
                "to": resolved,
                "kind": "workflow-variable-ebuilder-form",
                "status": "resolved" if resolved else "unresolved",
                "sourceTarget": {"formSourceId": form_id},
                "sourceRef": source_ref(WORKFLOW_SERVICE, "wfp_variables", variable.get("id")),
            })
        for subflow in subflows_by_wf.get(wf_id, []):
            target_id = sid(first_value(subflow, "subWfId", "sub_wf_id", "subwfid"))
            if target_id and target_id not in {"0", "-1"}:
                dependencies.append({
                    "logicalKey": f"dependency:{slug(key)}:sub-workflow:{slug(subflow.get('id'), 'source')}",
                    "from": key,
                    "to": None,
                    "kind": "workflow-subflow",
                    "status": "unresolved",
                    "sourceTarget": {"workflowSourceId": target_id},
                    "sourceRef": source_ref(WORKFLOW_SERVICE, "wfp_subsetdetail", subflow.get("id")),
                })

        versions_normalized = []
        for version in ordered:
            version_id = sid(version.get("id"))
            versions_normalized.append({
                "sourceId": version_id,
                "version": version.get("versionid"),
                "status": version.get("status"),
                "active": version_id == active_id,
                "nodeCount": len(nodes_by_wf.get(version_id, [])),
                "linkCount": len(links_by_wf.get(version_id, [])),
            })

        browser_scope_rows = []
        seen_scope_ids = set()
        for owner_id in (fixed_id, active_id, wf_id):
            for scope_row in browser_scopes_by_wf.get(owner_id, []):
                marker = sid(scope_row.get("id")) or repr(scope_row)
                if marker in seen_scope_ids:
                    continue
                seen_scope_ids.add(marker)
                browser_scope_rows.append(scope_row)

        workflows.append({
            "logicalKey": key,
            "name": name,
            "type": "workflow-path-definition",
            "description": first_value(active, "workflowdesc", "description", default=""),
            "fixedVersionSourceId": fixed_id,
            "activeVersionSourceId": active_id,
            "status": active.get("status"),
            "workflowTypeSourceId": sid(active.get("workflowtype")),
            "bridgeService": active.get("bridge_service"),
            "versions": versions_normalized,
            "nodes": nodes,
            "links": links,
            "conditions": normalized_conditions,
            "operatorGroups": [redact(x) for x in operator_groups_by_wf.get(wf_id, [])],
            "operators": [redact(x) for x in operators_by_wf.get(wf_id, [])],
            "actions": [redact(x) for x in actions_by_wf.get(wf_id, [])],
            "authorization": [redact(x) for x in auth_by_wf.get(wf_id, [])],
            "charts": [redact(x) for x in charts_by_wf.get(wf_id, [])],
            "relatedForms": [redact(x) for x in relate_forms_by_wf.get(wf_id, [])],
            "nodeFormBindings": [redact(x) for x in node_forms_by_wf.get(wf_id, [])],
            "applicationBindings": [redact(x) for x in bindings_by_wf.get(wf_id, [])],
            "browserDataScopes": [
                _workflow_browser_scope(row, field_by_id)
                for row in browser_scope_rows
            ],
            "migrationSemantics": {
                "allVersionsExported": True,
                "versionGroupIdentity": "fixed_version_id",
                "readOnlyGroupsPreserveTargetActiveVersion": True,
                "conflictingActiveVersionsDemotedToHistory": True,
                "hiddenOrganizationReferencesRequireSpecialReplacement": True,
            },
            "sourceRef": source_ref(WORKFLOW_SERVICE, "wfp_base", active.get("id")),
        })

    for dependency in dependencies:
        if dependency.get("kind") != "workflow-subflow":
            continue
        target_id = dependency.get("sourceTarget", {}).get("workflowSourceId")
        resolved = source_map.get(target_id)
        if resolved:
            dependency["to"] = resolved
            dependency["status"] = "resolved"
    return workflows, source_map, dependencies, unresolved
