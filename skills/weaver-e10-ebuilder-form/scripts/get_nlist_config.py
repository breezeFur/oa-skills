#!/usr/bin/env python3
"""Query and normalize one eBuilder NList view configuration."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ebuilder_http import (
    api_path,
    configure_utf8_output,
    resolve_api_prefix,
    resolve_origin,
    same_origin_headers,
)

BASIC_SETTING_KEYS = (
    "name",
    "type",
    "ebListId",
    "objId",
    "mode",
    "modeType",
    "pageMode",
    "pageSize",
    "detailPageSize",
    "title",
    "titleEnabled",
    "titleIcon",
    "footerEnabled",
    "hideTableHeader",
    "hideCheckbox",
    "operatColumnFixation",
    "enableSpreadTop",
    "isShowFollow",
    "readState",
    "batchAdd",
    "batchAddFields",
    "batchEdit",
    "batchEditFields",
    "batchEditValue",
    "setTop",
    "setTopType",
    "setTopRule",
    "enableGroup",
    "buttonConfig",
    "topOperatBtns",
    "bottomOperatBtns",
    "tableMergeMainData",
    "subFormMain",
    "filterWithMainId",
)

DISPLAY_COLUMN_KEYS = (
    "tableField",
    "listField",
    "logicField",
    "picField",
    "tableMergeFields",
    "personalFields",
    "excelDisabledFieldIds",
    "notTransformField",
    "cardLayout",
    "fieldUsage",
    "extendArea",
)

SORTING_KEYS = ("order", "refEbuilderDataset")
SEARCH_KEYS = ("searchConditions",)
STATISTICS_KEYS = ("listStatistics",)
CONDITION_KEYS = ("filter", "filterIsNull", "isFilterSub", "checkboxDisabledSet")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Return categorized configuration details for an eBuilder NList view."
    )
    parser.add_argument("list_id", help="NList view ID; preserved as a string")
    parser.add_argument(
        "--origin",
        help="eBuilder origin; required unless EBUILDER_ORIGIN is set",
    )
    parser.add_argument(
        "--api-prefix",
        help="API prefix; defaults to EBUILDER_API_PREFIX or /api/ebuilder",
    )
    parser.add_argument(
        "--terminal-type",
        default="PC",
        help="Page terminal type (default: %(default)s)",
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        help="Parse a local API response instead of making an HTTP request",
    )
    return parser.parse_args()


def fetch_payload(
    origin: str, api_prefix: str, list_id: str, terminal_type: str
) -> Any:
    origin = resolve_origin(origin)
    query = urllib.parse.urlencode(
        {"pageId": list_id, "terminalType": terminal_type}
    )
    url = (
        origin.rstrip("/")
        + api_path(api_prefix, "/form/viewdesigner/viewPageInfo")
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


def validate_payload(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise RuntimeError("接口响应根节点不是对象")
    code = payload.get("code")
    if code is not None and str(code) != "200":
        raise RuntimeError(f"接口业务码不是 200: {code}")
    if payload.get("status") is False:
        raise RuntimeError("接口返回 status=false")


def unwrap_page(payload: Any) -> Dict[str, Any]:
    current = payload
    for _ in range(5):
        if not isinstance(current, dict):
            break
        page = current.get("page")
        if isinstance(page, dict):
            return page
        next_value = current.get("data")
        if next_value is current:
            break
        current = next_value
    raise RuntimeError("响应中未找到 data.page")


def display_name(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("showName", "name", "value", "zh_CN", "zh-CN", "7"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate
        for candidate in value.values():
            if isinstance(candidate, str) and candidate.strip():
                return candidate
    return "" if value is None else str(value)


def parse_component_config(value: Any) -> Optional[Dict[str, Any]]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def select_primary_nlist_component(
    page: Dict[str, Any],
) -> Tuple[int, Dict[str, Any], Dict[str, Any]]:
    """Return the runtime NList component defined at data.page.comps[1]."""
    components = page.get("comps")
    if not isinstance(components, list) or len(components) <= 1:
        raise RuntimeError("响应缺少 data.page.comps[1]")
    component = components[1]
    if not isinstance(component, dict):
        raise RuntimeError("data.page.comps[1] 不是对象")
    config = parse_component_config(component.get("config"))
    if config is None:
        raise RuntimeError("data.page.comps[1].config 不是有效对象")
    return 1, component, config


def pick_present(config: Dict[str, Any], keys: Sequence[str]) -> Dict[str, Any]:
    return {key: config[key] for key in keys if key in config}


def categorize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    categories = {
        "basicSettings": pick_present(config, BASIC_SETTING_KEYS),
        "displayColumns": pick_present(config, DISPLAY_COLUMN_KEYS),
        "sorting": pick_present(config, SORTING_KEYS),
        "search": pick_present(config, SEARCH_KEYS),
        "statistics": pick_present(config, STATISTICS_KEYS),
        "conditions": pick_present(config, CONDITION_KEYS),
    }
    known_keys = set().union(
        BASIC_SETTING_KEYS,
        DISPLAY_COLUMN_KEYS,
        SORTING_KEYS,
        SEARCH_KEYS,
        STATISTICS_KEYS,
        CONDITION_KEYS,
    )
    categories["otherConfig"] = {
        key: value for key, value in config.items() if key not in known_keys
    }
    return categories


def normalize_payload(
    payload: Any, list_id: str, terminal_type: str, api_prefix: str
) -> Dict[str, Any]:
    validate_payload(payload)
    page = unwrap_page(payload)
    warnings: List[str] = []
    component_index, component, config = select_primary_nlist_component(page)
    resolved_list_id = config.get("ebListId")
    obj_id = config.get("objId")
    if resolved_list_id is None or not str(resolved_list_id).strip():
        raise RuntimeError("data.page.comps[1].config 缺少 ebListId")
    if obj_id is None or not str(obj_id).strip():
        raise RuntimeError("data.page.comps[1].config 缺少 objId")
    component_id = component.get("id")
    if component_id is None:
        component_id = component.get("compId")

    return {
        "hostPageId": str(list_id),
        "listId": str(resolved_list_id),
        "objId": str(obj_id),
        "apiPrefix": api_prefix,
        "terminalType": str(terminal_type),
        "pageName": display_name(page.get("name")),
        "componentId": "" if component_id is None else str(component_id),
        "componentIndex": component_index,
        "config": categorize_config(config),
        "warnings": warnings,
    }


def main() -> int:
    configure_utf8_output()
    args = parse_args()
    try:
        api_prefix = resolve_api_prefix(args.api_prefix)
        if args.input_json:
            payload = json.loads(args.input_json.read_text(encoding="utf-8-sig"))
        else:
            payload = fetch_payload(
                args.origin, api_prefix, args.list_id, args.terminal_type
            )
        output = normalize_payload(
            payload, str(args.list_id), args.terminal_type, api_prefix
        )
        json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
