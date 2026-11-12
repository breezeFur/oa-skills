#!/usr/bin/env python3
"""Parse nested eBuilder ZIP packages into a canonical application IR."""

from __future__ import annotations

import argparse
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


CHUNK_RE = re.compile(r"^(?P<table>.+)-(?P<chunk>[1-9][0-9]*)\.json$")
CUSTOM_MAPPING_RE = re.compile(r"^custom_.+\.json$", re.IGNORECASE)
SERVICE_RE = re.compile(r"^(?P<service>.+?-service)(?:_|$)")
PACKAGE_UNIT_RE = re.compile(
    r"^(?P<name>.+?)_(?P<id>[0-9]{12,})\.zip$", re.IGNORECASE
)
PROFILE_FILE = "profile.json"
IDM_MAPPING_RE = re.compile(r"^KEYS_.+\.idm$", re.IGNORECASE)
MIGRATION_FILE_RE = re.compile(r".+\.(?:idm|sidm)$", re.IGNORECASE)
IDM_FIELDS = (
    "serviceName", "tableName", "sourceId", "exportId", "importId",
    "sourceTargetId", "exportTargetId", "importTargetId",
)
KNOWN_COMPONENT_TABLES = {
    "Condition": "esb_component_condition",
    "MultipleExecution": "esb_component_multi_execute",
    "AssignVar": "esb_action_variable",
    "IncrementVar": "esb_action_variable",
    "ApproveCreate": "esb_approve_create",
    "ApproveCommit": "esb_approve_commit",
    "ApproveSave": "esb_approve_save",
    "Output": "esb_component_output",
    "EbGetDataById": "esb_com_eb_get_data_by_id",
    "PageInteraction": "esb_pageinterantion_action",
    "ActionEbUpdate": "esb_ebuilder_action",
    "ActionEbAdd": "esb_ebuilder_action",
    "ActionEbDelete": "esb_ebuilder_action",
    "ServerlessAction": "esb_action_serverless",
    "CustomTriggerAction": "esb_custom_trigger_action",
    "EnquiryForm": "esb_enquiryform",
    "DMLExecute": "esb_sql_execute",
    "InnerMQSend": "esb_action_inner_mq",
    "SingleCondition": "esb_component_single_condition",
}

COMPONENT_SEMANTICS = {
    "Condition": {
        "meaning": "evaluate a saved workflow-rule condition and route to a branch flow",
        "code": "weaver-esb-server/.../DefaultEsbEngine.java",
    },
    "MultipleExecution": {
        "meaning": "iterate by count, condition, data set, batch, or page and execute a child flow",
        "code": "weaver-esb-component/.../MultipleExecutionComponent.java",
    },
    "AssignVar": {
        "meaning": "evaluate a formula and assign the result to an application variable",
        "code": "weaver-esb-component/.../AssignVarComponent.java",
    },
    "IncrementVar": {
        "meaning": "increment or decrement an application variable and write it to execution context",
        "code": "weaver-esb-component/.../IncrementVarComponent.java",
    },
    "ApproveCreate": {
        "meaning": "create a workflow request with mapped main/detail form data",
        "code": "weaver-esb-component/.../ApproveCreateComponent.java",
    },
    "ApproveCommit": {
        "meaning": "submit an existing workflow request with operator, remark, document, and mapped form data",
        "code": "weaver-esb-component/.../ApproveCommitComponent.java",
    },
    "ApproveSave": {
        "meaning": "save an existing workflow request or workflow form data without normal submission",
        "code": "weaver-esb-component/.../ApproveSaveComponent.java",
    },
    "Output": {
        "meaning": "return status, reminder, page action, and optional custom output; next_action controls continuation",
        "code": "weaver-esb-component/.../OutputComponent.java",
    },
    "EbGetDataById": {
        "meaning": "read one eBuilder record by form and data ID with configured operator and permission behavior",
        "code": "weaver-esb-component/.../EbGetDataByIdComponent.java",
    },
    "PageInteraction": {
        "meaning": "emit page reminder, refresh, close, redirect, or custom page-interaction data",
        "code": "weaver-esb-component/.../PageInteractionComponent.java",
    },
    "ActionEbUpdate": {
        "meaning": "resolve update target and field mappings, then call eBuilder updateFormData",
        "code": "weaver-esb-component/.../EbUpdateComponent.java",
    },
    "ActionEbAdd": {
        "meaning": "resolve field mappings and operator, then call eBuilder saveFormData",
        "code": "weaver-esb-component/.../EbAddComponent.java",
    },
    "ActionEbDelete": {
        "meaning": "resolve target records or conditions, then call eBuilder deleteDatas",
        "code": "weaver-esb-component/.../EbDeleteComponent.java",
    },
    "ServerlessAction": {
        "meaning": "invoke a configured local/cross-service serverless action with mapped request and response parameters",
        "code": "weaver-esb-component/.../ServerlessActionComponent.java",
    },
    "CustomTriggerAction": {
        "meaning": "invoke another enabled ESB action-flow application and map its custom output",
        "code": "weaver-esb-component/.../CustomTriggerActionComponent.java",
    },
    "EnquiryForm": {
        "meaning": "query an eBuilder or configured data source with filters, fields, grouping, ordering, paging, and permission flags",
        "code": "weaver-esb-component/.../EnquiryFormComponent.java",
    },
    "DMLExecute": {
        "meaning": "evaluate SQL parameters and execute saved SQL against the configured data source",
        "code": "weaver-esb-component/.../DMLExecuteComponent.java",
    },
    "InnerMQSend": {
        "meaning": "resolve queue name and payload, then send or broadcast an internal MQ message",
        "code": "weaver-esb-component/.../InnerMQComponent.java",
    },
    "SingleCondition": {
        "meaning": "evaluate one saved condition and enter its configured child flow when satisfied",
        "code": "weaver-esb-component/.../SingleConditionComponent.java",
    },
}

DIRECT_COMPONENT_RELATIONS = {
    "Condition": [
        ("esb_component_condition_item", "component_id"),
    ],
    "ActionEbUpdate": [
        ("esb_ebuilder_action_detail", "action_id"),
        ("esb_ebuilder_action_handle", "action_id"),
        ("esb_ebuilder_action_other", "action_id"),
    ],
    "ActionEbAdd": [
        ("esb_ebuilder_action_detail", "action_id"),
        ("esb_ebuilder_action_handle", "action_id"),
        ("esb_ebuilder_action_other", "action_id"),
    ],
    "ActionEbDelete": [
        ("esb_ebuilder_action_detail", "action_id"),
        ("esb_ebuilder_action_handle", "action_id"),
        ("esb_ebuilder_action_other", "action_id"),
    ],
    "EnquiryForm": [
        ("esb_enquiryform_field", "enquiry_id"),
        ("esb_enquiryform_filter", "enquiry_id"),
        ("esb_enquiryform_condition", "enquiry_id"),
    ],
    "DMLExecute": [
        ("esb_sql_execute_assign", "relation_id"),
    ],
}


def normalize(value: Any, key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {str(k): normalize(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize(item, key) for item in value]
    if (
        isinstance(value, int)
        and value > 1_000_000_000
        and key
        and (
            key == "id"
            or key.endswith("_id")
            or key.endswith("Id")
            or key
            in {
                "applicationId",
                "flowId",
                "actionId",
                "versionId",
                "operator",
                "creator",
                "modifier",
                "updater",
            }
        )
    ):
        return str(value)
    return value


def service_from_name(name: str, inherited: str | None) -> str:
    stem = Path(name).stem
    match = SERVICE_RE.match(stem)
    if match:
        return match.group("service")
    return inherited or "__package__"


def top_level_package_unit(name: str) -> dict[str, str] | None:
    """识别批量包中的顶层应用 ZIP；普通服务 ZIP 不建立额外作用域。"""
    if SERVICE_RE.match(Path(name).stem):
        return None
    match = PACKAGE_UNIT_RE.match(Path(name).name)
    if not match:
        return None
    return {
        "id": match.group("id"),
        "name": match.group("name").strip(" _-"),
        "archiveName": Path(name).name,
    }


def parse_embedded_object(value: Any) -> dict[str, Any]:
    """Parse profile fields that are serialized as JSON strings."""
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def parse_profile_lineage(
    profile: dict[str, Any],
    evidence_path: str,
    depth: int,
) -> dict[str, Any]:
    """Extract migration identity data and the non-secret package export time."""
    homology = parse_embedded_object(profile.get("homologyMarkerField"))
    sub_homology = parse_embedded_object(profile.get("subHomologyMarkerField"))
    sub_old_export = parse_embedded_object(profile.get("subModuleOldExport"))
    export_ietype = parse_embedded_object(profile.get("exportIdIetype"))
    default_ietype = str(profile.get("ietype") or "")

    application_aliases: list[dict[str, Any]] = []
    for current_id, source_id in homology.items():
        if current_id in (None, "") or source_id in (None, ""):
            continue
        current = str(current_id)
        application_aliases.append({
            "currentId": current,
            "sourceId": str(source_id),
            "ietype": str(export_ietype.get(current) or default_ietype),
            "evidencePath": evidence_path,
        })

    submodule_aliases: list[dict[str, Any]] = []
    for main_current_id, group_map in sub_homology.items():
        if not isinstance(group_map, dict):
            continue
        old_group_map = sub_old_export.get(main_current_id)
        if not isinstance(old_group_map, dict):
            old_group_map = {}
        for group_key, aliases in group_map.items():
            if not isinstance(aliases, dict):
                continue
            old_aliases = old_group_map.get(group_key)
            if not isinstance(old_aliases, dict):
                old_aliases = {}
            for current_id, source_id in aliases.items():
                if current_id in (None, "") or source_id in (None, ""):
                    continue
                current = str(current_id)
                submodule_aliases.append({
                    "mainCurrentId": str(main_current_id),
                    "groupKey": str(group_key),
                    "currentId": current,
                    "sourceId": str(source_id),
                    "oldExportId": (
                        str(old_aliases[current])
                        if old_aliases.get(current) not in (None, "")
                        else None
                    ),
                    "evidencePath": evidence_path,
                })

    return {
        "applicationAliases": application_aliases,
        "submoduleAliases": submodule_aliases,
        "evidencePath": evidence_path,
        "depth": depth,
        "exportTime": (
            str(profile.get("exportTime")).strip()
            if profile.get("exportTime") not in (None, "")
            else None
        ),
        "ietype": default_ietype.strip().lower() or None,
        "exportIdIetype": {
            str(key): str(value).strip().lower()
            for key, value in export_ietype.items()
            if key not in (None, "") and value not in (None, "")
        },
    }


def parse_idm_mappings(
    payload: bytes,
    evidence_path: str,
    package_unit: dict[str, str] | None,
    mappings: list[dict[str, Any]],
    diagnostics: list[dict[str, Any]],
) -> None:
    """Parse one KEYS_*.idm JSON array without trusting it as a table chunk."""
    try:
        decoded = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        diagnostics.append({
            "code": "IDM_INVALID_JSON",
            "evidencePath": evidence_path,
            "message": f"KEYS_*.idm JSON parse failed: {exc}",
        })
        return
    if not isinstance(decoded, list):
        diagnostics.append({
            "code": "IDM_NOT_JSON_ARRAY",
            "evidencePath": evidence_path,
            "message": "KEYS_*.idm is not a JSON array",
        })
        return
    for ordinal, raw in enumerate(decoded):
        if not isinstance(raw, dict):
            diagnostics.append({
                "code": "IDM_ENTRY_NOT_OBJECT",
                "evidencePath": evidence_path,
                "recordOrdinal": ordinal,
                "message": "mapping entry is not a JSON object",
            })
            continue
        entry = {
            "packageUnit": package_unit,
            **{
                field: (
                    str(raw.get(field))
                    if raw.get(field) not in (None, "")
                    else None
                )
                for field in IDM_FIELDS
            },
            "evidencePath": evidence_path,
            "recordOrdinal": ordinal,
        }
        missing = [
            field for field in ("serviceName", "tableName", "sourceId")
            if entry.get(field) is None
        ]
        if missing:
            diagnostics.append({
                "code": "IDM_REQUIRED_FIELD_MISSING",
                "evidencePath": evidence_path,
                "recordOrdinal": ordinal,
                "missingFields": missing,
                "message": "mapping entry is incomplete and cannot form strong lineage",
            })
        mappings.append(entry)


def id_equal(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return False
    return str(left) == str(right)


def sorted_rows(rows: list[dict[str, Any]], *keys: str) -> list[dict[str, Any]]:
    def sort_key(row: dict[str, Any]) -> tuple[str, ...]:
        return tuple(str(row.get(key, "")) for key in keys)

    return sorted(rows, key=sort_key)


def walk_scalar_values(value: Any):
    if isinstance(value, dict):
        for child in value.values():
            yield from walk_scalar_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_scalar_values(child)
    elif isinstance(value, str):
        yield value
        stripped = value.strip()
        if stripped.startswith(("{", "[")) and stripped.endswith(("}", "]")):
            try:
                yield from walk_scalar_values(json.loads(stripped))
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
    elif value is not None:
        yield str(value)


def unique_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        key = json.dumps(row, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result


def build_import_requirements(
    package_resources: list[dict[str, Any]],
    modules: dict[str, Any],
) -> dict[str, Any]:
    """Normalize installer pre-process inputs without retaining secret values."""
    required_inputs: list[dict[str, Any]] = []
    optional_inputs: list[dict[str, Any]] = []
    evidence_files: list[str] = []

    for resource in package_resources:
        evidence_files.append(resource["path"])
        for item in resource.get("records", []):
            current_value = str(item.get("currentValue") or "")
            new_value = str(item.get("newValue") or "")
            field_name = str(item.get("customField") or "")
            sensitive = bool(
                "******" in current_value
                or re.search(
                    r"password|secret|token|credential|private[_-]?key",
                    field_name,
                    re.IGNORECASE,
                )
            )
            masked = "******" in current_value
            required = bool(item.get("fieldNotNull"))
            entry = {
                "requirementId": (
                    f"custom:{item.get('serverName') or resource.get('service')}:"
                    f"{item.get('tableName')}:{item.get('dataId')}:"
                    f"{item.get('customField')}"
                ),
                "category": "installer-custom-mapping",
                "service": item.get("serverName") or resource.get("service"),
                "table": item.get("tableName"),
                "dataId": (
                    str(item.get("dataId"))
                    if item.get("dataId") is not None
                    else None
                ),
                "displayName": item.get("displayName"),
                "group": item.get("targetGroup"),
                "field": item.get("customField"),
                "componentType": item.get("componentType") or "text",
                "options": item.get("comboBoxContent") or {},
                "required": required,
                "sensitive": sensitive,
                "sourceValueState": "MASKED" if masked else "AVAILABLE",
                "valueProvided": bool(
                    not sensitive and new_value and "******" not in new_value
                ),
                "status": (
                    "RESOLVED_FROM_PACKAGE"
                    if not sensitive and new_value and "******" not in new_value
                    else "USER_INPUT_REQUIRED" if required else "OPTIONAL_USER_INPUT"
                ),
                "sourceRef": {
                    "path": resource["path"],
                    "kind": "custom-mapping-file",
                },
            }
            (required_inputs if required else optional_inputs).append(entry)

    def all_table_rows(table_name: str) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for module in modules.values():
            result.extend(
                module.get("tables", {})
                .get(table_name, {})
                .get("records", [])
            )
        return result

    optional_mappings: list[dict[str, Any]] = []
    details = all_table_rows("eb_msgpush_pushrule_detail")
    corp_rows = all_table_rows("eb_third_corp")
    agent_rows = all_table_rows("eb_third_agent")
    corp_ids = {str(row.get("id")) for row in corp_rows if row.get("id") is not None}
    agent_ids = {str(row.get("id")) for row in agent_rows if row.get("id") is not None}
    seen_mapping_ids: set[str] = set()

    def add_optional_mapping(
        mapping_type: str,
        source_id: str,
        referenced_by: str | None,
        source_record_included: bool,
    ) -> None:
        requirement_id = f"message-account:{mapping_type}:{source_id}"
        if not source_id or requirement_id in seen_mapping_ids:
            return
        seen_mapping_ids.add(requirement_id)
        optional_mappings.append({
            "requirementId": requirement_id,
            "category": "target-resource-mapping",
            "mappingType": mapping_type,
            "sourceId": source_id,
            "referencedByRuleDetail": referenced_by,
            "sourceRecordIncluded": source_record_included,
            "required": False,
            "status": "OPTIONAL_TARGET_MAPPING",
            "blockingScope": "MESSAGE_CHANNEL_BINDING_ONLY",
            "actionFlowCreationPolicy": "NON_BLOCKING_STAGE_DISABLED",
            "skipAllowed": True,
        })

    for detail in details:
        detail_id = str(detail.get("id")) if detail.get("id") is not None else None
        corp_key = str(detail.get("corp_key") or "").strip()
        add_optional_mapping("message-corporation", corp_key, detail_id, corp_key in corp_ids)
        for agent_key in str(detail.get("agent_keys") or "").split(","):
            agent_key = agent_key.strip()
            add_optional_mapping("message-agent", agent_key, detail_id, agent_key in agent_ids)

    return {
        "schemaVersion": "1.0",
        "evidenceFiles": sorted(set(evidence_files)),
        "requiredInputs": required_inputs,
        "optionalInputs": optional_inputs,
        "optionalMappings": optional_mappings,
        "policy": {
            "collectRequiredInputsBeforeBuild": True,
            "neverPersistSecretValues": True,
            "messageAccountMappingIsNonBlocking": True,
            "unresolvedMessageChannelMode": "CREATE_FLOW_DISABLED_AND_RECORD_PENDING_BINDING",
        },
        "summary": {
            "requiredInputs": len(required_inputs),
            "unresolvedRequiredInputs": sum(
                item["status"] == "USER_INPUT_REQUIRED"
                for item in required_inputs
            ),
            "optionalInputs": len(optional_inputs),
            "optionalMappings": len(optional_mappings),
        },
    }


def component_related_records(
    component_type: str,
    base_rows: list[dict[str, Any]],
    tables: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    related: dict[str, list[dict[str, Any]]] = defaultdict(list)
    base_ids = {str(row.get("id")) for row in base_rows if row.get("id") is not None}

    def add(table_name: str, rows: list[dict[str, Any]]) -> None:
        if rows:
            related[table_name].extend(rows)

    for table_name, foreign_key in DIRECT_COMPONENT_RELATIONS.get(component_type, []):
        add(
            table_name,
            [
                row
                for row in tables.get(table_name, [])
                if str(row.get(foreign_key)) in base_ids
            ],
        )

    if component_type in {"ApproveCommit", "ApproveSave", "ApproveCreate"}:
        form_data_ids = {
            str(row.get("form_data_id"))
            for row in base_rows
            if row.get("form_data_id") not in (None, 0, "0", "")
        }
        form_actions = [
            row
            for row in tables.get("esb_ebuilder_action", [])
            if str(row.get("id")) in form_data_ids
        ]
        add("esb_ebuilder_action", form_actions)
        nested_action_ids = {
            str(row.get("id")) for row in form_actions if row.get("id") is not None
        }
        for table_name in (
            "esb_ebuilder_action_detail",
            "esb_ebuilder_action_handle",
            "esb_ebuilder_action_other",
        ):
            add(
                table_name,
                [
                    row
                    for row in tables.get(table_name, [])
                    if str(row.get("action_id")) in nested_action_ids
                ],
            )

    if component_type == "CustomTriggerAction":
        target_application_ids = {
            str(row.get("esb_flow_id"))
            for row in base_rows
            if row.get("esb_flow_id") is not None
        }
        add(
            "esb_application",
            [
                row
                for row in tables.get("esb_application", [])
                if str(row.get("id")) in target_application_ids
            ],
        )
        custom_output_ids = {
            str(row.get("custom_data_id"))
            for row in base_rows
            if row.get("custom_data_id") is not None
        }
        output_forms = [
            row
            for row in tables.get("custom_outform", [])
            if str(row.get("id")) in custom_output_ids
        ]
        add("custom_outform", output_forms)
        output_form_ids = {
            str(row.get("id")) for row in output_forms if row.get("id") is not None
        }
        output_tables = [
            row
            for row in tables.get("custom_outform_table", [])
            if str(row.get("out_form_id")) in output_form_ids
        ]
        add("custom_outform_table", output_tables)
        add(
            "custom_outform_detail",
            [
                row
                for row in tables.get("custom_outform_detail", [])
                if str(row.get("out_form_id")) in output_form_ids
            ],
        )

    if component_type in {"ServerlessAction", "InnerMQSend"}:
        param_root_ids: set[str] = set()
        for row in base_rows:
            for field in ("request_id", "response_id", "send_params_id"):
                if row.get(field) not in (None, 0, "0", ""):
                    param_root_ids.add(str(row.get(field)))
        root_tables = [
            row
            for row in tables.get("esb_param_table", [])
            if str(row.get("id")) in param_root_ids
        ]
        source_table_ids = {
            str(row.get("source_table"))
            for row in root_tables
            if row.get("source_table") not in (None, 0, "0", "")
        }
        all_param_table_ids = param_root_ids | source_table_ids
        param_tables = [
            row
            for row in tables.get("esb_param_table", [])
            if str(row.get("id")) in all_param_table_ids
        ]
        add("esb_param_table", param_tables)
        add(
            "esb_param_setting",
            [
                row
                for row in tables.get("esb_param_setting", [])
                if str(row.get("table_id")) in all_param_table_ids
            ],
        )
        add(
            "esb_param_mapping",
            [
                row
                for row in tables.get("esb_param_mapping", [])
                if str(row.get("table_id")) in param_root_ids
            ],
        )

    if component_type in {"Condition", "SingleCondition"}:
        component_rows = base_rows + [
            row for rows in related.values() for row in rows
        ]
        condition_ids = {
            str(row.get("condition_id"))
            for row in component_rows
            if row.get("condition_id") not in (None, -1, "-1", 0, "0", "")
        }
        for table_name in (
            "wfr_conditionbase",
            "wfr_expressionbase",
            "wfr_expressions",
            "wfr_maplist",
            "wfr_valuebase",
            "wfr_valuemap",
        ):
            key = "id" if table_name == "wfr_conditionbase" else "conditionid"
            add(
                table_name,
                [
                    row
                    for row in tables.get(table_name, [])
                    if str(row.get(key)) in condition_ids
                ],
            )
        map_base_ids = {
            str(row.get("mapbaseid"))
            for row in related.get("wfr_maplist", [])
            if row.get("mapbaseid") is not None
        }
        add(
            "wfr_mapbase",
            [
                row
                for row in tables.get("wfr_mapbase", [])
                if str(row.get("id")) in map_base_ids
            ],
        )

    scalar_ids = {
        scalar
        for row in base_rows + [row for rows in related.values() for row in rows]
        for scalar in walk_scalar_values(row)
        if scalar.isdigit()
    }
    content_main = [
        row
        for row in tables.get("esb_content_setting_main", [])
        if str(row.get("id")) in scalar_ids
    ]
    add("esb_content_setting_main", content_main)
    content_main_ids = {
        str(row.get("id")) for row in content_main if row.get("id") is not None
    }
    add(
        "esb_content_setting",
        [
            row
            for row in tables.get("esb_content_setting", [])
            if str(row.get("main_id")) in content_main_ids
        ],
    )

    scalar_ids = {
        scalar
        for row in base_rows + [row for rows in related.values() for row in rows]
        for scalar in walk_scalar_values(row)
        if scalar.isdigit()
    }
    formula_rows = [
        row
        for row in tables.get("esb_formula", [])
        if str(row.get("id")) in scalar_ids
    ]
    add("esb_formula", formula_rows)
    formula_ids = {
        str(row.get("id")) for row in formula_rows if row.get("id") is not None
    }
    add(
        "esb_formula_detail",
        [
            row
            for row in tables.get("esb_formula_detail", [])
            if str(row.get("formula_id")) in formula_ids
        ],
    )

    return [
        {
            "table": table_name,
            "records": unique_rows(rows),
        }
        for table_name, rows in sorted(related.items())
        if rows
    ]


def build_esb_index(module: dict[str, Any]) -> dict[str, Any]:
    tables = {
        name: table.get("records", [])
        for name, table in module.get("tables", {}).items()
    }
    applications = tables.get("esb_application", [])
    versions = tables.get("esb_action_flow_version", [])
    events = tables.get("esb_application_event", [])
    flows = tables.get("esb_flow", [])
    actions = tables.get("esb_flow_action", [])
    links = tables.get("esb_flow_action_link", [])
    flow_application_ids = {
        str(row.get("id")): row.get("application_id")
        for row in flows
        if row.get("id") is not None and row.get("application_id") is not None
    }
    for version in versions:
        if version.get("flow_id") is not None and version.get("application_id") is not None:
            flow_application_ids.setdefault(
                str(version.get("flow_id")),
                version.get("application_id"),
            )

    action_flow_apps: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    for app in sorted_rows(applications, "id"):
        app_id = app.get("id")
        app_flows = [
            row
            for row in flows
            if id_equal(row.get("application_id"), app_id)
            or id_equal(flow_application_ids.get(str(row.get("id"))), app_id)
        ]
        app_flow_ids = {str(row.get("id")) for row in app_flows}
        app_actions = [
            row
            for row in actions
            if id_equal(row.get("application_id"), app_id)
            or str(row.get("flow_id")) in app_flow_ids
        ]
        app_action_ids = {str(row.get("id")) for row in app_actions}
        app_links = [
            row
            for row in links
            if any(
                str(row.get(field)) in app_action_ids | app_flow_ids
                for field in (
                    "flow_id",
                    "action_id",
                    "source_id",
                    "target_id",
                    "source_action_id",
                    "target_action_id",
                    "from_action_id",
                    "to_action_id",
                )
                if row.get(field) is not None
            )
        ]
        action_flow_apps.append(
            {
                "application": app,
                "versions": [
                    row for row in versions if id_equal(row.get("application_id"), app_id)
                ],
                "events": [
                    row for row in events if id_equal(row.get("application_id"), app_id)
                ],
                "flows": sorted_rows(app_flows, "id"),
                "actions": sorted(
                    app_actions,
                    key=lambda row: (
                        str(row.get("flow_id", "")),
                        int(row.get("display_order") or 0),
                        str(row.get("id", "")),
                    ),
                ),
                "links": app_links,
            }
        )

    for action in actions:
        component_type = str(action.get("type") or "")
        table_name = KNOWN_COMPONENT_TABLES.get(component_type)
        data_id = action.get("data_id")
        if table_name is None:
            unresolved.append(
                {
                    "actionId": action.get("id"),
                    "componentType": component_type,
                    "dataId": data_id,
                    "reason": "component table mapping is not registered",
                }
            )
            continue
        matches = [
            row
            for row in tables.get(table_name, [])
            if id_equal(row.get("id"), data_id)
        ]
        binding = {
            "actionId": action.get("id"),
            "applicationId": action.get("application_id")
            or flow_application_ids.get(str(action.get("flow_id"))),
            "componentType": component_type,
            "configTable": table_name,
            "dataId": data_id,
            "records": matches,
            "relatedRecords": component_related_records(
                component_type,
                matches,
                tables,
            ),
            "semantics": COMPONENT_SEMANTICS.get(component_type),
        }
        if matches:
            bindings.append(binding)
        else:
            binding["reason"] = "no matching component configuration row"
            unresolved.append(binding)

    return {
        "applications": action_flow_apps,
        "componentBindings": bindings,
        "unresolvedComponentBindings": unresolved,
        "componentTableRegistry": KNOWN_COMPONENT_TABLES,
        "componentSemantics": COMPONENT_SEMANTICS,
    }


def is_active(row: dict[str, Any]) -> bool:
    delete_type = str(row.get("delete_type", 0)).lower()
    is_delete = str(row.get("is_delete", 0)).lower()
    return delete_type in {"", "0", "false", "none"} and is_delete in {
        "",
        "0",
        "false",
        "none",
    }


def row_value(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row and row.get(key) is not None:
            return row.get(key)
    return None


def rows_by(
    rows: list[dict[str, Any]],
    *keys: str,
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        value = row_value(row, *keys)
        if value is not None:
            result[str(value)].append(row)
    return result


def module_table_catalog(
    module: dict[str, Any],
    service: str,
    categories: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        {
            "table": name,
            "category": categories.get(name, "supporting_metadata"),
            "recordCount": len(table.get("records", [])),
            "activeRecordCount": sum(
                1 for row in table.get("records", []) if is_active(row)
            ),
            "sourcePath": f"modules.{service}.tables.{name}.records",
        }
        for name, table in sorted(module.get("tables", {}).items())
    ]


def walk_config(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk_config(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_config(child)


def component_conditions(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for node in walk_config(value):
        if not isinstance(node, dict) or not isinstance(node.get("conditions"), dict):
            continue
        condition = node["conditions"]
        item = {
            "fieldId": node.get("id") or node.get("fieldName"),
            "fieldName": node.get("text"),
            "operator": condition.get("func"),
            "displayValue": condition.get("text"),
            "sourceValue": condition.get("value"),
        }
        key = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            found.append(item)
    return found


def component_links(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for node in walk_config(value):
        if not isinstance(node, dict) or not isinstance(node.get("linkInfo"), dict):
            continue
        link = node["linkInfo"]
        page = link.get("page") if isinstance(link.get("page"), dict) else {}
        item = {
            "openMode": link.get("openMode"),
            "linkType": link.get("type"),
            "pageType": page.get("pageType"),
            "pageId": page.get("pageId"),
            "pageName": page.get("pageName"),
            "fields": [
                {
                    "id": field.get("id"),
                    "name": field.get("text"),
                    "dataKey": (
                        field.get("config", {}).get("dataKey")
                        if isinstance(field.get("config"), dict)
                        else None
                    ),
                }
                for field in link.get("fieldList", [])
                if isinstance(field, dict) and field.get("text")
            ],
        }
        key = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            found.append(item)
    return found


def permission_semantic(target_type: Any) -> str:
    return {
        "11": "EVERYONE",
        "17": "CURRENT_USER",
        "1": "PERSON",
        "10": "ROLE",
        "110": "EXTERNAL_CONTACT",
    }.get(str(target_type), f"TARGET_TYPE_{target_type}")


def normalize_page_component(row: dict[str, Any]) -> dict[str, Any]:
    config = row.get("config") if isinstance(row.get("config"), dict) else {}
    component_type = str(row.get("type") or config.get("type") or "")
    title_value = config.get("title")
    if isinstance(title_value, dict):
        title = title_value.get("nameAlias") or title_value.get("value")
    else:
        title = title_value
    result: dict[str, Any] = {
        "component": row,
        "id": row.get("id"),
        "parentId": row.get("pid"),
        "order": row.get("show_order"),
        "type": component_type,
        "title": title or component_type,
        "conditions": component_conditions(config.get("filter")),
        "actions": component_links(config.get("eventGroup")),
    }

    dataset = config.get("dataset")
    if isinstance(dataset, dict):
        result["dataset"] = {
            "id": dataset.get("id"),
            "name": dataset.get("text"),
            "type": dataset.get("type"),
            "dataPermission": (
                dataset.get("ebuilderDataConfig", {})
                .get("dataSetup", {})
                .get("dataPermission")
            ),
        }

    if component_type == "DigitalPanel":
        result["metrics"] = [
            {
                "title": panel.get("title"),
                "dataset": {
                    "id": (
                        panel.get("dataset", {}).get("id")
                        if isinstance(panel.get("dataset"), dict)
                        else None
                    ),
                    "name": (
                        panel.get("dataset", {}).get("text")
                        if isinstance(panel.get("dataset"), dict)
                        else None
                    ),
                    "type": (
                        panel.get("dataset", {}).get("type")
                        if isinstance(panel.get("dataset"), dict)
                        else None
                    ),
                },
                "fieldId": panel.get("id") or panel.get("fieldName"),
                "fieldName": panel.get("text"),
                "dataKey": (
                    panel.get("config", {}).get("dataKey")
                    if isinstance(panel.get("config"), dict)
                    else None
                ),
                "aggregator": panel.get("aggregator"),
                "conditions": component_conditions(panel),
                "actions": component_links(panel),
            }
            for panel in config.get("panels", [])
            if isinstance(panel, dict)
        ]
    elif component_type in {"Area", "BarStack", "Bar", "Line", "Pie", "Circular", "Scatter"}:
        result["measures"] = [
            {
                "fieldId": item.get("id") or item.get("fieldName"),
                "fieldName": item.get("text"),
                "dataKey": (
                    item.get("config", {}).get("dataKey")
                    if isinstance(item.get("config"), dict)
                    else None
                ),
                "aggregator": item.get("aggregator"),
            }
            for item in config.get("measures", [])
            if isinstance(item, dict)
        ]
        result["dimensions"] = [
            {
                "fieldId": item.get("id") or item.get("fieldName"),
                "fieldName": item.get("text"),
                "dataKey": (
                    item.get("config", {}).get("dataKey")
                    if isinstance(item.get("config"), dict)
                    else None
                ),
            }
            for item in config.get("dimensions", [])
            if isinstance(item, dict)
        ]
    elif component_type == "NavPanel":
        result["menus"] = [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "visible": item.get("show"),
                "actions": component_links(item),
            }
            for item in config.get("menuConfig", [])
            if isinstance(item, dict)
        ]
    elif component_type in {"Tab", "NewTab"}:
        result["tabs"] = [
            {
                "id": item.get("id"),
                "name": item.get("content"),
                "default": item.get("defaultActive"),
                "children": item.get("children", []),
            }
            for item in config.get("tabs", [])
            if isinstance(item, dict)
        ]
    elif component_type == "TabBar":
        result["tabs"] = [
            {
                "id": item.get("id"),
                "name": item.get("label") or item.get("name") or item.get("content"),
                "default": id_equal(item.get("id"), config.get("activeTabId")),
                "actions": component_links(item),
            }
            for item in config.get("items", [])
            if isinstance(item, dict)
        ]
    elif component_type == "WorkflowListTpl":
        result["workflow"] = {
            "searchCategory": config.get("searchCategory"),
            "pageSize": config.get("pageSize"),
            "showCount": config.get("showCount"),
            "pageMode": config.get("pageMode"),
            "fields": [
                {
                    "id": item.get("id"),
                    "name": item.get("text"),
                    "dataKey": (
                        item.get("config", {}).get("dataKey")
                        if isinstance(item.get("config"), dict)
                        else None
                    ),
                }
                for item in config.get("listField", [])
                if isinstance(item, dict) and item.get("text")
            ],
            "detailActions": component_links(config.get("url")),
        }
    return result


def build_ebuilder_page_index(module: dict[str, Any]) -> dict[str, Any]:
    tables = {
        name: table.get("records", [])
        for name, table in module.get("tables", {}).items()
    }

    def rows(name: str) -> list[dict[str, Any]]:
        return [row for row in tables.get(name, []) if is_active(row)]

    component_datasources: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdd_layout_comp_datasource"):
        component_datasources[str(row.get("comp_id"))].append(row)
    component_styles: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdd_layout_component_style"):
        component_styles[str(row.get("component_id"))].append(row)
    list_buttons: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdd_list_button_item"):
        list_buttons[str(row.get("comp_id"))].append(row)
    nav_menu_items: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdd_navmenu_item"):
        nav_menu_items[str(row.get("component_id"))].append(row)
    page_settings = {
        str(row.get("page_id")): row for row in rows("ebdp_page_settings")
    }

    extensions_by_page = {
        str(row.get("page_id")): row for row in rows("ebdd_page_extended")
    }
    layouts_by_extension: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdd_page_layout"):
        layouts_by_extension[str(row.get("page_id"))].append(row)
    components_by_layout: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdd_layout_component"):
        components_by_layout[str(row.get("layout_id"))].append(row)

    page_permissions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdp_page_ph_ebdcomm_view"):
        page_permissions[str(row.get("source_id"))].append(row)

    component_rights = {
        str(row.get("comp_id")): row
        for row in rows("ebdd_layout_component_right")
    }
    permissions_by_right: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdd_layout_c_ph_ebdcomm_view"):
        permissions_by_right[str(row.get("source_id"))].append(row)

    logic_refs: dict[str, dict[str, Any]] = defaultdict(dict)
    for row in rows("logic_flow_ref"):
        logic_refs[str(row.get("refer_id"))][str(row.get("ref_key"))] = row.get("ref_value")
    logic_by_page: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("logic_flow"):
        refs = logic_refs.get(str(row.get("refer_id")), {})
        page_id = str(refs.get("pageId") or "")
        logic_by_page[page_id].append({
            "logic": row,
            "references": refs,
        })

    normalized_pages: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    def normalize_extension_layouts(extension: dict[str, Any]) -> list[dict[str, Any]]:
        normalized_layouts = []
        for layout in sorted(
            layouts_by_extension.get(str(extension.get("id")), []),
            key=lambda row: (str(row.get("terminal_type", "")), str(row.get("id", ""))),
        ):
            layout_id = str(layout.get("id"))
            source_code = str(layout.get("source_code") or "")
            components = [
                normalize_page_component(row)
                for row in sorted(
                    components_by_layout.get(layout_id, []),
                    key=lambda row: (int(row.get("show_order") or 0), str(row.get("id", ""))),
                )
            ]
            for component in components:
                right = component_rights.get(str(component.get("id")))
                raw_permissions = (
                    permissions_by_right.get(str(right.get("id")), [])
                    if right
                    else []
                )
                component["permissions"] = [
                    {
                        "semantic": permission_semantic(row.get("target_type")),
                        "permission": row,
                    }
                    for row in raw_permissions
                ]
                component_id = str(component.get("id"))
                component["dataSourceBindings"] = component_datasources.get(
                    component_id, []
                )
                component["styleBindings"] = component_styles.get(component_id, [])
                component["listButtonItems"] = list_buttons.get(component_id, [])
                component["navMenuItems"] = nav_menu_items.get(component_id, [])
            normalized_layouts.append({
                "layout": layout,
                "id": layout.get("id"),
                "terminal": layout.get("terminal_type"),
                "ecodeVersion": layout.get("ecode_version"),
                "runtimeCodeEvidence": {
                    "sourceCodeLength": len(source_code),
                    "hasEcode": '"ecode"' in source_code or "%22ecode%22" in source_code,
                    "hasJavaScript": (
                        "js" in (layout.get("config", {}).get("ebCodeFileTypes", []) if isinstance(layout.get("config"), dict) else [])
                        or "%22js%22" in source_code
                    ),
                    "hasCssCache": "cssCache" in source_code,
                },
                "components": components,
            })
        return normalized_layouts

    for page in sorted(
        rows("ebdp_page"),
        key=lambda row: (str(row.get("appid", "")), int(row.get("show_order") or 0), str(row.get("id", ""))),
    ):
        page_id = str(page.get("id"))
        extension = extensions_by_page.get(page_id)
        if extension is None:
            unresolved.append({
                "kind": "page_extension",
                "sourceId": page.get("id"),
                "reason": "no active ebdd_page_extended row",
            })
            extension = {}
        normalized_layouts = normalize_extension_layouts(extension)
        normalized_pages.append({
            "page": page,
            "id": page.get("id"),
            "applicationId": page.get("appid"),
            "name": page.get("name"),
            "order": page.get("show_order"),
            "terminalScope": page.get("terminal_scope"),
            "enabled": page.get("is_enabled"),
            "readOnly": page.get("read_only"),
            "settings": page_settings.get(page_id, {}),
            "extension": extension,
            "permissions": [
                {
                    "semantic": permission_semantic(row.get("target_type")),
                    "permission": row,
                }
                for row in page_permissions.get(page_id, [])
            ],
            "logicFlows": logic_by_page.get(page_id, []),
            "layouts": normalized_layouts,
        })

    pages_by_app: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for page in normalized_pages:
        pages_by_app[str(page.get("applicationId"))].append(page)
    navigation_by_app: dict[str, list[dict[str, Any]]] = defaultdict(list)
    navigation_app_by_id: dict[str, str] = {}
    for navigation in rows("ebda_app_navigation"):
        navigation_app_id = str(navigation.get("appid"))
        navigation_by_app[navigation_app_id].append(navigation)
        navigation_app_by_id[str(navigation.get("id"))] = navigation_app_id
    page_groups_by_app: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for group in rows("ebdp_page_group"):
        page_groups_by_app[str(group.get("appid"))].append(group)
    menu_combinations_by_app: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for combination in rows("ebda_app_menu_comb"):
        menu_combinations_by_app[str(combination.get("app_id"))].append(combination)
    menus_by_app: dict[str, list[dict[str, Any]]] = defaultdict(list)
    menu_permissions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for permission in rows("ebda_app_menu_ph_ebdcomm_view"):
        menu_permissions[str(permission.get("source_id"))].append(permission)
    for menu in rows("ebda_app_menu"):
        menu_copy = dict(menu)
        menu_copy["permissions"] = menu_permissions.get(str(menu.get("id")), [])
        app_id = navigation_app_by_id.get(str(menu.get("nav_id")))
        if not app_id:
            combination = next(
                (
                    row
                    for row in rows("ebda_app_menu_comb")
                    if id_equal(row.get("id"), menu.get("combination_id"))
                ),
                {},
            )
            app_id = combination.get("app_id")
        if app_id is None:
            app_id = menu.get("remote_app_id")
        menus_by_app[str(app_id)].append(menu_copy)

    embedded_views_by_app: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for extension in rows("ebdd_page_extended"):
        if str(extension.get("belong_module")) == "EB_PAGE":
            continue
        app_id = str(extension.get("app_id") or "")
        embedded_views_by_app[app_id].append({
            "id": extension.get("page_id"),
            "applicationId": extension.get("app_id"),
            "belongModule": extension.get("belong_module"),
            "extension": extension,
            "layouts": normalize_extension_layouts(extension),
        })

    known_page_ids = {str(page.get("id")) for page in rows("ebdp_page")}
    unattached_page_settings = [
        setting
        for setting in rows("ebdp_page_settings")
        if str(setting.get("page_id")) not in known_page_ids
    ]
    datasets_by_app: dict[str, list[dict[str, Any]]] = defaultdict(list)
    dataset_connections: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for relation in rows("dataset_connection_relation"):
        dataset_connections[str(relation.get("dataset_id"))].append(relation)
    for dataset_row in rows("dataset"):
        dataset_copy = dict(dataset_row)
        dataset_copy["connections"] = dataset_connections.get(
            str(dataset_row.get("id")), []
        )
        dataset_app_ids = {
            str(page.get("applicationId"))
            for page in normalized_pages
            for layout in page.get("layouts", [])
            for component in layout.get("components", [])
            if any(
                id_equal(binding.get("datasource_id"), dataset_row.get("id"))
                for binding in component.get("dataSourceBindings", [])
            )
        }
        if not dataset_app_ids:
            dataset_app_ids = {str(app.get("id")) for app in rows("ebda_app")}
        for dataset_app_id in dataset_app_ids:
            datasets_by_app[dataset_app_id].append(dataset_copy)

    applications = []
    known_app_ids = set()
    for app in sorted(rows("ebda_app"), key=lambda row: str(row.get("id", ""))):
        app_id = str(app.get("id"))
        known_app_ids.add(app_id)
        app_pages = pages_by_app.get(app_id, [])
        embedded_views = embedded_views_by_app.get(app_id, [])
        applications.append({
            "application": app,
            "navigation": navigation_by_app.get(app_id, []),
            "pageGroups": page_groups_by_app.get(app_id, []),
            "menuCombinations": menu_combinations_by_app.get(app_id, []),
            "menus": sorted_rows(menus_by_app.get(app_id, []), "show_order", "id"),
            "datasets": datasets_by_app.get(app_id, []),
            "pages": app_pages,
            "embeddedViews": embedded_views,
            "unattachedPageSettings": unattached_page_settings,
            "statistics": {
                "pages": len(app_pages),
                "embeddedViews": len(embedded_views),
                "layouts": sum(len(page["layouts"]) for page in app_pages),
                "components": sum(
                    len(layout["components"])
                    for page in app_pages
                    for layout in page["layouts"]
                ),
                "embeddedViewLayouts": sum(
                    len(view["layouts"]) for view in embedded_views
                ),
                "embeddedViewComponents": sum(
                    len(layout["components"])
                    for view in embedded_views
                    for layout in view["layouts"]
                ),
                "componentTypes": dict(Counter(
                    component["type"]
                    for page in app_pages
                    for layout in page["layouts"]
                    for component in layout["components"]
                )),
            },
        })
    for setting in unattached_page_settings:
        unresolved.append({
            "kind": "page_setting",
            "sourceId": setting.get("id"),
            "pageId": setting.get("page_id"),
            "reason": "active setting references a page absent from active ebdp_page rows; preserved as unattachedPageSettings",
        })
    for app_id, app_pages in pages_by_app.items():
        if app_id and app_id not in known_app_ids:
            unresolved.append({
                "kind": "application",
                "sourceId": app_id,
                "pageIds": [page["id"] for page in app_pages],
                "reason": "pages reference an application absent from active ebda_app rows",
            })

    def app_table_category(name: str) -> str:
        if name.startswith(("i18n_", "ebuilder_")) and "packing" not in name:
            return "localization_metadata"
        if name.startswith("dataset"):
            return "dataset"
        if name.startswith("ebda_"):
            return "application_navigation"
        if name.startswith("ebdp_"):
            return "page"
        if name.startswith("ebdd_"):
            return "page_layout_component"
        if "packing" in name:
            return "migration_metadata"
        return "supporting_metadata"

    return {
        "applications": applications,
        "unresolvedReferences": unresolved,
        "recordCounts": {
            name: len(table_rows) for name, table_rows in sorted(tables.items())
        },
        "tableCatalog": [
            {
                "table": name,
                "category": app_table_category(name),
                "recordCount": len(table_rows),
                "activeRecordCount": sum(1 for row in table_rows if is_active(row)),
                "sourcePath": (
                    f"modules.weaver-ebuilder-app-service.tables.{name}.records"
                ),
            }
            for name, table_rows in sorted(tables.items())
        ],
    }


def build_ebuilder_form_index(module: dict[str, Any]) -> dict[str, Any]:
    tables = {
        name: table.get("records", [])
        for name, table in module.get("tables", {}).items()
    }

    def rows(name: str) -> list[dict[str, Any]]:
        return tables.get(name, [])

    forms_by_id = {str(row.get("id")): row for row in rows("form")}
    eb_fields_by_id = {str(row.get("id")): row for row in rows("ebdf_field")}
    child_fields_by_id = {
        str(row.get("id")): row for row in rows("ebdf_child_form_field")
    }

    table_fields_by_field: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("form_table_field"):
        table_fields_by_field[str(row.get("field_id"))].append(row)

    options_by_field: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("field_option"):
        if is_active(row):
            options_by_field[str(row.get("field_id"))].append(row)

    actions_by_button: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdf_button_action"):
        actions_by_button[str(row.get("button_id"))].append(row)

    button_permissions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdf_button_permission"):
        button_permissions[str(row.get("button_id"))].append(row)

    list_fields: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdf_list_field"):
        list_fields[str(row.get("list_id"))].append(row)

    list_permissions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdf_list_permission"):
        list_permissions[str(row.get("list_id"))].append(row)

    association_actions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdf_association_action"):
        association_actions[str(row.get("association_id"))].append(row)

    association_permissions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdf_association_permission"):
        association_permissions[str(row.get("association_id"))].append(row)

    esb_trigger_positions_by_button: dict[str, list[dict[str, Any]]] = defaultdict(list)
    esb_trigger_positions_by_scene: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdf_esb_triggerposition"):
        esb_trigger_positions_by_button[str(row.get("button_id"))].append(row)
        esb_trigger_positions_by_scene[str(row.get("esb_scene_id"))].append(row)
    esb_action_list_by_action: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdf_button_esb_list"):
        esb_action_list_by_action[str(row.get("action_id"))].append(row)

    list_filters: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdf_list_filter"):
        list_filters[str(row.get("list_id"))].append(row)
    list_filter_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdf_list_filter_group"):
        list_filter_groups[str(row.get("target_id"))].append(row)
    list_orders: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdf_list_order"):
        list_orders[str(row.get("list_id"))].append(row)
    list_line_actions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdf_list_line_action"):
        list_line_actions[str(row.get("list_id"))].append(row)
    list_field_actions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdf_list_field_action"):
        list_field_actions[str(row.get("list_field_id"))].append(row)
    list_code_blocks: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdf_codeblock"):
        list_code_blocks[str(row.get("view_id"))].append(row)

    trigger_rules: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("ebdf_trigger_rule"):
        trigger_rules[str(row.get("triggerid"))].append(row)
    field_permission_details: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("field_permission_detail"):
        field_permission_details[str(row.get("permission_id"))].append(row)
    view_linkage_details: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("form_view_linkage_detail"):
        view_linkage_details[str(row.get("ref_linkage_id"))].append(row)
    condition_details: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("form_condition_detail"):
        condition_details[str(row.get("condition_id"))].append(row)

    workflow_nodes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    workflow_links: dict[str, list[dict[str, Any]]] = defaultdict(list)
    workflow_charts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    workflow_node_menus: dict[str, list[dict[str, Any]]] = defaultdict(list)
    workflow_java_actions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("wfp_node"):
        workflow_nodes[str(row.get("workflowid"))].append(row)
    for row in rows("wfp_link"):
        workflow_links[str(row.get("workflowid"))].append(row)
    for row in rows("wfp_chart"):
        workflow_charts[str(row.get("workflowid"))].append(row)
    for row in rows("wfp_node_menu"):
        workflow_node_menus[str(row.get("workflowid"))].append(row)
    for row in rows("ebdf_java_action"):
        workflow_java_actions[str(row.get("ref_id"))].append(row)
    workflow_base_by_id = {
        str(row.get("id")): row for row in rows("wfp_base")
    }

    linkage_monitor_actions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    linkage_monitor_fields: dict[str, list[dict[str, Any]]] = defaultdict(list)
    linkage_extensions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    linkage_sources: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source_configs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source_config_columns: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source_config_tables: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source_esb: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source_excel: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source_mappings: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source_sql: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source_sql_columns: dict[str, list[dict[str, Any]]] = defaultdict(list)
    linkage_effects: dict[str, list[dict[str, Any]]] = defaultdict(list)
    effect_values: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows("fd_linkage_monitor_action"):
        linkage_monitor_actions[str(row.get("entity_id"))].append(row)
    for row in rows("fd_linkage_monitor_field"):
        linkage_monitor_fields[str(row.get("entity_id"))].append(row)
    for row in rows("fd_linkage_ext"):
        linkage_extensions[str(row.get("entity_id"))].append(row)
    for row in rows("fd_linkage_source"):
        linkage_sources[str(row.get("entity_id"))].append(row)
    for row in rows("fd_linkage_source_config"):
        source_configs[str(row.get("entity_id"))].append(row)
    for row in rows("fd_linkage_source_config_col"):
        source_config_columns[str(row.get("entity_id"))].append(row)
    for row in rows("fd_linkage_source_config_table"):
        source_config_tables[str(row.get("entity_id"))].append(row)
    for row in rows("fd_linkage_source_esb"):
        source_esb[str(row.get("entity_id"))].append(row)
    for row in rows("fd_linkage_source_excel"):
        source_excel[str(row.get("entity_id"))].append(row)
    for row in rows("fd_linkage_source_mapping"):
        source_mappings[str(row.get("entity_id"))].append(row)
    for row in rows("fd_linkage_source_sql"):
        source_sql[str(row.get("entity_id"))].append(row)
    for row in rows("fd_linkage_source_sql_column"):
        source_sql_columns[str(row.get("entity_id"))].append(row)
    for row in rows("fd_effect"):
        linkage_effects[str(row.get("ref_id"))].append(row)
    for row in rows("fd_effect_value"):
        effect_values[str(row.get("effect_id"))].append(row)

    form_entries: list[dict[str, Any]] = []
    for obj in sorted(
        rows("ebdf_obj"),
        key=lambda row: (
            int(row.get("show_order") or 0),
            str(row.get("id", "")),
        ),
    ):
        obj_id = str(obj.get("id"))
        form_id = str(obj.get("form_id"))
        form = forms_by_id.get(form_id)
        if form is None:
            form = next(
                (
                    row
                    for row in rows("form")
                    if id_equal(row.get("target_id"), obj.get("id"))
                ),
                {},
            )
            form_id = str(form.get("id", form_id))

        form_fields = [
            row for row in rows("form_field")
            if id_equal(row.get("form_id"), form_id)
        ]
        active_fields = [row for row in form_fields if is_active(row)]
        deleted_fields = [row for row in form_fields if not is_active(row)]
        sub_forms = [
            row for row in rows("sub_form")
            if id_equal(row.get("form_id"), form_id) and is_active(row)
        ]
        sub_form_ids = {str(row.get("id")) for row in sub_forms}
        main_fields = [
            row for row in active_fields
            if str(row.get("sub_form_id")) not in sub_form_ids
        ]
        detail_fields = [
            row for row in active_fields
            if str(row.get("sub_form_id")) in sub_form_ids
        ]

        def field_entry(field: dict[str, Any]) -> dict[str, Any]:
            field_id = str(field.get("id"))
            return {
                "field": field,
                "ebuilderExtension": (
                    eb_fields_by_id.get(field_id)
                    or child_fields_by_id.get(field_id)
                ),
                "physicalMappings": table_fields_by_field.get(field_id, []),
                "options": sorted_rows(
                    options_by_field.get(field_id, []),
                    "order",
                    "id",
                ),
            }

        layout_versions = [
            row for row in rows("form_layout_version")
            if id_equal(row.get("form_id"), form_id) and is_active(row)
        ]
        version_ids = {str(row.get("id")) for row in layout_versions}
        page_extensions = [
            row for row in rows("ebdd_page_extended")
            if str(row.get("page_id")) in version_ids and is_active(row)
        ]
        extension_ids = {str(row.get("id")) for row in page_extensions}
        page_layouts = [
            row for row in rows("ebdd_page_layout")
            if str(row.get("page_id")) in extension_ids and is_active(row)
        ]
        page_layout_ids = {str(row.get("id")) for row in page_layouts}
        layout_components = [
            row for row in rows("ebdd_layout_component")
            if str(row.get("layout_id")) in page_layout_ids and is_active(row)
        ]

        form_lists = [
            row for row in rows("ebdf_list")
            if id_equal(row.get("obj_id"), obj.get("id")) and is_active(row)
        ]
        normalized_lists = []
        for list_row in form_lists:
            list_id = str(list_row.get("id"))
            normalized_list_fields = sorted(
                list_fields[list_id],
                key=lambda row: (
                    1 if str(row.get("ismobile")) == "1" else 0,
                    int(row.get("showorder") or 0),
                    str(row.get("id", "")),
                ),
            )
            normalized_lists.append({
                "list": list_row,
                "fields": normalized_list_fields,
                "fieldActions": [
                    {
                        "listField": list_field,
                        "actions": sorted_rows(
                            list_field_actions.get(str(list_field.get("id")), []),
                            "show_order",
                            "id",
                        ),
                    }
                    for list_field in normalized_list_fields
                    if list_field_actions.get(str(list_field.get("id")))
                ],
                "lineActions": sorted_rows(
                    list_line_actions.get(list_id, []), "show_order", "id"
                ),
                "filters": sorted_rows(
                    list_filters.get(list_id, []), "showorder", "id"
                ),
                "filterGroups": list_filter_groups.get(list_id, []),
                "orders": sorted_rows(
                    list_orders.get(list_id, []), "showorder", "id"
                ),
                "runtimeCode": list_code_blocks.get(list_id, []),
                "permissions": list_permissions[list_id],
            })

        form_buttons = [
            row for row in rows("ebdf_button")
            if id_equal(row.get("obj_id"), obj.get("id")) and is_active(row)
        ]
        normalized_buttons = []
        for button in form_buttons:
            button_id = str(button.get("id"))
            normalized_actions = sorted(
                actions_by_button[button_id],
                key=lambda row: (
                    int(row.get("show_order") or 0),
                    str(row.get("id", "")),
                ),
            )
            normalized_buttons.append({
                "button": button,
                "actions": normalized_actions,
                "esbActions": [
                    esb_action
                    for action in normalized_actions
                    for esb_action in esb_action_list_by_action.get(
                        str(action.get("id")), []
                    )
                ],
                "esbTriggerPositions": esb_trigger_positions_by_button.get(
                    button_id, []
                ),
                "permissions": button_permissions[button_id],
            })

        form_associations = [
            row for row in rows("ebdf_data_association")
            if id_equal(row.get("obj_id"), obj.get("id")) and is_active(row)
        ]
        normalized_associations = []
        for association in form_associations:
            association_id = str(association.get("id"))
            normalized_associations.append({
                "association": association,
                "actions": association_actions[association_id],
                "permissions": association_permissions[association_id],
            })

        main_tables = [
            row for row in rows("form_table")
            if id_equal(row.get("form_id"), form_id) and is_active(row)
        ]
        detail_tables = [
            row for row in rows("form_table")
            if str(row.get("form_id")) in sub_form_ids and is_active(row)
        ]
        physical_table_name = str(obj.get("table_name") or "")

        form_linkages = []
        for linkage in [
            row
            for row in rows("fd_linkage")
            if id_equal(row.get("form_id"), form_id)
        ]:
            linkage_id = str(linkage.get("id"))
            monitors = []
            for monitor in linkage_monitor_actions.get(linkage_id, []):
                monitor_copy = dict(monitor)
                monitor_copy["fields"] = linkage_monitor_fields.get(
                    str(monitor.get("id")), []
                )
                monitors.append(monitor_copy)
            sources = []
            for source in linkage_sources.get(linkage_id, []):
                source_id = str(source.get("id"))
                configs = []
                for config in source_configs.get(source_id, []):
                    config_copy = dict(config)
                    config_id = str(config.get("id"))
                    config_copy["columns"] = source_config_columns.get(config_id, [])
                    config_copy["tables"] = source_config_tables.get(config_id, [])
                    configs.append(config_copy)
                sql_configs = []
                for sql_config in source_sql.get(source_id, []):
                    sql_copy = dict(sql_config)
                    sql_copy["columns"] = source_sql_columns.get(
                        str(sql_config.get("id")), []
                    )
                    sql_configs.append(sql_copy)
                source_copy = dict(source)
                source_copy.update({
                    "configs": configs,
                    "esbConfigs": source_esb.get(source_id, []),
                    "excelConfigs": source_excel.get(source_id, []),
                    "mappings": source_mappings.get(source_id, []),
                    "sqlConfigs": sql_configs,
                })
                sources.append(source_copy)
            effects = []
            for effect in linkage_effects.get(linkage_id, []):
                effect_copy = dict(effect)
                effect_copy["values"] = effect_values.get(str(effect.get("id")), [])
                effects.append(effect_copy)
            linkage_copy = dict(linkage)
            linkage_copy.update({
                "extensions": linkage_extensions.get(linkage_id, []),
                "monitors": monitors,
                "sources": sources,
                "effects": effects,
            })
            form_linkages.append(linkage_copy)

        form_view_linkages = []
        for linkage in [
            row
            for row in rows("form_view_linkage")
            if id_equal(row.get("form_id"), form_id)
        ]:
            linkage_copy = dict(linkage)
            condition_id = str(linkage.get("condition_id"))
            condition = next(
                (
                    row
                    for row in rows("form_condition")
                    if id_equal(row.get("id"), condition_id)
                ),
                {},
            )
            linkage_copy["details"] = view_linkage_details.get(
                str(linkage.get("id")), []
            )
            linkage_copy["condition"] = {
                "base": condition,
                "details": condition_details.get(condition_id, []),
            }
            form_view_linkages.append(linkage_copy)

        workflow_bindings = []
        for workflow_ref in [
            row
            for row in rows("ebdf_app_ref_workflow")
            if id_equal(row.get("relatekey"), form_id)
        ]:
            workflow_id = str(workflow_ref.get("workflowid"))
            workflow_bindings.append({
                "binding": workflow_ref,
                "workflow": workflow_base_by_id.get(workflow_id, {}),
                "nodes": workflow_nodes.get(workflow_id, []),
                "links": workflow_links.get(workflow_id, []),
                "charts": workflow_charts.get(workflow_id, []),
                "nodeMenus": workflow_node_menus.get(workflow_id, []),
                "javaActions": workflow_java_actions.get(workflow_id, []),
            })

        form_esb_scenes = []
        for scene in [
            row
            for row in rows("ebdf_button_esb")
            if id_equal(row.get("source_id"), obj.get("id"))
        ]:
            scene_copy = dict(scene)
            scene_copy["triggerPositions"] = esb_trigger_positions_by_scene.get(
                str(scene.get("id")), []
            )
            form_esb_scenes.append(scene_copy)

        message_triggers = []
        for trigger in [
            row
            for row in rows("ebdf_trigger_base")
            if id_equal(row.get("formid"), obj.get("id"))
        ]:
            trigger_copy = dict(trigger)
            trigger_copy["rules"] = trigger_rules.get(str(trigger.get("id")), [])
            message_triggers.append(trigger_copy)

        form_field_permissions = []
        for permission in [
            row
            for row in rows("field_permission")
            if id_equal(row.get("form_id"), form_id)
        ]:
            permission_copy = dict(permission)
            permission_copy["details"] = field_permission_details.get(
                str(permission.get("id")), []
            )
            form_field_permissions.append(permission_copy)

        form_entries.append({
            "object": obj,
            "form": form,
            "mainFields": [field_entry(row) for row in main_fields],
            "deletedFields": [field_entry(row) for row in deleted_fields],
            "subForms": [
                {
                    "subForm": sub_form,
                    "fields": [
                        field_entry(row)
                        for row in detail_fields
                        if id_equal(row.get("sub_form_id"), sub_form.get("id"))
                    ],
                    "physicalTables": [
                        row
                        for row in detail_tables
                        if id_equal(row.get("form_id"), sub_form.get("id"))
                    ],
                }
                for sub_form in sub_forms
            ],
            "storage": {
                "mainTables": main_tables,
                "packagedFormdataCount": sum(
                    1
                    for row in rows("formdata")
                    if id_equal(row.get("form_id"), form_id) and is_active(row)
                ),
                "packagedPhysicalRowCount": len(rows(physical_table_name)),
            },
            "layouts": {
                "multiple": [
                    row for row in rows("form_layout_multiple")
                    if id_equal(row.get("form_id"), form_id) and is_active(row)
                ],
                "versions": layout_versions,
                "styles": [
                    row for row in rows("form_style")
                    if id_equal(row.get("form_id"), form_id) and is_active(row)
                ],
                "pageExtensions": page_extensions,
                "pageLayouts": page_layouts,
                "components": layout_components,
                "fieldRelations": [
                    row for row in rows("form_view_relate_config")
                    if str(row.get("version_id")) in version_ids and is_active(row)
                ],
            },
            "lists": normalized_lists,
            "buttons": normalized_buttons,
            "permissions": [
                row for row in rows("ebdf_permission")
                if id_equal(row.get("belong_id"), obj.get("id")) and is_active(row)
            ],
            "associations": normalized_associations,
            "esbScenes": form_esb_scenes,
            "messageTriggers": message_triggers,
            "fieldPermissions": form_field_permissions,
            "dataLinkages": form_linkages,
            "fieldEffects": [
                {
                    **effect,
                    "values": effect_values.get(str(effect.get("id")), []),
                }
                for effect in rows("fd_effect")
                if id_equal(effect.get("form_id"), form_id)
            ],
            "viewLinkages": form_view_linkages,
            "workflowBindings": workflow_bindings,
            "options": [
                row for row in rows("ebdf_option")
                if id_equal(row.get("obj_id"), obj.get("id")) and is_active(row)
            ],
            "marksets": [
                row for row in rows("ebdf_markset")
                if id_equal(row.get("obj_id"), obj.get("id")) and is_active(row)
            ],
            "thirdPartyConfigs": [
                row for row in rows("ebdf_obj_tpa_config")
                if id_equal(row.get("obj_id"), obj.get("id")) and is_active(row)
            ],
            "thirdPartyDetails": [
                row for row in rows("ebdf_obj_tpa_dt_config")
                if id_equal(row.get("obj_id"), obj.get("id")) and is_active(row)
            ],
            "viewThirdPartyConfigs": [
                row for row in rows("ebdf_view_tpa_config")
                if id_equal(row.get("obj_id"), obj.get("id")) and is_active(row)
            ],
            "additionalSettings": {
                "base": [
                    row for row in rows("form_base_setting")
                    if id_equal(row.get("form_id"), form_id) and is_active(row)
                ],
                "attachments": [
                    row for row in rows("form_attachment_config")
                    if id_equal(row.get("form_id"), form_id) and is_active(row)
                ],
                "importExport": [
                    row for row in rows("ebdf_import_export_setting")
                    if id_equal(row.get("obj_id"), obj.get("id")) and is_active(row)
                ],
                "distribution": [
                    row for row in rows("ebdf_distribute")
                    if id_equal(row.get("obj_id"), obj.get("id")) and is_active(row)
                ],
                "comments": [
                    row for row in rows("ebdf_comment_relate")
                    if id_equal(row.get("obj_id"), obj.get("id")) and is_active(row)
                ],
                "gantt": [
                    row for row in rows("ebdf_gantt_chart")
                    if id_equal(row.get("obj_id"), obj.get("id")) and is_active(row)
                ],
                "dataRelations": [
                    row for row in rows("form_data_relate_config")
                    if (
                        id_equal(row.get("form_id"), form_id)
                        or str(row.get("version_id")) in version_ids
                    )
                    and is_active(row)
                ],
                "subFormConfigs": [
                    row for row in rows("sub_form_config")
                    if (
                        str(row.get("sub_form_id")) in sub_form_ids
                        or str(row.get("version_id")) in version_ids
                    )
                    and is_active(row)
                ],
            },
        })

    physical_table_names = {
        str(obj.get("table_name"))
        for obj in rows("ebdf_obj")
        if obj.get("table_name")
    }

    def form_table_category(name: str) -> str:
        if name in physical_table_names or name.startswith("uf_"):
            return "packaged_business_or_seed_data"
        if name.startswith(("wfp_", "wf_", "wfr_", "virtual_wfp_")) or name.startswith(
            "custom_outform"
        ):
            return "workflow_configuration"
        if name.startswith(("i18n_", "ebuilder_form_multilang", "dw_multilang")):
            return "localization_metadata"
        if name.startswith(("fd_", "express_formula")):
            return "linkage_formula"
        if name.startswith(("dataset", "panel_field")):
            return "dataset"
        if "browser" in name:
            return "browser_reference"
        if name.startswith(("ebdf_", "form", "field_", "sub_form")):
            return "form_configuration"
        if name.startswith(("govern_", "publishkit_", "auth_role", "custom_func")):
            return "domain_or_runtime_dependency"
        return "supporting_metadata"

    return {
        "forms": form_entries,
        "global": {
            "messageGroups": rows("ebdf_app_messagegroup"),
        },
        "recordCounts": {
            name: len(table_rows) for name, table_rows in sorted(tables.items())
        },
        "tableCatalog": [
            {
                "table": name,
                "category": form_table_category(name),
                "recordCount": len(table_rows),
                "activeRecordCount": sum(1 for row in table_rows if is_active(row)),
                "sourcePath": (
                    f"modules.weaver-ebuilder-form-service.tables.{name}.records"
                ),
            }
            for name, table_rows in sorted(tables.items())
        ],
    }


def build_edc_multi_filling_index(module: dict[str, Any]) -> dict[str, Any]:
    tables = {
        name: table.get("records", [])
        for name, table in module.get("tables", {}).items()
    }

    def rows(name: str) -> list[dict[str, Any]]:
        return [row for row in tables.get(name, []) if is_active(row)]

    nodes_by_task = rows_by(rows("edc_multi_task_node"), "task_id", "taskId")
    edges_by_task = rows_by(rows("edc_multi_task_edge"), "task_id", "taskId")
    executions_by_task = rows_by(
        rows("edc_multi_task_execution"), "task_id", "taskId"
    )
    permissions_by_execution = rows_by(
        rows("edc_multi_task_execution_ph_ec"), "source_id", "sourceId"
    )
    configs_by_execution = rows_by(
        rows("edc_multi_execution_config"), "execution_id", "executionId"
    )
    tasks = rows("edc_multi_report_task")
    task_ids = {str(row.get("id")) for row in tasks}
    unresolved: list[dict[str, Any]] = []
    task_entries: list[dict[str, Any]] = []

    for task in sorted_rows(tasks, "id"):
        task_id = str(task.get("id"))
        task_nodes = nodes_by_task.get(task_id, [])
        task_node_ids = {str(row.get("id")) for row in task_nodes}
        task_edges = edges_by_task.get(task_id, [])
        task_executions = executions_by_task.get(task_id, [])
        normalized_edges = []
        for edge in task_edges:
            source_id = row_value(edge, "edge_source", "edgeSource", "source_id")
            target_id = row_value(edge, "target", "target_id", "targetId")
            missing = [
                {"side": side, "nodeId": value}
                for side, value in (("source", source_id), ("target", target_id))
                if value not in (None, "", 0, "0")
                and str(value) not in task_node_ids
            ]
            if missing:
                unresolved.append({
                    "kind": "task_edge",
                    "taskId": task.get("id"),
                    "edgeId": edge.get("id"),
                    "missing": missing,
                    "reason": "edge endpoint is absent from the same task",
                })
            normalized_edges.append({"edge": edge, "missingEndpoints": missing})

        normalized_executions = []
        for execution in task_executions:
            execution_id = str(execution.get("id"))
            node_id = row_value(execution, "node_id", "nodeId")
            if node_id not in (None, "", 0, "0") and str(node_id) not in task_node_ids:
                unresolved.append({
                    "kind": "task_execution",
                    "taskId": task.get("id"),
                    "executionId": execution.get("id"),
                    "nodeId": node_id,
                    "reason": "execution node is absent from the same task",
                })
            normalized_executions.append({
                "execution": execution,
                "permissions": permissions_by_execution.get(execution_id, []),
                "configurations": configs_by_execution.get(execution_id, []),
            })

        task_entries.append({
            "task": task,
            "nodes": sorted_rows(task_nodes, "id"),
            "edges": normalized_edges,
            "executions": normalized_executions,
            "statistics": {
                "nodes": len(task_nodes),
                "edges": len(task_edges),
                "executions": len(task_executions),
                "executionPermissions": sum(
                    len(item["permissions"]) for item in normalized_executions
                ),
                "executionConfigurations": sum(
                    len(item["configurations"]) for item in normalized_executions
                ),
            },
        })

    for table_name, grouped_rows in (
        ("edc_multi_task_node", nodes_by_task),
        ("edc_multi_task_edge", edges_by_task),
        ("edc_multi_task_execution", executions_by_task),
    ):
        for task_id, orphan_rows in grouped_rows.items():
            if task_id not in task_ids:
                unresolved.append({
                    "kind": table_name,
                    "taskId": task_id,
                    "recordIds": [row.get("id") for row in orphan_rows],
                    "reason": "task-scoped records reference an absent task",
                })

    execution_ids = {
        str(row.get("id")) for row in rows("edc_multi_task_execution")
    }
    for table_name, grouped_rows in (
        ("edc_multi_task_execution_ph_ec", permissions_by_execution),
        ("edc_multi_execution_config", configs_by_execution),
    ):
        for execution_id, orphan_rows in grouped_rows.items():
            if execution_id not in execution_ids:
                unresolved.append({
                    "kind": table_name,
                    "executionId": execution_id,
                    "recordIds": [row.get("id") for row in orphan_rows],
                    "reason": "execution-scoped records reference an absent execution",
                })

    categories = {
        "edc_multi_report_task": "task",
        "edc_multi_task_node": "task_graph",
        "edc_multi_task_edge": "task_graph",
        "edc_multi_task_execution": "execution",
        "edc_multi_task_execution_ph_ec": "permission",
        "edc_multi_execution_config": "execution_configuration",
        "edc_multi_matrix_right": "matrix_permission",
    }
    return {
        "tasks": task_entries,
        "matrixRights": rows("edc_multi_matrix_right"),
        "unresolvedReferences": unresolved,
        "recordCounts": {
            name: len(table_rows) for name, table_rows in sorted(tables.items())
        },
        "tableCatalog": module_table_catalog(
            module, "weaver-edcapp-service", categories
        ),
    }


def build_edc_report_index(module: dict[str, Any]) -> dict[str, Any]:
    tables = {
        name: table.get("records", [])
        for name, table in module.get("tables", {}).items()
    }

    def rows(name: str) -> list[dict[str, Any]]:
        return [row for row in tables.get(name, []) if is_active(row)]

    reports = rows("edc_report_dev")
    groups = rows("edc_report_group")
    groups_by_id = {str(row.get("id")): row for row in groups}
    refs_by_report = rows_by(rows("edc_reportdsref_dev"), "report_id", "reportId")
    datasets_by_id = {
        str(row.get("id")): row for row in rows("edc_dataset_dev")
    }
    dataset_children = {
        "legacyFilters": rows_by(
            rows("edc_reportdsfilter_dev"), "dataSetId", "dataset_id", "datasetId"
        ),
        "newFilters": rows_by(
            rows("edc_reportdsfilternew_dev"),
            "dataSetId",
            "dataset_id",
            "datasetId",
        ),
        "ordering": rows_by(
            rows("edc_reportdsorderby_dev"), "dataset_id", "datasetId"
        ),
        "aggregation": rows_by(
            rows("edc_reportdsaggregate_dev"), "dataset_id", "datasetId"
        ),
        "queryInformation": rows_by(
            rows("edc_dataset_query_info_dev"), "dataset_id", "datasetId"
        ),
    }
    sheet_props_by_report = rows_by(
        rows("edc_reportsheetprops_dev"), "sheet_id", "sheetId"
    )
    sheet_fields_by_report = rows_by(
        rows("edc_reportsheetfield_dev"), "report_sheet_id", "reportSheetId"
    )
    query_fields_by_report = rows_by(
        rows("edc_reportqueryfield_dev"), "sheetId", "sheet_id"
    )
    splits_by_report = rows_by(
        rows("edc_reportsheetsplit_dev"), "sheetId", "sheet_id"
    )
    workbook_by_report = rows_by(
        rows("edc_reportwk_props_dev"), "sheet_id", "sheetId"
    )
    view_permissions_by_report = rows_by(
        rows("edc_report_ph_report_view"), "source_id", "sourceId"
    )
    matrix_by_target = rows_by(
        rows("edc_report_matrix_right"), "target_id", "targetId"
    )
    permission_groups_by_report = rows_by(
        rows("edc_report_group_right"), "report_id", "reportId"
    )
    versions = rows("edc_report_version_dev")
    system_datasets = rows("edc_system_dataset_dev")
    system_details_by_master = rows_by(
        rows("edc_system_datasetdt_dev"), "system_dataset_id", "systemDatasetId"
    )
    report_ids = {str(row.get("id")) for row in reports}
    unresolved: list[dict[str, Any]] = []
    report_entries: list[dict[str, Any]] = []

    for report in sorted_rows(reports, "appid", "id"):
        report_id = str(report.get("id"))
        group_id = row_value(report, "group_id", "groupId")
        group = groups_by_id.get(str(group_id), {}) if group_id is not None else {}
        if group_id not in (None, "", 0, "0", -1, "-1") and not group:
            unresolved.append({
                "kind": "report_group",
                "reportId": report.get("id"),
                "groupId": group_id,
                "reason": "report references an absent group",
            })

        normalized_datasets = []
        dataset_source_ids: set[str] = set()
        for ref in refs_by_report.get(report_id, []):
            dataset_id = row_value(ref, "dataset_id", "datasetId")
            dataset = datasets_by_id.get(str(dataset_id), {})
            if not dataset:
                unresolved.append({
                    "kind": "report_dataset",
                    "reportId": report.get("id"),
                    "referenceId": ref.get("id"),
                    "datasetId": dataset_id,
                    "reason": "report dataset reference has no matching dataset",
                })
            else:
                source_id = row_value(dataset, "source_id", "sourceId")
                if source_id is not None:
                    dataset_source_ids.add(str(source_id))
            normalized_datasets.append({
                "reference": ref,
                "dataset": dataset,
                **{
                    name: child_rows.get(str(dataset_id), [])
                    for name, child_rows in dataset_children.items()
                },
            })

        sheet_props = sheet_props_by_report.get(report_id, [])
        suffixes = {
            str(row_value(row, "table_name_suffix", "tableNameSuffix"))
            for row in sheet_props
            if row_value(row, "table_name_suffix", "tableNameSuffix")
            not in (None, "", 0, "0")
        }
        report_system_datasets = []
        for system_dataset in system_datasets:
            system_id = str(system_dataset.get("id"))
            suffix = row_value(
                system_dataset, "table_name_suffix", "tableNameSuffix"
            )
            if system_id in dataset_source_ids or (
                suffix not in (None, "", 0, "0") and str(suffix) in suffixes
            ):
                report_system_datasets.append({
                    "systemDataset": system_dataset,
                    "details": system_details_by_master.get(system_id, []),
                })

        report_entries.append({
            "report": report,
            "group": group,
            "datasets": normalized_datasets,
            "sheetProperties": sheet_props,
            "systemDatasets": report_system_datasets,
            "sheetFields": sheet_fields_by_report.get(report_id, []),
            "queryFields": query_fields_by_report.get(report_id, []),
            "sheetSplits": splits_by_report.get(report_id, []),
            "workbookProperties": workbook_by_report.get(report_id, []),
            "versions": [
                row
                for row in versions
                if id_equal(
                    row_value(row, "origin_report_id", "originReportId"),
                    report.get("id"),
                )
                or id_equal(
                    row_value(row, "report_id", "reportId"), report.get("id")
                )
            ],
            "viewPermissions": view_permissions_by_report.get(report_id, []),
            "matrixRights": matrix_by_target.get(report_id, []),
            "permissionGroups": permission_groups_by_report.get(report_id, []),
        })

    for ref in rows("edc_reportdsref_dev"):
        report_id = row_value(ref, "report_id", "reportId")
        if str(report_id) not in report_ids:
            unresolved.append({
                "kind": "report_dataset_reference",
                "referenceId": ref.get("id"),
                "reportId": report_id,
                "reason": "dataset reference points to an absent report",
            })

    categories = {
        "edc_report_dev": "report",
        "edc_report_group": "report_group",
        "edc_reportdsref_dev": "dataset_binding",
        "edc_dataset_dev": "dataset",
        "edc_reportdsfilter_dev": "dataset_filter",
        "edc_reportdsfilternew_dev": "dataset_filter",
        "edc_reportdsorderby_dev": "dataset_order",
        "edc_reportdsaggregate_dev": "dataset_aggregation",
        "edc_dataset_query_info_dev": "dataset_query",
        "edc_reportsheetprops_dev": "sheet",
        "edc_system_dataset_dev": "system_dataset",
        "edc_system_datasetdt_dev": "system_dataset",
        "edc_reportsheetfield_dev": "sheet_field",
        "edc_reportqueryfield_dev": "query_control",
        "edc_reportsheetsplit_dev": "sheet",
        "edc_reportwk_props_dev": "workbook",
        "edc_report_version_dev": "version",
        "edc_report_ph_report_view": "permission",
        "edc_report_matrix_right": "matrix_permission",
        "edc_report_group_right": "permission_group",
    }
    return {
        "reports": report_entries,
        "groups": groups,
        "applicationMatrixRights": [
            row
            for target_id, target_rows in matrix_by_target.items()
            if target_id not in report_ids
            for row in target_rows
        ],
        "unresolvedReferences": unresolved,
        "recordCounts": {
            name: len(table_rows) for name, table_rows in sorted(tables.items())
        },
        "tableCatalog": module_table_catalog(
            module, "weaver-edcreportd-service", categories
        ),
    }


def build_menu_tree(
    menu_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_id = {str(row.get("id")): row for row in menu_rows}
    children: dict[str, list[dict[str, Any]]] = defaultdict(list)
    roots: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for row in menu_rows:
        parent_id = row_value(row, "parent_id", "parentId", "pid")
        if parent_id in (None, "", 0, "0", -1, "-1"):
            roots.append(row)
        elif str(parent_id) in by_id:
            children[str(parent_id)].append(row)
        else:
            roots.append(row)
            unresolved.append({
                "menuId": row.get("id"),
                "parentId": parent_id,
                "reason": "menu parent is absent; row is exposed as a detached root",
            })

    def node(row: dict[str, Any], trail: set[str]) -> dict[str, Any]:
        row_id = str(row.get("id"))
        if row_id in trail:
            return {"menu": row, "children": [], "cycle": True}
        return {
            "menu": row,
            "children": [
                node(child, trail | {row_id})
                for child in sorted_rows(children.get(row_id, []), "sort", "id")
            ],
        }

    return [
        node(row, set()) for row in sorted_rows(roots, "sort", "id")
    ], unresolved


def build_cusapp_index(module: dict[str, Any]) -> dict[str, Any]:
    tables = {
        name: table.get("records", [])
        for name, table in module.get("tables", {}).items()
    }

    def rows(name: str) -> list[dict[str, Any]]:
        return [row for row in tables.get(name, []) if is_active(row)]

    applications = rows("t_cus_app")
    navigation_by_app = rows_by(
        rows("t_cus_app_navigation"), "app_id", "appId"
    )
    navigation_configs_by_nav = rows_by(
        rows("t_cus_app_navigation_config"), "nav_id", "navId"
    )
    combinations_by_app = rows_by(
        rows("t_cus_app_menu_comb"), "app_id", "appId"
    )
    system_permissions_by_menu = rows_by(
        rows("cus_app_ph_sys_view"), "source_id", "sourceId"
    )
    front_permissions_by_menu = rows_by(
        rows("cus_app_ph_cus_app_view"), "source_id", "sourceId"
    )
    matrix_rules_by_permission = rows_by(
        rows("permission_share_matrix_rule"),
        "permission_share_bean_id",
        "permissionShareBeanId",
    )
    matrix_values_by_permission = rows_by(
        rows("permission_share_matrix_value"),
        "permission_share_bean_id",
        "permissionShareBeanId",
    )
    controls_by_menu = rows_by(
        rows("t_cus_app_business_control"), "menu_id", "menuId"
    )
    permits_by_menu = rows_by(
        rows("t_cus_app_menu_permit"), "menu_id", "menuId"
    )
    personal_by_app = rows_by(
        rows("t_cus_app_sys_personal"), "app_id", "appId"
    )
    system_menus = rows("t_cus_app_system_menu")
    front_menus = rows("t_cus_app_menu")
    unresolved: list[dict[str, Any]] = []
    app_entries: list[dict[str, Any]] = []

    def permission_entry(
        permission: dict[str, Any],
    ) -> dict[str, Any]:
        permission_id = str(permission.get("id"))
        return {
            "permission": permission,
            "matrixRules": matrix_rules_by_permission.get(permission_id, []),
            "matrixValues": matrix_values_by_permission.get(permission_id, []),
        }

    for app in sorted_rows(applications, "id"):
        app_id = str(app.get("id"))
        navigations = navigation_by_app.get(app_id, [])
        nav_ids = {str(row.get("id")) for row in navigations}
        combinations = combinations_by_app.get(app_id, [])
        combination_ids = {str(row.get("id")) for row in combinations}
        app_system_menus = [
            row
            for row in system_menus
            if str(row_value(row, "nav_id", "navId")) in nav_ids
            or str(row_value(row, "combination_id", "combinationId"))
            in combination_ids
        ]
        system_menu_ids = {str(row.get("id")) for row in app_system_menus}
        app_front_menus = [
            row
            for row in front_menus
            if str(row_value(row, "nav_id", "navId")) in nav_ids
            or str(row_value(row, "combination_id", "combinationId"))
            in combination_ids
            or str(row_value(row, "sys_menu_id", "sysMenuId"))
            in system_menu_ids
        ]
        system_tree, system_tree_issues = build_menu_tree(app_system_menus)
        front_tree, front_tree_issues = build_menu_tree(app_front_menus)
        unresolved.extend(
            {"kind": "system_menu", "applicationId": app.get("id"), **issue}
            for issue in system_tree_issues
        )
        unresolved.extend(
            {"kind": "front_menu", "applicationId": app.get("id"), **issue}
            for issue in front_tree_issues
        )
        normalized_system_menus = []
        for menu in app_system_menus:
            normalized_system_menus.append({
                "menu": menu,
                "permissions": [
                    permission_entry(permission)
                    for permission in system_permissions_by_menu.get(
                        str(menu.get("id")), []
                    )
                ],
                "businessControls": controls_by_menu.get(str(menu.get("id")), []),
                "customPermissionSets": permits_by_menu.get(
                    str(menu.get("id")), []
                ),
            })
        normalized_front_menus = []
        for menu in app_front_menus:
            normalized_front_menus.append({
                "menu": menu,
                "permissions": [
                    permission_entry(permission)
                    for permission in front_permissions_by_menu.get(
                        str(menu.get("id")), []
                    )
                ],
            })
        app_entries.append({
            "application": app,
            "navigations": [
                {
                    "navigation": navigation,
                    "configurations": navigation_configs_by_nav.get(
                        str(navigation.get("id")), []
                    ),
                }
                for navigation in navigations
            ],
            "menuCombinations": combinations,
            "systemMenus": normalized_system_menus,
            "systemMenuTree": system_tree,
            "frontMenus": normalized_front_menus,
            "frontMenuTree": front_tree,
            "personalizationSync": personal_by_app.get(app_id, []),
            "statistics": {
                "navigations": len(navigations),
                "menuCombinations": len(combinations),
                "systemMenus": len(app_system_menus),
                "frontMenus": len(app_front_menus),
            },
        })

    known_nav_ids = {
        str(row.get("id")) for row in rows("t_cus_app_navigation")
    }
    for nav_id, config_rows in navigation_configs_by_nav.items():
        if nav_id not in known_nav_ids:
            unresolved.append({
                "kind": "navigation_configuration",
                "navigationId": nav_id,
                "recordIds": [row.get("id") for row in config_rows],
                "reason": "navigation configuration references an absent navigation",
            })

    known_permission_ids = {
        str(row.get("id"))
        for row in rows("cus_app_ph_sys_view")
        + rows("cus_app_ph_cus_app_view")
    }
    for table_name, grouped_rows in (
        ("permission_share_matrix_rule", matrix_rules_by_permission),
        ("permission_share_matrix_value", matrix_values_by_permission),
    ):
        for permission_id, matrix_rows in grouped_rows.items():
            if permission_id not in known_permission_ids:
                unresolved.append({
                    "kind": table_name,
                    "permissionId": permission_id,
                    "recordIds": [row.get("id") for row in matrix_rows],
                    "reason": "matrix child references an absent menu permission",
                })

    categories = {
        "t_cus_app": "application",
        "t_cus_app_navigation": "navigation",
        "t_cus_app_navigation_config": "navigation",
        "t_cus_app_menu_comb": "menu_combination",
        "t_cus_app_system_menu": "system_menu",
        "t_cus_app_menu": "front_menu",
        "cus_app_ph_sys_view": "permission",
        "cus_app_ph_cus_app_view": "permission",
        "permission_share_matrix_rule": "matrix_permission",
        "permission_share_matrix_value": "matrix_permission",
        "t_cus_app_business_control": "business_control",
        "t_cus_app_menu_permit": "custom_permission",
        "t_cus_app_sys_personal": "personalization_sync",
    }
    return {
        "applications": app_entries,
        "unresolvedReferences": unresolved,
        "recordCounts": {
            name: len(table_rows) for name, table_rows in sorted(tables.items())
        },
        "tableCatalog": module_table_catalog(
            module, "weaver-cusapp-service", categories
        ),
    }


def parse_archive(
    data: bytes,
    logical_path: str,
    depth: int,
    inherited_service: str | None,
    layers: list[dict[str, Any]],
    module_chunks: dict[str, dict[str, list[dict[str, Any]]]],
    module_archives: dict[str, set[str]],
    package_resources: list[dict[str, Any]],
    profile_lineage: list[dict[str, Any]],
    idm_mappings: list[dict[str, Any]],
    idm_diagnostics: list[dict[str, Any]],
    package_units: dict[str, dict[str, str]],
    package_unit: dict[str, str] | None,
    errors: list[dict[str, str]],
) -> None:
    service = service_from_name(Path(logical_path).name, inherited_service)
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, OSError) as exc:
        errors.append({"path": logical_path, "error": f"invalid ZIP: {exc}"})
        return

    with archive:
        names = archive.namelist()
        layers.append(
            {
                "path": logical_path,
                "depth": depth,
                "entries": len(names),
                "service": service,
            }
        )
        module_archives[service].add(logical_path)
        for name in names:
            if name.endswith("/"):
                continue
            entry_path = f"{logical_path}!/{name}"
            try:
                payload = archive.read(name)
            except (RuntimeError, OSError, KeyError) as exc:
                errors.append({"path": entry_path, "error": f"read failed: {exc}"})
                continue
            if name.lower().endswith(".zip"):
                child_unit = package_unit
                if depth == 0:
                    detected = top_level_package_unit(name)
                    if detected:
                        child_unit = detected
                        package_units[detected["id"]] = detected
                parse_archive(
                    payload,
                    entry_path,
                    depth + 1,
                    service,
                    layers,
                    module_chunks,
                    module_archives,
                    package_resources,
                    profile_lineage,
                    idm_mappings,
                    idm_diagnostics,
                    package_units,
                    child_unit,
                    errors,
                )
                continue
            base_name = Path(name).name
            if IDM_MAPPING_RE.match(base_name):
                parse_idm_mappings(
                    payload,
                    entry_path,
                    package_unit,
                    idm_mappings,
                    idm_diagnostics,
                )
                continue
            if MIGRATION_FILE_RE.match(base_name):
                idm_diagnostics.append({
                    "code": "IDM_UNSUPPORTED_FILE_SKIPPED",
                    "evidencePath": entry_path,
                    "message": "non-KEYS migration mapping file was safely skipped",
                })
                continue
            if base_name.lower() == PROFILE_FILE:
                try:
                    decoded_profile = json.loads(payload)
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    errors.append({
                        "path": entry_path,
                        "error": f"profile JSON parse failed: {exc}",
                    })
                    continue
                if not isinstance(decoded_profile, dict):
                    errors.append({
                        "path": entry_path,
                        "error": "profile.json is not a JSON object",
                    })
                    continue
                profile_lineage.append(
                    parse_profile_lineage(decoded_profile, entry_path, depth)
                )
                continue
            if CUSTOM_MAPPING_RE.match(base_name) and not base_name.lower().startswith("form_custom_"):
                try:
                    decoded = json.loads(payload)
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    errors.append({"path": entry_path, "error": f"JSON parse failed: {exc}"})
                    continue
                if not isinstance(decoded, list):
                    errors.append({"path": entry_path, "error": "custom mapping file is not a JSON list"})
                    continue
                normalized_records = normalize(decoded)
                for record in normalized_records:
                    field_name = str(record.get("customField") or "")
                    current_value = str(record.get("currentValue") or "")
                    if (
                        "******" in current_value
                        or re.search(
                            r"password|secret|token|credential|private[_-]?key",
                            field_name,
                            re.IGNORECASE,
                        )
                    ):
                        record["newValue"] = None
                package_resources.append({
                    "kind": "installer-custom-mapping",
                    "service": service,
                    "path": entry_path,
                    "records": normalized_records,
                })
                continue
            chunk_match = CHUNK_RE.match(base_name)
            if not chunk_match:
                continue
            table = chunk_match.group("table")
            chunk_number = int(chunk_match.group("chunk"))
            try:
                decoded = json.loads(payload)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                errors.append({"path": entry_path, "error": f"JSON parse failed: {exc}"})
                continue
            if not isinstance(decoded, list):
                errors.append({"path": entry_path, "error": "table chunk is not a JSON list"})
                continue
            module_chunks[service][table].append(
                {
                    "chunk": chunk_number,
                    "path": entry_path,
                    "records": normalize(decoded),
                    "packageUnit": package_unit,
                }
            )


def parse_package(package_path: Path) -> dict[str, Any]:
    layers: list[dict[str, Any]] = []
    module_chunks: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    module_archives: dict[str, set[str]] = defaultdict(set)
    package_resources: list[dict[str, Any]] = []
    profile_lineage: list[dict[str, Any]] = []
    idm_mappings: list[dict[str, Any]] = []
    idm_diagnostics: list[dict[str, Any]] = []
    package_units: dict[str, dict[str, str]] = {}
    errors: list[dict[str, str]] = []

    parse_archive(
        package_path.read_bytes(),
        package_path.name,
        0,
        None,
        layers,
        module_chunks,
        module_archives,
        package_resources,
        profile_lineage,
        idm_mappings,
        idm_diagnostics,
        package_units,
        None,
        errors,
    )

    # 只有真正包含多个顶层应用 ZIP 时才启用批量作用域；单应用包装包
    # 保持既有逻辑键，避免新增能力改变历史单包对比结果。
    if len(package_units) <= 1:
        package_units = {}
        for service_tables in module_chunks.values():
            for chunks in service_tables.values():
                for chunk in chunks:
                    chunk["packageUnit"] = None
        for mapping in idm_mappings:
            mapping["packageUnit"] = None

    modules: dict[str, Any] = {}
    for service in sorted(module_chunks):
        tables: dict[str, Any] = {}
        for table_name, chunks in sorted(module_chunks[service].items()):
            ordered = sorted(chunks, key=lambda item: (item["chunk"], item["path"]))
            records = [row for chunk in ordered for row in chunk["records"]]
            tables[table_name] = {
                "recordCount": len(records),
                "chunks": [
                    {
                        "chunk": chunk["chunk"],
                        "path": chunk["path"],
                        "recordCount": len(chunk["records"]),
                        "packageUnit": chunk.get("packageUnit"),
                    }
                    for chunk in ordered
                ],
                "recordSources": [
                    {
                        "path": chunk["path"],
                        "packageUnit": chunk.get("packageUnit"),
                    }
                    for chunk in ordered
                    for _ in chunk["records"]
                ],
                "records": records,
            }
        modules[service] = {
            "archives": sorted(module_archives[service]),
            "tables": tables,
        }

    indexes: dict[str, Any] = {}
    esb_module = modules.get("weaver-esb-setting-service")
    if esb_module:
        indexes["esbActionFlows"] = build_esb_index(esb_module)
    form_module = modules.get("weaver-ebuilder-form-service")
    if form_module:
        indexes["ebuilderForms"] = build_ebuilder_form_index(form_module)
    app_module = modules.get("weaver-ebuilder-app-service")
    if app_module:
        indexes["ebuilderPages"] = build_ebuilder_page_index(app_module)
    edcapp_module = modules.get("weaver-edcapp-service")
    if edcapp_module:
        indexes["edcMultiFilling"] = build_edc_multi_filling_index(
            edcapp_module
        )
    report_module = modules.get("weaver-edcreportd-service")
    if report_module:
        indexes["edcReports"] = build_edc_report_index(report_module)
    cusapp_module = modules.get("weaver-cusapp-service")
    if cusapp_module:
        indexes["cusApps"] = build_cusapp_index(cusapp_module)
    indexes["importRequirements"] = build_import_requirements(
        package_resources,
        modules,
    )

    application_aliases = unique_rows([
        alias
        for fragment in profile_lineage
        for alias in fragment.get("applicationAliases", [])
    ])
    submodule_aliases = unique_rows([
        alias
        for fragment in profile_lineage
        for alias in fragment.get("submoduleAliases", [])
    ])
    profile_candidates = [
        {
            "depth": int(fragment.get("depth", 0)),
            "exportTime": fragment.get("exportTime"),
            "evidencePath": fragment["evidencePath"],
        }
        for fragment in profile_lineage
    ]
    outermost_depth = min(
        (candidate["depth"] for candidate in profile_candidates),
        default=None,
    )
    outermost_profiles = [
        candidate
        for candidate in profile_candidates
        if candidate["depth"] == outermost_depth
    ]
    outermost_times = {
        candidate.get("exportTime")
        for candidate in outermost_profiles
        if candidate.get("exportTime") not in (None, "")
    }
    all_outermost_have_time = bool(outermost_profiles) and all(
        candidate.get("exportTime") not in (None, "")
        for candidate in outermost_profiles
    )
    profile_status = (
        "MISSING"
        if not outermost_profiles or not all_outermost_have_time
        else "CONFLICT"
        if len(outermost_times) != 1
        else "AVAILABLE"
    )
    selected_export_time = (
        next(iter(outermost_times))
        if profile_status == "AVAILABLE"
        else None
    )
    outermost_types = {
        value
        for fragment in profile_lineage
        if fragment.get("depth") == outermost_depth
        for value in (
            [fragment.get("ietype")]
            + list((fragment.get("exportIdIetype") or {}).values())
        )
        if value
    }
    selected_ietype = (
        next(iter(outermost_types)) if len(outermost_types) == 1 else None
    )
    ietype_status = (
        "MISSING" if not outermost_types else
        "CONFLICT" if len(outermost_types) != 1 else
        "AVAILABLE"
    )

    return {
        "schemaVersion": "1.0",
        "source": {
            "packagePath": str(package_path.resolve()),
            "packageName": package_path.name,
        },
        "zipLayers": layers,
        "modules": modules,
        "packageResources": package_resources,
        "packageUnits": sorted(
            package_units.values(), key=lambda item: (item["name"], item["id"])
        ),
        "packageProfile": {
            "schemaVersion": "ebuilder-package-profile/v1.0",
            "selectionRule": "minimum archive depth (outermost profile.json only)",
            "status": profile_status,
            "selectedExportTime": selected_export_time,
            "ietypeStatus": ietype_status,
            "selectedIetype": selected_ietype,
            "ietypeCandidates": sorted(outermost_types),
            "selectedDepth": outermost_depth,
            "candidateCount": len(profile_candidates),
            "outermostCandidateCount": len(outermost_profiles),
            "evidenceFiles": sorted(
                candidate["evidencePath"] for candidate in outermost_profiles
            ),
            "outermostCandidates": sorted(
                outermost_profiles,
                key=lambda item: item["evidencePath"],
            ),
        },
        "migrationLineage": {
            "schemaVersion": "ebuilder-migration-lineage/v1.1",
            "applicationAliases": application_aliases,
            "submoduleAliases": submodule_aliases,
            "idmMappings": idm_mappings,
            "idmDiagnostics": idm_diagnostics,
            "evidenceFiles": sorted({
                fragment["evidencePath"] for fragment in profile_lineage
            }),
            "summary": {
                "profiles": len(profile_lineage),
                "applicationAliases": len(application_aliases),
                "submoduleAliases": len(submodule_aliases),
                "idmMappings": len(idm_mappings),
                "idmDiagnostics": len(idm_diagnostics),
                "idmEvidenceFiles": len({
                    item["evidencePath"] for item in idm_mappings
                }),
                "nonIdentityAliases": sum(
                    str(alias.get("currentId")) != str(alias.get("sourceId"))
                    for alias in application_aliases + submodule_aliases
                ),
            },
        },
        "indexes": indexes,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--compact-output",
        action="store_true",
        help="使用紧凑 JSON 写入 canonical IR，减少大型包临时 I/O",
    )
    args = parser.parse_args()

    if not args.package.is_file():
        raise SystemExit(f"package not found: {args.package}")

    document = parse_package(args.package)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            document,
            ensure_ascii=False,
            indent=None if args.compact_output else 2,
            separators=(",", ":") if args.compact_output else None,
        ),
        encoding="utf-8",
    )
    import_requirements_path = args.output.parent / "import-required-inputs.json"
    import_requirements_path.write_text(
        json.dumps(
            document["indexes"]["importRequirements"],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    esb = document["indexes"].get("esbActionFlows", {})
    forms = document["indexes"].get("ebuilderForms", {})
    pages = document["indexes"].get("ebuilderPages", {})
    filling = document["indexes"].get("edcMultiFilling", {})
    reports = document["indexes"].get("edcReports", {})
    cusapps = document["indexes"].get("cusApps", {})
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "modules": sorted(document["modules"]),
                "tables": sum(
                    len(module["tables"]) for module in document["modules"].values()
                ),
                "esbActionFlows": len(esb.get("applications", [])),
                "ebuilderForms": len(forms.get("forms", [])),
                "ebuilderApplications": len(pages.get("applications", [])),
                "ebuilderPages": sum(
                    len(app.get("pages", []))
                    for app in pages.get("applications", [])
                ),
                "edcMultiFillingTasks": len(filling.get("tasks", [])),
                "edcReports": len(reports.get("reports", [])),
                "cusApps": len(cusapps.get("applications", [])),
                "requiredImportInputs": document["indexes"]
                .get("importRequirements", {})
                .get("summary", {})
                .get("requiredInputs", 0),
                "unresolvedRequiredImportInputs": document["indexes"]
                .get("importRequirements", {})
                .get("summary", {})
                .get("unresolvedRequiredInputs", 0),
                "optionalImportMappings": document["indexes"]
                .get("importRequirements", {})
                .get("summary", {})
                .get("optionalMappings", 0),
                "importRequirementsOutput": str(import_requirements_path.resolve()),
                "unresolvedComponents": len(esb.get("unresolvedComponentBindings", [])),
                "unresolvedReferences": sum(
                    len(index.get("unresolvedReferences", []))
                    for index in (pages, filling, reports, cusapps)
                ),
                "packageProfile": document.get("packageProfile") or {},
                "routingTables": sorted({
                    table_name
                    for module in document.get("modules", {}).values()
                    for table_name in (module.get("tables") or {})
                }),
                "errors": len(document["errors"]),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
