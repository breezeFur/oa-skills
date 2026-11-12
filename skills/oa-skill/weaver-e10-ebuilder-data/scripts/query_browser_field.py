#!/usr/bin/env python3
"""Resolve eBuilder browser-field display names to selectable option IDs."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from ebuilder_http import (
    agent_user_agent,
    api_path,
    auth_headers,
    resolve_api_prefix,
    resolve_origin,
)


MODULE_PATTERN = re.compile(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*")
BROWSER_TYPE_PATTERN = re.compile(r"[A-Za-z0-9_.-]+")

KIND_ALIASES = {
    "person": "person",
    "employee": "person",
    "resource": "person",
    "人员": "person",
    "department": "department",
    "dept": "department",
    "部门": "department",
    "subcompany": "subcompany",
    "branch": "subcompany",
    "分部": "subcompany",
    "workflow": "workflow",
    "flow": "workflow",
    "审批": "workflow",
    "流程": "workflow",
    "document": "document",
    "doc": "document",
    "文档": "document",
}

KIND_ROUTES = {
    "person": ("hrm", "resource", "人员"),
    "department": ("hrm", "department", "部门"),
    "subcompany": ("hrm", "subcompany", "分部"),
    "workflow": ("workflow/core", "wfcRequest", "审批数据"),
    "document": ("doc", "document", "文档"),
}

COMPONENT_KINDS = {
    "employee": "person",
    "person": "person",
    "personnel": "person",
    "resource": "person",
    "userselect": "person",
    "department": "department",
    "dept": "department",
    "subcompany": "subcompany",
    "subcompanyselect": "subcompany",
    "branch": "subcompany",
    "workflow": "workflow",
    "flow": "workflow",
    "document": "document",
    "doc": "document",
}

ID_KEYS = ("id", "optionId", "requestId", "value", "key")
NAME_KEYS = (
    "name",
    "content",
    "requestname",
    "fullName",
    "fullname",
    "username",
    "departmentName",
    "departmentname",
    "subcompanyName",
    "subcompanyname",
    "jobName",
    "title",
    "label",
)
DETAIL_KEYS = (
    "createdatetime",
    "createTime",
    "requestname",
    "requestmark",
    "workflowid",
    "workflowId",
    "code",
    "workcode",
    "departmentName",
    "departmentname",
    "subcompanyName",
    "subcompanyname",
    "supSubDepartment",
    "status",
    "statusname",
    "statusName",
    "currentnodename",
    "currentNodeName",
    "parentId",
    "typeName",
    "jobName",
    "title",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "按名称查询 eBuilder 人员、部门、分部、审批或关联浏览字段，"
            "并返回可写入表单的 optionId/content。"
        )
    )
    parser.add_argument("query", help="要查询的显示名称或关键词")
    parser.add_argument("--origin", help="OA 地址；未传时读取 EBUILDER_ORIGIN")
    parser.add_argument(
        "--api-prefix",
        help="字段接口前缀；默认读取 EBUILDER_API_PREFIX 或使用 /api/ebuilder",
    )
    parser.add_argument(
        "--kind",
        help="直接查询类型：person、department、subcompany、workflow、document",
    )
    parser.add_argument("--field", help="字段显示名称、数据键或字段 ID")
    parser.add_argument("--group-id", help="字段接口 groupId")
    parser.add_argument("--source-id", help="字段接口 sourceId")
    parser.add_argument(
        "--source-type",
        default="FORM",
        help="字段接口 sourceType（默认 FORM；布局逻辑场景常用 LOGIC）",
    )
    parser.add_argument(
        "--module",
        help="浏览接口模块，例如 task 或 workflow/core；需与 --browser-type 同时传入",
    )
    parser.add_argument(
        "--browser-type",
        help="浏览类型，例如 taskTypeBrowser；需与 --module 同时传入",
    )
    parser.add_argument(
        "--business-id",
        help="可选 eBusinessId；未传时读取 EBUILDER_BUSINESS_ID",
    )
    parser.add_argument(
        "--second-emp-id",
        help="可选 Secondempid；未传时读取 EBUILDER_SECOND_EMP_ID",
    )
    parser.add_argument(
        "--extra-json",
        help="合并到浏览请求体的 JSON 对象；可传 JSON 字符串或 @文件路径",
    )
    parser.add_argument(
        "--fields-json",
        type=Path,
        help="使用本地字段接口响应，代替在线读取字段定义",
    )
    parser.add_argument(
        "--response-json",
        type=Path,
        help="使用本地浏览接口响应，代替在线查询",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="最多输出多少条匹配数据（默认 20）",
    )
    parser.add_argument(
        "--require-unique",
        action="store_true",
        help="不是唯一结果时返回退出码 2，便于写操作前阻断",
    )
    multiple_group = parser.add_mutually_exclusive_group()
    multiple_group.add_argument(
        "--multiple", dest="multiple", action="store_true", help="按多选字段查询"
    )
    multiple_group.add_argument(
        "--single", dest="multiple", action="store_false", help="按单选字段查询"
    )
    parser.set_defaults(multiple=None)
    return parser.parse_args()


def read_json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise RuntimeError(f"无法读取 JSON 文件 {path}: {exc}") from None
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"JSON 文件格式错误 {path}: {exc}") from None


def read_json_argument(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {}
    payload = read_json_file(Path(value[1:])) if value.startswith("@") else None
    if payload is None:
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"--extra-json 不是有效 JSON: {exc}") from None
    if not isinstance(payload, dict):
        raise RuntimeError("--extra-json 必须是 JSON 对象")
    return payload


def runtime_headers(content_type: Optional[str], args: argparse.Namespace) -> Dict[str, str]:
    headers = auth_headers(content_type)
    headers["Accept-Language"] = "zh-CN,zh;q=0.9"
    headers["User-Agent"] = agent_user_agent()
    token = (os.environ.get("ETEAMSID") or "").strip()
    if token:
        headers["ETEAMSID"] = token
    business_id = (args.business_id or os.environ.get("EBUILDER_BUSINESS_ID") or "").strip()
    second_emp_id = (
        args.second_emp_id or os.environ.get("EBUILDER_SECOND_EMP_ID") or ""
    ).strip()
    if business_id:
        headers["ebbusinessid"] = business_id
    if second_emp_id:
        headers["Secondempid"] = second_emp_id
    headers["langtype"] = "zh_CN"
    return headers


def response_message(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    candidates: List[Any] = [payload.get("msg"), payload.get("message")]
    message = payload.get("message")
    if isinstance(message, dict):
        candidates.extend((message.get("msg"), message.get("message")))
    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value.strip()[:300]
    return ""


def request_json(
    origin: str,
    path: str,
    body: bytes,
    headers: Mapping[str, str],
) -> Any:
    resolved_origin = resolve_origin(origin)
    url = resolved_origin.rstrip("/") + path
    request_headers = dict(headers)
    request_headers.setdefault("Origin", resolved_origin)
    request_headers.setdefault("Referer", resolved_origin + "/")
    request = urllib.request.Request(
        url, data=body, headers=request_headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8-sig"))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise RuntimeError(f"接口返回 HTTP {exc.code}，请更新 Cookie/ETEAMSID") from None
        raise RuntimeError(f"接口返回 HTTP {exc.code}") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"接口请求失败: {exc.reason}") from None
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"接口没有返回有效 JSON: {exc}") from None

    if isinstance(payload, dict) and payload.get("status") is False:
        detail = response_message(payload)
        suffix = f": {detail}" if detail else ""
        raise RuntimeError(f"接口返回业务失败{suffix}")
    return payload


def encode_multipart(fields: Mapping[str, str]) -> Tuple[bytes, str]:
    boundary = "----EBuilderSkillBoundary" + uuid.uuid4().hex
    chunks: List[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            (
                f"--{boundary}\r\n".encode("ascii"),
                (
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                ).encode("ascii"),
                str(value).encode("utf-8"),
                b"\r\n",
            )
        )
    chunks.append(f"--{boundary}--\r\n".encode("ascii"))
    return b"".join(chunks), boundary


def fetch_fields(args: argparse.Namespace, origin: str) -> Any:
    if not args.group_id or not args.source_id:
        raise RuntimeError("在线查询字段时必须同时传 --group-id 和 --source-id")
    body, boundary = encode_multipart(
        {
            "groupId": args.group_id,
            "sourceId": args.source_id,
            "sourceType": args.source_type,
            "detailFieldsGroup": "true",
            "enableMerge": "true",
            "customParam": '{"terminal":""}',
            "params": "[]",
        }
    )
    path = api_path(resolve_api_prefix(args.api_prefix), "/common/ds/fields")
    headers = runtime_headers(f"multipart/form-data; boundary={boundary}", args)
    return request_json(origin, path, body, headers)


def display_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, dict):
        for key in ("showName", "name", "content", "zh_CN", "zh-CN", "7"):
            text = display_text(value.get(key))
            if text:
                return text
        for candidate in value.values():
            text = display_text(candidate)
            if text:
                return text
    if isinstance(value, list):
        for candidate in value:
            text = display_text(candidate)
            if text:
                return text
    return ""


def collect_fields(payload: Any) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    seen: set = set()

    def walk(node: Any, group_name: str = "", group_id: str = "") -> None:
        if isinstance(node, list):
            for item in node:
                walk(item, group_name, group_id)
            return
        if not isinstance(node, dict):
            return

        fields = node.get("fields")
        next_group_name = display_text(node.get("name")) or group_name
        next_group_id = display_text(node.get("id")) or group_id
        if isinstance(fields, list):
            for item in fields:
                if not isinstance(item, dict):
                    continue
                key = (
                    display_text(item.get("id")),
                    display_text(item.get("name")),
                    display_text(item.get("text")),
                    next_group_id,
                )
                if key in seen:
                    continue
                seen.add(key)
                enriched = dict(item)
                enriched["_groupName"] = next_group_name
                enriched["_groupId"] = next_group_id
                found.append(enriched)
        for key, value in node.items():
            if key != "fields":
                walk(value, next_group_name, next_group_id)

    walk(payload)
    return found


def field_labels(field: Mapping[str, Any]) -> List[str]:
    config = field.get("config") if isinstance(field.get("config"), dict) else {}
    labels = [
        display_text(field.get("text")),
        display_text(config.get("title")),
        display_text(config.get("name")),
        display_text(field.get("name")),
        display_text(config.get("dataKey")),
        display_text(field.get("id")),
    ]
    return list(dict.fromkeys(label for label in labels if label))


def field_summary(field: Mapping[str, Any]) -> Dict[str, Any]:
    config = field.get("config") if isinstance(field.get("config"), dict) else {}
    return {
        "id": display_text(field.get("id")),
        "title": (
            display_text(field.get("text"))
            or display_text(config.get("title"))
            or display_text(field.get("name"))
        ),
        "name": display_text(field.get("name")),
        "dataKey": display_text(config.get("dataKey")),
        "componentKey": (
            display_text(config.get("componentKey"))
            or display_text(field.get("compType"))
            or display_text(field.get("type"))
        ),
        "group": display_text(field.get("_groupName")),
    }


def select_field(payload: Any, query: str) -> Dict[str, Any]:
    fields = collect_fields(payload)
    needle = query.strip().casefold()
    if not needle:
        raise RuntimeError("--field 不能为空")
    exact = [field for field in fields if needle in {v.casefold() for v in field_labels(field)}]
    matches = exact or [
        field
        for field in fields
        if any(needle in value.casefold() for value in field_labels(field))
    ]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        candidates = [field_summary(field) for field in fields[:20]]
        raise RuntimeError(
            "没有找到字段；可用字段（最多 20 个）: "
            + json.dumps(candidates, ensure_ascii=False)
        )
    candidates = [field_summary(field) for field in matches[:20]]
    raise RuntimeError(
        "字段名称不唯一，请改用字段 ID 或更完整的名称: "
        + json.dumps(candidates, ensure_ascii=False)
    )


def decode_object(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip().startswith("{"):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def validate_route(module: str, browser_type: str) -> Tuple[str, str]:
    module = module.strip().strip("/")
    browser_type = browser_type.strip().strip("/")
    if not MODULE_PATTERN.fullmatch(module):
        raise RuntimeError("浏览模块格式无效")
    if not BROWSER_TYPE_PATTERN.fullmatch(browser_type):
        raise RuntimeError("浏览类型格式无效")
    return module, browser_type


def resolve_kind(value: str) -> str:
    key = value.strip().casefold()
    kind = KIND_ALIASES.get(key)
    if not kind:
        raise RuntimeError(f"未知 --kind: {value}")
    return kind


def route_from_field(field: Mapping[str, Any]) -> Tuple[str, str, str]:
    config = field.get("config") if isinstance(field.get("config"), dict) else {}
    browser_params = (
        field.get("browserParams") if isinstance(field.get("browserParams"), dict) else {}
    )
    browser_objects = (
        config.get("browserType"),
        field.get("browserType"),
        browser_params.get("browserType"),
    )
    for raw in browser_objects:
        browser = decode_object(raw)
        module = display_text(browser.get("module"))
        browser_type = display_text(browser.get("type"))
        if module and browser_type:
            return (*validate_route(module, browser_type), "field.browserType")

    component_values = (
        config.get("componentKey"),
        field.get("compType"),
        field.get("type"),
        config.get("type"),
        field.get("dataType"),
    )
    for value in component_values:
        component = display_text(value).casefold()
        kind = COMPONENT_KINDS.get(component)
        if kind:
            module, browser_type, _ = KIND_ROUTES[kind]
            return module, browser_type, f"component:{component}"

    type_only = ""
    for raw in browser_objects:
        if isinstance(raw, str) and BROWSER_TYPE_PATTERN.fullmatch(raw.strip()):
            type_only = raw.strip()
            break
    if type_only:
        raise RuntimeError(
            f"字段只返回了浏览类型 {type_only}，没有返回模块；请补充 --module 和 --browser-type"
        )
    raise RuntimeError(
        "无法从字段定义确定浏览接口；请检查 config.browserType，"
        "或显式传入 --module 和 --browser-type"
    )


def bool_value(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in ("true", "1", "yes", "y"):
            return True
        if normalized in ("false", "0", "no", "n"):
            return False
    return None


def field_is_multiple(field: Optional[Mapping[str, Any]]) -> bool:
    if not field:
        return False
    config = field.get("config") if isinstance(field.get("config"), dict) else {}
    is_single = bool_value(config.get("isSingle"))
    if is_single is not None:
        return not is_single
    for value in (field.get("multiSelect"), config.get("multiSelect"), config.get("multiple")):
        parsed = bool_value(value)
        if parsed is not None:
            return parsed
    return False


def build_form_param(field: Optional[Mapping[str, Any]]) -> Optional[str]:
    if not field:
        return None
    config = field.get("config") if isinstance(field.get("config"), dict) else {}
    browser_params = (
        field.get("browserParams") if isinstance(field.get("browserParams"), dict) else {}
    )
    form_id = display_text(browser_params.get("formId")) or display_text(config.get("formId"))
    layout_id = display_text(browser_params.get("layoutId")) or display_text(
        config.get("layoutId")
    )
    field_id = (
        display_text(browser_params.get("fieldId"))
        or display_text(config.get("fieldId"))
        or display_text(field.get("id"))
    )
    module = (
        display_text(browser_params.get("serviceModule"))
        or display_text(config.get("serviceModule"))
        or "ebuilderform"
    )
    if not form_id and not field_id:
        return None
    return json.dumps(
        {
            "formId": form_id,
            "layoutId": layout_id,
            "fieldId": field_id,
            "filterItems": [],
            "module": module,
            "dataDetails": [],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def build_browser_payload(
    query: str,
    multiple: bool,
    field: Optional[Mapping[str, Any]],
    extra: Mapping[str, Any],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "browserMultiple": multiple,
        "newly": 1,
        "searchValue": query,
    }
    form_param = build_form_param(field)
    if form_param:
        payload.update(
            {
                "formParam": form_param,
                "variableDataKeyMap": {},
                "customParam": {},
            }
        )
    payload.update(extra)
    return payload


def extract_result_records(payload: Any) -> Tuple[List[Mapping[str, Any]], Optional[int]]:
    container = payload.get("data") if isinstance(payload, dict) else payload
    total: Optional[int] = None
    records: Any = container
    if isinstance(container, dict):
        raw_total = container.get("total")
        if isinstance(raw_total, int):
            total = raw_total
        records = container.get("data", [])
    if isinstance(records, dict):
        records = list(records.values())
    if not isinstance(records, list):
        return [], total

    flattened: List[Mapping[str, Any]] = []

    def walk(items: Sequence[Any]) -> None:
        for item in items:
            if not isinstance(item, dict):
                continue
            flattened.append(item)
            children = item.get("children")
            if isinstance(children, list):
                walk(children)

    walk(records)
    return flattened, total


def first_text(record: Mapping[str, Any], keys: Iterable[str]) -> str:
    for key in keys:
        value = display_text(record.get(key))
        if value:
            return value
    return ""


def safe_details(record: Mapping[str, Any]) -> Dict[str, Any]:
    details: Dict[str, Any] = {}
    for key in DETAIL_KEYS:
        value = record.get(key)
        if isinstance(value, (str, int, float, bool)) and value not in ("", None):
            details[key] = value
    return details


def normalize_matches(payload: Any, limit: int) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    records, total = extract_result_records(payload)
    matches: List[Dict[str, Any]] = []
    seen: set = set()
    for record in records:
        option_id = first_text(record, ID_KEYS)
        content = first_text(record, NAME_KEYS)
        if not option_id and not content:
            continue
        key = (option_id, content)
        if key in seen:
            continue
        seen.add(key)
        item: Dict[str, Any] = {"id": option_id, "name": content}
        details = safe_details(record)
        if details:
            item["details"] = details
        if option_id and content:
            item["dataOption"] = {"optionId": option_id, "content": content}
        matches.append(item)
        if len(matches) >= limit:
            break
    return matches, total


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    args = parse_args()
    try:
        if args.limit < 1 or args.limit > 200:
            raise RuntimeError("--limit 必须在 1 到 200 之间")
        if bool(args.module) != bool(args.browser_type):
            raise RuntimeError("--module 和 --browser-type 必须同时传入")
        if bool(args.group_id) != bool(args.source_id):
            raise RuntimeError("--group-id 和 --source-id 必须同时传入")

        field: Optional[Dict[str, Any]] = None
        if args.field:
            fields_payload = (
                read_json_file(args.fields_json)
                if args.fields_json
                else fetch_fields(args, args.origin or os.environ.get("EBUILDER_ORIGIN") or "")
            )
            field = select_field(fields_payload, args.field)

        if args.module and args.browser_type:
            module, browser_type = validate_route(args.module, args.browser_type)
            route_source = "explicit"
            route_label = "自定义浏览数据"
        elif field:
            module, browser_type, route_source = route_from_field(field)
            route_label = field_summary(field)["title"] or "浏览字段"
        elif args.kind:
            kind = resolve_kind(args.kind)
            module, browser_type, route_label = KIND_ROUTES[kind]
            route_source = f"kind:{kind}"
        else:
            raise RuntimeError(
                "请使用 --field、--kind，或同时传入 --module 和 --browser-type"
            )

        multiple = args.multiple if args.multiple is not None else field_is_multiple(field)
        endpoint = f"/api/{module}/common/browser/complete/{browser_type}"
        extra = read_json_argument(args.extra_json)
        request_payload = build_browser_payload(args.query, multiple, field, extra)

        if args.response_json:
            response_payload = read_json_file(args.response_json)
        else:
            origin = resolve_origin(args.origin)
            body = json.dumps(request_payload, ensure_ascii=False).encode("utf-8")
            response_payload = request_json(
                origin,
                endpoint,
                body,
                runtime_headers("application/json", args),
            )

        all_matches, reported_total = normalize_matches(response_payload, args.limit)
        needle = args.query.strip().casefold()
        exact_matches = [
            item
            for item in all_matches
            if display_text(item.get("name")).casefold() == needle
        ]
        matches = exact_matches or all_matches
        exact_count = len(exact_matches)
        output: Dict[str, Any] = {
            "query": args.query,
            "field": field_summary(field) if field else None,
            "browser": {
                "label": route_label,
                "module": module,
                "type": browser_type,
                "endpoint": endpoint,
                "routeSource": route_source,
                "multiple": multiple,
            },
            "candidateCount": len(all_matches),
            "matchCount": len(matches),
            "reportedTotal": reported_total,
            "exactNameCount": exact_count,
            "unique": len(matches) == 1,
            "ambiguous": len(matches) > 1,
            "matches": matches,
        }
        json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        if args.require_unique and len(matches) != 1:
            return 2
        return 0
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
