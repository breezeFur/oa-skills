#!/usr/bin/env python3
"""使用稳定逻辑键、内容签名和保守相似度匹配两个版本的对象。"""

from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher
from typing import Any

from normalize_records import canonical_json


NAME_TOKENS = ("name", "title", "label", "display", "show_name")


def has_strong_idm_identity(item: dict[str, Any]) -> bool:
    return item.get("identityMethod") == "MIGRATION_IDM_SOURCE_ID"


def comparison_tokens(value: Any, prefix: str = "") -> dict[str, str]:
    result: dict[str, str] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if any(token in str(key).lower() for token in NAME_TOKENS):
                continue
            result.update(comparison_tokens(child, path))
    elif isinstance(value, list):
        result[prefix] = canonical_json(value)
    else:
        result[prefix] = canonical_json(value)
    return result


def similarity(
    left: dict[str, Any],
    right: dict[str, Any],
    left_tokens: dict[str, str] | None = None,
    right_tokens: dict[str, str] | None = None,
) -> float:
    if (
        left["module"] != right["module"]
        or left["table"] != right["table"]
        or left.get("packageUnitKey") != right.get("packageUnitKey")
    ):
        return 0.0
    left_tokens = left_tokens if left_tokens is not None else comparison_tokens(left["canonical"])
    right_tokens = right_tokens if right_tokens is not None else comparison_tokens(right["canonical"])
    keys = set(left_tokens) | set(right_tokens)
    if not keys:
        return 0.0
    exact = sum(left_tokens.get(key) == right_tokens.get(key) for key in keys)
    structural = exact / len(keys)
    key_similarity = SequenceMatcher(
        None,
        left["logicalKey"].split("::")[-1],
        right["logicalKey"].split("::")[-1],
    ).ratio()
    return structural * 0.9 + key_similarity * 0.1


def non_name_content_hash(item: dict[str, Any]) -> str:
    import hashlib

    tokens = comparison_tokens(item["canonical"])
    payload = canonical_json(tokens)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def match_objects(old_index: dict[str, Any], new_index: dict[str, Any]) -> dict[str, Any]:
    old_objects = old_index["objects"]
    new_objects = new_index["objects"]
    old_by_key: dict[str, list[int]] = defaultdict(list)
    new_by_key: dict[str, list[int]] = defaultdict(list)
    for index, item in enumerate(old_objects):
        old_by_key[item["logicalKey"]].append(index)
    for index, item in enumerate(new_objects):
        new_by_key[item["logicalKey"]].append(index)

    matches: list[dict[str, Any]] = []
    used_old: set[int] = set()
    used_new: set[int] = set()
    for key in sorted(set(old_by_key) & set(new_by_key)):
        old_candidates = old_by_key[key]
        new_candidates = new_by_key[key]
        for old_idx, new_idx in zip(old_candidates, new_candidates):
            old_item = old_objects[old_idx]
            new_item = new_objects[new_idx]
            old_method = old_item.get("identityMethod")
            new_method = new_item.get("identityMethod")
            method_match_types = {
                "MIGRATION_IDM_SOURCE_ID": "MIGRATION_IDM_SOURCE_ID",
                "PROFILE_HOMOLOGY": "PROFILE_HOMOLOGY",
                "BUSINESS_KEY": "BUSINESS_KEY",
                "PARENT_RELATION_PATH": "PARENT_RELATION_PATH",
                "CONTENT_FINGERPRINT": "CONTENT_FINGERPRINT",
            }
            matches.append({
                "oldIndex": old_idx,
                "newIndex": new_idx,
                "matchType": (
                    method_match_types.get(old_method, "STABLE_LOGICAL_KEY")
                    if old_method == new_method
                    else "STABLE_LOGICAL_KEY"
                ),
                "confidence": "HIGH",
                "score": 1.0,
            })
            used_old.add(old_idx)
            used_new.add(new_idx)

    old_remaining = [
        index for index in range(len(old_objects)) if index not in used_old
    ]
    new_remaining = [
        index for index in range(len(new_objects)) if index not in used_new
    ]
    new_by_content: dict[tuple[str, str, str, str], list[int]] = defaultdict(list)
    for index in new_remaining:
        item = new_objects[index]
        if has_strong_idm_identity(item):
            continue
        new_by_content[
            (item.get("packageUnitKey", "__single__"), item["module"], item["table"], item["identityContentHash"])
        ].append(index)
    for old_idx in list(old_remaining):
        old = old_objects[old_idx]
        if has_strong_idm_identity(old):
            continue
        candidates = new_by_content.get(
            (old.get("packageUnitKey", "__single__"), old["module"], old["table"], old["identityContentHash"]), []
        )
        candidates = [index for index in candidates if index not in used_new]
        if len(candidates) == 1:
            new_idx = candidates[0]
            matches.append({
                "oldIndex": old_idx,
                "newIndex": new_idx,
                "matchType": "CONTENT_EQUIVALENT_IDENTITY_CHANGED",
                "confidence": "MEDIUM",
                "score": 1.0,
            })
            used_old.add(old_idx)
            used_new.add(new_idx)

    old_remaining = [
        index for index in range(len(old_objects)) if index not in used_old
    ]
    new_remaining = [
        index for index in range(len(new_objects)) if index not in used_new
    ]
    new_by_non_name: dict[tuple[str, str, str, str], list[int]] = defaultdict(list)
    for index in new_remaining:
        item = new_objects[index]
        if has_strong_idm_identity(item):
            continue
        new_by_non_name[
            (item.get("packageUnitKey", "__single__"), item["module"], item["table"], non_name_content_hash(item))
        ].append(index)
    for old_idx in list(old_remaining):
        old = old_objects[old_idx]
        if has_strong_idm_identity(old):
            continue
        candidates = new_by_non_name.get(
            (old.get("packageUnitKey", "__single__"), old["module"], old["table"], non_name_content_hash(old)), []
        )
        candidates = [index for index in candidates if index not in used_new]
        if len(candidates) == 1:
            new_idx = candidates[0]
            matches.append({
                "oldIndex": old_idx,
                "newIndex": new_idx,
                "matchType": "POSSIBLE_RENAME",
                "confidence": "MEDIUM",
                "score": 1.0,
            })
            used_old.add(old_idx)
            used_new.add(new_idx)

    old_remaining = [
        index for index in range(len(old_objects)) if index not in used_old
    ]
    new_remaining = [
        index for index in range(len(new_objects)) if index not in used_new
    ]
    by_table_new: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for index in new_remaining:
        item = new_objects[index]
        if has_strong_idm_identity(item):
            continue
        by_table_new[(item.get("packageUnitKey", "__single__"), item["module"], item["table"])].append(index)

    candidate_registry: dict[int, list[tuple[float, int]]] = {}
    # Weak-candidate scoring used to recursively tokenize the same records for
    # every pair in a table (up to 200 times per object).  Cache each record's
    # tokens once; this changes neither candidate scope nor similarity maths.
    old_token_cache: dict[int, dict[str, str]] = {}
    new_token_cache: dict[int, dict[str, str]] = {}
    for old_idx in old_remaining:
        old = old_objects[old_idx]
        if has_strong_idm_identity(old):
            candidate_registry[old_idx] = []
            continue
        table_candidates = by_table_new.get(
            (old.get("packageUnitKey", "__single__"), old["module"], old["table"]), []
        )
        if len(table_candidates) > 200:
            candidate_registry[old_idx] = []
            continue
        left_tokens = old_token_cache.get(old_idx)
        if left_tokens is None:
            left_tokens = comparison_tokens(old["canonical"])
            old_token_cache[old_idx] = left_tokens
        scored = []
        for new_idx in table_candidates:
            right_tokens = new_token_cache.get(new_idx)
            if right_tokens is None:
                right_tokens = comparison_tokens(new_objects[new_idx]["canonical"])
                new_token_cache[new_idx] = right_tokens
            scored.append(
                (
                    similarity(old, new_objects[new_idx], left_tokens, right_tokens),
                    new_idx,
                )
            )
        scored = sorted(
            ((score, index) for score, index in scored if score >= 0.65),
            reverse=True,
        )[:3]
        candidate_registry[old_idx] = scored

    proposals = []
    for old_idx, candidates in candidate_registry.items():
        if not candidates:
            continue
        best_score, best_new = candidates[0]
        second_score = candidates[1][0] if len(candidates) > 1 else 0.0
        if best_score >= 0.92 and best_score - second_score >= 0.08:
            proposals.append((best_score, old_idx, best_new))
    for score, old_idx, new_idx in sorted(proposals, reverse=True):
        if old_idx in used_old or new_idx in used_new:
            continue
        competing = [
            proposal
            for proposal in proposals
            if proposal[2] == new_idx and proposal[1] not in used_old
        ]
        if len(competing) > 1 and competing[0][0] - competing[1][0] < 0.08:
            continue
        matches.append({
            "oldIndex": old_idx,
            "newIndex": new_idx,
            "matchType": "POSSIBLE_RENAME",
            "confidence": "MEDIUM",
            "score": round(score, 6),
        })
        used_old.add(old_idx)
        used_new.add(new_idx)

    unmatched_old = []
    for old_idx in range(len(old_objects)):
        if old_idx in used_old:
            continue
        candidates = [
            {
                "newIndex": new_idx,
                "logicalKey": new_objects[new_idx]["logicalKey"],
                "score": round(score, 6),
            }
            for score, new_idx in candidate_registry.get(old_idx, [])
            if new_idx not in used_new
        ]
        unmatched_old.append({"index": old_idx, "candidates": candidates})
    unmatched_new = [
        {"index": index}
        for index in range(len(new_objects))
        if index not in used_new
    ]
    return {
        "matches": sorted(matches, key=lambda item: (item["oldIndex"], item["newIndex"])),
        "unmatchedOld": unmatched_old,
        "unmatchedNew": unmatched_new,
    }
