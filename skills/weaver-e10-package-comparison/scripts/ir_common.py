#!/usr/bin/env python3
from __future__ import annotations

import base64
import gzip
import io
import hashlib
import json
import re
from pathlib import Path


SENSITIVE_KEYS = {
    "password", "passwd", "pwd", "secret", "secret_key", "access_key",
    "accesskey", "private_key", "token", "credential",
}


def load_json(path):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def iter_jsonl(path):
    path = Path(path)
    compressed = Path(f"{path}.gz")
    wrapped = path.with_suffix(".json")
    resolved = path if path.is_file() else compressed if compressed.is_file() else wrapped
    if resolved.suffix == ".gz":
        handle = gzip.open(resolved, "rt", encoding="utf-8")
    elif resolved.suffix == ".json":
        wrapper = json.loads(resolved.read_text(encoding="utf-8"))
        wrapper_format = wrapper.get("format")
        if wrapper_format == "skillhub-gzip-base64-v1":
            compressed_data = base64.b64decode(wrapper["data"], validate=True)
        elif wrapper_format == "skillhub-gzip-base85-v1":
            compressed_data = base64.b85decode(wrapper["data"])
        else:
            raise ValueError(f"unsupported knowledge wrapper: {resolved}")
        handle = io.StringIO(gzip.decompress(compressed_data).decode("utf-8"))
    else:
        handle = resolved.open("rt", encoding="utf-8")
    with handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def dump_json(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def sid(value):
    if value is None or value == "":
        return None
    return str(value)


def slug(value, fallback="unnamed"):
    text = str(value or "").strip().lower()
    text = "".join(ch if ch.isalnum() else "-" for ch in text)
    text = re.sub(r"-+", "-", text).strip("-")
    if text:
        return text
    digest = hashlib.sha1(str(value).encode("utf-8")).hexdigest()[:10]
    return f"{fallback}-{digest}"


def logical_key(kind, name=None, stable=None):
    return f"{kind}:{slug(stable or name, kind)}"


def source_ref(service, table, source_id=None, level="CONFIG_OBSERVED", path=None):
    return {
        "level": level,
        "service": service,
        "table": table,
        "sourceId": sid(source_id),
        "path": path,
    }


def table_records(ir, service, table):
    return (
        ir.get("modules", {})
        .get(service, {})
        .get("tables", {})
        .get(table, {})
        .get("records", [])
    )


def parse_object(value):
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except (ValueError, TypeError):
        return {}


def redact(value):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            lowered = str(key).lower()
            result[key] = "***REDACTED***" if lowered in SENSITIVE_KEYS else redact(item)
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def first_value(record, *keys, default=None):
    for key in keys:
        value = record.get(key)
        if value is not None and value != "":
            return value
    return default


def unique_by(items, key="logicalKey"):
    result = []
    seen = set()
    for item in items:
        marker = item.get(key)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(item)
    return result
