#!/usr/bin/env python3
"""Query paginated rows from one eBuilder NList view."""

from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from get_nlist_config import (
    display_name,
    select_primary_nlist_component,
    unwrap_page,
    validate_payload,
)
from ebuilder_http import (
    api_path,
    configure_utf8_output,
    resolve_api_prefix,
    resolve_origin,
    same_origin_headers,
)


DEFAULT_PLUGIN_PACKAGE_ID = "933846626099339271"
DEFAULT_PAGE_FILTER = {"filter": {}, "filterIsNull": True, "esbFilter": []}
DEFAULT_CUSTOM_CONFIG = {"superiorField": {"enable": False}}
MAX_PAGE_SIZE = 200
MAX_ALL_PAGE_COUNT = 100


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query one page or all pages from an eBuilder NList view."
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
        "--host-page-id",
        help="Host page ID when the NList is embedded; defaults to list_id",
    )
    parser.add_argument(
        "--comp-id",
        help="Component ID override when the host page contains ambiguous NLists",
    )
    parser.add_argument("--page-no", type=positive_int, default=1)
    parser.add_argument(
        "--page-size",
        type=page_size_int,
        help="Rows per page, maximum 200; defaults to the NList pageSize configuration",
    )
    parser.add_argument(
        "--all-pages",
        action="store_true",
        help="Query every main-record page from page 1 without deduplicating rows",
    )
    parser.add_argument(
        "--filter-json",
        help="Complete filter JSON array, or @path to a UTF-8 JSON file",
    )
    parser.add_argument(
        "--field-filter-json",
        default="{}",
        help="fieldFilter JSON object, or @path (default: {})",
    )
    parser.add_argument(
        "--page-filter-json",
        help="pageFilter JSON object, or @path",
    )
    parser.add_argument(
        "--custom-config-json",
        help="customConfig JSON object, or @path; defaults to superiorField.enable=false",
    )
    parser.add_argument(
        "--search-field-id",
        help="Build a common-search filter for this configured field ID",
    )
    parser.add_argument(
        "--search-value",
        help="Value used with --search-field-id",
    )
    parser.add_argument(
        "--search-operator",
        default="eq",
        help="Search funcType such as eq, like, gt, or between (default: %(default)s)",
    )
    parser.add_argument(
        "--terminal-type",
        default="PC",
        help="Page terminal type (default: %(default)s)",
    )
    return parser.parse_args()


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("必须是大于等于 1 的整数")
    return parsed


def page_size_int(value: str) -> int:
    parsed = positive_int(value)
    if parsed > MAX_PAGE_SIZE:
        raise argparse.ArgumentTypeError(f"每页数量不能超过 {MAX_PAGE_SIZE}")
    return parsed


def compact_json(value: Any, *, ascii_only: bool = False) -> str:
    return json.dumps(
        value,
        ensure_ascii=ascii_only,
        separators=(",", ":"),
    )


def load_json_option(
    raw_value: Optional[str],
    *,
    default: Any,
    expected_type: type,
    option_name: str,
) -> Any:
    if raw_value is None:
        return default
    source = raw_value
    if raw_value.startswith("@"):
        path = Path(raw_value[1:])
        source = path.read_text(encoding="utf-8-sig")
    try:
        value = json.loads(source)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{option_name} 不是有效 JSON: {exc}") from None
    if not isinstance(value, expected_type):
        raise RuntimeError(f"{option_name} 必须是 {expected_type.__name__}")
    return value


def read_json_response(request: urllib.request.Request) -> Any:
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


def fetch_page_info(
    origin: str, api_prefix: str, host_page_id: str, terminal_type: str
) -> Any:
    query = urllib.parse.urlencode(
        {
            "pageId": host_page_id,
            "terminalType": terminal_type,
            "entranceType": "RUN",
            "runType": "",
        }
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
    return read_json_response(request)


def post_form(origin: str, path: str, fields: Dict[str, Any], query: str = "") -> Any:
    encoded = urllib.parse.urlencode(
        {key: "" if value is None else str(value) for key, value in fields.items()}
    ).encode("utf-8")
    url = origin.rstrip("/") + path + query
    request = urllib.request.Request(
        url,
        data=encoded,
        headers=same_origin_headers(
            origin,
            "application/x-www-form-urlencoded; charset=UTF-8",
        ),
        method="POST",
    )
    return read_json_response(request)


def component_id(component: Dict[str, Any]) -> str:
    value = component.get("id")
    if value is None:
        value = component.get("compId")
    return "" if value is None else str(value)


def select_component(
    page: Dict[str, Any],
    list_id: str,
    requested_comp_id: Optional[str],
    warnings: List[str],
) -> Tuple[int, Dict[str, Any], Dict[str, Any]]:
    selected = select_primary_nlist_component(page)
    if requested_comp_id:
        actual_comp_id = component_id(selected[1])
        if actual_comp_id != requested_comp_id:
            raise RuntimeError("--comp-id 与 data.page.comps[1] 的组件 ID 不一致")
    configured_id = selected[2].get("ebListId")
    if configured_id is None or not str(configured_id).strip():
        raise RuntimeError("data.page.comps[1].config 缺少 ebListId")
    if str(configured_id) != list_id:
        raise RuntimeError("list_id 必须使用 data.page.comps[1].config.ebListId")
    return selected


def encode_custom_config(value: Dict[str, Any]) -> str:
    source = compact_json(value, ascii_only=True)
    if not source:
        return ""

    dictionary: Dict[str, int] = {}
    output: List[int] = []
    next_code = 1 << 16
    current = source[0]

    def code_for(token: str) -> int:
        if token in dictionary:
            return dictionary[token]
        if len(token) != 1:
            raise RuntimeError(f"无法编码 customConfig 片段: {token!r}")
        dictionary[token] = ord(token)
        return dictionary[token]

    for char in source[1:]:
        combined = current + char
        if combined in dictionary:
            current = combined
            continue
        output.append(code_for(current))
        dictionary[combined] = next_code
        next_code += 1
        current = char
    output.append(code_for(current))
    return ",".join(str(code) for code in output)


def base_filter(comp_id: str) -> Dict[str, Any]:
    return {
        "conditionComId": f"{comp_id}_filter_EXCLUDECACHE",
        "conditionType": "and",
        "dataType": "classification",
        "id": uuid.uuid4().hex,
        "useConfig": True,
    }


def iter_search_fields(config: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    search = config.get("searchConditions")
    if not isinstance(search, dict):
        return
    for key in ("commonFilters", "quickFilters", "groupFilters"):
        values = search.get(key)
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, dict):
                yield value


def search_field_id(field: Dict[str, Any]) -> str:
    for key in ("fieldId", "id"):
        value = field.get(key)
        if value is not None:
            return str(value)
    return ""


def build_search_filter(
    config: Dict[str, Any],
    comp_id: str,
    field_id: str,
    operator: str,
    value: str,
) -> Dict[str, Any]:
    matches = [
        field
        for field in iter_search_fields(config)
        if search_field_id(field) == field_id
    ]
    if len(matches) != 1:
        raise RuntimeError("--search-field-id 未能唯一匹配已配置的搜索字段")
    field = matches[0]
    dataset = config.get("dataset")
    if not isinstance(dataset, dict):
        raise RuntimeError("NList 配置缺少 dataset，无法构造搜索条件")

    field_name = field.get("fieldName") or field.get("name")
    field_obj_id = field.get("objId") or dataset.get("id")
    field_type = field.get("fieldType") or field.get("type")
    field_comp_type = field.get("compType") or field.get("componentKey")
    if not all((field_name, field_obj_id, field_type, field_comp_type)):
        raise RuntimeError("搜索字段元数据不完整，请改用 --filter-json 传入完整条件")

    return {
        "conditionType": "and",
        "dataType": "field",
        "id": uuid.uuid4().hex,
        "conditionComId": f"{comp_id}_advance_EXCLUDECACHE",
        "filterFields": [
            {
                "compId": comp_id,
                "compType": field_comp_type,
                "dataset": dataset,
                "fieldName": str(field_name),
                "id": field_id,
                "objId": str(field_obj_id),
                "type": str(field_type),
            }
        ],
        "funcType": operator,
        "value": value,
    }


def validate_runtime_payload(payload: Any, operation: str) -> Dict[str, Any]:
    validate_payload(payload)
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise RuntimeError(f"{operation} 响应缺少 data 对象")
    return data


def extract_rows(payload: Any) -> List[Dict[str, Any]]:
    data = validate_runtime_payload(payload, "getData")
    rows = data.get("list")
    if not isinstance(rows, list):
        raise RuntimeError("getData 响应中的 data.list 不是数组")
    return [row for row in rows if isinstance(row, dict)]


def extract_total(payload: Any) -> int:
    data = validate_runtime_payload(payload, "getCount")
    value = data.get("total")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise RuntimeError("getCount 响应中的 data.total 不是整数") from None


def stable_id(row: Dict[str, Any]) -> Optional[str]:
    value = row.get("id")
    if value is None:
        value = row.get("form_data_id")
    return None if value is None else str(value)


def query_rows(args: argparse.Namespace) -> Dict[str, Any]:
    origin = resolve_origin(args.origin)
    api_prefix = resolve_api_prefix(args.api_prefix)
    if args.all_pages and args.page_no != 1:
        raise RuntimeError("--all-pages 必须从 --page-no 1 开始")
    if bool(args.search_field_id) != (args.search_value is not None):
        raise RuntimeError("--search-field-id 与 --search-value 必须同时提供")
    if args.filter_json and args.search_field_id:
        raise RuntimeError("--filter-json 与简化搜索参数不能同时使用")

    list_id = str(args.list_id)
    host_page_id = str(args.host_page_id or list_id)
    page_info = fetch_page_info(
        origin, api_prefix, host_page_id, args.terminal_type
    )
    validate_payload(page_info)
    page = unwrap_page(page_info)
    warnings: List[str] = []
    component_index, component, config = select_component(
        page, list_id, args.comp_id, warnings
    )

    comp_id = component_id(component)
    page_app_id = page.get("appId")
    form_obj_id = config.get("objId")
    plugin_package_id = (
        component.get("refPluginPackageId")
        or config.get("refPluginPackageId")
        or DEFAULT_PLUGIN_PACKAGE_ID
    )
    if not comp_id or page_app_id is None or form_obj_id is None:
        raise RuntimeError(
            "页面配置缺少 compId、pageAppId 或 data.page.comps[1].config.objId"
        )

    configured_page_size = config.get("pageSize")
    try:
        default_page_size = int(configured_page_size)
    except (TypeError, ValueError):
        default_page_size = 10
    page_size = args.page_size or min(MAX_PAGE_SIZE, max(1, default_page_size))

    field_filter = load_json_option(
        args.field_filter_json,
        default={},
        expected_type=dict,
        option_name="--field-filter-json",
    )
    page_filter = load_json_option(
        args.page_filter_json,
        default=DEFAULT_PAGE_FILTER,
        expected_type=dict,
        option_name="--page-filter-json",
    )
    custom_config = load_json_option(
        args.custom_config_json,
        default=DEFAULT_CUSTOM_CONFIG,
        expected_type=dict,
        option_name="--custom-config-json",
    )
    if args.filter_json:
        filters = load_json_option(
            args.filter_json,
            default=[],
            expected_type=list,
            option_name="--filter-json",
        )
    else:
        filters = [base_filter(comp_id)]
        if args.search_field_id:
            filters.append(
                build_search_filter(
                    config,
                    comp_id,
                    str(args.search_field_id),
                    str(args.search_operator),
                    str(args.search_value),
                )
            )

    tableuid = uuid.uuid4().hex
    base_form = {
        "pageAppId": str(page_app_id),
        "pageId": host_page_id,
        "compId": comp_id,
        "pageSize": page_size,
        "tableuid": tableuid,
        "filter": compact_json(filters),
        "fieldFilter": compact_json(field_filter),
        "pageFilter": compact_json(page_filter),
        "refPluginPackageId": str(plugin_package_id),
        "customConfig": encode_custom_config(custom_config),
    }

    first_page_no = 1 if args.all_pages else args.page_no
    first_payload = post_form(
        origin,
        api_path(api_prefix, "/form/eblist/getData"),
        {**base_form, "pageNo": first_page_no},
    )
    first_rows = extract_rows(first_payload)
    count_payload = post_form(
        origin,
        api_path(api_prefix, "/form/eblist/getCount"),
        {
            "tableuid": tableuid,
            "pageId": host_page_id,
            "compId": comp_id,
            "refPluginPackageId": str(plugin_package_id),
        },
        query="?" + urllib.parse.urlencode({"passid": str(form_obj_id)}),
    )
    total = extract_total(count_payload)
    main_page_count = math.ceil(total / page_size) if total > 0 else 0
    if args.all_pages and main_page_count >= MAX_ALL_PAGE_COUNT:
        raise RuntimeError(
            f"预计需要查询 {main_page_count} 页，达到或超过 "
            f"{MAX_ALL_PAGE_COUNT} 页批量查询限制；请增加筛选条件并缩小结果范围"
        )

    pages: List[Dict[str, Any]] = [
        {"pageNo": first_page_no, "returnedRowCount": len(first_rows), "rows": first_rows}
    ]
    if args.all_pages:
        for page_no in range(2, main_page_count + 1):
            payload = post_form(
                origin,
                api_path(api_prefix, "/form/eblist/getData"),
                {**base_form, "pageNo": page_no},
            )
            rows = extract_rows(payload)
            pages.append(
                {"pageNo": page_no, "returnedRowCount": len(rows), "rows": rows}
            )

    rows = [row for page_result in pages for row in page_result["rows"]]
    distinct_ids = {value for row in rows if (value := stable_id(row)) is not None}
    return {
        "listId": list_id,
        "apiPrefix": api_prefix,
        "pageName": display_name(page.get("name")),
        "context": {
            "hostPageId": host_page_id,
            "pageAppId": str(page_app_id),
            "formObjId": str(form_obj_id),
            "componentId": comp_id,
            "componentIndex": component_index,
            "refPluginPackageId": str(plugin_package_id),
            "terminalType": str(args.terminal_type),
            "tableuid": tableuid,
        },
        "pagination": {
            "requestedPageNo": first_page_no,
            "pageSize": page_size,
            "allPages": bool(args.all_pages),
            "mainRecordTotal": total,
            "mainPageCount": main_page_count,
            "queriedPageCount": len(pages),
            "returnedRowCount": len(rows),
            "distinctStableIdCount": len(distinct_ids),
        },
        "filters": filters,
        "pages": pages,
        "rows": rows,
        "warnings": warnings,
    }


def main() -> int:
    configure_utf8_output()
    args = parse_args()
    try:
        output = query_rows(args)
        json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    except (OSError, RuntimeError, json.JSONDecodeError, ValueError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
