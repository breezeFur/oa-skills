#!/usr/bin/env python3
"""从 canonical package IR 建立跨版本可比较的逻辑对象索引。"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from knowledge_io import iter_jsonl
from normalize_records import (
    canonical_json,
    digest_value,
    is_id_field,
    is_id_value,
    normalize_record,
    normalize_value,
    stable_content_for_identity,
)


BUSINESS_FIELD_PRIORITY = [
    "data_key", "datakey", "field_key", "fieldkey", "field_code", "fieldcode",
    "app_code", "appcode", "page_code", "pagecode", "menu_code", "menucode",
    "role_code", "code", "key", "tag", "label", "name", "title",
    "field_name", "fieldname", "form_name", "formname", "page_name", "pagename",
    "menu_name", "menuname", "display_name", "displayname", "table_name",
    "column_name", "type", "scene",
]

# Only customer-recognizable root objects may use record-level lineage as a
# standalone one-to-one identity. Detail/shared/language/range rows must remain
# parent-scoped even when their .idm sourceId happens to be unique in one file.
BUSINESS_ROOT_TABLES = {
    "form", "ebdp_page", "ebdf_view_designer", "esb_application",
    "wfp_base", "wfc_base", "bpm_process", "bpm_new_base",
    "t_cus_app", "t_cus_app_system_menu", "t_cus_app_tenant_menu",
    "t_cus_app_navigation", "edc_report_dev", "edc_multi_task",
    "edc_multi_filling", "dataset", "ebda_app",
}


def hash_token(value: Any, length: int = 24) -> str | None:
    if value in (None, ""):
        return None
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:length]


def load_rules(knowledge_dir: Path) -> dict[tuple[str, str], dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for rule in iter_jsonl(knowledge_dir / "logical-key-rules.jsonl"):
        table = str(rule.get("table") or "").lower()
        services = rule.get("services") or [rule.get("module")]
        for service in services:
            grouped[(str(service or ""), table)].append(rule)
        grouped[("", table)].append(rule)

    result: dict[tuple[str, str], dict[str, Any]] = {}
    for key, rules in grouped.items():
        primary: list[str] = []
        parents: list[dict[str, str]] = []
        config_ids: list[str] = []
        for rule in rules:
            for field in rule.get("primaryKeyFields") or []:
                if field not in primary:
                    primary.append(field)
            for relation in rule.get("parentReferenceFields") or []:
                signature = canonical_json(relation)
                if all(canonical_json(existing) != signature for existing in parents):
                    parents.append(relation)
            source = rule.get("source") or {}
            if source.get("recordId") is not None:
                config_ids.append(str(source["recordId"]))
        result[key] = {
            "primaryFields": primary or ["id"],
            "parentReferences": parents,
            "configIds": sorted(set(config_ids)),
        }
    return result


def module_kind(service: str, table: str) -> str:
    text = f"{service}:{table}".lower()
    if "ebuilder-form" in text or table.startswith(("ebdf_", "form_", "sub_form", "field_")):
        return "表单"
    if "ebuilder-app" in text or table.startswith(("ebda_", "ebdp_", "ebdd_")):
        return "页面与应用"
    if "esb" in text or table.startswith(("esb_", "wfr_")):
        return "ESB动作流"
    if "edcreport" in text or table.startswith("edc_report"):
        return "EDC报表"
    if "edcapp" in text or table.startswith("edc_multi"):
        return "EDC多级填报"
    if "cusapp" in text or table.startswith(("cus_", "cusapp_")):
        return "CusApp菜单"
    if "bpm" in text or table.startswith(("bpm_", "wfp_", "wfc_")):
        return "工作流"
    if any(token in table for token in ("permission", "right", "auth_role")):
        return "权限"
    return "其他配置"


def case_insensitive_lookup(row: dict[str, Any]) -> dict[str, tuple[str, Any]]:
    """Index the first spelling of each field once, preserving legacy choice."""
    lookup: dict[str, tuple[str, Any]] = {}
    for key, value in row.items():
        lookup.setdefault(str(key).lower(), (str(key), value))
    return lookup


def find_case_insensitive(
    row: dict[str, Any],
    candidate: str,
    lookup: dict[str, tuple[str, Any]] | None = None,
) -> tuple[str, Any] | None:
    candidate_lower = candidate.lower()
    if lookup is not None:
        found = lookup.get(candidate_lower)
        if found and found[1] not in (None, "", [], {}):
            return found
        return None
    for key, value in row.items():
        if str(key).lower() == candidate_lower and value not in (None, "", [], {}):
            return str(key), value
    return None


def choose_business_key_fields(
    row: dict[str, Any],
    lookup: dict[str, tuple[str, Any]] | None = None,
) -> list[tuple[str, Any]]:
    selected: list[tuple[str, Any]] = []
    for candidate in BUSINESS_FIELD_PRIORITY:
        found = find_case_insensitive(row, candidate, lookup)
        if not found:
            continue
        field, value = found
        normalized = normalize_value(value, field)
        if normalized in (None, "", [], {}):
            continue
        if is_id_value(normalized):
            continue
        selected.append((field, normalized))
        if len(selected) >= 3:
            break
    return selected


def collect_rows(ir: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for service, module in sorted((ir.get("modules") or {}).items()):
        for table, table_data in sorted((module.get("tables") or {}).items()):
            record_sources = table_data.get("recordSources") or []
            for ordinal, row in enumerate(table_data.get("records") or []):
                if not isinstance(row, dict):
                    continue
                record_source = (
                    record_sources[ordinal]
                    if ordinal < len(record_sources)
                    else {}
                )
                package_unit = record_source.get("packageUnit")
                current_id = find_case_insensitive(row, "id")
                result.append({
                    "service": service,
                    "table": table,
                    "ordinal": ordinal,
                    "row": row,
                    "packageUnit": package_unit,
                    "packageUnitKey": str((package_unit or {}).get("id") or "__single__"),
                    "currentRecordId": (
                        str(current_id[1]) if current_id else None
                    ),
                    "source": {
                        "archive": record_source.get("path"),
                        "table": table,
                        "recordOrdinal": ordinal,
                    },
                })
    return result


def get_primary_value(
    row: dict[str, Any],
    primary_fields: list[str],
    lookup: dict[str, tuple[str, Any]] | None = None,
) -> str | None:
    values = []
    for field in primary_fields:
        found = find_case_insensitive(row, field, lookup)
        if found and found[1] not in (None, ""):
            values.append(str(found[1]))
    return "|".join(values) if values else None


def build_profile_lineage_registry(ir: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Index current IDs to their migration source IDs from profile.json."""
    lineage = ir.get("migrationLineage") or {}
    registry: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for kind, entries in (
        ("APPLICATION_HOMOLOGY", lineage.get("applicationAliases") or []),
        ("SUBMODULE_HOMOLOGY", lineage.get("submoduleAliases") or []),
    ):
        for entry in entries:
            current_id = entry.get("currentId")
            source_id = entry.get("sourceId")
            if current_id in (None, "") or source_id in (None, ""):
                continue
            registry[str(current_id)].append({
                "kind": kind,
                "sourceId": str(source_id),
                "groupKey": entry.get("groupKey"),
                "oldExportId": entry.get("oldExportId"),
                "evidencePath": entry.get("evidencePath"),
            })
    return registry


def resolve_lineage_identity(
    primary_value: str | None,
    registry: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    """Resolve only unambiguous current-ID -> original-source-ID relations."""
    if not primary_value or "|" in primary_value:
        return None
    aliases = registry.get(primary_value) or []
    source_ids = sorted({
        str(alias["sourceId"])
        for alias in aliases
        if alias.get("sourceId") not in (None, "")
    })
    if len(source_ids) != 1:
        return None
    source_id = source_ids[0]
    return {
        "sourceId": source_id,
        "sourceIdHash": hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:24],
        "aliasKinds": sorted({
            str(alias.get("kind")) for alias in aliases if alias.get("kind")
        }),
        "groupKeys": sorted({
            str(alias.get("groupKey")) for alias in aliases if alias.get("groupKey")
        }),
        "evidencePaths": sorted({
            str(alias.get("evidencePath"))
            for alias in aliases
            if alias.get("evidencePath")
        }),
    }


def resolve_idm_record_links(
    ir: dict[str, Any],
    rows: list[dict[str, Any]],
) -> tuple[dict[int, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Link .idm entries to current rows using importId first, exportId second."""
    lineage = ir.get("migrationLineage") or {}
    diagnostics = list(lineage.get("idmDiagnostics") or [])
    by_current: dict[tuple[str, str, str, str], list[int]] = defaultdict(list)
    for index, item in enumerate(rows):
        current_id = item.get("currentRecordId")
        if current_id:
            by_current[(
                item["packageUnitKey"],
                item["service"].lower(),
                item["table"].lower(),
                current_id,
            )].append(index)

    resolved: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for mapping in lineage.get("idmMappings") or []:
        unit = mapping.get("packageUnit") or {}
        unit_key = str(unit.get("id") or "__single__")
        service = str(mapping.get("serviceName") or "").lower()
        table = str(mapping.get("tableName") or "").lower()
        source_id = mapping.get("sourceId")
        evidence = mapping.get("evidencePath")
        ordinal = mapping.get("recordOrdinal")
        if not service or not table or source_id in (None, ""):
            continue

        def candidates(field: str) -> list[int]:
            value = mapping.get(field)
            if value in (None, ""):
                return []
            return by_current.get((unit_key, service, table, str(value)), [])

        import_hits = candidates("importId")
        export_hits = candidates("exportId")
        if len(import_hits) > 1 or len(export_hits) > 1:
            diagnostics.append({
                "code": "IDM_CURRENT_ID_AMBIGUOUS",
                "evidencePath": evidence,
                "recordOrdinal": ordinal,
                "serviceName": service,
                "tableName": table,
                "importCandidateCount": len(import_hits),
                "exportCandidateCount": len(export_hits),
                "message": "importId/exportId matched multiple current records",
            })
            continue
        if import_hits and export_hits and import_hits[0] != export_hits[0]:
            diagnostics.append({
                "code": "IDM_CURRENT_ID_CONFLICT",
                "evidencePath": evidence,
                "recordOrdinal": ordinal,
                "serviceName": service,
                "tableName": table,
                "importIdHash": hash_token(mapping.get("importId"), 16),
                "exportIdHash": hash_token(mapping.get("exportId"), 16),
                "message": "importId and exportId resolved to different current records",
            })
            continue
        if import_hits:
            row_index = import_hits[0]
            resolution = (
                "IMPORT_AND_EXPORT_AGREE" if export_hits else "IMPORT_ID"
            )
        elif export_hits:
            row_index = export_hits[0]
            resolution = "EXPORT_ID_FALLBACK"
        else:
            diagnostics.append({
                "code": "IDM_CURRENT_RECORD_NOT_FOUND",
                "evidencePath": evidence,
                "recordOrdinal": ordinal,
                "serviceName": service,
                "tableName": table,
                "sourceIdHash": hash_token(source_id, 16),
                "message": "neither importId nor exportId matched a current record",
            })
            continue
        scoped = f"{unit_key}|{service}|{table}|{source_id}"
        resolved[row_index].append({
            "sourceId": str(source_id),
            "sourceIdHash": hash_token(source_id),
            "lineageKeyHash": hash_token(scoped),
            "evidencePath": evidence,
            "currentIdResolution": resolution,
            "sourceTargetIdHash": hash_token(mapping.get("sourceTargetId"), 16),
            "exportTargetIdHash": hash_token(mapping.get("exportTargetId"), 16),
            "importTargetIdHash": hash_token(mapping.get("importTargetId"), 16),
        })
    return resolved, diagnostics


def build_object_index(ir: dict[str, Any], knowledge_dir: Path) -> dict[str, Any]:
    rules = load_rules(knowledge_dir)
    profile_registry = build_profile_lineage_registry(ir)
    rows = collect_rows(ir)
    idm_by_row, lineage_diagnostics = resolve_idm_record_links(ir, rows)
    idm_scope_counts: Counter[tuple[str, str, str, str]] = Counter()
    for row_index, identities in idm_by_row.items():
        item = rows[row_index]
        # Uniqueness is about how many distinct current records share one
        # lineage source, not how many duplicate KEYS_*.idm entries point to
        # the same record.  Count each source only once per resolved row.
        for source_id in {identity["sourceId"] for identity in identities}:
            idm_scope_counts[(
                item["packageUnitKey"], item["service"].lower(),
                item["table"].lower(), source_id,
            )] += 1
    staged: list[dict[str, Any]] = []
    raw_id_entries: list[tuple[str, str, str, int]] = []

    for index, item in enumerate(rows):
        service = item["service"]
        table = item["table"]
        row = item["row"]
        row_lookup = case_insensitive_lookup(row)
        rule = rules.get((service, table.lower())) or rules.get(("", table.lower())) or {
            "primaryFields": ["id"],
            "parentReferences": [],
            "configIds": [],
        }
        business_fields = choose_business_key_fields(row, row_lookup)
        content = stable_content_for_identity(
            row,
            primary_fields=rule["primaryFields"],
            preserve_fields=[field for field, _ in business_fields],
        )
        parent_values = []
        for relation in rule["parentReferences"]:
            found = find_case_insensitive(
                row, relation.get("sourceField") or "", row_lookup
            )
            if found and found[1] not in (None, ""):
                parent_values.append({
                    "field": found[0],
                    "value": str(found[1]),
                    "targetTable": relation.get("targetTable"),
                })
        primary_value = get_primary_value(row, rule["primaryFields"], row_lookup)
        unit_lineage_identity = (
            resolve_lineage_identity(item["packageUnitKey"], profile_registry)
            if item.get("packageUnit") else None
        )
        if unit_lineage_identity:
            item["packageUnitKey"] = (
                "migration-source-" + unit_lineage_identity["sourceIdHash"]
            )
        profile_identity = resolve_lineage_identity(
            item.get("currentRecordId") or primary_value, profile_registry
        )
        resolved_idm = idm_by_row.get(index) or []
        idm_source_ids = sorted({entry["sourceId"] for entry in resolved_idm})
        idm_identity = resolved_idm[0] if len(idm_source_ids) == 1 else None
        ambiguity_reason = None
        if len(idm_source_ids) > 1:
            ambiguity_reason = "AMBIGUOUS_LINEAGE_MULTIPLE_SOURCE_IDS_FOR_RECORD"
            lineage_diagnostics.append({
                "code": "AMBIGUOUS_LINEAGE",
                "serviceName": service,
                "tableName": table,
                "recordOrdinal": item["ordinal"],
                "candidateCount": len(idm_source_ids),
                "candidateSourceIdHashes": [hash_token(value, 16) for value in idm_source_ids],
                "message": "one current record is associated with multiple .idm source IDs",
            })
        profile_corroborated = None
        if idm_identity and profile_identity:
            profile_corroborated = (
                idm_identity["sourceId"] == profile_identity["sourceId"]
            )
            if not profile_corroborated:
                lineage_diagnostics.append({
                    "code": "LINEAGE_EVIDENCE_CONFLICT",
                    "serviceName": service,
                    "tableName": table,
                    "recordOrdinal": item["ordinal"],
                    "idmSourceIdHash": idm_identity["sourceIdHash"],
                    "profileSourceIdHash": profile_identity["sourceIdHash"],
                    "evidencePath": idm_identity.get("evidencePath"),
                    "profileEvidencePaths": profile_identity.get("evidencePaths") or [],
                    "message": ".idm and profile lineage disagree; unique .idm remains primary",
                })
        root_lineage_unique = bool(
            idm_identity
            and table.lower() in BUSINESS_ROOT_TABLES
            and idm_scope_counts[(
                item["packageUnitKey"], service.lower(), table.lower(),
                idm_identity["sourceId"],
            )] == 1
        )
        base_parts = [
            f"{field.lower()}={canonical_json(value)}"
            for field, value in business_fields
        ]
        if root_lineage_unique:
            scoped_lineage = (
                f"{item['packageUnitKey']}|{service.lower()}|{table.lower()}|"
                f"{idm_identity['sourceId']}"
            )
            base_key = (
                "idm-lineage="
                + hashlib.sha256(scoped_lineage.encode("utf-8")).hexdigest()[:24]
            )
            confidence = "HIGH"
            identity_method = "MIGRATION_IDM_SOURCE_ID"
            lineage_identity = idm_identity
            lineage_source = "KEYS_IDM"
        elif idm_identity and table.lower() not in BUSINESS_ROOT_TABLES:
            lineage_identity = idm_identity
            lineage_source = "KEYS_IDM_CONTEXT_ONLY"
            ambiguity_reason = ambiguity_reason or "IDM_DETAIL_REQUIRES_PARENT_CONTEXT"
            context_prefix = f"idm-context={idm_identity['sourceIdHash']}::"
            if base_parts:
                base_key = context_prefix + "|".join(base_parts)
                confidence = "HIGH"
                identity_method = "BUSINESS_KEY"
            elif content:
                base_key = context_prefix + f"content={digest_value(content)[:24]}"
                confidence = "MEDIUM"
                identity_method = "CONTENT_FINGERPRINT"
            else:
                base_key = "anonymous"
                confidence = "LOW"
                identity_method = "UNMATCHED"
        elif profile_identity:
            scoped_lineage = (
                f"{item['packageUnitKey']}|{service.lower()}|{table.lower()}|"
                f"{profile_identity['sourceId']}"
            )
            base_key = (
                "profile-lineage="
                + hashlib.sha256(scoped_lineage.encode("utf-8")).hexdigest()[:24]
            )
            confidence = "HIGH"
            identity_method = "PROFILE_HOMOLOGY"
            lineage_identity = profile_identity
            lineage_source = "PROFILE_JSON"
        elif base_parts:
            base_key = "|".join(base_parts)
            confidence = "HIGH"
            identity_method = "BUSINESS_KEY"
            lineage_identity = None
            lineage_source = None
        elif content:
            base_key = f"content={digest_value(content)[:24]}"
            confidence = "MEDIUM"
            identity_method = "CONTENT_FINGERPRINT"
            lineage_identity = None
            lineage_source = None
        else:
            base_key = "anonymous"
            confidence = "LOW"
            identity_method = "UNMATCHED"
            lineage_identity = None
            lineage_source = None
        staged.append({
            **item,
            "index": index,
            "rule": rule,
            "businessFields": business_fields,
            "identityContent": content,
            "parentValues": parent_values,
            "primaryValue": primary_value,
            "lineageIdentity": lineage_identity,
            "lineageSource": lineage_source,
            "profileCorroborated": profile_corroborated,
            "currentIdResolution": (
                idm_identity.get("currentIdResolution") if idm_identity else
                "PROFILE_CURRENT_ID" if profile_identity else None
            ),
            "ambiguityReason": ambiguity_reason,
            "unitLineageIdentity": unit_lineage_identity,
            "baseKey": base_key,
            "identityConfidence": confidence,
            "identityMethod": identity_method,
        })
        if primary_value:
            raw_id_entries.append((service, table, primary_value, index))

    by_table_id: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    global_id: dict[tuple[str, str], list[int]] = defaultdict(list)
    for service, table, value, index in raw_id_entries:
        unit_key = staged[index]["packageUnitKey"]
        by_table_id[(unit_key, table.lower(), value)].append(index)
        global_id[(unit_key, value)].append(index)

    initial_keys = {}
    for item in staged:
        unit_prefix = (
            f"package-unit={item['packageUnitKey']}::"
            if item.get("packageUnit") else ""
        )
        initial_keys[item["index"]] = (
            f"{unit_prefix}{item['service']}::{item['table']}::{item['baseKey']}"
        )
    for _ in range(2):
        for item in staged:
            resolved_parents = []
            for parent in item["parentValues"]:
                candidates = by_table_id.get(
                    (
                        item["packageUnitKey"],
                        str(parent.get("targetTable") or "").lower(),
                        parent["value"],
                    ),
                    [],
                )
                if len(candidates) == 1:
                    resolved_parents.append(initial_keys[candidates[0]])
            if resolved_parents:
                parent_path = hashlib.sha256(
                    "|".join(sorted(resolved_parents)).encode("utf-8")
                ).hexdigest()[:16]
                item["parentIdentityKey"] = parent_path
                if item["identityMethod"] == "MIGRATION_IDM_SOURCE_ID":
                    continue
                if item["identityMethod"] in {"CONTENT_FINGERPRINT", "UNMATCHED"}:
                    item["identityMethod"] = "PARENT_RELATION_PATH"
                    item["identityConfidence"] = "MEDIUM"
                if item.get("ambiguityReason") == "IDM_DETAIL_REQUIRES_PARENT_CONTEXT":
                    item["ambiguityReason"] = None
                unit_prefix = (
                    f"package-unit={item['packageUnitKey']}::"
                    if item.get("packageUnit") else ""
                )
                initial_keys[item["index"]] = (
                    f"{unit_prefix}{item['service']}::{item['table']}::"
                    f"{item['baseKey']}::parent={parent_path}"
                )

    key_counts = Counter(initial_keys.values())
    occurrence_counter: Counter[str] = Counter()
    objects = []

    for item in staged:
        logical_key = initial_keys[item["index"]]
        if key_counts[logical_key] > 1:
            discriminator = digest_value(item["identityContent"])[:16]
            candidate = f"{logical_key}::content={discriminator}"
            occurrence_counter[candidate] += 1
            if occurrence_counter[candidate] > 1:
                candidate = f"{candidate}::occurrence={occurrence_counter[candidate]}"
                item["identityConfidence"] = "LOW"
            logical_key = candidate
        def resolve_id(value: Any, field: str) -> str | None:
            candidates = global_id.get(
                (item["packageUnitKey"], str(value)), []
            )
            if len(candidates) == 1:
                return initial_keys[candidates[0]]
            return None

        canonical, unresolved = normalize_record(
            item["row"],
            primary_fields=item["rule"]["primaryFields"],
            id_resolver=resolve_id,
        )
        display_name = next(
            (
                str(value)
                for field, value in item["businessFields"]
                if any(token in field.lower() for token in ("name", "title", "label"))
            ),
            item["baseKey"][:160],
        )
        objects.append({
            "objectId": hashlib.sha256(logical_key.encode("utf-8")).hexdigest()[:24],
            "module": item["service"],
            "moduleKind": module_kind(item["service"], item["table"]),
            "table": item["table"],
            "objectType": item["table"],
            "packageUnit": item.get("packageUnit"),
            "packageUnitKey": item["packageUnitKey"],
            "packageUnitIdentityMethod": (
                "PROFILE_HOMOLOGY" if item.get("unitLineageIdentity") else
                "TOP_LEVEL_ARCHIVE_ID" if item.get("packageUnit") else
                "SINGLE_PACKAGE"
            ),
            "logicalKey": logical_key,
            "displayName": display_name,
            "identityConfidence": item["identityConfidence"],
            "identityMethod": item["identityMethod"],
            "lineageSource": item.get("lineageSource"),
            "lineageEvidencePath": (
                item["lineageIdentity"].get("evidencePath")
                if item.get("lineageIdentity") else None
            ),
            "lineageKeyHash": (
                item["lineageIdentity"].get("lineageKeyHash")
                if item.get("lineageIdentity") else None
            ),
            "currentIdResolution": item.get("currentIdResolution"),
            "ambiguityReason": item.get("ambiguityReason"),
            "parentIdentityKey": item.get("parentIdentityKey"),
            "profileCorroborated": item.get("profileCorroborated"),
            "lineageIdentity": (
                {
                    key: value
                    for key, value in item["lineageIdentity"].items()
                    if key != "sourceId"
                }
                if item.get("lineageIdentity")
                else None
            ),
            "configIds": item["rule"]["configIds"],
            "canonical": canonical,
            "canonicalHash": digest_value(canonical),
            "identityContentHash": digest_value(item["identityContent"]),
            "businessFields": [
                {"field": field, "value": value}
                for field, value in item["businessFields"]
            ],
            "unresolvedReferences": unresolved,
            "sourceEvidence": {
                "moduleArchive": item["source"].get("archive"),
                "packageUnit": item.get("packageUnit"),
                "table": item["table"],
                "recordOrdinal": item["ordinal"],
                "primaryValueHash": hashlib.sha256(
                    str(item["primaryValue"] or "").encode("utf-8")
                ).hexdigest()[:16],
                "migrationSourceIdHash": (
                    item["lineageIdentity"]["sourceIdHash"]
                    if item.get("lineageIdentity")
                    else None
                ),
                "migrationProfileEvidence": (
                    item["lineageIdentity"].get("evidencePaths") or []
                    if item.get("lineageIdentity")
                    else []
                ),
                "migrationIdmEvidence": (
                    [item["lineageIdentity"].get("evidencePath")]
                    if item.get("lineageIdentity")
                    and item["lineageIdentity"].get("evidencePath")
                    else []
                ),
            },
        })
    return {
        "schemaVersion": "ebuilder-object-index/v1.0",
        "package": {
            "name": (ir.get("source") or {}).get("packageName"),
            "modules": sorted((ir.get("modules") or {}).keys()),
            "parseErrors": ir.get("errors") or [],
            "packageUnits": ir.get("packageUnits") or [],
        },
        "objects": objects,
        "summary": {
            "objects": len(objects),
            "tables": len({(item["module"], item["table"]) for item in objects}),
            "unresolvedReferenceTokens": sum(
                len(item["unresolvedReferences"]) for item in objects
            ),
            "identityConfidence": dict(Counter(
                item["identityConfidence"] for item in objects
            )),
            "migrationSourceIdentityObjects": sum(
                item.get("identityMethod") == "MIGRATION_IDM_SOURCE_ID"
                for item in objects
            ),
            "profileHomologyIdentityObjects": sum(
                item.get("identityMethod") == "PROFILE_HOMOLOGY"
                for item in objects
            ),
            "migrationLineage": (
                ir.get("migrationLineage") or {}
            ).get("summary") or {},
            "packageUnits": len(ir.get("packageUnits") or []),
        },
        "lineageDiagnostics": sorted(
            lineage_diagnostics,
            key=lambda item: (
                str(item.get("code") or ""),
                str(item.get("evidencePath") or ""),
                int(item.get("recordOrdinal") or 0),
            ),
        ),
    }
