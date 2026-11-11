#!/usr/bin/env python3
"""仅对实际变化与实际字段门禁命中的规则触发风险，并按根因去重。"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from knowledge_io import iter_jsonl

SEVERITY_ORDER = {"LOW": 0, "MEDIUM": 1, "UNKNOWN": 2, "HIGH": 3}

def split_tables(values: list[str]) -> set[str]:
    result = set()
    for value in values:
        for table in re.split(r"[;,+|/]", str(value)):
            if table.strip():
                result.add(table.strip().lower())
    return result


def changed_root_fields(fact: dict[str, Any]) -> set[str]:
    if fact["changeType"] in {"ADDED", "REMOVED"}:
        return {"*"}
    return {
        str(item.get("path") or "").split(".", 1)[0].split("[", 1)[0].lower()
        for item in fact.get("changedPaths") or []
    }


def value_gate(fact: dict[str, Any], required_fields: set[str], require_non_empty: bool) -> bool:
    roots = changed_root_fields(fact)
    if required_fields and "*" not in roots and not (roots & required_fields):
        return False
    if not require_non_empty:
        return True
    if fact["changeType"] in {"ADDED", "REMOVED"}:
        return fact.get("before") is not None or fact.get("after") is not None
    for item in fact.get("changedPaths") or []:
        root = str(item.get("path") or "").split(".", 1)[0].lower()
        if not required_fields or root in required_fields:
            if item.get("before") not in (None, "", [], {}) or item.get("after") not in (None, "", [], {}):
                return True
    return False


def default_fact_risk(fact: dict[str, Any]) -> str:
    change_type = fact["changeType"]
    if change_type == "REMOVED":
        return "HIGH"
    if change_type in {"UNMATCHED", "POSSIBLE_RENAME"}:
        return "UNKNOWN"
    if change_type == "ADDED":
        return "MEDIUM"
    if change_type == "UNCHANGED":
        return "LOW"
    categories = {
        item.get("category") for item in fact.get("changedPaths") or []
    }
    if categories & {
        "FUNCTION_BEHAVIOR", "DATA_SEMANTICS", "PERMISSION_SECURITY", "REFERENCE_ID"
    }:
        return "HIGH"
    if "NAVIGATION_DISPLAY" in categories:
        return "MEDIUM"
    return "LOW"


def _risk_id(prefix: str, seed: str) -> str:
    return prefix + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16].upper()


def derived_trigger_fields(rule: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    allowed_key = re.compile(
        r"fields?$|fieldnames?$|columns?$|additionalreferencefields?$|referencefields?$",
        re.IGNORECASE,
    )

    def walk(value: Any, parent_key: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, str(key))
        elif isinstance(value, list):
            for child in value:
                walk(child, parent_key)
        elif isinstance(value, str) and allowed_key.search(parent_key):
            for token in re.split(r"[,;|+\s]+", value):
                if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{1,63}", token):
                    result.add(token.lower())

    walk(rule.get("evidence") or {})
    trigger_text = str((rule.get("signature") or {}).get("triggerCondition") or "")
    for table, field in re.findall(
        r"\b([A-Za-z][A-Za-z0-9_]*)\.([A-Za-z][A-Za-z0-9_]*)\b",
        trigger_text,
    ):
        result.add(field.lower())
    return result


def has_restrictive_condition(rule: dict[str, Any]) -> bool:
    text = str((rule.get("signature") or {}).get("triggerCondition") or "")
    return bool(re.search(r"仅当|仅在|有值时|非空时|满足.+时|实际包含|启用.+时", text))


def trigger_risks(
    facts: list[dict[str, Any]],
    knowledge_dir: Path,
) -> list[dict[str, Any]]:
    changed = [fact for fact in facts if fact["changeType"] != "UNCHANGED"]
    by_table: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_config: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_change_id = {fact["changeId"]: fact for fact in changed}
    for fact in facts:
        fact["riskLevel"] = default_fact_risk(fact)
        fact["riskIds"] = []
    for fact in changed:
        by_table[str(fact["object"]["table"]).lower()].append(fact)
        for config_id in fact["object"].get("configIds") or []:
            by_config[str(config_id)].append(fact)

    results: list[dict[str, Any]] = []
    seen_roots: set[str] = set()

    for rule in iter_jsonl(knowledge_dir / "risk-rules.jsonl"):
        trigger = rule.get("runtimeTrigger") or {}
        tables = split_tables(trigger.get("tables") or [])
        fields = {str(value).lower() for value in trigger.get("fields") or []}
        if not fields:
            fields = derived_trigger_fields(rule)
        if not fields and has_restrictive_condition(rule):
            continue
        candidates: dict[str, dict[str, Any]] = {}
        if tables:
            for table in tables:
                for fact in by_table.get(table, []):
                    candidates[fact["changeId"]] = fact
        else:
            for config_id in trigger.get("configIds") or []:
                for fact in by_config.get(str(config_id), []):
                    candidates[fact["changeId"]] = fact
        if not candidates:
            continue
        matched = [
            fact for fact in candidates.values()
            if value_gate(
                fact,
                fields,
                bool(trigger.get("requiresNonEmptyValue") or fields),
            )
        ]
        if not matched:
            continue
        root = str(rule.get("signatureHash") or rule.get("riskId"))
        if root in seen_roots:
            continue
        seen_roots.add(root)
        severity = str(rule.get("severity") or "UNKNOWN").upper()
        signature = rule.get("signature") or {}
        risk_id = str(rule.get("riskId"))
        result = {
            "riskId": risk_id,
            "rootSignature": root,
            "riskType": signature.get("type") or rule.get("classification"),
            "severity": severity if severity in SEVERITY_ORDER else "UNKNOWN",
            "title": signature.get("triggerCondition") or "配置变化命中已知迁移风险根因",
            "migrationMechanism": signature.get("handlerOrIdMapMechanism"),
            "classification": rule.get("classification"),
            "affectedChangeIds": sorted(fact["changeId"] for fact in matched),
            "affectedObjects": sorted({
                fact["object"]["logicalKey"] for fact in matched
            }),
            "evidenceLevel": "OBSERVED",
            "knowledgeEvidence": {
                "codexRiskId": rule.get("riskId"),
                "affectedConfigIds": rule.get("affectedConfigIds") or [],
                "affectedEdgeIds": rule.get("affectedEdgeIds") or [],
            },
            "verificationGuidance": rule.get("verification") or [],
            "triggerEvidence": {
                "tables": sorted(tables),
                "fields": sorted(fields),
                "actualChangedRecords": len(matched),
            },
        }
        results.append(result)
        for fact in matched:
            fact["riskIds"].append(risk_id)
            if SEVERITY_ORDER[result["severity"]] > SEVERITY_ORDER[fact["riskLevel"]]:
                fact["riskLevel"] = result["severity"]

    id_groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for rule in iter_jsonl(knowledge_dir / "id-replacement-rules.jsonl"):
        trigger = rule.get("runtimeTrigger") or {}
        table = str(trigger.get("table") or "").lower()
        field = str(trigger.get("field") or "").lower()
        failure = rule.get("failureBehavior") or {}
        failure_signature = json.dumps(failure, ensure_ascii=False, sort_keys=True)
        key = (
            table,
            field,
            str(rule.get("relationKind") or ""),
            hashlib.sha256(failure_signature.encode("utf-8")).hexdigest()[:12],
        )
        id_groups[key].append(rule)
    for (table, field, relation_kind, failure_hash), rules in id_groups.items():
        if not table:
            continue
        fields = {field} if field else set()
        matched = [
            fact for fact in by_table.get(table, [])
            if value_gate(fact, fields, bool(field))
        ]
        if not matched:
            continue
        failure = rules[0].get("failureBehavior") or {}
        severity = (
            "HIGH"
            if relation_kind in {"JSON_REFERENCE", "POLYMORPHIC_REFERENCE", "CROSS_SERVICE_REFERENCE"}
            or failure.get("setNull")
            or failure.get("partialReplacementPossible")
            else "MEDIUM"
        )
        seed = f"{table}|{field}|{relation_kind}|{failure_hash}"
        risk_id = _risk_id("IDR-", seed)
        result = {
            "riskId": risk_id,
            "rootSignature": seed,
            "riskType": "ID_REPLACEMENT",
            "severity": severity,
            "title": f"{table}.{field or '*'} 的 {relation_kind or 'ID'} 替换需核对",
            "migrationMechanism": rules[0].get("replaceMethod"),
            "classification": "KNOWN_ID_REPLACEMENT_PATH",
            "affectedChangeIds": sorted(fact["changeId"] for fact in matched),
            "affectedObjects": sorted({fact["object"]["logicalKey"] for fact in matched}),
            "evidenceLevel": "OBSERVED",
            "knowledgeEvidence": {
                "codexClosureIds": [rule.get("closureId") for rule in rules[:50]],
                "closureCount": len(rules),
            },
            "verificationGuidance": rules[0].get("importVerificationPoints") or [],
            "triggerEvidence": {
                "tables": [table],
                "fields": [field] if field else [],
                "actualChangedRecords": len(matched),
            },
        }
        results.append(result)
        for fact in matched:
            fact["riskIds"].append(risk_id)
            if SEVERITY_ORDER[severity] > SEVERITY_ORDER[fact["riskLevel"]]:
                fact["riskLevel"] = severity

    external_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for rule in iter_jsonl(knowledge_dir / "external-reference-rules.jsonl"):
        trigger = rule.get("runtimeTrigger") or {}
        table = str(trigger.get("table") or "").lower()
        field = str(trigger.get("field") or "").lower()
        classification = str(rule.get("finalClassification") or "UNKNOWN")
        external_groups[(table, field, classification)].append(rule)
    for (table, field, classification), rules in external_groups.items():
        if not table:
            continue
        matched = [
            fact for fact in by_table.get(table, [])
            if value_gate(fact, {field} if field else set(), bool(field))
        ]
        if not matched:
            continue
        unknown = any(
            str(rule.get("decisionStatus") or "").startswith("REQUIRES")
            for rule in rules
        )
        severity = "UNKNOWN" if unknown else "HIGH"
        seed = f"{table}|{field}|{classification}"
        risk_id = _risk_id("EXT-", seed)
        first = rules[0]
        decision = first.get("migrationDecision") or {}
        result = {
            "riskId": risk_id,
            "rootSignature": seed,
            "riskType": "EXTERNAL_REFERENCE",
            "severity": severity,
            "title": f"{table}.{field or '*'} 存在包外或跨服务引用，需按证据门禁确认",
            "migrationMechanism": decision.get("importUiOrMappingInput"),
            "classification": classification,
            "affectedChangeIds": sorted(fact["changeId"] for fact in matched),
            "affectedObjects": sorted({fact["object"]["logicalKey"] for fact in matched}),
            "evidenceLevel": "UNKNOWN" if unknown else "INFERRED",
            "knowledgeEvidence": {
                "codexExternalEdgeIds": [rule.get("edgeId") for rule in rules],
                "ruleCount": len(rules),
            },
            "verificationGuidance": [
                decision.get("importUiOrMappingInput"),
                decision.get("missingBehavior"),
            ],
            "triggerEvidence": {
                "tables": [table],
                "fields": [field] if field else [],
                "actualChangedRecords": len(matched),
            },
            "uncertaintyStatement": (
                "当前只能确认存在引用门禁，不能据此断言目标环境已经故障。"
                if unknown else None
            ),
        }
        results.append(result)
        for fact in matched:
            fact["riskIds"].append(risk_id)
            if SEVERITY_ORDER[severity] > SEVERITY_ORDER[fact["riskLevel"]]:
                fact["riskLevel"] = severity

    existing_risk_ids = {item["riskId"] for item in results}
    for fact in changed:
        if fact.get("object", {}).get("unresolvedReferences"):
            seed = f"unresolved|{fact['object']['module']}|{fact['object']['table']}"
            risk_id = _risk_id("UNK-", seed)
            if risk_id not in existing_risk_ids:
                peers = [
                    peer for peer in by_table[fact["object"]["table"].lower()]
                    if peer.get("object", {}).get("unresolvedReferences")
                ]
                results.append({
                    "riskId": risk_id,
                    "rootSignature": seed,
                    "riskType": "UNRESOLVED_EMBEDDED_REFERENCE",
                    "severity": "UNKNOWN",
                    "title": f"{fact['object']['table']} 变化记录含无法稳定解析的 ID 形态",
                    "migrationMechanism": "需要结合目标映射或运行证据确认",
                    "classification": "UNKNOWN_REFERENCE",
                    "affectedChangeIds": sorted(peer["changeId"] for peer in peers),
                    "affectedObjects": sorted({peer["object"]["logicalKey"] for peer in peers}),
                    "evidenceLevel": "UNKNOWN",
                    "knowledgeEvidence": {},
                    "verificationGuidance": [
                        "解析变更字段中的 ID，并与目标环境对象映射逐项核对。",
                        "未确认前不得描述为确定故障。",
                    ],
                    "triggerEvidence": {
                        "tables": [fact["object"]["table"].lower()],
                        "actualChangedRecords": len(peers),
                    },
                    "uncertaintyStatement": "存在未解析引用形态，但静态证据不足以确认迁入后故障。",
                })
                for peer in peers:
                    peer["riskIds"].append(risk_id)
                    if SEVERITY_ORDER["UNKNOWN"] > SEVERITY_ORDER[peer["riskLevel"]]:
                        peer["riskLevel"] = "UNKNOWN"
                existing_risk_ids.add(risk_id)

    results.sort(key=lambda item: (
        -SEVERITY_ORDER.get(item["severity"], 2),
        item["riskId"],
    ))
    return results
