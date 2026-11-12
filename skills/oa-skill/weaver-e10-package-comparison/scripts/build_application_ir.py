#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from ir_common import (
    dump_json,
    first_value,
    load_json,
    logical_key,
    parse_object,
    redact,
    sid,
    slug,
    source_ref,
    table_records,
    unique_by,
)
from service_analysis import analyze_services
from semantic_service_analysis import build_ai_applications, build_workflow_pathdefs


SERVICE_CAPABILITIES = {
    "weaver-ai-application-service": "ai-applications-agents-knowledge",
    "weaver-cusapp-service": "application-shell-navigation-security",
    "weaver-ebuilder-form-service": "forms-data-model",
    "weaver-ebuilder-app-service": "pages-components",
    "weaver-esb-setting-service": "action-flows",
    "weaver-bpm-service": "workflows",
    "weaver-edcreportd-service": "reports",
    "weaver-edcapp-service": "multi-level-filling",
    "weaver-workflow-pathdef-service": "workflow-definitions-runtime-bindings",
}

BUILD_ORDER = [
    "preflight",
    "application-shell-and-roles",
    "data-model-and-forms",
    "action-flows-and-extensions",
    "ai-applications-and-agents",
    "pages-and-navigation",
    "workflows",
    "reports-and-integrations",
    "multi-filling",
    "cusapp-navigation-and-menus",
    "permissions-and-cross-bindings",
    "business-report-and-coverage-validation",
    "verification",
    "publish-after-explicit-authorization",
]


def unique_key(candidate, used, source_id):
    if candidate not in used:
        used.add(candidate)
        return candidate
    revised = f"{candidate}-{slug(source_id, 'source')}"
    used.add(revised)
    return revised


def idm_root_identity_map(ir, service, table, current_ids):
    """Return unique current-record -> hashed .idm lineage for one root table."""
    current_ids = {sid(value) for value in current_ids if sid(value)}
    candidates = defaultdict(list)
    for item in (ir.get("migrationLineage") or {}).get("idmMappings", []):
        if str(item.get("serviceName") or "").lower() != service.lower():
            continue
        if str(item.get("tableName") or "").lower() != table.lower():
            continue
        source = sid(item.get("sourceId"))
        import_id = sid(item.get("importId"))
        export_id = sid(item.get("exportId"))
        import_hit = import_id if import_id in current_ids else None
        export_hit = export_id if export_id in current_ids else None
        if not source or (import_hit and export_hit and import_hit != export_hit):
            continue
        current = import_hit or export_hit
        if current:
            candidates[current].append(item)
    result = {}
    for current, items in candidates.items():
        sources = {sid(item.get("sourceId")) for item in items}
        if len(sources) != 1:
            continue
        source = next(iter(sources))
        scoped = f"{service.lower()}|{table.lower()}|{source}"
        result[current] = {
            "identityMethod": "MIGRATION_IDM_SOURCE_ID",
            "lineageKeyHash": hashlib.sha256(scoped.encode("utf-8")).hexdigest()[:24],
            "lineageEvidencePath": sorted({
                str(item.get("evidencePath")) for item in items
                if item.get("evidencePath")
            })[0],
        }
    return result


def field_item(wrapper, entity_key, service="weaver-ebuilder-form-service"):
    field = wrapper.get("field", wrapper)
    props = parse_object(field.get("other_properties"))
    data_key = field.get("data_key") or field.get("column_name") or sid(field.get("id"))
    key = f"{entity_key}/field:{slug(data_key, 'field')}"
    options = []
    for option_wrapper in wrapper.get("options", []):
        option = option_wrapper.get("option", option_wrapper)
        options.append({
            "label": first_value(option, "name", "show_name", "option_name", "label"),
            "logicalValue": first_value(option, "value", "option_value", "data_value"),
            "sourceId": sid(option.get("id")),
            "enabled": not bool(option.get("delete_type") or option.get("is_delete") == "1"),
        })
    relation = None
    if props.get("sformId") or props.get("formName"):
        relation = {
            "targetSourceId": sid(props.get("sformId")),
            "targetName": props.get("formName"),
            "single": props.get("isSingle", field.get("single")),
        }
    return {
        "logicalKey": key,
        "name": first_value(field, "title", "show_name", default=data_key),
        "dataKey": data_key,
        "component": first_value(field, "component_key", "component_type"),
        "type": field.get("data_type"),
        "required": str(field.get("required", "0")).lower() in {"1", "true"},
        "single": field.get("single"),
        "description": field.get("describe") or "",
        "default": props.get("defaultExtend"),
        "options": options,
        "relation": relation,
        "sourceRef": source_ref(service, "form_field", field.get("id")),
    }


def build_forms(ir):
    indexed = ir.get("indexes", {}).get("ebuilderForms", {}).get("forms", [])
    forms, entities, relations, dependencies, permissions, integrations = [], [], [], [], [], []
    source_to_form, source_to_entity = {}, {}
    used_form_keys, used_entity_keys = set(), set()

    for item in indexed:
        obj, form = item.get("object", {}), item.get("form", {})
        name = first_value(obj, "obj_name", "show_name", default=form.get("name") or "未命名表单")
        stable = obj.get("tag") or name
        form_key = unique_key(logical_key("form", stable=stable), used_form_keys, obj.get("id") or form.get("id"))
        entity_key = unique_key(logical_key("entity", stable=stable), used_entity_keys, obj.get("id") or form.get("id"))
        for value in (obj.get("id"), obj.get("form_id"), form.get("id"), form.get("target_id")):
            if value is not None:
                source_to_form[sid(value)] = form_key
                source_to_entity[sid(value)] = entity_key

        main_fields = [field_item(x, entity_key) for x in item.get("mainFields", [])]
        detail_forms = []
        for sub in item.get("subForms", []):
            base = sub.get("subForm", {})
            sub_name = base.get("title") or "未命名明细"
            sub_data_key = base.get("data_key") or sid(base.get("id"))
            detail_entity_key = f"{entity_key}/detail:{slug(sub_data_key, 'detail')}"
            detail_fields = [field_item(x, detail_entity_key) for x in sub.get("fields", [])]
            detail_forms.append({
                "logicalKey": f"{form_key}/detail:{slug(sub_data_key, 'detail')}",
                "name": sub_name,
                "dataKey": sub_data_key,
                "entityRef": detail_entity_key,
                "fields": [x["logicalKey"] for x in detail_fields],
                "sourceRef": source_ref("weaver-ebuilder-form-service", "form_sub_form", base.get("id")),
            })
            entities.append({
                "logicalKey": detail_entity_key,
                "name": sub_name,
                "kind": "detail",
                "fields": detail_fields,
                "sourceRef": source_ref("weaver-ebuilder-form-service", "form_sub_form", base.get("id")),
            })
            relations.append({
                "logicalKey": f"relation:{slug(entity_key)}-to-{slug(detail_entity_key)}",
                "from": entity_key,
                "to": detail_entity_key,
                "type": "one-to-many",
                "binding": {"kind": "detail-table", "dataKey": sub_data_key},
                "sourceRef": source_ref("weaver-ebuilder-form-service", "form_sub_form", base.get("id")),
            })

        buttons = []
        for wrapper in item.get("buttons", []):
            button = wrapper.get("button", {})
            button_name = first_value(button, "name", "button_name", "show_name", default="未命名按钮")
            buttons.append({
                "logicalKey": f"{form_key}/button:{slug(button_name)}-{slug(button.get('id'), 'source')}",
                "name": button_name,
                "enabled": not bool(button.get("delete_type") or button.get("is_delete") == "1"),
                "actionCount": len(wrapper.get("actions", [])),
                "actions": redact(wrapper.get("actions", [])),
                "esbActions": redact(wrapper.get("esbActions", [])),
                "esbTriggerPositions": redact(wrapper.get("esbTriggerPositions", [])),
                "permissionCount": len(wrapper.get("permissions", [])),
                "sourceRef": source_ref("weaver-ebuilder-form-service", "form_button", button.get("id")),
            })

        lists = []
        for wrapper in item.get("lists", []):
            row = wrapper.get("list", {})
            list_name = first_value(row, "name", "show_name", "title", default="默认列表")
            lists.append({
                "logicalKey": f"{form_key}/list:{slug(list_name)}-{slug(row.get('id'), 'source')}",
                "name": list_name,
                "fieldCount": len(wrapper.get("fields", [])),
                "filterCount": len(wrapper.get("filters", [])),
                "filterGroupCount": len(wrapper.get("filterGroups", [])),
                "orderCount": len(wrapper.get("orders", [])),
                "fieldActionCount": len(wrapper.get("fieldActions", [])),
                "lineActionCount": len(wrapper.get("lineActions", [])),
                "runtimeCodeCount": len(wrapper.get("runtimeCode", [])),
                "filters": redact(wrapper.get("filters", [])),
                "orders": redact(wrapper.get("orders", [])),
                "permissionCount": len(wrapper.get("permissions", [])),
                "sourceRef": source_ref("weaver-ebuilder-form-service", "form_list", row.get("id")),
            })

        form_permissions = []
        for permission in item.get("permissions", []):
            pkey = f"permission:form:{slug(form_key)}:{slug(permission.get('id'), 'source')}"
            normalized = {
                "logicalKey": pkey,
                "name": f"{name}权限",
                "resource": form_key,
                "resourceType": "form",
                "subjectType": permission.get("org_type"),
                "subjectSourceId": sid(permission.get("org_id")),
                "actions": str(permission.get("right_type") or "").split(",") if permission.get("right_type") is not None else [],
                "scope": permission.get("code_type"),
                "sourceRef": source_ref("weaver-ebuilder-form-service", "form_permission", permission.get("id")),
            }
            form_permissions.append(pkey)
            permissions.append(normalized)

        field_permission_refs = []
        for field_permission in item.get("fieldPermissions", []):
            pkey = f"permission:form-field:{slug(form_key)}:{slug(field_permission.get('id'), 'source')}"
            details = []
            for detail in field_permission.get("details", []):
                details.append({
                    "fieldSourceId": sid(detail.get("field_id")),
                    "read": str(detail.get("field_read", "0")) in {"1", "true", "True"},
                    "write": str(detail.get("field_write", "0")) in {"1", "true", "True"},
                    "required": str(detail.get("required", "0")) in {"1", "true", "True"},
                    "sourceId": sid(detail.get("id")),
                })
            permissions.append({
                "logicalKey": pkey,
                "name": f"{name}字段权限",
                "resource": form_key,
                "resourceType": "form-fields",
                "subjectType": field_permission.get("module"),
                "actions": ["field-read", "field-write", "field-required"],
                "fieldRules": details,
                "sourceRef": source_ref(
                    "weaver-ebuilder-form-service",
                    "field_permission",
                    field_permission.get("id"),
                ),
            })
            field_permission_refs.append(pkey)

        automation_dependencies = []
        for scene in item.get("esbScenes", []):
            dep = {
                "logicalKey": f"dependency:{slug(form_key)}-esb-scene-{slug(scene.get('id'), 'source')}",
                "from": form_key,
                "to": None,
                "kind": "form-action-flow-binding",
                "status": "external",
                "sourceTarget": {
                    "actionFlowSourceId": sid(scene.get("application_id")),
                    "sceneSourceId": sid(scene.get("id")),
                    "sceneName": scene.get("scene_name"),
                    "triggerMode": scene.get("trigger_mode"),
                    "triggerPositions": redact(scene.get("triggerPositions", [])),
                },
                "sourceRef": source_ref(
                    "weaver-ebuilder-form-service", "ebdf_button_esb", scene.get("id")
                ),
            }
            dependencies.append(dep)
            automation_dependencies.append(dep["logicalKey"])

        for workflow_binding in item.get("workflowBindings", []):
            binding = workflow_binding.get("binding", {})
            workflow = workflow_binding.get("workflow", {})
            dep = {
                "logicalKey": f"dependency:{slug(form_key)}-workflow-{slug(workflow.get('id') or binding.get('workflowid'), 'source')}",
                "from": form_key,
                "to": None,
                "kind": "form-workflow-binding",
                "status": "unresolved",
                "sourceTarget": {
                    "workflowSourceId": sid(workflow.get("id") or binding.get("workflowid")),
                    "workflowName": first_value(workflow, "workflowname", "name"),
                    "triggerMode": binding.get("trigger_mode"),
                },
                "sourceRef": source_ref(
                    "weaver-ebuilder-form-service", "ebdf_app_ref_workflow", binding.get("id")
                ),
            }
            dependencies.append(dep)
            automation_dependencies.append(dep["logicalKey"])

        integration_refs = []
        for linkage in item.get("dataLinkages", []):
            for linkage_source in linkage.get("sources", []):
                integration_key = (
                    f"integration:{slug(form_key)}:linkage-"
                    f"{slug(linkage_source.get('id'), 'source')}"
                )
                integrations.append({
                    "logicalKey": integration_key,
                    "name": first_value(
                        linkage_source, "data_source_name", "source_name",
                        default=linkage.get("linkage_name") or "表单联动数据源"
                    ),
                    "type": f"form-linkage:{linkage_source.get('linkage_type') or 'unknown'}",
                    "formRef": form_key,
                    "configurationSummary": {
                        "configCount": len(linkage_source.get("configs", [])),
                        "esbConfigCount": len(linkage_source.get("esbConfigs", [])),
                        "excelConfigCount": len(linkage_source.get("excelConfigs", [])),
                        "mappingCount": len(linkage_source.get("mappings", [])),
                        "sqlConfigCount": len(linkage_source.get("sqlConfigs", [])),
                    },
                    "sourceRef": source_ref(
                        "weaver-ebuilder-form-service",
                        "fd_linkage_source",
                        linkage_source.get("id"),
                    ),
                })
                integration_refs.append(integration_key)

        forms.append({
            "logicalKey": form_key,
            "name": name,
            "tag": obj.get("tag"),
            "status": form.get("status"),
            "entityRefs": [entity_key],
            "fields": [x["logicalKey"] for x in main_fields],
            "subForms": detail_forms,
            "layouts": {
                "multipleCount": len(item.get("layouts", {}).get("multiple", [])),
                "versionCount": len(item.get("layouts", {}).get("versions", [])),
                "componentCount": len(item.get("layouts", {}).get("components", [])),
                "pageLayoutCount": len(item.get("layouts", {}).get("pageLayouts", [])),
            },
            "lists": lists,
            "buttons": buttons,
            "permissionRefs": form_permissions + field_permission_refs,
            "associationCount": len(item.get("associations", [])),
            "automation": {
                "esbScenes": [{
                    "sourceId": sid(scene.get("id")),
                    "name": scene.get("scene_name"),
                    "actionFlowSourceId": sid(scene.get("application_id")),
                    "triggerMode": scene.get("trigger_mode"),
                    "triggerPositionCount": len(scene.get("triggerPositions", [])),
                } for scene in item.get("esbScenes", [])],
                "messageTriggers": [{
                    "sourceId": sid(trigger.get("id")),
                    "name": first_value(trigger, "trigger_name", "name"),
                    "ruleCount": len(trigger.get("rules", [])),
                } for trigger in item.get("messageTriggers", [])],
                "dataLinkages": [{
                    "sourceId": sid(linkage.get("id")),
                    "name": linkage.get("linkage_name"),
                    "type": linkage.get("linkage_type"),
                    "monitorCount": len(linkage.get("monitors", [])),
                    "sourceCount": len(linkage.get("sources", [])),
                    "effectCount": len(linkage.get("effects", [])),
                } for linkage in item.get("dataLinkages", [])],
                "fieldEffects": [{
                    "sourceId": sid(effect.get("id")),
                    "name": effect.get("effect_name"),
                    "type": effect.get("effect_type"),
                    "valueCount": len(effect.get("values", [])),
                } for effect in item.get("fieldEffects", [])],
                "viewLinkages": [{
                    "sourceId": sid(linkage.get("id")),
                    "name": linkage.get("linkage_name"),
                    "enabled": linkage.get("enable_state"),
                    "detailCount": len(linkage.get("details", [])),
                    "hasCondition": bool(linkage.get("condition")),
                } for linkage in item.get("viewLinkages", [])],
                "workflowBindings": [{
                    "sourceId": sid(binding.get("binding", {}).get("id")),
                    "workflowSourceId": sid(
                        binding.get("workflow", {}).get("id")
                        or binding.get("binding", {}).get("workflowid")
                    ),
                    "name": first_value(
                        binding.get("workflow", {}), "workflowname", "name"
                    ),
                    "nodeCount": len(binding.get("nodes", [])),
                    "linkCount": len(binding.get("links", [])),
                    "conditionCount": len(binding.get("conditions", [])),
                    "javaActionCount": len(binding.get("javaActions", [])),
                } for binding in item.get("workflowBindings", [])],
                "dependencyRefs": automation_dependencies,
                "integrationRefs": integration_refs,
            },
            "thirdParty": {
                "configCount": len(item.get("thirdPartyConfigs", [])),
                "detailCount": len(item.get("thirdPartyDetails", [])),
                "viewConfigCount": len(item.get("viewThirdPartyConfigs", [])),
            },
            "packagedBusinessRowCount": item.get("storage", {}).get("packagedFormdataCount", 0),
            "sourceRef": source_ref("weaver-ebuilder-form-service", "ebdf_obj", obj.get("id")),
        })
        entities.append({
            "logicalKey": entity_key,
            "name": name,
            "kind": "main",
            "fields": main_fields,
            "sourceRef": source_ref("weaver-ebuilder-form-service", "ebdf_obj", obj.get("id")),
        })

    for entity in entities:
        for field in entity.get("fields", []):
            relation = field.get("relation")
            if not relation:
                continue
            target_source = relation.get("targetSourceId")
            target_entity = source_to_entity.get(target_source)
            target_form = source_to_form.get(target_source)
            rel_key = f"relation:{slug(field['logicalKey'])}"
            relations.append({
                "logicalKey": rel_key,
                "from": entity["logicalKey"],
                "to": target_entity or f"external:{slug(relation.get('targetName') or target_source, 'form')}",
                "type": "reference",
                "binding": {"field": field["logicalKey"], "single": relation.get("single")},
                "sourceRef": field["sourceRef"],
            })
            dependencies.append({
                "logicalKey": f"dependency:{slug(field['logicalKey'])}",
                "from": next((f["logicalKey"] for f in forms if entity["logicalKey"] in f.get("entityRefs", [])), entity["logicalKey"]),
                "to": target_form,
                "kind": "form-reference",
                "status": "resolved" if target_form else "external",
                "sourceTarget": relation,
                "sourceRef": field["sourceRef"],
            })
    return (
        forms,
        entities,
        relations,
        dependencies,
        permissions,
        integrations,
        source_to_form,
    )


def build_pages(ir, form_source_map, application_key):
    applications = ir.get("indexes", {}).get("ebuilderPages", {}).get("applications", [])
    pages, dependencies, permissions, datasets = [], [], [], []
    used_pages, used_datasets = set(), set()
    page_source_map, dataset_source_map = {}, {}

    for application in applications:
        for dataset in application.get("datasets", []):
            dataset_id = sid(dataset.get("id"))
            name = first_value(dataset, "dataset_name", "name", default="未命名数据集")
            dataset_key = unique_key(
                logical_key("dataset", stable=name),
                used_datasets,
                dataset_id,
            )
            if dataset_id:
                dataset_source_map[dataset_id] = dataset_key
            datasets.append({
                "logicalKey": dataset_key,
                "name": name,
                "type": first_value(dataset, "dataset_type", "type"),
                "connectionCount": len(dataset.get("connections", [])),
                "configurationPresent": bool(dataset.get("dataset_sql")),
                "sourceRef": source_ref(
                    "weaver-ebuilder-app-service", "dataset", dataset_id
                ),
            })

    def dataset_ids(wrapper, config):
        found = []
        dataset = wrapper.get("dataset") or {}
        for value in (
            dataset.get("id"),
            config.get("dataId"),
            config.get("dataSourceId"),
            config.get("datasetId"),
        ):
            if value is not None and sid(value) not in found:
                found.append(sid(value))
        for binding in wrapper.get("dataSourceBindings", []):
            value = first_value(
                binding, "datasource_id", "dataset_id", "data_source_id"
            )
            if value is not None and sid(value) not in found:
                found.append(sid(value))
        return found

    def compact_components(page_key, layouts):
        result = []
        for layout in layouts:
            for wrapper in layout.get("components", []):
                component = wrapper.get("component", {})
                config = (
                    component.get("config")
                    if isinstance(component.get("config"), dict)
                    else parse_object(component.get("config"))
                )
                component_key = (
                    f"{page_key}/component:{slug(wrapper.get('id'), 'source')}"
                )
                ids = dataset_ids(wrapper, config)
                resolved_refs = [
                    dataset_source_map.get(value) or form_source_map.get(value)
                    for value in ids
                ]
                resolved_refs = [value for value in resolved_refs if value]
                list_buttons = []
                for row in wrapper.get("listButtonItems", []):
                    list_buttons.append({
                        "sourceId": sid(row.get("id")),
                        "buttonSourceId": sid(row.get("button_id")),
                        "permissionType": row.get("permission_type"),
                        "targetType": row.get("target_type"),
                        "targetSourceId": sid(row.get("target_id")),
                    })
                result.append({
                    "logicalKey": component_key,
                    "parentSourceId": sid(wrapper.get("parentId")),
                    "order": wrapper.get("order"),
                    "type": wrapper.get("type"),
                    "title": wrapper.get("title"),
                    "datasetSourceIds": ids,
                    "datasetRefs": resolved_refs,
                    "conditions": wrapper.get("conditions", []),
                    "actions": wrapper.get("actions", []),
                    "dataSourceBindings": redact(
                        wrapper.get("dataSourceBindings", [])
                    ),
                    "styleBindingCount": len(wrapper.get("styleBindings", [])),
                    "listButtons": list_buttons,
                    "navMenuItems": redact(wrapper.get("navMenuItems", [])),
                    "functionalConfigKeys": sorted(config.keys()),
                    "sourceRef": source_ref(
                        "weaver-ebuilder-app-service",
                        "ebdd_layout_component",
                        wrapper.get("id"),
                    ),
                })
                for dataset_id in ids:
                    target = (
                        dataset_source_map.get(dataset_id)
                        or form_source_map.get(dataset_id)
                    )
                    dependencies.append({
                        "logicalKey": (
                            f"dependency:{slug(component_key)}-dataset-"
                            f"{slug(dataset_id, 'source')}"
                        ),
                        "from": page_key,
                        "to": target,
                        "kind": "dataset",
                        "status": "resolved" if target else "external",
                        "sourceTarget": {"sourceId": dataset_id},
                        "sourceRef": source_ref(
                            "weaver-ebuilder-app-service",
                            "ebdd_layout_comp_datasource",
                            wrapper.get("id"),
                        ),
                    })
        return result

    for application in applications:
        for item in application.get("pages", []):
            raw = item.get("page", {})
            name = item.get("name") or raw.get("name") or "未命名页面"
            terminal = (
                item.get("terminalScope")
                or raw.get("terminal_scope")
                or "UNKNOWN"
            )
            page_key = unique_key(
                logical_key("page", stable=f"{terminal}:{name}"),
                used_pages,
                item.get("id"),
            )
            page_source_map[sid(item.get("id"))] = page_key
            permission_refs = []
            for permission in item.get("permissions", []):
                pkey = (
                    f"permission:page:{slug(page_key)}:"
                    f"{slug(permission.get('id'), 'source')}"
                )
                permissions.append({
                    "logicalKey": pkey,
                    "name": f"{name}页面权限",
                    "resource": page_key,
                    "resourceType": "page",
                    "subjectType": first_value(permission, "org_type", "type"),
                    "subjectSourceId": sid(
                        first_value(permission, "org_id", "role_id", "user_id")
                    ),
                    "actions": ["view"],
                    "sourceRef": source_ref(
                        "weaver-ebuilder-app-service",
                        "ebdp_page_ph_ebdcomm_view",
                        permission.get("id"),
                    ),
                })
                permission_refs.append(pkey)
            pages.append({
                "logicalKey": page_key,
                "name": name,
                "type": "application-page",
                "terminalScope": terminal,
                "order": item.get("order"),
                "enabled": item.get("enabled"),
                "readOnly": item.get("readOnly"),
                "settings": redact(item.get("settings", {})),
                "components": compact_components(page_key, item.get("layouts", [])),
                "logicFlows": item.get("logicFlows", []),
                "runtimeExtensions": [
                    layout.get("runtimeCodeEvidence", {})
                    for layout in item.get("layouts", [])
                    if layout.get("runtimeCodeEvidence")
                ],
                "permissionRefs": permission_refs,
                "sourceRef": source_ref(
                    "weaver-ebuilder-app-service", "ebdp_page", item.get("id")
                ),
            })

        for view in application.get("embeddedViews", []):
            view_id = sid(view.get("id"))
            terminal = ",".join(
                sorted({
                    str(layout.get("terminal"))
                    for layout in view.get("layouts", [])
                    if layout.get("terminal")
                })
            ) or "UNKNOWN"
            name = f"嵌入式表单列表视图-{view_id}"
            page_key = unique_key(
                logical_key("page", stable=f"embedded:{view_id}"),
                used_pages,
                view_id,
            )
            page_source_map[view_id] = page_key
            pages.append({
                "logicalKey": page_key,
                "name": name,
                "type": "embedded-form-view",
                "terminalScope": terminal,
                "belongModule": view.get("belongModule"),
                "enabled": True,
                "components": compact_components(
                    page_key, view.get("layouts", [])
                ),
                "logicFlows": [],
                "runtimeExtensions": [
                    layout.get("runtimeCodeEvidence", {})
                    for layout in view.get("layouts", [])
                    if layout.get("runtimeCodeEvidence")
                ],
                "permissionRefs": [],
                "sourceRef": source_ref(
                    "weaver-ebuilder-app-service",
                    "ebdd_page_extended",
                    view.get("extension", {}).get("id"),
                ),
            })

    for unresolved in (
        ir.get("indexes", {})
        .get("ebuilderPages", {})
        .get("unresolvedReferences", [])
    ):
        dependencies.append({
            "logicalKey": (
                "dependency:page-unresolved:"
                f"{slug(unresolved.get('sourceId') or unresolved.get('sourceComponentId') or unresolved.get('sourceTarget'), 'source')}"
            ),
            "from": application_key,
            "to": None,
            "kind": unresolved.get("kind") or "page-reference",
            "status": "unresolved",
            "sourceTarget": unresolved,
            "sourceRef": source_ref(
                "weaver-ebuilder-app-service",
                "embedded-reference",
                unresolved.get("sourceId") or unresolved.get("sourceComponentId"),
                level="UNRESOLVED",
            ),
        })
    return (
        pages,
        dependencies,
        permissions,
        datasets,
        page_source_map,
    )


def build_action_flows(ir):
    index = ir.get("indexes", {}).get("esbActionFlows", {})
    bindings, unresolved = defaultdict(list), defaultdict(list)
    for binding in index.get("componentBindings", []):
        bindings[sid(binding.get("actionId"))].append(binding)
    for binding in index.get("unresolvedComponentBindings", []):
        unresolved[sid(binding.get("actionId"))].append(binding)
    flows, integrations, dependencies, source_map = [], [], [], {}
    used = set()
    applications = index.get("applications", [])
    idm_identities = idm_root_identity_map(
        ir,
        "weaver-esb-setting-service",
        "esb_application",
        [item.get("application", {}).get("id") for item in applications],
    )
    for item in applications:
        app = item.get("application", {})
        name = app.get("name") or "未命名动作流"
        lineage = idm_identities.get(sid(app.get("id")))
        # Keep customer-facing logical keys deterministic without embedding a
        # raw/masked migration ID or a long hexadecimal token.
        stable = (
            "lineage-" + lineage["lineageKeyHash"].translate(
                str.maketrans("0123456789abcdef", "ghijklmnopqrstuv")
            )
            if lineage else name
        )
        flow_key = unique_key(logical_key("flow", stable), used, app.get("id"))
        source_map[sid(app.get("id"))] = flow_key
        nodes = []
        for action in item.get("actions", []):
            aid = sid(action.get("id"))
            action_bindings = bindings.get(aid, [])
            missing = unresolved.get(aid, [])
            config = [{
                "table": x.get("configTable"),
                "records": redact(x.get("records", [])),
            } for x in action_bindings]
            node_key = f"{flow_key}/node:{slug(aid, 'source')}"
            nodes.append({
                "logicalKey": node_key,
                "name": action.get("name") or action.get("type") or "未命名节点",
                "type": action.get("type"),
                "order": action.get("display_order"),
                "flowSourceId": sid(action.get("flow_id")),
                "configuration": config,
                "unresolvedBindings": missing,
                "sourceRef": source_ref("weaver-esb-setting-service", "esb_action", aid),
            })
            if missing:
                dependencies.append({
                    "logicalKey": f"dependency:{slug(node_key)}-component-adapter",
                    "from": flow_key,
                    "to": None,
                    "kind": "component-adapter",
                    "status": "unresolved",
                    "sourceTarget": missing,
                    "sourceRef": source_ref("weaver-esb-setting-service", "esb_action", aid, level="UNRESOLVED"),
                })
            if action.get("type") in {"DMLExecute", "ServerlessAction", "InnerMQSend", "ApproveCommit", "ApproveSave"}:
                integration_key = f"integration:{slug(flow_key)}:{slug(aid, 'source')}"
                integrations.append({
                    "logicalKey": integration_key,
                    "name": action.get("name") or action.get("type"),
                    "type": action.get("type"),
                    "flowRef": flow_key,
                    "nodeRef": node_key,
                    "configurationStatus": "observed" if action_bindings else "adapter-required",
                    "sourceRef": source_ref("weaver-esb-setting-service", "esb_action", aid),
                })
        edges = []
        for link in item.get("links", []):
            edges.append({
                "sourceId": sid(link.get("id")),
                "fromSourceId": sid(first_value(link, "source_id", "source", "from_id", "start_id")),
                "toSourceId": sid(first_value(link, "target_id", "target", "to_id", "end_id")),
                "condition": first_value(link, "condition", "label", "name"),
            })
        flows.append({
            "logicalKey": flow_key,
            "name": name,
            "identityMethod": (
                lineage.get("identityMethod") if lineage else "BUSINESS_KEY"
            ),
            "lineageKeyHash": (
                lineage.get("lineageKeyHash") if lineage else None
            ),
            "lineageEvidencePath": (
                lineage.get("lineageEvidencePath") if lineage else None
            ),
            "status": app.get("status"),
            "triggers": [{
                "name": event.get("name"),
                "type": event.get("type"),
                "sourceId": sid(event.get("id")),
                "flowSourceId": sid(event.get("flow_id")),
            } for event in item.get("events", [])],
            "segments": [{
                "name": segment.get("name"),
                "type": segment.get("type"),
                "sourceId": sid(segment.get("id")),
            } for segment in item.get("flows", [])],
            "nodes": nodes,
            "edges": edges,
            "sourceRef": source_ref("weaver-esb-setting-service", "esb_application", app.get("id")),
        })
    return flows, integrations, dependencies, source_map


def build_workflows(ir):
    service = "weaver-bpm-service"
    bases = table_records(ir, service, "bpm_new_base")
    nodes = table_records(ir, service, "bpm_node_base")
    actions = table_records(ir, service, "bpm_node_action")
    by_bpm = defaultdict(list)
    actions_by_node = defaultdict(list)
    for action in actions:
        actions_by_node[sid(first_value(action, "node_id", "bpm_node_id", "nodeid"))].append(redact(action))
    for node in nodes:
        by_bpm[sid(first_value(node, "bpm_id", "bpmid", "main_bpmid"))].append(node)
    workflows, source_map = [], {}
    used = set()
    for base in bases:
        name = first_value(base, "bpm_name", "name", "title", default="未命名流程")
        key = unique_key(logical_key("workflow", name), used, base.get("id"))
        source_map[sid(base.get("id"))] = key
        workflow_nodes = []
        for node in by_bpm.get(sid(base.get("id")), []):
            node_id = sid(node.get("id"))
            workflow_nodes.append({
                "logicalKey": f"{key}/node:{slug(node_id, 'source')}",
                "name": first_value(node, "node_name", "name", "title", default="未命名节点"),
                "moduleSourceId": sid(node.get("module_id")),
                "selectedDataSourceId": sid(first_value(node, "select_dataid", "data_id")),
                "actions": actions_by_node.get(node_id, []),
                "sourceRef": source_ref(service, "bpm_node_base", node_id),
            })
        workflows.append({
            "logicalKey": key,
            "name": name,
            "type": "bpm-application-map",
            "status": first_value(base, "bpm_status", "status"),
            "nodes": workflow_nodes,
            "sourceRef": source_ref(service, "bpm_new_base", base.get("id")),
        })

    for form_entry in (
        ir.get("indexes", {}).get("ebuilderForms", {}).get("forms", [])
    ):
        for entry in form_entry.get("workflowBindings", []):
            workflow = entry.get("workflow", {})
            binding = entry.get("binding", {})
            workflow_id = sid(workflow.get("id") or binding.get("workflowid"))
            if not workflow_id or workflow_id in source_map:
                continue
            name = first_value(
                workflow, "workflowname", "name", default="未命名审批流程"
            )
            key = unique_key(
                logical_key("workflow", name), used, workflow_id
            )
            source_map[workflow_id] = key
            compact_nodes = []
            menus = entry.get("nodeMenus", [])
            menus_by_node = Counter(sid(row.get("nodeid")) for row in menus)
            for node in entry.get("nodes", []):
                node_id = sid(node.get("id"))
                compact_nodes.append({
                    "logicalKey": f"{key}/node:{slug(node_id, 'source')}",
                    "name": first_value(
                        node, "nodename", "name", default="未命名节点"
                    ),
                    "type": node.get("nodetype"),
                    "order": node.get("orderid"),
                    "menuCount": menus_by_node.get(node_id, 0),
                    "sourceRef": source_ref(
                        "weaver-ebuilder-form-service", "wfp_node", node_id
                    ),
                })
            workflows.append({
                "logicalKey": key,
                "name": name,
                "type": "form-workflow",
                "status": workflow.get("status"),
                "nodes": compact_nodes,
                "linkCount": len(entry.get("links", [])),
                "conditionCount": len(entry.get("conditions", [])),
                "operatorGroupCount": len(entry.get("operatorGroups", [])),
                "javaActions": [{
                    "sourceId": sid(action.get("id")),
                    "name": action.get("action_name"),
                    "enabled": action.get("enable"),
                    "interface": action.get("interface_url"),
                } for action in entry.get("javaActions", [])],
                "binding": {
                    "sourceId": sid(binding.get("id")),
                    "triggerMode": binding.get("trigger_mode"),
                    "flowSourceType": binding.get("flow_source_type"),
                },
                "sourceRef": source_ref(
                    "weaver-ebuilder-form-service", "wfp_base", workflow_id
                ),
            })
    return workflows, source_map


def build_reports(ir):
    service = "weaver-edcreportd-service"
    indexed = ir.get("indexes", {}).get("edcReports", {})
    reports, dependencies, permissions, source_map, used = [], [], [], {}, set()
    entries = indexed.get("reports", [])
    if not entries:
        entries = [{"report": row} for row in table_records(ir, service, "edc_report_dev")]
    for entry in entries:
        base = entry.get("report", {})
        name = first_value(base, "report_name", "name", "title", default="未命名报表")
        key = unique_key(logical_key("report", name), used, base.get("id"))
        report_id = sid(base.get("id"))
        if report_id:
            source_map[report_id] = key
        normalized_datasets = []
        for wrapper in entry.get("datasets", []):
            dataset = wrapper.get("dataset", {})
            reference = wrapper.get("reference", {})
            dataset_id = sid(dataset.get("id") or first_value(reference, "dataset_id", "datasetId"))
            dataset_key = f"{key}/dataset:{slug(dataset_id or first_value(dataset, 'name', 'dataset_name'), 'dataset')}"
            normalized_datasets.append({
                "logicalKey": dataset_key,
                "name": first_value(dataset, "name", "dataset_name", "title", default="未命名数据集"),
                "sourceId": dataset_id,
                "sourceType": first_value(dataset, "source_type", "sourceType", "type"),
                "sourceTargetId": sid(first_value(dataset, "source_id", "sourceId")),
                "legacyFilters": [redact(x) for x in wrapper.get("legacyFilters", [])],
                "newFilters": [redact(x) for x in wrapper.get("newFilters", [])],
                "ordering": [redact(x) for x in wrapper.get("ordering", [])],
                "aggregation": [redact(x) for x in wrapper.get("aggregation", [])],
                "queryInformation": [redact(x) for x in wrapper.get("queryInformation", [])],
                "sourceRef": source_ref(service, "edc_dataset_dev", dataset_id),
            })
            source_target = sid(first_value(dataset, "source_id", "sourceId"))
            if source_target:
                dependencies.append({
                    "logicalKey": f"dependency:{slug(key)}-dataset-source-{slug(source_target, 'source')}",
                    "from": key,
                    "to": f"external:data-source:{source_target}",
                    "kind": "report-dataset-source",
                    "status": "external",
                    "sourceTarget": {"sourceId": source_target},
                    "sourceRef": source_ref(service, "edc_dataset_dev", dataset_id),
                })
        permission_refs = []
        for permission_type, table, rows in (
            ("report-view", "edc_report_ph_report_view", entry.get("viewPermissions", [])),
            ("report-matrix", "edc_report_matrix_right", entry.get("matrixRights", [])),
            ("report-group", "edc_report_group_right", entry.get("permissionGroups", [])),
        ):
            for row in rows:
                permission_key = (
                    f"permission:{permission_type}:{slug(row.get('id'), 'source')}"
                )
                permission_refs.append(permission_key)
                permissions.append({
                    "logicalKey": permission_key,
                    "name": f"{name}-{permission_type}",
                    "type": permission_type,
                    "resourceRef": key,
                    "configuration": redact(row),
                    "sourceRef": source_ref(service, table, row.get("id")),
                })
        reports.append({
            "logicalKey": key,
            "name": name,
            "status": first_value(base, "status", "enable", "enabled"),
            "systemType": first_value(base, "system_type", "systemType"),
            "applicationSourceId": sid(first_value(base, "appid", "app_id", "appId")),
            "group": redact(entry.get("group", {})),
            "datasets": normalized_datasets,
            "sheetProperties": [redact(x) for x in entry.get("sheetProperties", [])],
            "systemDatasets": [redact(x) for x in entry.get("systemDatasets", [])],
            "sheetFields": [redact(x) for x in entry.get("sheetFields", [])],
            "queryFields": [redact(x) for x in entry.get("queryFields", [])],
            "sheetSplits": [redact(x) for x in entry.get("sheetSplits", [])],
            "workbookProperties": [redact(x) for x in entry.get("workbookProperties", [])],
            "versions": [redact(x) for x in entry.get("versions", [])],
            "permissionRefs": permission_refs,
            "sourceRef": source_ref(service, "edc_report_dev", base.get("id")),
        })
    return reports, dependencies, permissions, source_map


def build_multi_filling(ir, form_source_map, report_source_map):
    service = "weaver-edcapp-service"
    indexed = ir.get("indexes", {}).get("edcMultiFilling", {})
    tasks, dependencies, permissions, used = [], [], [], set()
    for entry in indexed.get("tasks", []):
        task = entry.get("task", {})
        name = first_value(
            task, "task_name", "name", "title",
            default=f"多级填报任务-{sid(task.get('id')) or 'unknown'}",
        )
        key = unique_key(logical_key("multi-filling", name), used, task.get("id"))
        node_map = {}
        nodes = []
        for node in entry.get("nodes", []):
            node_id = sid(node.get("id"))
            node_key = f"{key}/node:{slug(node_id, 'source')}"
            node_map[node_id] = node_key
            nodes.append({
                "logicalKey": node_key,
                "name": first_value(node, "node_name", "name", "title", default="未命名填报节点"),
                "designNodeSourceId": sid(first_value(node, "node_id", "nodeId")),
                "status": first_value(node, "status", "state"),
                "sourceRef": source_ref(service, "edc_multi_task_node", node.get("id")),
            })
        edges = []
        for wrapper in entry.get("edges", []):
            edge = wrapper.get("edge", wrapper)
            source_id = sid(first_value(edge, "edge_source", "edgeSource", "source_id"))
            target_id = sid(first_value(edge, "target", "target_id", "targetId"))
            edges.append({
                "logicalKey": f"{key}/edge:{slug(edge.get('id'), 'source')}",
                "from": node_map.get(source_id),
                "to": node_map.get(target_id),
                "sourceNodeSourceId": source_id,
                "targetNodeSourceId": target_id,
                "missingEndpoints": wrapper.get("missingEndpoints", []),
                "sourceRef": source_ref(service, "edc_multi_task_edge", edge.get("id")),
            })
        executions = []
        for wrapper in entry.get("executions", []):
            execution = wrapper.get("execution", {})
            execution_id = sid(execution.get("id"))
            execution_key = f"{key}/execution:{slug(execution_id, 'source')}"
            configs = []
            for config in wrapper.get("configurations", []):
                form_id = sid(first_value(config, "form_id", "formId"))
                layout_id = sid(first_value(config, "layout_id", "layoutId"))
                target = form_source_map.get(form_id) or report_source_map.get(form_id)
                if form_id:
                    dependencies.append({
                        "logicalKey": f"dependency:{slug(execution_key)}-form-report-{slug(form_id, 'source')}",
                        "from": key,
                        "to": target or f"external:form-or-report:{form_id}",
                        "kind": "multi-filling-form-report-binding",
                        "status": "resolved" if target else "external",
                        "sourceTarget": {"formOrReportSourceId": form_id},
                        "sourceRef": source_ref(service, "edc_multi_execution_config", config.get("id")),
                    })
                if layout_id:
                    dependencies.append({
                        "logicalKey": f"dependency:{slug(execution_key)}-layout-{slug(layout_id, 'source')}",
                        "from": key,
                        "to": f"external:layout:{layout_id}",
                        "kind": "multi-filling-layout-binding",
                        "status": "external",
                        "sourceTarget": {"layoutSourceId": layout_id},
                        "sourceRef": source_ref(service, "edc_multi_execution_config", config.get("id")),
                    })
                configs.append({
                    "sourceId": sid(config.get("id")),
                    "formOrReportSourceId": form_id,
                    "layoutSourceId": layout_id,
                    "operation": first_value(config, "operation", "operation_type", "operationType"),
                    "summarySetting": parse_object(first_value(config, "summary_setting", "summarySetting")),
                })
            permission_refs = []
            for row in wrapper.get("permissions", []):
                permission_key = (
                    f"permission:multi-filling-execution:{slug(row.get('id'), 'source')}"
                )
                permission_refs.append(permission_key)
                permissions.append({
                    "logicalKey": permission_key,
                    "name": f"{name}-执行权限",
                    "type": "multi-filling-execution",
                    "resourceRef": execution_key,
                    "configuration": redact(row),
                    "sourceRef": source_ref(
                        service, "edc_multi_task_execution_ph_ec", row.get("id")
                    ),
                })
            executions.append({
                "logicalKey": execution_key,
                "nodeRef": node_map.get(sid(first_value(execution, "node_id", "nodeId"))),
                "status": first_value(execution, "status", "state"),
                "businessDataSourceId": sid(first_value(execution, "dataId", "data_id")),
                "configurations": configs,
                "permissionRefs": permission_refs,
                "sourceRef": source_ref(service, "edc_multi_task_execution", execution_id),
            })
        design_report_id = sid(first_value(task, "report_id", "reportId"))
        design_target = report_source_map.get(design_report_id)
        if design_report_id:
            dependencies.append({
                "logicalKey": f"dependency:{slug(key)}-design-report-{slug(design_report_id, 'source')}",
                "from": key,
                "to": design_target or f"external:multi-filling-design:{design_report_id}",
                "kind": "multi-filling-design-report",
                "status": "resolved" if design_target else "external",
                "sourceTarget": {"reportSourceId": design_report_id},
                "sourceRef": source_ref(service, "edc_multi_report_task", task.get("id")),
            })
        tasks.append({
            "logicalKey": key,
            "name": name,
            "type": "edc-multi-level-filling",
            "designReportSourceId": design_report_id,
            "nodes": nodes,
            "edges": edges,
            "executions": executions,
            "statistics": entry.get("statistics", {}),
            "sourceRef": source_ref(service, "edc_multi_report_task", task.get("id")),
        })
    for row in indexed.get("matrixRights", []):
        permissions.append({
            "logicalKey": f"permission:multi-filling-matrix:{slug(row.get('id'), 'source')}",
            "name": "多级填报矩阵权限",
            "type": "multi-filling-matrix",
            "resourceSourceId": sid(first_value(row, "target_id", "targetId")),
            "configuration": redact(row),
            "sourceRef": source_ref(service, "edc_multi_matrix_right", row.get("id")),
        })
    return tasks, dependencies, permissions


def build_navigation(ir, pages, page_source_map):
    terminals, menus, groups, combinations, unattached_settings = [], [], [], [], []
    for app in ir.get("indexes", {}).get("ebuilderPages", {}).get("applications", []):
        for nav in app.get("navigation", []):
            terminal = nav.get("nav_type")
            if terminal:
                terminals.append(terminal)
        for group in app.get("pageGroups", []):
            groups.append({
                "logicalKey": (
                    f"navigation-group:{slug(first_value(group, 'name', 'group_name', default=group.get('id')))}-"
                    f"{slug(group.get('id'), 'source')}"
                ),
                "name": first_value(
                    group, "name", "group_name", "show_name", default="未命名页面组"
                ),
                "sourceRef": source_ref(
                    "weaver-ebuilder-app-service", "ebdp_page_group", group.get("id")
                ),
            })
        for combination in app.get("menuCombinations", []):
            combinations.append({
                "logicalKey": (
                    f"menu-combination:{slug(combination.get('id'), 'source')}"
                ),
                "name": first_value(
                    combination, "name", "combination_name", default="菜单组合"
                ),
                "sourceRef": source_ref(
                    "weaver-ebuilder-app-service",
                    "ebda_app_menu_comb",
                    combination.get("id"),
                ),
            })
        for setting in app.get("unattachedPageSettings", []):
            unattached_settings.append({
                "sourceId": sid(setting.get("id")),
                "pageSourceId": sid(setting.get("page_id")),
                "status": "unresolved",
            })
        for row in app.get("menus", []):
            target_source = sid(
                first_value(row, "page_id", "target_id", "data_id")
            )
            menus.append({
                "logicalKey": (
                    f"menu:application:"
                    f"{slug(first_value(row, 'name', 'page_name', default=row.get('id')))}-"
                    f"{slug(row.get('id'), 'source')}"
                ),
                "name": first_value(
                    row, "name", "page_name", "name_alias", default="未命名菜单"
                ),
                "kind": "application-menu",
                "parentSourceId": sid(first_value(row, "pid", "parent_id")),
                "targetSourceId": target_source,
                "targetRef": page_source_map.get(target_source),
                "pageType": row.get("page_type"),
                "terminalScope": row.get("terminal_scopes"),
                "order": row.get("show_order"),
                "permissionCount": len(row.get("permissions", [])),
                "sourceRef": source_ref(
                    "weaver-ebuilder-app-service", "ebda_app_menu", row.get("id")
                ),
            })
    for row in table_records(ir, "weaver-cusapp-service", "t_cus_app_system_menu"):
        menus.append({
            "logicalKey": f"menu:system:{slug(first_value(row, 'name', 'menu_name', 'show_name', default=row.get('id')))}-{slug(row.get('id'), 'source')}",
            "name": first_value(row, "name", "menu_name", "show_name", "title", default="未命名菜单"),
            "kind": "system-menu",
            "parentSourceId": sid(first_value(row, "parent_id", "pid")),
            "targetSourceId": sid(first_value(row, "page_id", "target_id", "data_id")),
            "order": first_value(row, "show_order", "dsporder", "sort"),
            "sourceRef": source_ref("weaver-cusapp-service", "t_cus_app_system_menu", row.get("id")),
        })
    if not terminals:
        terminals = sorted({p.get("terminalScope") for p in pages if p.get("terminalScope")})
    return {
        "terminals": sorted(set(terminals)),
        "groups": groups,
        "combinations": combinations,
        "menus": menus,
        "unattachedPageSettings": unattached_settings,
    }


def build_cusapp(ir, page_source_map, form_source_map, report_source_map):
    service = "weaver-cusapp-service"
    indexed = ir.get("indexes", {}).get("cusApps", {})
    shells, navigations, combinations, menus = [], [], [], []
    personalization, permissions, dependencies = [], [], []
    target_maps = {}
    target_maps.update(page_source_map)
    target_maps.update(form_source_map)
    target_maps.update(report_source_map)
    combination_map = {}
    for entry in indexed.get("applications", []):
        app = entry.get("application", {})
        app_id = sid(app.get("id"))
        app_key = logical_key(
            "cusapp", stable=first_value(app, "tag", "app_tag", "name", "app_name", default=app_id)
        )
        shells.append({
            "logicalKey": app_key,
            "name": first_value(app, "name", "app_name", "show_name", default="未命名应用"),
            "sourceRef": source_ref(service, "t_cus_app", app.get("id")),
        })
        for wrapper in entry.get("navigations", []):
            navigation = wrapper.get("navigation", {})
            nav_id = sid(navigation.get("id"))
            navigations.append({
                "logicalKey": f"navigation:cusapp:{slug(nav_id, 'source')}",
                "applicationRef": app_key,
                "terminal": first_value(
                    navigation, "terminal", "terminal_type", "terminalType", "nav_type", "type"
                ),
                "name": first_value(navigation, "name", "nav_name", "title", default="应用导航"),
                "configurations": [redact(x) for x in wrapper.get("configurations", [])],
                "sourceRef": source_ref(service, "t_cus_app_navigation", navigation.get("id")),
            })
        for combination in entry.get("menuCombinations", []):
            combination_id = sid(combination.get("id"))
            combination_key = f"menu-combination:cusapp:{slug(combination_id, 'source')}"
            combination_map[combination_id] = combination_key
            combinations.append({
                "logicalKey": combination_key,
                "name": first_value(
                    combination, "name", "combination_name", "title", default="组合菜单"
                ),
                "applicationRef": app_key,
                "sourceRef": source_ref(service, "t_cus_app_menu_comb", combination.get("id")),
            })

        def add_menu(wrapper, kind, table):
            menu = wrapper.get("menu", {})
            menu_id = sid(menu.get("id"))
            menu_key = f"menu:cusapp:{kind}:{slug(menu_id, 'source')}"
            target_source_id = sid(first_value(menu, "page_id", "pageId", "target_id", "targetId"))
            combination_id = sid(first_value(menu, "combination_id", "combinationId"))
            target_ref = (
                target_maps.get(target_source_id)
                or combination_map.get(target_source_id)
            )
            target_evidence = target_source_id
            if target_evidence:
                dependencies.append({
                    "logicalKey": f"dependency:{slug(menu_key)}-target-{slug(target_evidence, 'source')}",
                    "from": menu_key,
                    "to": target_ref or f"external:menu-target:{target_evidence}",
                    "kind": "cusapp-menu-target",
                    "status": "resolved" if target_ref else "external",
                    "sourceTarget": {
                        "pageType": first_value(menu, "page_type", "pageType"),
                        "sourceId": target_evidence,
                    },
                    "sourceRef": source_ref(service, table, menu.get("id")),
                })
            permission_refs = []
            for permission_wrapper in wrapper.get("permissions", []):
                permission = permission_wrapper.get("permission", {})
                permission_id = sid(permission.get("id"))
                permission_key = (
                    f"permission:cusapp-{kind}:{slug(permission_id, 'source')}"
                )
                permission_refs.append(permission_key)
                permissions.append({
                    "logicalKey": permission_key,
                    "name": f"{first_value(menu, 'name', 'menu_name', 'title', default='菜单')}-可见权限",
                    "type": f"cusapp-{kind}-visibility",
                    "resourceRef": menu_key,
                    "configuration": redact(permission),
                    "matrixRules": [
                        redact(x) for x in permission_wrapper.get("matrixRules", [])
                    ],
                    "matrixValues": [
                        redact(x) for x in permission_wrapper.get("matrixValues", [])
                    ],
                    "sourceRef": source_ref(
                        service,
                        "cus_app_ph_sys_view"
                        if kind == "system"
                        else "cus_app_ph_cus_app_view",
                        permission.get("id"),
                    ),
                })
            menus.append({
                "logicalKey": menu_key,
                "name": first_value(
                    menu, "name", "menu_name", "show_name", "title", default="未命名菜单"
                ),
                "kind": f"cusapp-{kind}-menu",
                "applicationRef": app_key,
                "parentSourceId": sid(first_value(menu, "parent_id", "parentId", "pid")),
                "navigationSourceId": sid(first_value(menu, "nav_id", "navId")),
                "combinationSourceId": combination_id,
                "pageType": first_value(menu, "page_type", "pageType"),
                "targetSourceId": target_source_id,
                "targetRef": target_ref,
                "businessSourceId": sid(first_value(menu, "business_id", "businessId")),
                "params": parse_object(menu.get("params")),
                "tabs": parse_object(menu.get("tabs")),
                "order": first_value(menu, "sort", "show_order", "dsporder"),
                "permissionRefs": permission_refs,
                "businessControls": [
                    redact(x) for x in wrapper.get("businessControls", [])
                ],
                "customPermissionSets": [
                    redact(x) for x in wrapper.get("customPermissionSets", [])
                ],
                "sourceRef": source_ref(service, table, menu.get("id")),
            })

        for wrapper in entry.get("systemMenus", []):
            add_menu(wrapper, "system", "t_cus_app_system_menu")
        for wrapper in entry.get("frontMenus", []):
            add_menu(wrapper, "front", "t_cus_app_menu")
        personalization.extend({
            "applicationRef": app_key,
            "configuration": redact(row),
            "sourceRef": source_ref(service, "t_cus_app_sys_personal", row.get("id")),
        } for row in entry.get("personalizationSync", []))
    terminals = sorted({
        item.get("terminal") for item in navigations if item.get("terminal") is not None
    })
    return {
        "applicationShells": shells,
        "terminals": terminals,
        "navigations": navigations,
        "combinations": combinations,
        "menus": menus,
        "personalizationSync": personalization,
    }, permissions, dependencies


def identify_application(ir):
    source = ir.get("source", {})
    page_apps = ir.get("indexes", {}).get("ebuilderPages", {}).get("applications", [])
    cusapp_entries = ir.get("indexes", {}).get("cusApps", {}).get("applications", [])
    raw = cusapp_entries[0].get("application", {}) if cusapp_entries else {}
    if not raw:
        raw = page_apps[0].get("application", {}) if page_apps else {}
    if not raw:
        cusapps = table_records(ir, "weaver-cusapp-service", "t_cus_app")
        raw = cusapps[0] if cusapps else {}
    package = source.get("packageName") or Path(source.get("packagePath") or "unknown.zip").name
    name = first_value(raw, "name", "app_name", "show_name", default=Path(package).stem)
    tag = first_value(raw, "tag", "app_tag")
    return {
        "logicalKey": logical_key("app", stable=tag or name),
        "name": name,
        "tag": tag,
        "description": raw.get("description") or "",
        "scope": raw.get("scope"),
        "sourcePackage": package,
        "services": sorted(ir.get("modules", {}).keys()),
        "sourceRef": source_ref(
            "weaver-cusapp-service" if cusapp_entries else "weaver-ebuilder-app-service",
            "t_cus_app" if cusapp_entries else "eb_app",
            raw.get("id"),
        ),
    }


def build_modules(ir, service_analysis):
    fragments = {x["service"]: x for x in service_analysis["serviceFragments"]}
    result = []
    for inventory in service_analysis["serviceInventory"]:
        service = inventory["service"]
        fragment = fragments[service]
        result.append({
            "logicalKey": logical_key("module", stable=service),
            "service": service,
            "capability": inventory["capability"],
            "serviceRole": inventory["serviceRole"],
            "analysisLevel": inventory["analysisLevel"],
            "dedicatedParser": inventory["dedicatedParser"],
            "adapterStatus": (
                "available" if inventory["dedicatedParser"]
                else "structural-analysis" if inventory["knownInConfiguration"]
                else "required"
            ),
            "tableCount": inventory["packageTableCount"],
            "recordCount": inventory["packageRecordCount"],
            "tableCounts": {x["table"]: x["recordCount"] for x in fragment["tables"]},
            "featureGroupCount": len(fragment.get("featureGroupRefs", [])),
            "relationshipCount": len(fragment.get("relationships", [])),
            "externalReferenceCount": len(fragment.get("externalReferences", [])),
            "sourceRef": source_ref(service, "*"),
        })
    return result


def resolve_cross_module_dependencies(dependencies, flow_source_map, workflow_source_map):
    for dependency in dependencies:
        target = dependency.get("sourceTarget", {})
        if dependency.get("kind") == "form-action-flow-binding":
            resolved = flow_source_map.get(target.get("actionFlowSourceId"))
            if resolved:
                dependency["to"] = resolved
                dependency["status"] = "resolved"
        elif dependency.get("kind") == "form-workflow-binding":
            resolved = workflow_source_map.get(target.get("workflowSourceId"))
            if resolved:
                dependency["to"] = resolved
                dependency["status"] = "resolved"
    return dependencies


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("canonical_ir")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    ir = load_json(args.canonical_ir)
    application = identify_application(ir)
    (
        forms,
        entities,
        relations,
        form_deps,
        form_permissions,
        form_integrations,
        form_map,
    ) = build_forms(ir)
    (
        pages,
        page_deps,
        page_permissions,
        page_datasets,
        page_source_map,
    ) = build_pages(ir, form_map, application["logicalKey"])
    action_flows, flow_integrations, flow_deps, flow_source_map = (
        build_action_flows(ir)
    )
    legacy_workflows, legacy_workflow_source_map = build_workflows(ir)
    bpm_workflows = [
        item for item in legacy_workflows
        if item.get("type") == "bpm-application-map"
    ]
    pathdef_workflows, pathdef_source_map, pathdef_deps, pathdef_unresolved = (
        build_workflow_pathdefs(ir, form_map)
    )
    workflows = bpm_workflows + pathdef_workflows
    workflow_source_map = {
        **{
            source_id: key
            for source_id, key in legacy_workflow_source_map.items()
            if key in {item["logicalKey"] for item in bpm_workflows}
        },
        **pathdef_source_map,
    }
    ai_applications, ai_integrations, ai_deps, ai_unresolved = (
        build_ai_applications(ir)
    )
    reports, report_deps, report_permissions, report_source_map = build_reports(ir)
    multi_filling_tasks, multi_filling_deps, multi_filling_permissions = (
        build_multi_filling(ir, form_map, report_source_map)
    )
    navigation = build_navigation(ir, pages, page_source_map)
    cusapp_navigation, cusapp_permissions, cusapp_deps = build_cusapp(
        ir, page_source_map, form_map, report_source_map
    )
    navigation["terminals"] = sorted(set(
        navigation.get("terminals", []) + cusapp_navigation.get("terminals", [])
    ))
    navigation["applicationShells"] = cusapp_navigation.get("applicationShells", [])
    navigation["navigations"] = cusapp_navigation.get("navigations", [])
    navigation["combinations"] = unique_by(
        navigation.get("combinations", [])
        + cusapp_navigation.get("combinations", [])
    )
    navigation["menus"] = unique_by(
        navigation.get("menus", []) + cusapp_navigation.get("menus", [])
    )
    navigation["personalizationSync"] = cusapp_navigation.get(
        "personalizationSync", []
    )
    structural_analysis = analyze_services(ir)
    modules = build_modules(ir, structural_analysis)
    unknown = [x["service"] for x in modules if x["adapterStatus"] == "required"]
    structural_only = [
        x["service"] for x in modules if x["analysisLevel"] == "STRUCTURAL"
    ]
    unresolved_esb = ir.get("indexes", {}).get("esbActionFlows", {}).get("unresolvedComponentBindings", [])
    unresolved_pages = ir.get("indexes", {}).get("ebuilderPages", {}).get("unresolvedReferences", [])
    unresolved_multi_filling = ir.get("indexes", {}).get("edcMultiFilling", {}).get("unresolvedReferences", [])
    unresolved_reports = ir.get("indexes", {}).get("edcReports", {}).get("unresolvedReferences", [])
    unresolved_cusapp = ir.get("indexes", {}).get("cusApps", {}).get("unresolvedReferences", [])
    import_requirements = ir.get("indexes", {}).get("importRequirements", {
        "schemaVersion": "1.0",
        "requiredInputs": [],
        "optionalInputs": [],
        "optionalMappings": [],
        "policy": {},
        "summary": {
            "requiredInputs": 0,
            "unresolvedRequiredInputs": 0,
            "optionalInputs": 0,
            "optionalMappings": 0,
        },
    })
    dependencies = unique_by(
        resolve_cross_module_dependencies(
            form_deps
            + page_deps
            + flow_deps
            + ai_deps
            + pathdef_deps
            + report_deps
            + multi_filling_deps
            + cusapp_deps
            + structural_analysis["dependencies"],
            flow_source_map,
            workflow_source_map,
        )
    )
    evidence_unresolved = [
        {"kind": "esb-component-binding", **x} for x in unresolved_esb
    ] + [
        {"kind": "page-reference", **x} for x in unresolved_pages
    ] + [
        {"kind": "multi-filling-reference", **x}
        for x in unresolved_multi_filling
    ] + [
        {"kind": "edc-report-reference", **x} for x in unresolved_reports
    ] + [
        {"kind": "cusapp-reference", **x} for x in unresolved_cusapp
    ] + [
        {"kind": "ai-application-reference", **x} for x in ai_unresolved
    ] + [
        {"kind": "workflow-pathdef-reference", **x}
        for x in pathdef_unresolved
    ] + [
        {"kind": "module-adapter", "service": service} for service in unknown
    ]
    result = {
        "irVersion": "1.0",
        "kind": "ebuilder.application-ir",
        "application": application,
        "modules": modules,
        "serviceInventory": structural_analysis["serviceInventory"],
        "serviceFragments": structural_analysis["serviceFragments"],
        "semanticServiceCoverage": sorted({
            owner
            for item in structural_analysis["serviceInventory"]
            for owner in item.get("semanticOwnerServices", [item["service"]])
        }),
        "businessObjects": structural_analysis["businessObjects"],
        "dataModel": {
            "entities": unique_by(entities),
            "relations": unique_by(relations),
            "datasets": unique_by(page_datasets),
        },
        "forms": unique_by(forms),
        "pages": unique_by(pages),
        "actionFlows": unique_by(action_flows),
        "aiApplications": unique_by(ai_applications),
        "multiFillingTasks": unique_by(multi_filling_tasks),
        "workflows": unique_by(workflows),
        "permissions": unique_by(
            form_permissions
            + page_permissions
            + report_permissions
            + multi_filling_permissions
            + cusapp_permissions
        ),
        "reports": unique_by(reports),
        "navigation": navigation,
        "integrations": unique_by(
            form_integrations + flow_integrations + ai_integrations
        ),
        "externalResources": structural_analysis["externalResources"],
        "migrationRules": {
            "sourceOfTruth": "packing-installer-code-and-configuration",
            "idPolicy": "typed-source-target-mapping; never reuse source environment IDs",
            "customInputPolicy": "only structurally identifiable custom mappings become required or optional inputs",
            "secretPolicy": "credentials and secrets are runtime-only and are never persisted in IR",
            "nonBlockingMappings": [
                "target-message-account-mapping affects only message-channel bindings",
                "missing target enterprise/application mapping must not erase source design evidence",
            ],
        },
        "importRequirements": import_requirements,
        "dependencies": dependencies,
        "evidence": {
            "sources": [{
                "package": ir.get("source", {}).get("packageName"),
                "packagePath": ir.get("source", {}).get("packagePath"),
                "canonicalIR": str(Path(args.canonical_ir).resolve()),
                "zipLayers": len(ir.get("zipLayers", [])),
                "canonicalSchemaVersion": ir.get("schemaVersion"),
            }],
            "assertions": [{
                "level": "CONFIG_OBSERVED",
                "statement": "Application IR 由 canonical package IR 的显式索引和原始模块记录生成。",
            }, {
                "level": "CONFIG_OBSERVED",
                "statement": "所有包内服务均进入动态服务清单；无专用语义解析器的服务使用配置表链、业务链和外部引用规则生成结构化片段。",
            }],
            "unresolved": evidence_unresolved,
            "parseErrors": ir.get("errors", []),
        },
        "build": {
            "status": "ADAPTER_REQUIRED",
            "order": BUILD_ORDER,
            "blockers": [],
            "adapterRequirements": (
                ["target-builder-contract"]
                + [f"module:{x}" for x in unknown]
                + [f"dedicated-semantic-parser:{x}" for x in structural_only]
                + (["esb-component-registry"] if unresolved_esb else [])
                + (["external-page-reference-resolution"] if unresolved_pages else [])
                + (
                    ["external-edc-reference-resolution"]
                    if unresolved_multi_filling or unresolved_reports
                    else []
                )
                + (
                    ["external-cusapp-menu-target-resolution"]
                    if unresolved_cusapp
                    else []
                )
            ),
        },
    }
    result["summary"] = {
        "modules": len(modules),
        "fullSemanticServices": sum(x.get("analysisLevel") == "FULL_SEMANTIC" for x in modules),
        "structuralServices": sum(x.get("analysisLevel") == "STRUCTURAL" for x in modules),
        "evidenceOnlyServices": sum(x.get("analysisLevel") == "EVIDENCE_ONLY" for x in modules),
        "serviceFragments": len(result["serviceFragments"]),
        "semanticServiceCoverage": len(result["semanticServiceCoverage"]),
        "businessObjects": len(result["businessObjects"]),
        "externalResources": len(result["externalResources"]),
        "entities": len(result["dataModel"]["entities"]),
        "relations": len(result["dataModel"]["relations"]),
        "datasets": len(result["dataModel"].get("datasets", [])),
        "forms": len(result["forms"]),
        "pages": len(result["pages"]),
        "applicationPages": sum(
            item.get("type") == "application-page" for item in result["pages"]
        ),
        "embeddedViews": sum(
            item.get("type") == "embedded-form-view" for item in result["pages"]
        ),
        "pageComponents": sum(len(x.get("components", [])) for x in result["pages"]),
        "actionFlows": len(result["actionFlows"]),
        "actionNodes": sum(len(x.get("nodes", [])) for x in result["actionFlows"]),
        "aiApplications": len(result["aiApplications"]),
        "aiFunctions": sum(
            len(x.get("functions", [])) for x in result["aiApplications"]
        ),
        "multiFillingTasks": len(result["multiFillingTasks"]),
        "multiFillingNodes": sum(
            len(x.get("nodes", [])) for x in result["multiFillingTasks"]
        ),
        "workflows": len(result["workflows"]),
        "workflowPathDefinitions": sum(
            x.get("type") == "workflow-path-definition"
            for x in result["workflows"]
        ),
        "permissions": len(result["permissions"]),
        "reports": len(result["reports"]),
        "cusappMenus": sum(
            str(item.get("kind", "")).startswith("cusapp-")
            for item in result["navigation"].get("menus", [])
        ),
        "integrations": len(result["integrations"]),
        "requiredImportInputs": import_requirements.get("summary", {}).get(
            "requiredInputs", 0
        ),
        "unresolvedRequiredImportInputs": import_requirements.get(
            "summary", {}
        ).get("unresolvedRequiredInputs", 0),
        "optionalImportMappings": import_requirements.get("summary", {}).get(
            "optionalMappings", 0
        ),
        "dependencies": len(result["dependencies"]),
        "unresolved": sum(
            item.get("status") == "unresolved"
            for item in result["dependencies"]
        ),
    }
    dump_json(args.output, result)
    print(json.dumps({"output": str(Path(args.output).resolve()), **result["summary"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
