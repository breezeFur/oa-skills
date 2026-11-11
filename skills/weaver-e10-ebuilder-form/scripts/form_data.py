#!/usr/bin/env python3
"""Unified, timed eBuilder form context and CRUD CLI."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import urllib.parse
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from ebuilder_http import (
    EbuilderHttpClient,
    api_path,
    configure_utf8_output,
    encode_multipart,
    resolve_api_prefix,
    resolve_origin,
)
from get_nlist_config import select_primary_nlist_component, unwrap_page
from query_browser_field import (
    build_browser_payload,
    display_text,
    field_is_multiple,
    field_summary,
    normalize_matches,
    route_from_field,
    select_field,
)


SUCCESS_CODES = {"0", "200", "success"}
BROWSER_COMPONENTS = {
    "employee",
    "person",
    "personnel",
    "resource",
    "userselect",
    "department",
    "dept",
    "subcompany",
    "subcompanyselect",
    "branch",
    "workflow",
    "flow",
    "document",
    "doc",
    "relatebrowser",
}
SELECT_COMPONENTS = {"select", "radiobox", "checkbox"}
CONTEXT_CACHE_TTL_SECONDS = 30 * 60
FIELDS_CACHE_TTL_SECONDS = 10 * 60
CACHE_SCHEMA_VERSION = 2
CACHE_DIRECTORY_NAME = "weaver-e10-ebuilder-form-cache-v2"
DIRECT_LIST_TYPES = {
    "list": ("SEARCH", "List"),
    "search": ("SEARCH", "List"),
    "viewport": ("VIEWPORT", "NList"),
    "nlist": ("VIEWPORT", "NList"),
}


class ResolveError(RuntimeError):
    """Target or field cannot be resolved without user input."""


class BusinessFailure(RuntimeError):
    """The server returned a clear business failure; never retry blindly."""

    def __init__(self, message: str, result: Mapping[str, Any]) -> None:
        super().__init__(message)
        self.result = dict(result)


class PerformanceRecorder:
    def __init__(self) -> None:
        self.started = time.perf_counter()
        self.stages: List[Dict[str, Any]] = []

    @contextmanager
    def stage(self, name: str) -> Iterable[None]:
        started = time.perf_counter()
        try:
            yield
        finally:
            self.stages.append(
                {
                    "name": name,
                    "elapsedMs": round((time.perf_counter() - started) * 1000, 1),
                }
            )

    def output(self, client: EbuilderHttpClient) -> Dict[str, Any]:
        requests = client.timings
        return {
            "totalMs": round((time.perf_counter() - self.started) * 1000, 1),
            "requestCount": len(requests),
            "stages": list(self.stages),
            "requests": requests,
        }


def auth_cache_scope() -> str:
    """Return a one-way session scope without persisting authentication values."""
    cookie = (os.environ.get("EBUILDER_COOKIE") or "").strip()
    token = (os.environ.get("ETEAMSID") or "").strip()
    if not cookie and not token:
        return ""
    source = json.dumps(
        {
            "cookie": cookie,
            "token": token,
            "businessId": (os.environ.get("EBUILDER_BUSINESS_ID") or "").strip(),
            "secondEmpId": (os.environ.get("EBUILDER_SECOND_EMP_ID") or "").strip(),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


class RuntimeCache:
    """Short-lived, credential-free cache for form context and field metadata."""

    def __init__(
        self,
        origin: str,
        *,
        enabled: bool = True,
        refresh: bool = False,
        directory: Optional[str] = None,
    ) -> None:
        auth_scope = auth_cache_scope()
        self.enabled = bool(enabled and auth_scope)
        self.refresh = bool(refresh)
        root_value = directory or os.environ.get("EBUILDER_CACHE_DIR")
        self.root = (
            Path(root_value).expanduser()
            if root_value
            else Path(tempfile.gettempdir()) / CACHE_DIRECTORY_NAME
        )
        namespace_source = f"{origin}\0{auth_scope}"
        self.namespace = hashlib.sha256(
            namespace_source.encode("utf-8")
        ).hexdigest()
        self.events: List[Dict[str, str]] = []

    def _path(self, kind: str, key: Any) -> Path:
        serialized = json.dumps(
            key, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return self.root / self.namespace / f"{kind}-{digest}.json"

    def _event(self, kind: str, status: str) -> None:
        self.events.append({"kind": kind, "status": status})

    def discard(self, kind: str, key: Any, *, status: str = "invalid") -> None:
        if not self.enabled:
            return
        path = self._path(kind, key)
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass
        self._event(kind, status)

    def get(self, kind: str, key: Any) -> Any:
        if not self.enabled:
            return None
        if self.refresh:
            self._event(kind, "refresh")
            return None
        path = self._path(kind, key)
        try:
            wrapper = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            self._event(kind, "miss")
            return None
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            self.discard(kind, key)
            return None
        if (
            not isinstance(wrapper, Mapping)
            or wrapper.get("schemaVersion") != CACHE_SCHEMA_VERSION
            or wrapper.get("kind") != kind
        ):
            self.discard(kind, key)
            return None
        try:
            expires_at = float(wrapper.get("expiresAt") or 0)
        except (TypeError, ValueError):
            self.discard(kind, key)
            return None
        if expires_at <= time.time():
            self.discard(kind, key, status="expired")
            return None
        self._event(kind, "hit")
        return wrapper.get("payload")

    def put(self, kind: str, key: Any, payload: Any, ttl_seconds: int) -> None:
        if not self.enabled:
            return
        path = self._path(kind, key)
        temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
        wrapper = {
            "schemaVersion": CACHE_SCHEMA_VERSION,
            "kind": kind,
            "expiresAt": time.time() + ttl_seconds,
            "payload": payload,
        }
        try:
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            temporary.write_text(
                json.dumps(wrapper, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            try:
                temporary.chmod(0o600)
            except OSError:
                pass
            os.replace(temporary, path)
        except (OSError, TypeError, ValueError):
            try:
                temporary.unlink()
            except (FileNotFoundError, OSError):
                pass
            self._event(kind, "write-skipped")
            return
        self._event(kind, "write")

    def summary(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "refresh": self.refresh,
            "contextTtlSeconds": CONTEXT_CACHE_TTL_SECONDS,
            "fieldsTtlSeconds": FIELDS_CACHE_TTL_SECONDS,
            "hits": sum(item["status"] == "hit" for item in self.events),
            "misses": sum(
                item["status"] in {"miss", "refresh", "expired", "invalid"}
                for item in self.events
            ),
            "writes": sum(item["status"] == "write" for item in self.events),
        }


def read_json_value(
    value: Optional[str],
    *,
    label: str,
    expected_type: type = dict,
    required: bool = False,
) -> Any:
    if not value:
        if required:
            raise ResolveError(f"缺少 {label}")
        return expected_type()
    if value == "-":
        raw = sys.stdin.read()
    elif value.startswith("@"):
        try:
            raw = Path(value[1:]).read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise ResolveError(f"无法读取 {label}: {exc}") from None
    else:
        raw = value
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ResolveError(f"{label} 不是有效 JSON: {exc}") from None
    if not isinstance(payload, expected_type):
        raise ResolveError(f"{label} 必须是 JSON {expected_type.__name__}")
    return payload


def string_id(value: Any, label: str, *, required: bool = True) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        if required:
            raise ResolveError(f"缺少 {label}")
        return ""
    if not text.isdigit():
        raise ResolveError(f"{label} 必须是十进制 ID")
    return text


def direct_url_origin(value: Optional[str]) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if "\r" in raw or "\n" in raw:
        raise ResolveError("页面 URL 包含非法换行")
    parsed = urllib.parse.urlsplit(raw)
    if bool(parsed.scheme) != bool(parsed.netloc):
        raise ResolveError("页面 URL 必须是完整 http/https 地址或以 / 开头的同源路径")
    if not parsed.scheme:
        return ""
    try:
        return resolve_origin(
            urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
        )
    except RuntimeError as exc:
        raise ResolveError(f"页面 URL 无效：{exc}") from None


def parse_direct_list_url(
    value: Optional[str], expected_origin: Optional[str] = None
) -> Dict[str, str]:
    raw = str(value or "").strip()
    if not raw:
        raise ResolveError("缺少页面 URL")
    url_origin = direct_url_origin(raw)
    confirmed_origin = resolve_origin(expected_origin) if expected_origin else url_origin
    if not confirmed_origin:
        raise ResolveError("相对页面 URL 还需提供 --origin 或 EBUILDER_ORIGIN")
    if url_origin and url_origin != confirmed_origin:
        raise ResolveError("页面 URL 与当前 origin 不同源")

    parsed = urllib.parse.urlsplit(raw)
    if not parsed.scheme:
        if not parsed.path.startswith("/") or parsed.path.startswith("//"):
            raise ResolveError("相对页面 URL 必须以单个 / 开头")
        entry_url = confirmed_origin + raw
    else:
        entry_url = raw

    segments = [item for item in parsed.path.split("/") if item]
    path_markers = [
        item.casefold()
        for item in segments
        if item.casefold() in DIRECT_LIST_TYPES
    ]
    if len({DIRECT_LIST_TYPES[item][0] for item in path_markers}) > 1:
        raise ResolveError("页面 URL 路径同时包含表格和数据列表类型")
    path_type = ""
    path_id = ""
    path_app_id = ""
    path_menu_id = ""
    if len(segments) >= 2:
        marker = segments[-2].casefold()
        candidate = segments[-1]
        if marker in DIRECT_LIST_TYPES:
            if candidate.isdigit():
                path_type = marker
                path_id = candidate
            else:
                combined_match = re.fullmatch(r"([0-9]+)_([0-9]+)", candidate)
                menu_match = re.fullmatch(r"([0-9]+)-([0-9]+)", candidate)
                if combined_match:
                    path_type = marker
                    path_app_id = combined_match.group(1)
                    path_id = combined_match.group(2)
                elif (
                    menu_match
                    and len(segments) >= 4
                    and segments[-4].casefold() in {"view", "detail"}
                    and segments[-3].isdigit()
                ):
                    path_type = marker
                    path_app_id = segments[-3]
                    path_id = menu_match.group(1)
                    path_menu_id = menu_match.group(2)

    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=False)
    normalized_query = {str(key).casefold(): values for key, values in query.items()}
    query_types: List[str] = []
    for key in ("pagetype", "listkind", "viewtype"):
        for item in normalized_query.get(key, []):
            marker = str(item).strip().casefold()
            if marker in DIRECT_LIST_TYPES:
                query_types.append(marker)
    query_type = ""
    if query_types:
        normalized_types = {DIRECT_LIST_TYPES[item][0] for item in query_types}
        if len(normalized_types) != 1:
            raise ResolveError("页面 URL 的列表类型参数互相冲突")
        query_type = query_types[0]

    if path_type and query_type:
        if DIRECT_LIST_TYPES[path_type][0] != DIRECT_LIST_TYPES[query_type][0]:
            raise ResolveError("页面 URL 的路径与 pageType/listKind 类型冲突")
    marker = path_type or query_type
    if not marker:
        raise ResolveError(
            "无法从页面 URL 识别列表类型；需要 list/search 或 viewport/VIEWPORT"
        )

    query_ids: List[str] = []
    for key in ("pageid", "listid"):
        for item in normalized_query.get(key, []):
            text = str(item).strip()
            if text:
                query_ids.append(string_id(text, f"URL {key}"))
    if len(set(query_ids)) > 1:
        raise ResolveError("页面 URL 中的 pageId/listId 互相冲突")
    query_id = query_ids[0] if query_ids else ""
    if path_id and query_id and path_id != query_id:
        raise ResolveError("页面 URL 路径 ID 与 pageId/listId 参数不一致")
    page_id = path_id or query_id
    if not page_id:
        raise ResolveError("页面 URL 缺少可识别的 pageId/listId")

    app_ids: List[str] = []
    if path_app_id:
        app_ids.append(path_app_id)
    for item in normalized_query.get("appid", []):
        text = str(item).strip()
        if text:
            app_ids.append(string_id(text, "URL appId"))
    path_match = re.search(
        r"/(?:sp/)?ebdapp/(?:view|detail)/([0-9]+)(?:/|$)",
        parsed.path,
        re.I,
    )
    if path_match:
        app_ids.append(path_match.group(1))
    if len(set(app_ids)) > 1:
        raise ResolveError("页面 URL 中的 appId 互相冲突")

    menu_ids: List[str] = []
    if path_menu_id:
        menu_ids.append(path_menu_id)
    for key in ("cusmenuid", "menuid"):
        for item in normalized_query.get(key, []):
            text = str(item).strip()
            if text:
                menu_ids.append(string_id(text, f"URL {key}"))
    if len(set(menu_ids)) > 1:
        raise ResolveError("页面 URL 中的 menuId/cusMenuId 互相冲突")

    page_type, list_kind = DIRECT_LIST_TYPES[marker]
    return {
        "origin": confirmed_origin,
        "entryUrl": entry_url,
        "pageId": page_id,
        "pageType": page_type,
        "listKind": list_kind,
        "appId": app_ids[0] if app_ids else "",
        "menuId": menu_ids[0] if menu_ids else "",
    }


def response_message(payload: Any) -> str:
    if not isinstance(payload, Mapping):
        return ""
    values: List[Any] = [payload.get("msg"), payload.get("message")]
    message = payload.get("message")
    if isinstance(message, Mapping):
        values.extend((message.get("msg"), message.get("message")))
    data = payload.get("data")
    if isinstance(data, Mapping):
        datajson = data.get("datajson")
        if isinstance(datajson, Mapping):
            values.extend((datajson.get("message"), datajson.get("msg")))
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()[:500]
    return ""


def unwrap_wea(payload: Any, label: str) -> Any:
    if not isinstance(payload, Mapping):
        raise RuntimeError(f"{label} 响应根节点不是对象")
    code = payload.get("code")
    if code is not None and str(code).casefold() not in SUCCESS_CODES:
        raise RuntimeError(f"{label} 业务失败: {response_message(payload) or code}")
    if payload.get("status") is False or payload.get("fail") is True:
        raise RuntimeError(f"{label} 业务失败: {response_message(payload) or 'status=false'}")
    if "data" not in payload:
        raise RuntimeError(f"{label} 响应缺少 data")
    return payload["data"]


def normalize_data_ids(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split(",") if item.strip()]


def parse_openapi_result(payload: Any, label: str) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise RuntimeError(f"{label} 响应根节点不是对象")
    outer_message = payload.get("message")
    outer_code = outer_message.get("code") if isinstance(outer_message, Mapping) else None
    if outer_code is not None and str(outer_code).casefold() not in SUCCESS_CODES:
        message = response_message(payload) or str(outer_code)
        raise BusinessFailure(message, {"status": False, "message": message})
    data = payload.get("data")
    datajson = data.get("datajson") if isinstance(data, Mapping) else None
    if not isinstance(datajson, Mapping):
        raise RuntimeError(f"{label} 响应缺少 data.datajson")
    status = datajson.get("status") is True
    ids = normalize_data_ids(datajson.get("dataIds"))
    inner_message = str(
        datajson.get("message") or datajson.get("msg") or ""
    ).strip()
    message = (
        (response_message(payload) or "success")
        if status
        else (inner_message or response_message(payload) or "业务状态为 false")
    )
    result = {
        "status": status,
        "message": message,
        "dataIds": ids,
    }
    for source in (data, datajson):
        if isinstance(source, Mapping):
            for key in ("costTime", "cost", "timings"):
                if key in source:
                    result["serverCost"] = source[key]
                    break
    if not status:
        raise BusinessFailure(message, result)
    return result


def labels_for_menu(menu: Mapping[str, Any]) -> List[str]:
    return [
        str(value).strip()
        for value in (menu.get("menuName"), menu.get("refferName"))
        if str(value or "").strip()
    ]


def menu_score(menu: Mapping[str, Any], keywords: Sequence[str]) -> int:
    needles = [item.strip().casefold() for item in keywords if item.strip()]
    labels = [item.casefold() for item in labels_for_menu(menu)]
    if not needles or not labels:
        return -1
    joined = " ".join(needles)
    best = -1
    for label in labels:
        if label == joined or (len(needles) == 1 and label == needles[0]):
            best = max(best, 100000)
        elif all(needle in label for needle in needles):
            extra = max(0, len(label) - sum(len(item) for item in needles))
            best = max(best, 10000 - extra)
        elif any(needle in label for needle in needles):
            best = max(best, 1000 - len(label))
    return best


def candidate_summary(menu: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "menuId": str(menu.get("menuId") or ""),
        "menuName": menu.get("menuName"),
        "refferName": menu.get("refferName"),
        "pageType": str(menu.get("pageType") or ""),
        "pageId": str(menu.get("pageId") or ""),
        "appId": str(menu.get("appId") or ""),
        "menuUrl": menu.get("menuUrl"),
    }


def select_menu(
    payload: Any, keywords: Sequence[str], explicit_menu_id: Optional[str]
) -> Dict[str, Any]:
    candidates = [
        item
        for item in unwrap_wea(payload, "菜单搜索")
        if isinstance(item, Mapping)
        and str(item.get("pageType") or "").upper() in {"SEARCH", "VIEWPORT"}
        and str(item.get("pageId") or "").isdigit()
        and str(item.get("appId") or "").isdigit()
    ]
    if explicit_menu_id:
        matches = [item for item in candidates if str(item.get("menuId")) == explicit_menu_id]
        if len(matches) == 1:
            return dict(matches[0])
        raise ResolveError(
            "没有找到指定 menuId；候选: "
            + json.dumps([candidate_summary(item) for item in candidates], ensure_ascii=False)
        )
    scored = [(menu_score(item, keywords), item) for item in candidates]
    scored = [item for item in scored if item[0] >= 0]
    if not scored:
        raise ResolveError("没有找到合适的表格或数据列表菜单")
    best_score = max(score for score, _ in scored)
    best = [item for score, item in scored if score == best_score]
    if len(best) != 1:
        raise ResolveError(
            "菜单不唯一，请传 --menu-id；候选: "
            + json.dumps([candidate_summary(item) for item in best], ensure_ascii=False)
        )
    return dict(best[0])


class FormRuntime:
    def __init__(
        self,
        client: EbuilderHttpClient,
        *,
        workers: int = 4,
        cache: Optional[RuntimeCache] = None,
    ) -> None:
        self.client = client
        self.workers = max(1, min(int(workers), 8))
        self.cache = cache
        self._context_cache: Dict[str, Dict[str, Any]] = {}
        self._fields_cache: Dict[Tuple[str, str, str, str], Any] = {}
        self._browser_lookup_cache: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}

    def _load_cached_context(self, key: Any) -> Optional[Dict[str, Any]]:
        if self.cache is None:
            return None
        cached = self.cache.get("context", key)
        if not isinstance(cached, Mapping):
            return None
        try:
            return self._validate_context(cached)
        except (RuntimeError, ValueError):
            self.cache.discard("context", key)
            return None

    def _store_context(self, key: Any, context: Mapping[str, Any]) -> None:
        if self.cache is not None:
            self.cache.put(
                "context", key, dict(context), CONTEXT_CACHE_TTL_SECONDS
            )

    def resolve_context(self, args: argparse.Namespace) -> Dict[str, Any]:
        raw_context = read_json_value(
            args.context_json or os.environ.get("EBUILDER_CONTEXT_JSON"),
            label="--context-json",
        )
        if "context" in raw_context and isinstance(raw_context.get("context"), Mapping):
            raw_context = dict(raw_context["context"])
        if raw_context:
            if args.url:
                raise ResolveError("--context-json 与 --url 不能同时使用")
            return self._validate_context(raw_context)

        if args.url:
            if args.menu or args.menu_id or args.obj_id:
                raise ResolveError("--url 不能与 --menu、--menu-id 或 --obj-id 同时使用")
            return self.resolve_url_context(args)

        if args.obj_id:
            requested_prefix = (
                args.api_prefix or os.environ.get("EBUILDER_API_PREFIX") or ""
            )
            persistent_key = {
                "mode": "obj",
                "objId": str(args.obj_id),
                "appId": str(args.app_id or ""),
                "apiPrefix": requested_prefix,
            }
            cached_context = self._load_cached_context(persistent_key)
            if cached_context is not None:
                return cached_context
            context: Dict[str, Any] = {
                "origin": self.client.origin,
                "objId": string_id(args.obj_id, "objId"),
                "appId": string_id(args.app_id, "appId", required=False),
                "apiPrefix": requested_prefix,
                "listId": "",
                "listKind": "",
                "menuUrl": "",
            }
            if not context["apiPrefix"]:
                if not context["appId"]:
                    raise ResolveError("直接使用 objId 时还需提供 --app-id 或 --api-prefix")
                context["apiPrefix"] = self.resolve_deployment(context["appId"])
            context = self._validate_context(context)
            self._store_context(persistent_key, context)
            return context

        keywords = [item.strip() for item in (args.menu or []) if item.strip()]
        if not keywords:
            raise ResolveError("请传 --url、--menu、--context-json，或 --obj-id")
        persistent_key = {
            "mode": "menu",
            "keywords": keywords,
            "menuId": str(args.menu_id or ""),
        }
        cache_key = json.dumps(persistent_key, ensure_ascii=False, sort_keys=True)
        if cache_key in self._context_cache:
            return dict(self._context_cache[cache_key])
        cached_context = self._load_cached_context(persistent_key)
        if cached_context is not None:
            self._context_cache[cache_key] = dict(cached_context)
            return cached_context
        payload = self.client.request_json(
            "POST",
            "/api/ebuilder/form/viewlist/searchPermittedEbMenus",
            json_body=keywords,
            label="menu.search",
        )
        menu = select_menu(payload, keywords, args.menu_id)
        app_id = string_id(menu.get("appId"), "menu.appId")
        menu_page_id = string_id(menu.get("pageId"), "menu.pageId")
        page_type = str(menu.get("pageType") or "").upper()
        api_prefix = self.resolve_deployment(app_id)
        list_id, obj_id = self.resolve_list_target(
            api_prefix, app_id, menu_page_id, page_type
        )
        context = self._validate_context(
            {
                "origin": self.client.origin,
                "appId": app_id,
                "apiPrefix": api_prefix,
                "listId": list_id,
                "hostPageId": menu_page_id if page_type == "VIEWPORT" else "",
                "listKind": "List" if page_type == "SEARCH" else "NList",
                "menuUrl": str(menu.get("menuUrl") or ""),
                "menuId": str(menu.get("menuId") or ""),
                "menuName": menu.get("menuName") or menu.get("refferName") or "",
                "objId": obj_id,
            }
        )
        self._context_cache[cache_key] = dict(context)
        self._store_context(persistent_key, context)
        return context

    def resolve_url_context(self, args: argparse.Namespace) -> Dict[str, Any]:
        target = parse_direct_list_url(args.url, self.client.origin)
        requested_prefix = (
            args.api_prefix or os.environ.get("EBUILDER_API_PREFIX") or ""
        )
        requested_app_id = string_id(args.app_id, "appId", required=False)
        target_app_id = string_id(target.get("appId"), "URL appId", required=False)
        if requested_app_id and target_app_id and requested_app_id != target_app_id:
            raise ResolveError("--app-id 与页面 URL 中的 appId 不一致")
        app_id = requested_app_id or target_app_id
        if requested_prefix:
            requested_prefix = resolve_api_prefix(requested_prefix)
            prefix_app_id = requested_prefix.removeprefix("/api/ebuilder")
            if prefix_app_id:
                if app_id and app_id != prefix_app_id:
                    raise ResolveError("--api-prefix 与页面 URL/--app-id 中的 appId 不一致")
                app_id = prefix_app_id

        persistent_key = {
            "mode": "url",
            "url": target["entryUrl"],
            "appId": app_id,
            "apiPrefix": requested_prefix,
        }
        cached_context = self._load_cached_context(persistent_key)
        if cached_context is not None:
            return cached_context

        page_id = target["pageId"]
        page_type = target["pageType"]
        if app_id:
            api_prefix = requested_prefix or self.resolve_deployment(app_id)
            list_id, obj_id = self.resolve_list_target(
                api_prefix, app_id, page_id, page_type
            )
        elif page_type == "SEARCH":
            payload = self.client.request_json(
                "POST",
                api_path("/api/ebuilder", "/form/list/listInit"),
                json_body={"listId": page_id},
                label="url.listInit.discovery",
            )
            app_id, obj_id = self.parse_list_context(payload, "链接表格上下文")
            list_id = page_id
            api_prefix = requested_prefix or self.resolve_deployment(app_id)
        else:
            payload = self.request_nlist_page(
                "/api/ebuilder",
                page_id,
                label="url.viewPageInfo.discovery",
            )
            app_id, list_id, obj_id = self.parse_nlist_context(
                payload, "链接数据列表上下文"
            )
            api_prefix = requested_prefix or self.resolve_deployment(app_id)

        context = self._validate_context(
            {
                "origin": self.client.origin,
                "appId": app_id,
                "apiPrefix": api_prefix,
                "hostPageId": page_id if page_type == "VIEWPORT" else "",
                "listId": list_id,
                "listKind": target["listKind"],
                "menuUrl": "",
                "entryUrl": target["entryUrl"],
                "menuId": target["menuId"],
                "objId": obj_id,
            }
        )
        self._store_context(persistent_key, context)
        return context

    def _validate_context(self, context: Mapping[str, Any]) -> Dict[str, Any]:
        origin = str(context.get("origin") or self.client.origin).rstrip("/")
        if resolve_origin(origin) != self.client.origin:
            raise ResolveError("context origin 与当前 origin 不一致")
        api_prefix = resolve_api_prefix(str(context.get("apiPrefix") or ""))
        app_id = string_id(context.get("appId"), "appId", required=False)
        if api_prefix != "/api/ebuilder":
            prefix_app_id = api_prefix.removeprefix("/api/ebuilder")
            if app_id and prefix_app_id != app_id:
                raise ResolveError("apiPrefix 中的 appId 与 context.appId 不一致")
        result = dict(context)
        result.update(
            {
                "origin": self.client.origin,
                "appId": app_id,
                "apiPrefix": api_prefix,
                "objId": string_id(context.get("objId"), "objId"),
                "listId": string_id(context.get("listId"), "listId", required=False),
                "hostPageId": string_id(
                    context.get("hostPageId"), "hostPageId", required=False
                ),
                "listKind": str(context.get("listKind") or ""),
                "menuUrl": str(context.get("menuUrl") or ""),
                "entryUrl": str(context.get("entryUrl") or ""),
                "menuId": string_id(
                    context.get("menuId"), "menuId", required=False
                ),
            }
        )
        if result["entryUrl"]:
            result["entryUrl"] = parse_direct_list_url(
                result["entryUrl"], self.client.origin
            )["entryUrl"]
        return result

    def resolve_deployment(self, app_id: str) -> str:
        payload = self.client.request_json(
            "GET",
            "/api/ebuilder/form/app/isIndependentDeploy",
            query={"appId": app_id},
            label="context.deployment",
        )
        independent = unwrap_wea(payload, "独立部署检查")
        if not isinstance(independent, bool):
            raise RuntimeError("独立部署检查 data 不是布尔值")
        return f"/api/ebuilder{app_id}" if independent else "/api/ebuilder"

    def parse_list_context(
        self,
        payload: Any,
        label: str,
        expected_app_id: str = "",
    ) -> Tuple[str, str]:
        data = unwrap_wea(payload, label)
        if not isinstance(data, Mapping):
            raise RuntimeError(f"{label} data 不是对象")
        response_app_id = string_id(
            data.get("appId"),
            f"{label}.appId",
            required=not bool(expected_app_id),
        )
        if expected_app_id and response_app_id and response_app_id != expected_app_id:
            raise ResolveError(f"{label} appId 与已确认 appId 不一致")
        app_id = response_app_id or expected_app_id
        obj_id = string_id(data.get("objid") or data.get("objId"), f"{label}.objId")
        return app_id, obj_id

    def request_nlist_page(
        self,
        api_prefix: str,
        page_id: str,
        *,
        label: str,
    ) -> Any:
        return self.client.request_json(
            "GET",
            api_path(api_prefix, "/form/viewdesigner/viewPageInfo"),
            query={
                "pageId": page_id,
                "terminalType": "PC",
                "entranceType": "RUN",
                "runType": "",
            },
            label=label,
        )

    def parse_nlist_context(
        self,
        payload: Any,
        label: str,
        expected_app_id: str = "",
    ) -> Tuple[str, str, str]:
        unwrap_wea(payload, label)
        try:
            page = unwrap_page(payload)
            _, _, config = select_primary_nlist_component(page)
        except RuntimeError as exc:
            raise ResolveError(f"无法读取数据列表运行配置：{exc}") from None
        response_app_id = string_id(
            page.get("appId") or page.get("appid"),
            f"{label}.page.appId",
            required=not bool(expected_app_id),
        )
        if expected_app_id and response_app_id and response_app_id != expected_app_id:
            raise ResolveError(f"{label} appId 与已确认 appId 不一致")
        app_id = response_app_id or expected_app_id
        list_id = string_id(
            config.get("ebListId"),
            "data.page.comps[1].config.ebListId",
        )
        obj_id = string_id(
            config.get("objId"),
            "data.page.comps[1].config.objId",
        )
        return app_id, list_id, obj_id

    def resolve_list_target(
        self, api_prefix: str, app_id: str, menu_page_id: str, page_type: str
    ) -> Tuple[str, str]:
        if page_type == "SEARCH":
            payload = self.client.request_json(
                "POST",
                api_path(api_prefix, "/form/list/listInit"),
                json_body={"listId": menu_page_id},
                label="context.listInit",
            )
            _, obj_id = self.parse_list_context(
                payload,
                "表格上下文",
                expected_app_id=app_id,
            )
            return menu_page_id, obj_id
        if page_type != "VIEWPORT":
            raise ResolveError(f"不支持的菜单 pageType: {page_type}")
        payload = self.request_nlist_page(
            api_prefix,
            menu_page_id,
            label="context.viewPageInfo",
        )
        _, list_id, obj_id = self.parse_nlist_context(
            payload,
            "数据列表上下文",
            expected_app_id=app_id,
        )
        return list_id, obj_id

    def fields(self, context: Mapping[str, Any]) -> Any:
        key = (
            context["apiPrefix"],
            context["appId"],
            context["objId"],
            "FORM",
        )
        if key in self._fields_cache:
            return self._fields_cache[key]
        persistent_key = {
            "apiPrefix": context["apiPrefix"],
            "appId": context["appId"],
            "objId": context["objId"],
            "sourceType": "FORM",
        }
        if self.cache is not None:
            cached = self.cache.get("fields", persistent_key)
            if cached is not None:
                try:
                    unwrap_wea(cached, "字段定义缓存")
                except RuntimeError:
                    self.cache.discard("fields", persistent_key)
                else:
                    self._fields_cache[key] = cached
                    return cached
        if not context.get("appId"):
            raise ResolveError("字段查询缺少 appId/groupId")
        boundary = "----EBuilderSkillBoundary" + uuid.uuid4().hex
        body = encode_multipart(
            {
                "groupId": context["appId"],
                "sourceId": context["objId"],
                "sourceType": "FORM",
                "detailFieldsGroup": "true",
                "enableMerge": "true",
                "customParam": '{"terminal":""}',
                "params": "[]",
            },
            boundary,
        )
        payload = self.client.request_json(
            "POST",
            api_path(context["apiPrefix"], "/common/ds/fields"),
            body=body,
            content_type=f"multipart/form-data; boundary={boundary}",
            label="fields.fetch",
        )
        unwrap_wea(payload, "字段定义")
        self._fields_cache[key] = payload
        if self.cache is not None:
            self.cache.put(
                "fields", persistent_key, payload, FIELDS_CACHE_TTL_SECONDS
            )
        return payload

    def browser_headers(self) -> Dict[str, str]:
        headers = {
            "langtype": "zh_CN",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
            ),
        }
        token = (os.environ.get("ETEAMSID") or "").strip()
        if token:
            headers["ETEAMSID"] = token
        business_id = (os.environ.get("EBUILDER_BUSINESS_ID") or "").strip()
        second_emp_id = (os.environ.get("EBUILDER_SECOND_EMP_ID") or "").strip()
        if business_id:
            headers["ebbusinessid"] = business_id
        if second_emp_id:
            headers["Secondempid"] = second_emp_id
        return headers

    def resolve_browser_value(
        self, field: Mapping[str, Any], raw_value: Any
    ) -> Tuple[Any, Dict[str, Any]]:
        module, browser_type, route_source = route_from_field(field)
        queries = raw_value if isinstance(raw_value, list) else [raw_value]
        if not queries:
            return "", {"field": field_summary(field), "matches": []}
        selected: List[Dict[str, Any]] = []
        for raw in queries:
            if isinstance(raw, Mapping):
                option_id = str(raw.get("optionId") or raw.get("id") or "").strip()
                option_name = str(raw.get("content") or raw.get("name") or "").strip()
                if option_id:
                    selected.append({"id": option_id, "name": option_name})
                    continue
                query = str(raw.get("query") or "").strip()
            else:
                query = str(raw).strip()
            if not query:
                raise ResolveError(f"浏览字段 {field_summary(field)['title']} 的名称为空")
            multiple = field_is_multiple(field)
            endpoint = f"/api/{module}/common/browser/complete/{browser_type}"
            lookup_key = (
                str(field.get("id") or ""),
                module,
                browser_type,
                query.casefold(),
            )
            match = self._browser_lookup_cache.get(lookup_key)
            if match is None:
                payload = self.client.request_json(
                    "POST",
                    endpoint,
                    json_body=build_browser_payload(query, multiple, field, {}),
                    headers=self.browser_headers(),
                    label=f"browser.{field_summary(field)['dataKey'] or field_summary(field)['id']}",
                )
                matches, _ = normalize_matches(payload, 20)
                exact = [
                    item
                    for item in matches
                    if display_text(item.get("name")).casefold() == query.casefold()
                ]
                matches = exact or matches
                if len(matches) != 1:
                    raise ResolveError(
                        f"浏览字段 {field_summary(field)['title']} 查询结果不唯一: "
                        + json.dumps(matches, ensure_ascii=False)
                    )
                match = dict(matches[0])
                self._browser_lookup_cache[lookup_key] = match
            selected.append(dict(match))
        ids = [str(item.get("id") or "") for item in selected]
        if any(not item for item in ids):
            raise ResolveError(f"浏览字段 {field_summary(field)['title']} 的结果缺少 ID")
        value = ",".join(ids) if field_is_multiple(field) or len(ids) > 1 else ids[0]
        return value, {
            "field": field_summary(field),
            "route": {
                "module": module,
                "type": browser_type,
                "source": route_source,
            },
            "matches": selected,
        }

    def resolve_select_value(
        self, context: Mapping[str, Any], field: Mapping[str, Any], raw_value: Any
    ) -> Tuple[Any, Dict[str, Any]]:
        queries = raw_value if isinstance(raw_value, list) else [raw_value]
        selected: List[Dict[str, Any]] = []
        payload = self.client.request_json(
            "GET",
            api_path(context["apiPrefix"], "/common/ds/options"),
            query={
                "fieldName": str(field.get("id") or ""),
                "objId": context["objId"],
                "sourceType": "FORM",
                "groupId": context["appId"],
                "optionLevel": "1",
            },
            label=f"options.{field_summary(field)['dataKey'] or field_summary(field)['id']}",
        )
        options = unwrap_wea(payload, "字段选项")
        if not isinstance(options, list):
            raise RuntimeError("字段选项 data 不是数组")
        for raw in queries:
            if isinstance(raw, Mapping):
                option_id = str(raw.get("optionId") or raw.get("id") or "").strip()
                option_name = str(raw.get("content") or raw.get("name") or "").strip()
                if option_id:
                    selected.append({"id": option_id, "name": option_name})
                    continue
                query = str(raw.get("query") or "").strip()
            else:
                query = str(raw).strip()
            exact = [
                item
                for item in options
                if isinstance(item, Mapping)
                and str(item.get("name") or "").strip().casefold() == query.casefold()
            ]
            if len(exact) != 1:
                raise ResolveError(
                    f"选择字段 {field_summary(field)['title']} 没有唯一匹配 {query}"
                )
            selected.append(
                {"id": str(exact[0].get("id") or ""), "name": exact[0].get("name")}
            )
        ids = [item["id"] for item in selected]
        value = ",".join(ids) if field_is_multiple(field) or len(ids) > 1 else ids[0]
        return value, {"field": field_summary(field), "matches": selected}

    def build_values(
        self, context: Mapping[str, Any], values: Mapping[str, Any]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        fields_payload = self.fields(context)
        prepared: Dict[str, Any] = {}
        resolutions: List[Dict[str, Any]] = []
        tasks: List[Tuple[str, Any, Any]] = []
        seen_keys: set = set()
        for user_key, raw_value in values.items():
            field = select_field(fields_payload, str(user_key))
            summary = field_summary(field)
            config = field.get("config") if isinstance(field.get("config"), Mapping) else {}
            data_key = display_text(config.get("dataKey")) or display_text(field.get("name"))
            if not data_key or data_key == "id":
                raise ResolveError(f"字段 {user_key} 不能作为可写入字段")
            if data_key in seen_keys:
                raise ResolveError(f"字段 {user_key} 与其他输入映射到相同数据键 {data_key}")
            seen_keys.add(data_key)
            component = (
                display_text(config.get("componentKey"))
                or display_text(field.get("compType"))
                or display_text(field.get("type"))
            ).casefold()
            browser_routable = False
            try:
                route_from_field(field)
                browser_routable = True
            except RuntimeError:
                pass
            if browser_routable or component in BROWSER_COMPONENTS:
                tasks.append((data_key, self.resolve_browser_value, (field, raw_value)))
            elif component in SELECT_COMPONENTS and isinstance(raw_value, (str, list, Mapping)):
                tasks.append(
                    (data_key, self.resolve_select_value, (context, field, raw_value))
                )
            else:
                prepared[data_key] = raw_value

        if tasks:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=min(self.workers, len(tasks)),
                thread_name_prefix="eb-browser",
            ) as executor:
                future_map = {
                    executor.submit(function, *params): data_key
                    for data_key, function, params in tasks
                }
                for future in concurrent.futures.as_completed(future_map):
                    data_key = future_map[future]
                    value, resolution = future.result()
                    prepared[data_key] = value
                    resolutions.append(resolution)
        return prepared, resolutions

    def add(
        self, context: Mapping[str, Any], values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        main_table, resolutions = self.build_values(context, values)
        payload = {
            "datajson": {
                "datas": [{"mainTable": main_table}],
                "header": {"objId": context["objId"]},
                "operationinfo": {
                    "fieldNoFindIgnore": "false",
                    "checkRight": "true",
                    "doAction": "false",
                    "printCost": "true",
                },
            }
        }
        response = self.client.request_json(
            "POST",
            api_path(context["apiPrefix"], "/form/dataset/v2/saveFormData"),
            json_body=payload,
            label="form.add",
        )
        result = parse_openapi_result(response, "新增")
        if not result["dataIds"]:
            raise BusinessFailure("新增响应没有 dataId", result)
        result["resolutions"] = resolutions
        result["records"] = [self.verify_detail(context, item) for item in result["dataIds"]]
        return result

    def update(
        self, context: Mapping[str, Any], data_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        data_id = string_id(data_id, "dataId")
        main_table, resolutions = self.build_values(context, values)
        main_table = {"id": data_id, **main_table}
        payload = {
            "datajson": {
                "datas": [{"mainTable": main_table}],
                "header": {"objId": context["objId"]},
                "operationinfo": {
                    "updateType": "ids",
                    "needAdd": "false",
                    "fieldNoFindIgnore": "false",
                    "checkRight": "true",
                    "doAction": "false",
                    "printCost": "true",
                },
            }
        }
        response = self.client.request_json(
            "POST",
            api_path(context["apiPrefix"], "/form/dataset/v2/updateFormData"),
            json_body=payload,
            label="form.update",
        )
        result = parse_openapi_result(response, "修改")
        if data_id not in result["dataIds"]:
            raise BusinessFailure("修改响应未包含目标 dataId", result)
        result["resolutions"] = resolutions
        result["records"] = [self.verify_detail(context, data_id)]
        return result

    def detail(self, context: Mapping[str, Any], data_id: str) -> Dict[str, Any]:
        data_id = string_id(data_id, "dataId")
        payload = {
            "datajson": {
                "header": {"objId": context["objId"]},
                "mainTable": {"id": data_id},
                "operationinfo": {
                    "isReturnDetail": "y",
                    "fieldNoFindIgnore": "false",
                },
            }
        }
        response = self.client.request_json(
            "POST",
            api_path(context["apiPrefix"], "/form/dataset/v2/getDataById"),
            json_body=payload,
            label="form.getDataById",
        )
        result = parse_openapi_result(response, "详情")
        datajson = response["data"]["datajson"]
        datas = datajson.get("datas")
        if not isinstance(datas, list) or not datas:
            raise BusinessFailure("详情查询没有返回目标数据", result)
        return {
            "dataId": data_id,
            "verified": True,
            "data": datas[0],
            "url": self.data_url(context, data_id),
        }

    def verify_detail(self, context: Mapping[str, Any], data_id: str) -> Dict[str, Any]:
        return self.detail(context, data_id)

    def delete(
        self, context: Mapping[str, Any], data_id: str, confirmation: str
    ) -> Dict[str, Any]:
        data_id = string_id(data_id, "dataId")
        if confirmation.strip() != data_id:
            raise ResolveError("删除前必须用 --confirm-delete 再次传入完全相同的 dataId")
        payload = {
            "datajson": {
                "header": {"objId": context["objId"]},
                "mainTable": {"id": data_id},
                "operationinfo": {
                    "fieldNoFindIgnore": "false",
                    "checkRight": "true",
                    "doAction": "false",
                    "printCost": "true",
                },
            }
        }
        response = self.client.request_json(
            "POST",
            api_path(context["apiPrefix"], "/form/dataset/v2/deleteData"),
            json_body=payload,
            label="form.delete",
        )
        result = parse_openapi_result(response, "删除")
        if data_id not in result["dataIds"]:
            raise BusinessFailure("删除响应未包含目标 dataId", result)
        result["records"] = [
            {
                "dataId": data_id,
                "url": self.data_url(context, data_id, deleted=True),
            }
        ]
        return result

    def data_url(
        self, context: Mapping[str, Any], data_id: str, *, deleted: bool = False
    ) -> str:
        url = (
            f"{self.client.origin}/sp/ebdfpage/card/0/"
            f"{context['objId']}/{data_id}"
        )
        return url + "?fromRecycle=1" if deleted else url

    def list_url(self, context: Mapping[str, Any]) -> str:
        entry_url = str(context.get("entryUrl") or "").strip()
        if entry_url:
            return parse_direct_list_url(entry_url, self.client.origin)["entryUrl"]
        menu_url = str(context.get("menuUrl") or "").strip()
        if menu_url:
            parsed = urllib.parse.urlsplit(menu_url)
            if parsed.scheme or parsed.netloc:
                target_origin = resolve_origin(
                    urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
                )
                if target_origin == self.client.origin:
                    return menu_url
            elif menu_url.startswith("/") and not menu_url.startswith("//"):
                return self.client.origin + menu_url
        if context.get("listId") and context.get("listKind") == "List":
            return f"{self.client.origin}/sp/ebdfpage/list/{context['listId']}"
        if context.get("listId") and context.get("listKind") == "NList":
            return f"{self.client.origin}/sp/ebdfpage/viewport/{context['listId']}"
        return ""


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--origin", help="E10 origin；默认读取 EBUILDER_ORIGIN")
    common.add_argument("--timeout", type=float, default=30.0, help="单次请求超时秒数")
    common.add_argument("--api-prefix", help="已确认的 /api/ebuilder 前缀")
    common.add_argument("--app-id", help="应用 ID")
    common.add_argument("--obj-id", help="表单对象 ID")
    common.add_argument(
        "--url",
        help="E10 列表页面 URL；识别 list/search 为表格、viewport/VIEWPORT 为数据列表",
    )
    common.add_argument(
        "--context-json",
        help="复用 resolve 输出的 context；支持 JSON、@文件或环境变量 EBUILDER_CONTEXT_JSON",
    )
    common.add_argument(
        "--menu",
        action="append",
        help="菜单业务关键词，可重复传入；未提供明确 context 时使用",
    )
    common.add_argument("--menu-id", help="菜单重名时指定 menuId")
    common.add_argument(
        "--workers", type=int, default=4, help="浏览字段并行查询数，默认 4，最大 8"
    )
    common.add_argument(
        "--refresh",
        action="store_true",
        help="忽略短期上下文和字段缓存，成功后写入最新缓存",
    )
    common.add_argument(
        "--no-cache",
        action="store_true",
        help="本次操作完全禁用跨进程短期缓存",
    )
    common.add_argument(
        "--cache-dir",
        help="短期缓存目录；默认使用系统临时目录，也可读取 EBUILDER_CACHE_DIR",
    )

    parser = argparse.ArgumentParser(description="统一解析并操作 eBuilder 表单数据")
    subparsers = parser.add_subparsers(dest="operation", required=True)
    subparsers.add_parser("resolve", parents=[common], help="解析菜单和表单上下文")
    subparsers.add_parser("fields", parents=[common], help="查询并汇总字段定义")

    add_parser = subparsers.add_parser("add", parents=[common], help="新增并按 ID 回查")
    add_parser.add_argument(
        "--values-json", required=True, help="字段显示名到值的 JSON；支持 @文件或 -"
    )

    update_parser = subparsers.add_parser(
        "update", parents=[common], help="按 dataId 修改并回查"
    )
    update_parser.add_argument("--data-id", required=True)
    update_parser.add_argument("--values-json", required=True)

    detail_parser = subparsers.add_parser("detail", parents=[common], help="按 dataId 查询详情")
    detail_parser.add_argument("--data-id", required=True)

    delete_parser = subparsers.add_parser("delete", parents=[common], help="按 dataId 删除")
    delete_parser.add_argument("--data-id", required=True)
    delete_parser.add_argument(
        "--confirm-delete",
        required=True,
        help="必须再次传入完全相同的 dataId，防止误删",
    )
    return parser


def summarize_fields(payload: Any) -> List[Dict[str, Any]]:
    data = unwrap_wea(payload, "字段定义")
    summaries: List[Dict[str, Any]] = []
    for group in data if isinstance(data, list) else []:
        if not isinstance(group, Mapping):
            continue
        for field in group.get("fields") if isinstance(group.get("fields"), list) else []:
            if isinstance(field, Mapping):
                summaries.append(field_summary(field))
    return summaries


def main() -> int:
    configure_utf8_output()
    args = build_parser().parse_args()
    recorder = PerformanceRecorder()
    context: Dict[str, Any] = {}
    result: Dict[str, Any] = {}
    origin_value = args.origin or os.environ.get("EBUILDER_ORIGIN")
    if not origin_value and args.url:
        origin_value = direct_url_origin(args.url)
    if not origin_value:
        context_value = read_json_value(
            args.context_json or os.environ.get("EBUILDER_CONTEXT_JSON"),
            label="--context-json",
        )
        if "context" in context_value and isinstance(
            context_value.get("context"), Mapping
        ):
            context_value = context_value["context"]
        origin_value = context_value.get("origin") if context_value else None
    origin = resolve_origin(origin_value)
    client = EbuilderHttpClient(origin, timeout=args.timeout)
    cache = RuntimeCache(
        origin,
        enabled=not args.no_cache,
        refresh=args.refresh,
        directory=args.cache_dir,
    )
    runtime = FormRuntime(client, workers=args.workers, cache=cache)
    exit_code = 0
    output: Dict[str, Any]
    try:
        with client:
            with recorder.stage("context.resolve"):
                context = runtime.resolve_context(args)
            if args.operation == "resolve":
                result = {"listUrl": runtime.list_url(context)}
            elif args.operation == "fields":
                with recorder.stage("fields.fetch"):
                    fields = runtime.fields(context)
                result = {"fields": summarize_fields(fields), "cacheEntries": 1}
            elif args.operation == "detail":
                with recorder.stage("detail.getDataById"):
                    result = runtime.detail(context, args.data_id)
            elif args.operation == "add":
                values = read_json_value(
                    args.values_json,
                    label="--values-json",
                    expected_type=dict,
                    required=True,
                )
                with recorder.stage("form.add-and-verify"):
                    result = runtime.add(context, values)
            elif args.operation == "update":
                values = read_json_value(
                    args.values_json,
                    label="--values-json",
                    expected_type=dict,
                    required=True,
                )
                with recorder.stage("form.update-and-verify"):
                    result = runtime.update(context, args.data_id, values)
            elif args.operation == "delete":
                with recorder.stage("form.delete"):
                    result = runtime.delete(
                        context, args.data_id, args.confirm_delete
                    )
            else:
                raise ResolveError(f"未知操作: {args.operation}")
        output = {
            "status": "success",
            "operation": args.operation,
            "context": context,
            "result": result,
            "cache": cache.summary(),
            "performance": recorder.output(client),
        }
    except BusinessFailure as exc:
        exit_code = 3
        output = {
            "status": "failed",
            "errorType": "business",
            "operation": args.operation,
            "message": str(exc),
            "context": context,
            "result": exc.result,
            "cache": cache.summary(),
            "performance": recorder.output(client),
        }
    except ResolveError as exc:
        exit_code = 2
        output = {
            "status": "blocked",
            "errorType": "resolution",
            "operation": args.operation,
            "message": str(exc),
            "context": context,
            "cache": cache.summary(),
            "performance": recorder.output(client),
        }
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        exit_code = 1
        output = {
            "status": "failed",
            "errorType": "runtime",
            "operation": args.operation,
            "message": str(exc),
            "context": context,
            "cache": cache.summary(),
            "performance": recorder.output(client),
        }
    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
