#!/usr/bin/env python3
"""把匹配结果计算为字段级原始事实。"""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from typing import Any

from normalize_records import diff_values, summarize_value


def change_id(seed: str) -> str:
    return "CHG-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16].upper()


def object_stub(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "module": item["module"],
        "moduleKind": item["moduleKind"],
        "table": item["table"],
        "objectType": item["objectType"],
        "packageUnit": item.get("packageUnit"),
        "packageUnitKey": item.get("packageUnitKey", "__single__"),
        "logicalKey": item["logicalKey"],
        "displayName": item["displayName"],
        "identityConfidence": item["identityConfidence"],
        "identityMethod": item.get("identityMethod"),
        "lineageSource": item.get("lineageSource"),
        "lineageEvidencePath": item.get("lineageEvidencePath"),
        "lineageKeyHash": item.get("lineageKeyHash"),
        "currentIdResolution": item.get("currentIdResolution"),
        "ambiguityReason": item.get("ambiguityReason"),
        "parentIdentityKey": item.get("parentIdentityKey"),
        "profileCorroborated": item.get("profileCorroborated"),
        "lineageIdentity": item.get("lineageIdentity"),
        "configIds": item.get("configIds") or [],
        "sourceEvidence": item.get("sourceEvidence") or {},
        "unresolvedReferences": item.get("unresolvedReferences") or [],
    }


def calculate_diff(
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    matching: dict[str, Any],
) -> dict[str, Any]:
    old_objects = old_index["objects"]
    new_objects = new_index["objects"]
    facts: list[dict[str, Any]] = []

    for match in matching["matches"]:
        old = old_objects[match["oldIndex"]]
        new = new_objects[match["newIndex"]]
        paths = diff_values(old["canonical"], new["canonical"])
        if match["matchType"] == "POSSIBLE_RENAME":
            change_type = "POSSIBLE_RENAME"
        else:
            change_type = "UPDATED" if paths else "UNCHANGED"
        identifier = change_id(
            f"{old['logicalKey']}|{new['logicalKey']}|{change_type}"
        )
        facts.append({
            "changeId": identifier,
            "changeType": change_type,
            "evidenceLevel": "OBSERVED",
            "match": match,
            "object": object_stub(new),
            "oldObject": object_stub(old),
            "beforeHash": old["canonicalHash"],
            "afterHash": new["canonicalHash"],
            "before": None if change_type == "UNCHANGED" else summarize_value(old["canonical"]),
            "after": None if change_type == "UNCHANGED" else summarize_value(new["canonical"]),
            "changedPaths": paths,
            "sourceIdOnlyChange": bool(
                not paths and old["sourceEvidence"].get("primaryValueHash")
                != new["sourceEvidence"].get("primaryValueHash")
            ),
        })

    for item in matching["unmatchedOld"]:
        old = old_objects[item["index"]]
        ambiguous = bool(old.get("ambiguityReason"))
        low_confidence = old["identityConfidence"] == "LOW"
        change_type = "UNMATCHED" if ambiguous or low_confidence or item.get("candidates") else "REMOVED"
        identifier = change_id(f"{old['logicalKey']}|{change_type}|old")
        facts.append({
            "changeId": identifier,
            "changeType": change_type,
            "evidenceLevel": "UNKNOWN" if change_type == "UNMATCHED" else "OBSERVED",
            "object": object_stub(old),
            "oldObject": object_stub(old),
            "beforeHash": old["canonicalHash"],
            "afterHash": None,
            "before": summarize_value(old["canonical"]),
            "after": None,
            "changedPaths": [],
            "matchCandidates": item.get("candidates") or [],
            "sourceIdOnlyChange": False,
        })
    for item in matching["unmatchedNew"]:
        new = new_objects[item["index"]]
        ambiguous = bool(new.get("ambiguityReason"))
        low_confidence = new["identityConfidence"] == "LOW"
        change_type = "UNMATCHED" if ambiguous or low_confidence else "ADDED"
        identifier = change_id(f"{new['logicalKey']}|{change_type}|new")
        facts.append({
            "changeId": identifier,
            "changeType": change_type,
            "evidenceLevel": "UNKNOWN" if change_type == "UNMATCHED" else "OBSERVED",
            "object": object_stub(new),
            "oldObject": None,
            "beforeHash": None,
            "afterHash": new["canonicalHash"],
            "before": None,
            "after": summarize_value(new["canonical"]),
            "changedPaths": [],
            "matchCandidates": [],
            "sourceIdOnlyChange": False,
        })

    facts.sort(key=lambda item: (
        item["object"]["module"],
        item["object"]["table"],
        item["object"]["logicalKey"],
        item["changeType"],
    ))
    type_counts = Counter(item["changeType"] for item in facts)
    module_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for item in facts:
        module_counts[item["object"]["module"]][item["changeType"]] += 1
    return {
        "schemaVersion": "ebuilder-comparison-facts/v1.0",
        "facts": facts,
        "summary": {
            "total": len(facts),
            "byChangeType": dict(type_counts),
            "byModule": {
                module: dict(counts)
                for module, counts in sorted(module_counts.items())
            },
            "sourceIdOnlyChangesSuppressed": sum(
                item["sourceIdOnlyChange"] for item in facts
            ),
        },
    }
