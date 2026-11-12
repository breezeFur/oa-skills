#!/usr/bin/env python3
"""Query paginated rows from one traditional eBuilder List view."""

from __future__ import annotations

import argparse
import json
import math
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from get_table_config import (
    normalize_ids,
    request_json,
    string_value,
    unwrap_data,
)
from ebuilder_http import api_path, configure_utf8_output, resolve_api_prefix, resolve_origin


NULL_OPERATORS = {"isNull", "isNotNull"}
MAX_PAGE_SIZE = 200
MAX_ALL_PAGE_COUNT = 100


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query one page or all pages from an eBuilder table/List view."
    )
    parser.add_argument("table_id", help="Table view ID; preserved as a string")
    parser.add_argument(
        "--origin",
        help="eBuilder origin; required unless EBUILDER_ORIGIN is set",
    )
    parser.add_argument(
        "--api-prefix",
        help="API prefix; defaults to EBUILDER_API_PREFIX or /api/ebuilder",
    )
    parser.add_argument("--page-no", type=positive_int, default=1)
    parser.add_argument(
        "--page-size",
        type=page_size_int,
        help="Rows per page, maximum 200; defaults to the listInit pageSize",
    )
    parser.add_argument(
        "--all-pages",
        action="store_true",
        help="Query every main-record page from page 1 without deduplicating rows",
    )
    parser.add_argument(
        "--search-field-id",
        help="Build one common-search condition for this field ID",
    )
    parser.add_argument("--search-value", help="String value for the simple search")
    parser.add_argument(
        "--search-value-json",
        help="JSON value or @path for browse, multiselect, or structured search values",
    )
    parser.add_argument(
        "--search-operator",
        default="eq",
        help="Condition type such as eq, like, gt, between, isNull, or isNotNull",
    )
    parser.add_argument(
        "--search-param-json",
        help="Complete searchParamData JSON object, or @path",
    )
    parser.add_argument(
        "--sort-key",
        help="Column orderKey/dataIndex used for one explicit sort",
    )
    parser.add_argument(
        "--sort-direction",
        choices=("asc", "desc"),
        help="Sort direction used with --sort-key",
    )
    parser.add_argument(
        "--sort-json",
        help="Complete sortParams JSON array, or @path",
    )
    parser.add_argument(
        "--filter-condition-json",
        help="Complete filterCondition JSON object, or @path",
    )
    parser.add_argument(
        "--request-json",
        help="Advanced request-body overrides as a JSON object, or @path",
    )
    parser.add_argument(
        "--pass-id",
        help="passid override; defaults to the objId discovered by listInit",
    )
    parser.add_argument(
        "--cid",
        help="cid override; defaults to objId unless --pass-id is explicitly supplied",
    )
    parser.add_argument(
        "--terminal",
        default="PC",
        help="Runtime terminal value (default: %(default)s)",
    )
    return parser.parse_args()


def load_json_option(
    raw_value: Optional[str],
    *,
    default: Any,
    expected_type: Optional[type],
    option_name: str,
) -> Any:
    if raw_value is None:
        return default
    source = raw_value
    if raw_value.startswith("@"):
        source = Path(raw_value[1:]).read_text(encoding="utf-8-sig")
    try:
        value = json.loads(source)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{option_name} 不是有效 JSON: {exc}") from None
    if expected_type is not None and not isinstance(value, expected_type):
        raise RuntimeError(f"{option_name} 必须是 {expected_type.__name__}")
    return value


def configured_page_size(context: Dict[str, Any]) -> int:
    values = [context.get("pageSize")]
    base_info = context.get("listBaseInfo")
    if isinstance(base_info, dict):
        values.append(base_info.get("pageSize"))
    for value in values:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            return min(parsed, MAX_PAGE_SIZE)
    return 10


def build_simple_search(args: argparse.Namespace) -> Dict[str, Any]:
    field_id = string_value(args.search_field_id)
    operator = string_value(args.search_operator)
    has_string_value = args.search_value is not None
    has_json_value = args.search_value_json is not None
    if has_string_value and has_json_value:
        raise RuntimeError("--search-value 与 --search-value-json 不能同时使用")
    if not field_id:
        if has_string_value or has_json_value:
            raise RuntimeError("搜索值必须与 --search-field-id 一起提供")
        return {}
    if operator not in NULL_OPERATORS and not (has_string_value or has_json_value):
        raise RuntimeError("非空值判断必须提供 --search-value 或 --search-value-json")
    if operator in NULL_OPERATORS and (has_string_value or has_json_value):
        raise RuntimeError("isNull/isNotNull 不需要搜索值")

    field_key = f"field_{field_id}"
    condition: Dict[str, Any] = {f"{field_key}_condition_type": operator}
    if operator not in NULL_OPERATORS:
        condition[field_key] = (
            args.search_value
            if has_string_value
            else load_json_option(
                args.search_value_json,
                default=None,
                expected_type=None,
                option_name="--search-value-json",
            )
        )
    return {"commonSearchFields": {field_key: [condition]}}


def build_query_params(
    obj_id: str, pass_id_override: Optional[str], cid_override: Optional[str]
) -> Dict[str, str]:
    pass_id = string_value(pass_id_override) or obj_id
    query = {"passid": pass_id}
    if cid_override is not None:
        query["cid"] = string_value(cid_override)
    elif pass_id_override is None:
        query["cid"] = obj_id
    return query


def validate_options(args: argparse.Namespace) -> None:
    if args.all_pages and args.page_no != 1:
        raise RuntimeError("--all-pages 必须从 --page-no 1 开始")
    if args.search_param_json and (
        args.search_field_id
        or args.search_value is not None
        or args.search_value_json is not None
    ):
        raise RuntimeError("--search-param-json 与简化搜索参数不能同时使用")
    if bool(args.sort_key) != bool(args.sort_direction):
        raise RuntimeError("--sort-key 与 --sort-direction 必须同时提供")
    if args.sort_json and args.sort_key:
        raise RuntimeError("--sort-json 与简化排序参数不能同时使用")


def extract_table_data(payload: Any, operation: str) -> Dict[str, Any]:
    data = unwrap_data(payload, operation)
    if not isinstance(data, dict):
        raise RuntimeError(f"{operation} 响应中的 data 不是对象")
    display_data = data.get("displayData")
    if not isinstance(display_data, (list, dict)):
        raise RuntimeError(f"{operation} 响应中的 data.displayData 不是数组或对象")
    return data


def extract_total(payload: Any) -> int:
    data = unwrap_data(payload, "表格总数")
    if not isinstance(data, dict):
        raise RuntimeError("表格总数响应中的 data 不是对象")
    try:
        return int(data.get("total"))
    except (TypeError, ValueError):
        raise RuntimeError("表格总数响应中的 data.total 不是整数") from None


def stable_id(row: Dict[str, Any]) -> Optional[str]:
    for key in ("id", "form_data_id", "ebrecord_rowkey", "rowKey"):
        value = row.get(key)
        if value is not None:
            return str(value)
    return None


def page_result(page_no: int, data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Any]]:
    display_data = data.get("displayData")
    if isinstance(display_data, list):
        rows = list(display_data)
        return {
            "pageNo": page_no,
            "returnedRowCount": len(rows),
            "rows": rows,
        }, rows
    return {
        "pageNo": page_no,
        "returnedRowCount": 0,
        "groupedEntryCount": len(display_data),
        "groupedDisplayData": display_data,
        "rows": [],
    }, []


def query_rows(args: argparse.Namespace) -> Dict[str, Any]:
    validate_options(args)
    origin = resolve_origin(args.origin)
    api_prefix = resolve_api_prefix(args.api_prefix)
    table_id = str(args.table_id)
    init_payload = request_json(
        origin,
        api_path(api_prefix, "/form/list/listInit"),
        body={"listId": table_id},
    )
    context = unwrap_data(init_payload, "表格上下文")
    if not isinstance(context, dict):
        raise RuntimeError("表格上下文 data 不是对象")

    obj_id = string_value(context.get("objid") or context.get("objId"))
    app_id = string_value(context.get("appId"))
    if not obj_id:
        raise RuntimeError("表格上下文未返回 objId")
    page_size = args.page_size or configured_page_size(context)
    tableuid = uuid.uuid4().hex
    query = build_query_params(obj_id, args.pass_id, args.cid)

    request_overrides = load_json_option(
        args.request_json,
        default={},
        expected_type=dict,
        option_name="--request-json",
    )
    payload: Dict[str, Any] = {
        "requiredMatch": 1,
        "listId": table_id,
        "searchParamData": {
            "searchType": "2",
            "type": "and",
            "groupFields": {},
        },
        "isFollow": 0,
        "isShareToMe": 0,
        "filterCondition": {},
        "terminal": args.terminal,
    }
    payload.update(request_overrides)

    if args.search_param_json:
        payload["searchParamData"] = load_json_option(
            args.search_param_json,
            default={},
            expected_type=dict,
            option_name="--search-param-json",
        )
    else:
        simple_search = build_simple_search(args)
        if simple_search:
            search_data = payload.get("searchParamData")
            if not isinstance(search_data, dict):
                raise RuntimeError("searchParamData 必须是对象")
            search_data.update(simple_search)

    if args.sort_json:
        payload["sortParams"] = load_json_option(
            args.sort_json,
            default=[],
            expected_type=list,
            option_name="--sort-json",
        )
    elif args.sort_key:
        payload["sortParams"] = [
            {"orderKey": args.sort_key, "orderType": args.sort_direction}
        ]

    if args.filter_condition_json:
        payload["filterCondition"] = load_json_option(
            args.filter_condition_json,
            default={},
            expected_type=dict,
            option_name="--filter-condition-json",
        )

    first_page_no = 1 if args.all_pages else args.page_no
    payload.update(
        {
            "current": first_page_no,
            "pageSize": page_size,
            "listId": table_id,
            "requiredMatch": 1,
            "tableuid": tableuid,
        }
    )
    first_payload = request_json(
        origin,
        api_path(api_prefix, "/form/list/getListDatas"),
        query=query,
        body=payload,
    )
    first_data = extract_table_data(first_payload, "表格分页数据")
    count_payload = request_json(
        origin,
        api_path(api_prefix, "/form/list/getListDataCount"),
        query=query,
        body=payload,
    )
    total = extract_total(count_payload)
    main_page_count = math.ceil(total / page_size) if total > 0 else 0
    if args.all_pages and main_page_count >= MAX_ALL_PAGE_COUNT:
        raise RuntimeError(
            f"预计需要查询 {main_page_count} 页，达到或超过 "
            f"{MAX_ALL_PAGE_COUNT} 页批量查询限制；请增加筛选条件并缩小结果范围"
        )

    warnings: List[str] = []
    first_page, first_rows = page_result(first_page_no, first_data)
    if "groupedDisplayData" in first_page:
        warnings.append("该表格为分组返回，已原样保留 pages[].groupedDisplayData")
    pages = [first_page]
    rows = list(first_rows)
    if args.all_pages:
        for page_no in range(2, main_page_count + 1):
            payload["current"] = page_no
            page_payload = request_json(
                origin,
                api_path(api_prefix, "/form/list/getListDatas"),
                query=query,
                body=payload,
            )
            page_data = extract_table_data(page_payload, f"表格第 {page_no} 页数据")
            current_page, current_rows = page_result(page_no, page_data)
            pages.append(current_page)
            rows.extend(current_rows)

    distinct_ids = {
        value
        for row in rows
        if isinstance(row, dict) and (value := stable_id(row)) is not None
    }
    columns = first_data.get("columns")
    if not isinstance(columns, list):
        columns = []
    result = {
        "tableId": table_id,
        "apiPrefix": api_prefix,
        "tableName": string_value(context.get("name")),
        "context": {
            "appId": app_id,
            "objId": obj_id,
            "tableType": string_value(context.get("tableType")),
            "viewType": string_value(context.get("viewType", "list")),
            "terminal": string_value(args.terminal),
            "tableuid": tableuid,
        },
        "pagination": {
            "requestedPageNo": first_page_no,
            "pageSize": page_size,
            "allPages": bool(args.all_pages),
            "mainRecordTotal": total,
            "mainPageCount": main_page_count,
            "queriedPageCount": len(pages),
            "returnedRowCount": sum(page["returnedRowCount"] for page in pages),
            "groupedEntryCount": sum(
                page.get("groupedEntryCount", 0) for page in pages
            ),
            "distinctStableIdCount": len(distinct_ids),
        },
        "columns": columns,
        "searchParamData": payload.get("searchParamData", {}),
        "sortParams": payload.get("sortParams", []),
        "filterCondition": payload.get("filterCondition", {}),
        "pages": pages,
        "rows": rows,
        "warnings": warnings,
    }
    return normalize_ids(result)


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
