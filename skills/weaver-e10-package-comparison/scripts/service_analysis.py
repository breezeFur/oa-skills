#!/usr/bin/env python3
"""面向 Application IR 的动态服务识别、通用表链和业务对象解析。"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from ir_common import iter_jsonl, logical_key, slug, source_ref


SKILL_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = SKILL_DIR / "reconstruct-knowledge"

SEMANTIC_SIGNATURE_TABLES = {
    "weaver-ai-application-service": {"ai_application_config"},
    "weaver-workflow-pathdef-service": {"wfp_base"},
}


def _jsonl(name):
    path = KNOWLEDGE_DIR / name
    if not path.exists() and not Path(f"{path}.gz").exists() and not path.with_suffix(".json").exists():
        return []
    return list(iter_jsonl(path))


def load_knowledge():
    catalog_path = KNOWLEDGE_DIR / "service-analysis-catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8")) if catalog_path.exists() else {"services": []}
    return {
        "catalog": {item["service"]: item for item in catalog.get("services", [])},
        "features": _jsonl("feature-groups.jsonl"),
        "logicalRules": _jsonl("table-analysis-rules.jsonl"),
        "relations": _jsonl("table-relation-rules.jsonl"),
        "externalReferences": _jsonl("external-reference-rules.jsonl"),
        "handlers": _jsonl("handler-semantics.jsonl"),
        "summary": catalog.get("counts", {}),
    }


def record_count(payload):
    return payload.get("recordCount", len(payload.get("records", [])))


def analyze_services(ir):
    knowledge = load_knowledge()
    catalog = knowledge["catalog"]
    package_modules = ir.get("modules", {})
    present_tables = {
        service: set(payload.get("tables", {}))
        for service, payload in package_modules.items()
    }
    table_owners = defaultdict(set)
    for service, entry in catalog.items():
        for table in entry.get("configuredTables", []):
            table_owners[table].add(service)

    service_inventory, fragments, business_objects = [], [], []
    fragment_keys = {}
    for service, payload in sorted(package_modules.items()):
        tables = payload.get("tables", {})
        configured = catalog.get(service)
        semantic_owners = sorted({service} | {
            owner
            for owner, signatures in SEMANTIC_SIGNATURE_TABLES.items()
            if signatures & set(tables)
        })
        level = configured.get("analysisLevel") if configured else "EVIDENCE_ONLY"
        capability = configured.get("capability") if configured else "unclassified-package-service"
        service_role = configured.get("serviceRole") if configured else "EVIDENCE_ONLY"
        service_inventory.append({
            "logicalKey": logical_key("service", stable=service),
            "service": service,
            "packagePresent": True,
            "analysisLevel": level,
            "capability": capability,
            "serviceRole": service_role,
            "dedicatedParser": bool(configured and configured.get("dedicatedParser")),
            "semanticOwnerServices": semantic_owners,
            "knownInConfiguration": configured is not None,
            "configuredTableCount": len(configured.get("configuredTables", [])) if configured else 0,
            "packageTableCount": len(tables),
            "packageRecordCount": sum(record_count(value) for value in tables.values()),
            "matchedConfiguredTables": sorted(present_tables[service] & set(configured.get("configuredTables", []))) if configured else [],
            "unclassifiedTables": sorted(present_tables[service] - set(configured.get("configuredTables", []))) if configured else sorted(tables),
            "sourceRef": source_ref(service, "*"),
        })

        rules = [x for x in knowledge["logicalRules"] if service in x.get("services", []) and x.get("table") in tables]
        rule_by_table = defaultdict(list)
        for rule in rules:
            rule_by_table[rule.get("table")].append(rule)
        relations = [x for x in knowledge["relations"] if x.get("childTable") in tables and service in x.get("childServices", [])]
        external = [x for x in knowledge["externalReferences"] if service in x.get("referencingServices", []) and x.get("runtimeTrigger", {}).get("table") in tables]
        features = [x for x in knowledge["features"] if service in x.get("services", []) and set(x.get("memberTables", [])) & present_tables[service]]
        fragment_key = f"service-fragment:{slug(service)}"
        fragment_keys[service] = fragment_key
        fragments.append({
            "logicalKey": fragment_key,
            "service": service,
            "analysisLevel": level,
            "capability": capability,
            "serviceRole": service_role,
            "semanticOwnerServices": semantic_owners,
            "tables": [{
                "table": table,
                "recordCount": record_count(value),
                "configured": table in (configured.get("configuredTables", []) if configured else []),
                "configuredSemanticOwnerCandidates": sorted(
                    owner for owner in table_owners.get(table, set())
                    if catalog.get(owner, {}).get("dedicatedParser")
                ),
                "primaryKeyFields": sorted({field for rule in rule_by_table[table] for field in rule.get("primaryKeyFields", [])}),
                "businessKeyCandidates": sorted({field for rule in rule_by_table[table] for field in rule.get("businessKeyCandidates", [])}),
                "parentReferences": [ref for rule in rule_by_table[table] for ref in rule.get("parentReferenceFields", [])],
            } for table, value in sorted(tables.items())],
            "relationships": relations,
            "featureGroupRefs": [x.get("featureGroupId") for x in features],
            "externalReferences": external,
            "sourceRef": source_ref(service, "*"),
        })

        for feature in features:
            member_tables = sorted(set(feature.get("memberTables", [])) & present_tables[service])
            business_objects.append({
                "logicalKey": f"business-object:{slug(service)}:{slug(feature.get('featureGroupId'), 'feature')}",
                "service": service,
                "featureGroupId": feature.get("featureGroupId"),
                "name": feature.get("businessName") or feature.get("rootTable") or "未命名业务对象",
                "purpose": feature.get("businessPurpose") or "",
                "userVisibleFunctions": feature.get("userVisibleFunctions") or "",
                "rootTable": feature.get("rootTable"),
                "presentTables": member_tables,
                "presentRecordCount": sum(record_count(tables[x]) for x in member_tables),
                "confidence": feature.get("confidence") or "unknown",
                "analysisLevel": "CONFIG_OBSERVED",
                "sourceRef": source_ref(service, feature.get("rootTable") or "*", feature.get("featureGroupId")),
            })

    dependencies = []
    seen = set()
    for relation in knowledge["relations"]:
        if relation.get("scope") != "cross-module":
            continue
        child_service = next((x for x in relation.get("childServices", []) if x in package_modules), None)
        if not child_service or relation.get("childTable") not in present_tables[child_service]:
            continue
        parent_candidates = sorted(
            service for service in table_owners.get(relation.get("parentTable"), set())
            if service in package_modules and relation.get("parentTable") in present_tables[service]
        )
        if not parent_candidates:
            continue
        for parent_service in parent_candidates:
            if parent_service == child_service:
                continue
            key = (child_service, parent_service, relation.get("childTable"), relation.get("parentTable"), relation.get("sourceField"))
            if key in seen:
                continue
            seen.add(key)
            dependencies.append({
                "logicalKey": f"dependency:service:{slug(child_service)}:{slug(parent_service)}:{slug(relation.get('edgeId'), 'edge')}",
                "from": fragment_keys[child_service],
                "to": fragment_keys[parent_service],
                "kind": "configuration-table-reference",
                "status": "resolved",
                "binding": {
                    "childTable": relation.get("childTable"),
                    "sourceField": relation.get("sourceField"),
                    "parentTable": relation.get("parentTable"),
                    "parentField": relation.get("parentField"),
                },
                "sourceRef": source_ref(child_service, relation.get("childTable"), relation.get("edgeId")),
            })

    external_resources = []
    for fragment in fragments:
        for item in fragment.get("externalReferences", []):
            external_resources.append({
                "logicalKey": f"external-resource:{slug(fragment['service'])}:{slug(item.get('edgeId'), 'edge')}",
                "name": f"{item.get('runtimeTrigger', {}).get('table') or '未知来源'} → {item.get('target', {}).get('table') or '未知目标'}",
                "service": fragment["service"],
                "sourceTable": item.get("runtimeTrigger", {}).get("table"),
                "sourceField": item.get("runtimeTrigger", {}).get("field"),
                "targetTable": item.get("target", {}).get("table"),
                "targetField": item.get("target", {}).get("field"),
                "ownerServiceCandidates": item.get("target", {}).get("ownerServiceCandidates") or [],
                "classification": item.get("classification"),
                "idMechanism": item.get("idMechanism"),
                "resolutionPolicy": item.get("migrationDecision") or {},
                "sourceRef": source_ref(fragment["service"], item.get("runtimeTrigger", {}).get("table") or "*", item.get("edgeId")),
            })
    return {
        "serviceInventory": service_inventory,
        "serviceFragments": fragments,
        "businessObjects": business_objects,
        "dependencies": dependencies,
        "externalResources": external_resources,
        "knowledgeSummary": knowledge["summary"],
    }
