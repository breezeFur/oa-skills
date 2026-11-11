#!/usr/bin/env python3
"""eBuilder 记录归一化、字段分类和字段级差异工具。"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable


NOISE_RE = re.compile(
    r"(^|_)(create|created|update|updated|modify|modified|export|import|batch|task)"
    r"(_)?(time|date|at|id)?$|^(creator|modifier|updater|operator|tenant_key)$",
    re.IGNORECASE,
)
ID_FIELD_RE = re.compile(
    r"(^id$|_id$|Id$|^id_|ids$|_ids$|uuid|guid|source_id|target_id|ref_id|relation_id)",
    re.IGNORECASE,
)
ID_VALUE_RE = re.compile(
    r"^(?:-?\d{10,}|[0-9a-f]{8}-[0-9a-f-]{27,}|[0-9a-f]{24,})$",
    re.IGNORECASE,
)
UNORDERED_FIELD_RE = re.compile(
    r"(permissions?|rights?|roles?|members?|ids?|options?|sets?|tags?|"
    r"columns?|fields?|resources?|scopes?|authorities?)$",
    re.IGNORECASE,
)
PERMISSION_RE = re.compile(r"permission|right|auth|role|scope|visible", re.IGNORECASE)
NAVIGATION_RE = re.compile(r"menu|nav|route|path|url|page|layout|style|order", re.IGNORECASE)
DATA_RE = re.compile(
    r"field|column|type|length|len|precision|required|nullable|default|option|"
    r"dataset|table|form|sub_form|data_key",
    re.IGNORECASE,
)
BEHAVIOR_RE = re.compile(
    r"action|flow|formula|condition|trigger|event|script|sql|mapping|handler|"
    r"component|enable|status|method|request|response",
    re.IGNORECASE,
)
SENSITIVE_RE = re.compile(
    r"password|passwd|secret|token|credential|private[_-]?key|access[_-]?key|db_password",
    re.IGNORECASE,
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def is_noise_field(field: str) -> bool:
    return bool(NOISE_RE.search(field))


def is_id_field(field: str) -> bool:
    return bool(ID_FIELD_RE.search(field))


def is_id_value(value: Any) -> bool:
    return isinstance(value, (str, int)) and bool(ID_VALUE_RE.match(str(value).strip()))


def normalize_scalar(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lower() in {"", "null", "none", "undefined", "~null~"}:
            return None
        if stripped.lower() == "true":
            return True
        if stripped.lower() == "false":
            return False
        if re.fullmatch(r"-?\d+", stripped) and len(stripped.lstrip("-")) < 10:
            try:
                return int(stripped)
            except ValueError:
                pass
        if re.fullmatch(r"-?\d+\.\d+", stripped):
            try:
                return float(stripped)
            except ValueError:
                pass
        return stripped
    return value


def parse_json_string(value: str) -> Any:
    stripped = value.strip()
    if not (
        (stripped.startswith("{") and stripped.endswith("}"))
        or (stripped.startswith("[") and stripped.endswith("]"))
    ):
        return value
    try:
        return json.loads(stripped)
    except (json.JSONDecodeError, TypeError, ValueError):
        return value


def normalize_value(
    value: Any,
    field: str = "",
    *,
    id_resolver=None,
    unresolved_ids: list[dict[str, Any]] | None = None,
    path: str = "",
) -> Any:
    if SENSITIVE_RE.search(field):
        return {
            "$redacted": True,
            "present": value not in (None, "", [], {}),
            "valueHash": (
                hashlib.sha256(str(value).encode("utf-8")).hexdigest()
                if value not in (None, "", [], {})
                else None
            ),
        }
    if isinstance(value, str):
        parsed = parse_json_string(value)
        if parsed is not value:
            return normalize_value(
                parsed,
                field,
                id_resolver=id_resolver,
                unresolved_ids=unresolved_ids,
                path=path,
            )
        value = normalize_scalar(value)
    if isinstance(value, dict):
        result = {}
        for key in sorted(value, key=lambda item: str(item).lower()):
            key_text = str(key)
            if is_noise_field(key_text):
                continue
            result[key_text] = normalize_value(
                value[key],
                key_text,
                id_resolver=id_resolver,
                unresolved_ids=unresolved_ids,
                path=f"{path}.{key_text}" if path else key_text,
            )
        return result
    if isinstance(value, list):
        normalized = [
            normalize_value(
                item,
                field,
                id_resolver=id_resolver,
                unresolved_ids=unresolved_ids,
                path=f"{path}[{index}]",
            )
            for index, item in enumerate(value)
        ]
        if UNORDERED_FIELD_RE.search(field) or all(
            not isinstance(item, (dict, list)) for item in normalized
        ):
            return sorted(normalized, key=canonical_json)
        return normalized
    if is_id_value(value):
        resolved = id_resolver(value, field) if id_resolver else None
        if resolved:
            return {"$ref": resolved}
        if unresolved_ids is not None:
            unresolved_ids.append({
                "path": path or field,
                "field": field,
                "valueHash": hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16],
                "shape": "UUID" if "-" in str(value) else f"NUMERIC_{len(str(value).lstrip('-'))}",
            })
        return {"$unresolvedId": "UUID" if "-" in str(value) else "NUMERIC"}
    return normalize_scalar(value)


def normalize_record(
    row: dict[str, Any],
    *,
    primary_fields: Iterable[str] = (),
    id_resolver=None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    primary_lower = {str(field).lower() for field in primary_fields}
    unresolved: list[dict[str, Any]] = []
    result: dict[str, Any] = {}
    for key in sorted(row, key=lambda item: str(item).lower()):
        field = str(key)
        if field.lower() in primary_lower or is_noise_field(field):
            continue
        result[field] = normalize_value(
            row[key],
            field,
            id_resolver=id_resolver,
            unresolved_ids=unresolved,
            path=field,
        )
    return result, unresolved


def stable_content_for_identity(
    row: dict[str, Any],
    *,
    primary_fields: Iterable[str] = (),
    preserve_fields: Iterable[str] = (),
) -> dict[str, Any]:
    primary_lower = {str(field).lower() for field in primary_fields}
    preserve_lower = {str(field).lower() for field in preserve_fields}
    result: dict[str, Any] = {}
    for key in sorted(row, key=lambda item: str(item).lower()):
        field = str(key)
        lowered = field.lower()
        if lowered in primary_lower or is_noise_field(field):
            continue
        if is_id_field(field) and lowered not in preserve_lower:
            continue
        value = normalize_value(row[key], field)
        if value not in (None, "", [], {}):
            result[field] = value
    return result


def diff_values(before: Any, after: Any, path: str = "") -> list[dict[str, Any]]:
    if before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        changes: list[dict[str, Any]] = []
        for key in sorted(set(before) | set(after)):
            child_path = f"{path}.{key}" if path else str(key)
            if key not in before:
                changes.append({
                    "path": child_path,
                    "operation": "FIELD_ADDED",
                    "before": None,
                    "after": summarize_value(after[key]),
                    "category": classify_field(child_path),
                })
            elif key not in after:
                changes.append({
                    "path": child_path,
                    "operation": "FIELD_REMOVED",
                    "before": summarize_value(before[key]),
                    "after": None,
                    "category": classify_field(child_path),
                })
            else:
                changes.extend(diff_values(before[key], after[key], child_path))
        return changes
    if isinstance(before, list) and isinstance(after, list):
        return [{
            "path": path,
            "operation": "LIST_UPDATED",
            "before": summarize_value(before),
            "after": summarize_value(after),
            "category": classify_field(path),
        }]
    return [{
        "path": path,
        "operation": "VALUE_UPDATED",
        "before": summarize_value(before),
        "after": summarize_value(after),
        "category": classify_field(path),
    }]


def summarize_value(value: Any, limit: int = 480) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = canonical_json(value) if isinstance(value, (dict, list)) else str(value)
    if len(text) <= limit:
        return value
    return {
        "summary": text[:limit] + "…",
        "length": len(text),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "truncated": True,
    }


def classify_field(path: str) -> str:
    if is_noise_field(path.split(".")[-1]):
        return "NOISE"
    if PERMISSION_RE.search(path):
        return "PERMISSION_SECURITY"
    if BEHAVIOR_RE.search(path):
        return "FUNCTION_BEHAVIOR"
    if DATA_RE.search(path):
        return "DATA_SEMANTICS"
    if NAVIGATION_RE.search(path):
        return "NAVIGATION_DISPLAY"
    if is_id_field(path.split(".")[-1]):
        return "REFERENCE_ID"
    return "UNKNOWN"
