#!/usr/bin/env python3
"""Query and normalize eBuilder list/layout metadata for one form ObjId."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from ebuilder_http import (
    api_path,
    configure_utf8_output,
    resolve_api_prefix,
    resolve_origin,
    same_origin_headers,
)

LIST_TYPES = {
    "list": ("表格", "list"),
    "nlist": ("数据列表", "viewport"),
}
LAYOUT_TYPES = {
    "add": ("新建", "1"),
    "edit": ("编辑", "2"),
    "view": ("查询", "0"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Return lists and layouts belonging to an eBuilder form."
    )
    parser.add_argument("obj_id", help="Form ObjId; preserved as a string")
    parser.add_argument(
        "--origin",
        help="eBuilder origin; required unless EBUILDER_ORIGIN is set",
    )
    parser.add_argument(
        "--api-prefix",
        help="API prefix; defaults to EBUILDER_API_PREFIX or /api/ebuilder",
    )
    parser.add_argument(
        "--data-id",
        help="Record ID used to make query/edit layout URLs concrete",
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        help="Parse a local API response instead of making an HTTP request",
    )
    return parser.parse_args()


def fetch_payload(origin: str, api_prefix: str, obj_id: str) -> Any:
    origin = resolve_origin(origin)
    safe_obj_id = urllib.parse.quote(obj_id, safe="")
    query = urllib.parse.urlencode({"objId": obj_id})
    url = (
        origin.rstrip("/")
        + api_path(api_prefix, "/form/viewlist/getViewlist/")
        + safe_obj_id
        + "?"
        + query
    )
    request = urllib.request.Request(
        url,
        headers=same_origin_headers(origin),
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8-sig"))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise RuntimeError(
                f"接口返回 HTTP {exc.code}，请更新 Cookie/ETEAMSID"
            ) from None
        raise RuntimeError(f"接口返回 HTTP {exc.code}") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"接口请求失败: {exc.reason}") from None
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"接口没有返回有效 JSON: {exc}") from None


def unwrap_data(payload: Any) -> Dict[str, Any]:
    current = payload
    for _ in range(4):
        if not isinstance(current, dict):
            break
        if "tableView" in current or "formView" in current:
            return current
        next_value = current.get("data")
        if next_value is current:
            break
        current = next_value
    raise RuntimeError("响应中未找到 data.tableView 或 data.formView")


def as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def display_name(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("showName", "name", "zh_CN", "zh-CN", "7"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate
        for candidate in value.values():
            if isinstance(candidate, str) and candidate.strip():
                return candidate
    if isinstance(value, list):
        for candidate in value:
            name = display_name(candidate)
            if name:
                return name
    return "" if value is None else str(value)


def normalize_lists(root: Dict[str, Any], warnings: List[str]) -> List[Dict[str, Any]]:
    table_view = root.get("tableView") or {}
    details = as_list(table_view.get("detail") if isinstance(table_view, dict) else None)
    result: List[Dict[str, Any]] = []
    for item in details:
        if not isinstance(item, dict):
            warnings.append("忽略了一条非对象格式的列表记录")
            continue
        item_id = "" if item.get("id") is None else str(item.get("id"))
        raw_type = "" if item.get("viewType") is None else str(item.get("viewType"))
        mapping = LIST_TYPES.get(raw_type.lower())
        if not mapping:
            continue
        type_name, route = mapping
        url = f"/sp/ebdfpage/{route}/{item_id}" if item_id else None
        result.append(
            {
                "id": item_id,
                "name": display_name(item.get("name")),
                "type": type_name,
                "viewType": raw_type,
                "url": url,
            }
        )
    return result


def iter_default_types(value: Any) -> Iterable[str]:
    values = as_list(value)
    for raw in values:
        text = "" if raw is None else str(raw)
        for part in text.replace("，", ",").split(","):
            if part.strip():
                yield part.strip().lower()


def layout_url(obj_id: str, card_type: str, data_id: Optional[str]) -> str:
    record_id = "0" if card_type == "1" else (data_id or "{dataId}")
    return f"/sp/ebdfpage/card/{card_type}/{obj_id}/{record_id}"


def normalize_layouts(
    root: Dict[str, Any], obj_id: str, data_id: Optional[str], warnings: List[str]
) -> List[Dict[str, Any]]:
    form_view = root.get("formView") or {}
    detail = form_view.get("detail") if isinstance(form_view, dict) else {}
    details = as_list(detail.get("detailList") if isinstance(detail, dict) else None)
    grouped: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []

    for item in details:
        if not isinstance(item, dict):
            warnings.append("忽略了一条非对象格式的布局记录")
            continue
        item_id = "" if item.get("id") is None else str(item.get("id"))
        name = display_name(item.get("name"))
        key = item_id or f"__missing_id_{len(order)}"
        if key not in grouped:
            grouped[key] = {"id": item_id, "name": name, "types": [], "urls": {}}
            order.append(key)
        elif not grouped[key]["name"] and name:
            grouped[key]["name"] = name

        default_types = list(iter_default_types(item.get("defaultType")))
        expanded = ["add", "edit", "view"] if "all" in default_types else default_types
        if not expanded:
            warnings.append(f"布局 {item_id or '(无 id)'} 缺少 defaultType")
        for raw_type in expanded:
            mapping = LAYOUT_TYPES.get(raw_type)
            if not mapping:
                warnings.append(
                    f"布局 {item_id or '(无 id)'} 使用未知 defaultType: {raw_type}"
                )
                continue
            type_name, card_type = mapping
            if type_name not in grouped[key]["types"]:
                grouped[key]["types"].append(type_name)
                grouped[key]["urls"][type_name] = layout_url(obj_id, card_type, data_id)

    return [grouped[key] for key in order]


def main() -> int:
    configure_utf8_output()
    args = parse_args()
    try:
        api_prefix = resolve_api_prefix(args.api_prefix)
        if args.input_json:
            payload = json.loads(args.input_json.read_text(encoding="utf-8-sig"))
        else:
            payload = fetch_payload(args.origin, api_prefix, args.obj_id)
        root = unwrap_data(payload)
        warnings: List[str] = []
        output = {
            "objId": str(args.obj_id),
            "apiPrefix": api_prefix,
            "lists": normalize_lists(root, warnings),
            "layouts": normalize_layouts(root, str(args.obj_id), args.data_id, warnings),
            "warnings": warnings,
        }
        json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
