#!/usr/bin/env python3
"""Shared runtime URL and authentication helpers for eBuilder scripts."""

from __future__ import annotations

import os
import re
import urllib.parse
from typing import Dict, Optional


API_PREFIX_PATTERN = re.compile(r"/api/ebuilder(?:[0-9]+)?")

AGENT_TYPE_ENV = "EBUILDER_AGENT_TYPE"
DEFAULT_AGENT_TYPE = "WorkBuddy"


def agent_user_agent() -> str:
    """构造平台要求的 Agent 标识 User-Agent。

    格式：AgentType=<agentType>,IsAgent=true。agentType 可通过环境变量
    EBUILDER_AGENT_TYPE 覆盖（默认 WorkBuddy），便于区分调用方。
    """
    agent_type = (os.environ.get(AGENT_TYPE_ENV) or DEFAULT_AGENT_TYPE).strip()
    if not agent_type:
        agent_type = DEFAULT_AGENT_TYPE
    return f"AgentType={agent_type},IsAgent=true"


def resolve_origin(value: Optional[str]) -> str:
    raw = (value or os.environ.get("EBUILDER_ORIGIN") or "").strip()
    if not raw:
        raise RuntimeError("缺少 eBuilder origin，请传 --origin 或设置 EBUILDER_ORIGIN")
    if "\r" in raw or "\n" in raw:
        raise RuntimeError("eBuilder origin 包含非法换行")

    parsed = urllib.parse.urlsplit(raw)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise RuntimeError("eBuilder origin 必须是完整的 http/https 地址")
    if "@" in parsed.netloc:
        raise RuntimeError("eBuilder origin 不能包含用户信息")
    if parsed.query or parsed.fragment:
        raise RuntimeError("eBuilder origin 不能包含 query 或 fragment")
    if parsed.path not in ("", "/"):
        raise RuntimeError("eBuilder origin 只能包含 scheme 和 host，不能包含业务路径")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def resolve_api_prefix(value: Optional[str]) -> str:
    raw = (value or os.environ.get("EBUILDER_API_PREFIX") or "/api/ebuilder").strip()
    if not API_PREFIX_PATTERN.fullmatch(raw):
        raise RuntimeError(
            "apiPrefix 必须是 /api/ebuilder 或 /api/ebuilder{appId}"
        )
    return raw


def api_path(api_prefix: str, suffix: str) -> str:
    prefix = resolve_api_prefix(api_prefix)
    if not suffix.startswith("/") or suffix.startswith("/api/"):
        raise RuntimeError("API suffix 必须是以 / 开头且不含 /api 前缀的相对路径")
    return prefix + suffix


def auth_headers(content_type: Optional[str] = None) -> Dict[str, str]:
    cookie = (os.environ.get("EBUILDER_COOKIE") or "").strip()
    token = (os.environ.get("ETEAMSID") or "").strip()
    if not cookie and token:
        cookie = f"ETEAMSID={token}"
    if not cookie:
        raise RuntimeError(
            "缺少运行时认证，请设置 EBUILDER_COOKIE 或 ETEAMSID，或改用已登录浏览器"
        )
    if "\r" in cookie or "\n" in cookie:
        raise RuntimeError("Cookie 包含非法换行")

    headers = {
        "Accept": "application/json",
        "Cookie": cookie,
        "User-Agent": agent_user_agent(),
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers
