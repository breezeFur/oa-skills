#!/usr/bin/env python3
"""Shared runtime URL, authentication, HTTP-session, and timing helpers."""

from __future__ import annotations

import http.client
import json
import os
import re
import sys
import threading
import time
import urllib.parse
from typing import Any, Dict, List, Mapping, Optional


API_PREFIX_PATTERN = re.compile(r"/api/ebuilder(?:[0-9]+)?")
PUBLIC_API_PREFIX = "/api/ebuilder"


class EbuilderHttpError(RuntimeError):
    """HTTP or response-decoding failure without exposing credentials."""


def configure_utf8_output() -> None:
    """Keep JSON output readable when Python is invoked from Windows shells."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


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
    """Route only /form APIs through an independent-deployment prefix."""
    prefix = resolve_api_prefix(api_prefix)
    if not suffix.startswith("/") or suffix.startswith("/api/"):
        raise RuntimeError("API suffix 必须是以 / 开头且不含 /api 前缀的相对路径")
    routed_prefix = (
        prefix
        if suffix == "/form" or suffix.startswith("/form/")
        else PUBLIC_API_PREFIX
    )
    return routed_prefix + suffix


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
        "eteamsid": token if token else "",
        "User-Agent": "AgentType=WorkBuddy,IsAgent=true",
    }
    if not headers["eteamsid"]:
        del headers["eteamsid"]
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def same_origin_headers(
    origin: str,
    content_type: Optional[str] = None,
    extra_headers: Optional[Mapping[str, str]] = None,
) -> Dict[str, str]:
    """Build authenticated headers required by same-origin eBuilder APIs."""
    resolved_origin = resolve_origin(origin)
    headers = auth_headers(content_type)
    if extra_headers:
        headers.update(dict(extra_headers))
    headers["Origin"] = resolved_origin
    headers["Referer"] = resolved_origin + "/"
    return headers


def encode_multipart(fields: Mapping[str, Any], boundary: str) -> bytes:
    """Encode scalar multipart fields with a caller-provided safe boundary."""
    chunks: List[bytes] = []
    for raw_name, raw_value in fields.items():
        name = str(raw_name)
        if any(char in name for char in ('"', "\r", "\n")):
            raise RuntimeError("multipart 字段名包含非法字符")
        chunks.extend(
            (
                f"--{boundary}\r\n".encode("ascii"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(
                    "ascii"
                ),
                str(raw_value).encode("utf-8"),
                b"\r\n",
            )
        )
    chunks.append(f"--{boundary}--\r\n".encode("ascii"))
    return b"".join(chunks)


class EbuilderHttpClient:
    """Same-origin JSON client with per-thread keep-alive connections and timings.

    A thread-local connection lets independent browser-field lookups run in
    parallel while sequential calls in each worker reuse the same connection.
    Requests are never retried automatically, which is important for writes.
    """

    def __init__(self, origin: str, *, timeout: float = 30.0) -> None:
        self.origin = resolve_origin(origin)
        parsed = urllib.parse.urlsplit(self.origin)
        self.scheme = parsed.scheme
        self.host = parsed.hostname or ""
        self.port = parsed.port
        self.timeout = timeout
        self._local = threading.local()
        self._connections: List[http.client.HTTPConnection] = []
        self._lock = threading.Lock()
        self._timings: List[Dict[str, Any]] = []

    def __enter__(self) -> "EbuilderHttpClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def _new_connection(self) -> http.client.HTTPConnection:
        if self.scheme == "https":
            connection: http.client.HTTPConnection = http.client.HTTPSConnection(
                self.host, self.port, timeout=self.timeout
            )
        else:
            connection = http.client.HTTPConnection(
                self.host, self.port, timeout=self.timeout
            )
        with self._lock:
            self._connections.append(connection)
        return connection

    def _connection(self) -> http.client.HTTPConnection:
        connection = getattr(self._local, "connection", None)
        if connection is None:
            connection = self._new_connection()
            self._local.connection = connection
        return connection

    def _drop_current_connection(self) -> None:
        connection = getattr(self._local, "connection", None)
        if connection is not None:
            try:
                connection.close()
            finally:
                self._local.connection = None

    def close(self) -> None:
        with self._lock:
            connections = list(self._connections)
            self._connections.clear()
        for connection in connections:
            try:
                connection.close()
            except OSError:
                pass

    @property
    def timings(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._timings]

    def _record_timing(self, item: Dict[str, Any]) -> None:
        with self._lock:
            self._timings.append(item)

    def request_json(
        self,
        method: str,
        path: str,
        *,
        query: Optional[Mapping[str, Any]] = None,
        json_body: Any = None,
        body: Optional[bytes] = None,
        content_type: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
        label: str = "request",
    ) -> Any:
        if not path.startswith("/") or path.startswith("//") or "://" in path:
            raise RuntimeError("HTTP path 必须是同源绝对路径")
        if json_body is not None and body is not None:
            raise RuntimeError("json_body 与 body 不能同时提供")
        request_path = path
        if query:
            request_path += "?" + urllib.parse.urlencode(query, doseq=True)
        request_body = body
        if json_body is not None:
            request_body = json.dumps(
                json_body, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            content_type = content_type or "application/json"
        request_headers = same_origin_headers(
            self.origin,
            content_type,
            headers,
        )
        request_headers.setdefault("Accept-Language", "zh-CN,zh;q=0.9")
        request_headers.setdefault("Connection", "keep-alive")

        started = time.perf_counter()
        status: Optional[int] = None
        try:
            connection = self._connection()
            connection.request(
                method.upper(), request_path, body=request_body, headers=request_headers
            )
            response = connection.getresponse()
            status = response.status
            raw = response.read()
            if response.getheader("Connection", "").lower() == "close":
                self._drop_current_connection()
        except (OSError, http.client.HTTPException) as exc:
            self._drop_current_connection()
            raise EbuilderHttpError(f"{label} 请求失败: {exc}") from None
        finally:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
            self._record_timing(
                {
                    "label": label,
                    "method": method.upper(),
                    "path": path,
                    "status": status,
                    "elapsedMs": elapsed_ms,
                }
            )

        if status in (401, 403):
            raise EbuilderHttpError(f"{label} 返回 HTTP {status}，请重新建立认证会话")
        if status is None or status < 200 or status >= 300:
            raise EbuilderHttpError(f"{label} 返回 HTTP {status}")
        try:
            return json.loads(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EbuilderHttpError(f"{label} 没有返回有效 UTF-8 JSON: {exc}") from None
