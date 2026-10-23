# -*- coding: utf-8 -*-
"""E10 雪花 ID 安全 JSON 解析（与 json_snowflake.js 对齐）。"""
from __future__ import annotations

import json
import re
from typing import Iterable, Optional, Union

SNOWFLAKE_MIN_DIGITS = 16

ID_FIELD_NAMES = (
    "id", "reportId", "sheetId", "pageId", "sourceId", "targetId", "navId",
    "appId", "appid", "groupId", "groupid", "objId", "designKey", "datasetId",
    "dataSetId", "permissionId", "sysMenuId", "remoteAppId", "creator", "formId",
    "objid", "reportid",
)


def quote_snowflake_literals(json_text: str) -> str:
    """仅对已知 ID 字段名的长整数加引号，避免破坏嵌套 JSON 字符串。"""
    out = str(json_text)
    for key in ID_FIELD_NAMES:
        pattern = rf'("{re.escape(key)}"\s*:\s*)(-?\d{{{SNOWFLAKE_MIN_DIGITS},}})(?=\s*[,}}\]])'
        out = re.sub(pattern, r'\1"\2"', out, flags=re.IGNORECASE)
    return out


def parse_json_snowflake_safe(json_text: Union[str, bytes]) -> dict:
    text = json_text.decode("utf-8") if isinstance(json_text, bytes) else str(json_text)
    return json.loads(quote_snowflake_literals(text))


def extract_id_from_raw(raw: str, keys: Iterable[str] = ("id", "reportId")) -> str:
    """从 raw 响应文本提取 ID（双保险，不依赖 parse 后的 number）。"""
    for key in keys:
        m = re.search(rf'"{re.escape(key)}"\s*:\s*"?(\d{{{SNOWFLAKE_MIN_DIGITS},}})"?', str(raw))
        if m:
            return m.group(1)
    return ""


def stringify_id(value) -> str:
    if value is None or value == "":
        return ""
    return str(value)
