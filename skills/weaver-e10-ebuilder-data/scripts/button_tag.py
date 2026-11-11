#!/usr/bin/env python3
"""E10 eBuilder 表单按钮 Tag 查询封装。

提供一个登录态 PC 前台接口的调用封装：
- queryButtonsByTags(objId, dataId, tags, viewType)：按一个或多个 Tag 查询按钮及其动作。

认证与运行方式与包内其他脚本一致：先通过 weaver-e10-login 建立会话，
再以环境变量 EBUILDER_ORIGIN / EBUILDER_COOKIE 或 ETEAMSID 注入运行时认证。
服务端返回的 WeaResult（含业务异常与单按钮 success=false）原样透传，不做本地权限模拟。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ebuilder_http import (
    agent_user_agent,
    api_path,
    auth_headers,
    resolve_api_prefix,
    resolve_origin,
)

BUTTON_BASE_PATH = "/form/button"
QUERY_BY_TAGS_PATH = BUTTON_BASE_PATH + "/queryByTags"
VIEW_TYPES = ("0", "2")


def runtime_headers(content_type: Optional[str]) -> Dict[str, str]:
    """构造按钮接口请求头：会话 Cookie、eteamsid 与 Agent 标识 User-Agent。"""
    headers = auth_headers(content_type)
    headers["Accept-Language"] = "zh-CN,zh;q=0.9"
    headers["User-Agent"] = agent_user_agent()
    token = (os.environ.get("ETEAMSID") or "").strip()
    if token:
        headers["ETEAMSID"] = token
    headers["langtype"] = "zh_CN"
    return headers


def normalize_tags(tags: Any) -> str:
    """将 Tag 参数规范化为英文逗号分隔的字符串：拆分、去除首尾空格、去重（保留顺序）。

    服务端对 tags 会自动去除首尾空格并去重，客户端做同样的规范化保持一致。
    """
    if isinstance(tags, str):
        parts = tags.split(",")
    elif isinstance(tags, (list, tuple)):
        parts = [str(item) for item in tags]
    else:
        raise RuntimeError("tags 必须是逗号分隔的字符串或字符串列表")
    cleaned: List[str] = []
    seen = set()
    for part in parts:
        value = part.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    if not cleaned:
        raise RuntimeError("tags 不能为空，至少需要一个有效 Tag")
    return ",".join(cleaned)


def request_json(
    origin: str,
    path: str,
    body: bytes,
    headers: Mapping[str, str],
) -> Any:
    """POST JSON 并返回响应；仅处理 HTTP 层异常，业务结果原样返回。"""
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
            return json.loads(response.read().decode("utf-8-sig"))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise RuntimeError(f"接口返回 HTTP {exc.code}，请更新 Cookie/ETEAMSID") from None
        raise RuntimeError(f"接口返回 HTTP {exc.code}") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"接口请求失败: {exc.reason}") from None
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"接口没有返回有效 JSON: {exc}") from None


def queryButtonsByTags(
    obj_id: Any,
    data_id: Any,
    tags: Any,
    view_type: Any,
    *,
    origin: Optional[str] = None,
    api_prefix: Optional[str] = None,
) -> Dict[str, Any]:
    """按一个或多个 Tag 查询按钮。

    viewType 仅支持 "0"（显示布局，按查看权限判断）或 "2"（编辑布局，按编辑权限判断）。
    返回 WeaResult 原样透传：调用方需同时处理 HTTP 异常、WeaResult 业务失败，
    以及 data 内单个按钮的 success=false（例如「该按钮无权限显示」）。
    """
    normalized = normalize_tags(tags)
    normalized_view = str(view_type)
    if normalized_view not in VIEW_TYPES:
        raise RuntimeError('viewType 仅支持 "0"（显示布局）或 "2"（编辑布局）')
    payload = {
        "objId": obj_id,
        "dataId": data_id,
        "tags": normalized,
        "viewType": normalized_view,
    }
    path = api_path(
        api_prefix or os.environ.get("EBUILDER_API_PREFIX") or "/api/ebuilder",
        QUERY_BY_TAGS_PATH,
    )
    headers = runtime_headers("application/json")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    result = request_json(origin or "", path, body, headers)
    if not isinstance(result, dict):
        raise RuntimeError("queryByTags 接口没有返回 JSON 对象")
    return result


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="E10 eBuilder 表单按钮 Tag 查询封装"
    )
    parser.add_argument("--origin", help="OA 地址；未传时读取 EBUILDER_ORIGIN")
    parser.add_argument(
        "--api-prefix",
        help="接口前缀；默认读取 EBUILDER_API_PREFIX 或使用 /api/ebuilder",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    query_parser = subparsers.add_parser("query", help="按 Tag 查询按钮")
    query_parser.add_argument("--obj-id", required=True, help="表单对象 ID")
    query_parser.add_argument("--data-id", required=True, help="当前表单数据 ID")
    query_parser.add_argument(
        "--tags", required=True, help="一个或多个 Tag，英文逗号分隔"
    )
    query_parser.add_argument(
        "--view-type", required=True, help="布局类型：0 显示布局 / 2 编辑布局"
    )
    query_parser.set_defaults(func=cmd_query)
    return parser.parse_args(argv)


def cmd_query(args: argparse.Namespace) -> int:
    result = queryButtonsByTags(
        args.obj_id,
        args.data_id,
        args.tags,
        args.view_type,
        origin=args.origin,
        api_prefix=args.api_prefix,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
