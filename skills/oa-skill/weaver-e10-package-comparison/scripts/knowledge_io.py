#!/usr/bin/env python3
"""Read plain or deterministically gzip-compressed knowledge files."""

from __future__ import annotations

import base64
import gzip
import io
import json
from pathlib import Path


BASE64_WRAPPER_FORMAT = "skillhub-gzip-base64-v1"
BASE85_WRAPPER_FORMAT = "skillhub-gzip-base85-v1"


def resolve_data_path(path: Path) -> Path:
    path = Path(path)
    if path.is_file():
        return path
    compressed = Path(f"{path}.gz")
    if compressed.is_file():
        return compressed
    wrapped = path.with_suffix(".json")
    if wrapped.is_file():
        return wrapped
    raise FileNotFoundError(path)


def decode_wrapper(path: Path) -> bytes:
    wrapper = json.loads(path.read_text(encoding="utf-8"))
    wrapper_format = wrapper.get("format")
    if wrapper_format == BASE64_WRAPPER_FORMAT:
        compressed = base64.b64decode(wrapper["data"], validate=True)
    elif wrapper_format == BASE85_WRAPPER_FORMAT:
        compressed = base64.b85decode(wrapper["data"])
    else:
        raise ValueError(f"unsupported knowledge wrapper: {path}")
    return gzip.decompress(compressed)


def open_binary(path: Path):
    resolved = resolve_data_path(path)
    if resolved.suffix == ".gz":
        return gzip.open(resolved, "rb")
    if resolved.suffix == ".json":
        return io.BytesIO(decode_wrapper(resolved))
    return resolved.open("rb")


def open_text(path: Path):
    resolved = resolve_data_path(path)
    if resolved.suffix == ".gz":
        return gzip.open(resolved, "rt", encoding="utf-8")
    if resolved.suffix == ".json":
        return io.StringIO(decode_wrapper(resolved).decode("utf-8"))
    return resolved.open("r", encoding="utf-8")


def iter_jsonl(path: Path):
    with open_text(path) as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)
