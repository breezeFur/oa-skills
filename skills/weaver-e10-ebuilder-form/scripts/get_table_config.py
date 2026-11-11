#!/usr/bin/env python3
"""Query and normalize one eBuilder table-view configuration."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from ebuilder_http import (
    api_path,
    configure_utf8_output,
    resolve_api_prefix,
    resolve_origin,
    same_origin_headers,
)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Return categorized configuration details for an eBuilder table view."
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
    parser.add_argument(
        "--client-type",
        default="PC",
        help="Client type used for display columns (default: %(default)s)",
    )
    parser.add_argument(
        "--is-virtual-form",
        choices=("true", "false"),
        default="false",
        help="Whether the table belongs to a virtual form (default: %(default)s)",
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        help="Normalize a saved aggregate fixture instead of making HTTP requests",
    )
    return parser.parse_args()


def request_json(
    origin: str,
    path: str,
    *,
    query: Optional[Mapping[str, Any]] = None,
    body: Optional[Mapping[str, Any]] = None,
) -> Any:
    origin = resolve_origin(origin)
    url = origin.rstrip("/") + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = same_origin_headers(
        origin,
        "application/json" if data is not None else None,
    )
    request = urllib.request.Request(
        url,
        headers=headers,
        data=data,
        method="POST" if data is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8-sig"))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise RuntimeError(
                f"接口返回 HTTP {exc.code}，请更新 Cookie/ETEAMSID"
            ) from None
        raise RuntimeError(f"接口返回 HTTP {exc.code}: {path}") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"接口请求失败: {exc.reason}") from None
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"接口没有返回有效 JSON: {exc}") from None


def validate_payload(payload: Any, label: str) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} 响应根节点不是对象")
    code = payload.get("code")
    if code is not None and str(code) != "200":
        raise RuntimeError(f"{label} 业务码不是 200: {code}")
    if payload.get("status") is False:
        raise RuntimeError(f"{label} 返回 status=false")
    return payload


def unwrap_data(payload: Any, label: str, *, allow_missing: bool = False) -> Any:
    response = validate_payload(payload, label)
    if "data" not in response:
        if allow_missing:
            return None
        raise RuntimeError(f"{label} 响应中缺少 data")
    return response["data"]


def string_value(value: Any) -> str:
    return "" if value is None else str(value)


def is_id_key(key: str) -> bool:
    normalized = key.lower()
    return normalized == "id" or normalized.endswith("id") or normalized.endswith("ids")


def normalize_ids(value: Any, parent_key: str = "") -> Any:
    """Preserve all eBuilder identifiers as strings without changing ordinary numbers."""
    if isinstance(value, dict):
        return {str(key): normalize_ids(item, str(key)) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_ids(item, parent_key) for item in value]
    if is_id_key(parent_key) and value is not None and not isinstance(value, bool):
        return str(value)
    return value


def parse_root_data(value: Any) -> Any:
    if not isinstance(value, str) or not value.strip():
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def build_conditions(condition_id: str, payload: Any) -> Dict[str, Any]:
    data = unwrap_data(payload, "条件", allow_missing=True) if payload else None
    root_data = None
    if isinstance(data, dict):
        root_data = data.get("rootdata", data.get("rootData"))
    elif isinstance(data, str):
        root_data = data
    parsed_root = parse_root_data(root_data)
    configured = parsed_root not in (None, "", {}, [])
    return {
        "conditionId": condition_id,
        "configured": configured,
        "rootData": parsed_root if configured else {},
        "raw": data if data is not None else {},
    }


def fetch_live_bundle(
    origin: str,
    api_prefix: str,
    table_id: str,
    client_type: str,
    is_virtual_form: str,
) -> Dict[str, Any]:
    context_payload = request_json(
        origin,
        api_path(api_prefix, "/form/list/listInit"),
        body={"listId": table_id},
    )
    context = unwrap_data(context_payload, "表格上下文")
    if not isinstance(context, dict):
        raise RuntimeError("表格上下文 data 不是对象")

    app_id = string_value(context.get("appId"))
    obj_id = string_value(context.get("objId", context.get("objid")))
    if not app_id or not obj_id:
        raise RuntimeError("表格上下文未返回 appId 或 objId")

    common = {"apid": app_id, "tpaid": table_id, "objId": obj_id}
    virtual_query = "true" if is_virtual_form == "true" else "false"
    condition_id = string_value(context.get("conditionId"))

    bundle: Dict[str, Any] = {
        "context": context_payload,
        "basicSettings": request_json(
            origin,
            api_path(api_prefix, f"/form/list/getBaseInfo/{table_id}"),
            query=common,
        ),
        "displayColumns": request_json(
            origin,
            api_path(api_prefix, f"/form/list/getListFields/{table_id}"),
            query={
                **common,
                "isVirtualForm": virtual_query,
                "clientType": client_type,
            },
        ),
        "sorting": request_json(
            origin,
            api_path(api_prefix, "/form/viewlist/getViewOrder"),
            query={
                **common,
                "viewType": "tableView",
                "viewId": table_id,
                "isVirtualForm": virtual_query,
            },
        ),
        "search": request_json(
            origin,
            api_path(api_prefix, f"/form/listFilter/getSearchFilters/{table_id}"),
            query={
                **common,
                "isVirtualForm": virtual_query,
                "viewType": "tableView",
            },
        ),
        "statistics": request_json(
            origin,
            api_path(
                api_prefix,
                f"/form/listStatistics/getStatisticsList/{table_id}",
            ),
            query={
                **common,
                "isVirtualForm": virtual_query,
            },
        ),
    }
    if condition_id and condition_id != "0":
        bundle["conditions"] = request_json(
            origin,
            api_path(api_prefix, "/form/plugin/conditionEditor/getById"),
            query={
                "apid": app_id,
                "id": condition_id,
                "type": "search",
                "objId": obj_id,
            },
        )
    else:
        bundle["conditions"] = None
    return bundle


def normalize_bundle(
    bundle: Any, table_id: str, client_type: str, api_prefix: str
) -> Dict[str, Any]:
    if not isinstance(bundle, dict):
        raise RuntimeError("聚合输入根节点不是对象")
    context = unwrap_data(bundle.get("context"), "表格上下文")
    if not isinstance(context, dict):
        raise RuntimeError("表格上下文 data 不是对象")

    context_table_id = string_value(context.get("listId", context.get("id")))
    if context_table_id and context_table_id != table_id:
        raise RuntimeError(
            f"上下文中的表格 ID {context_table_id} 与请求的 {table_id} 不一致"
        )

    app_id = string_value(context.get("appId"))
    obj_id = string_value(context.get("objId", context.get("objid")))
    condition_id = string_value(context.get("conditionId"))
    config = {
        "basicSettings": unwrap_data(bundle.get("basicSettings"), "基础设置"),
        "displayColumns": unwrap_data(bundle.get("displayColumns"), "显示列"),
        "sorting": unwrap_data(bundle.get("sorting"), "排序"),
        "search": unwrap_data(bundle.get("search"), "搜索"),
        "statistics": unwrap_data(bundle.get("statistics"), "统计"),
        "conditions": build_conditions(condition_id, bundle.get("conditions")),
    }
    result = {
        "tableId": table_id,
        "apiPrefix": api_prefix,
        "tableName": string_value(context.get("name")),
        "appId": app_id,
        "objId": obj_id,
        "viewType": string_value(context.get("viewType", "list")),
        "clientType": client_type,
        "config": config,
        "warnings": [],
    }
    return normalize_ids(result)


def main() -> int:
    configure_utf8_output()
    args = parse_args()
    table_id = str(args.table_id)
    try:
        api_prefix = resolve_api_prefix(args.api_prefix)
        if args.input_json:
            bundle = json.loads(args.input_json.read_text(encoding="utf-8-sig"))
        else:
            bundle = fetch_live_bundle(
                args.origin,
                api_prefix,
                table_id,
                args.client_type,
                args.is_virtual_form,
            )
        output = normalize_bundle(bundle, table_id, args.client_type, api_prefix)
        json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
