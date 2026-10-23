# -*- coding: utf-8 -*-
"""
report_api_client.py
封装报表保存接口：鉴权、gzip+base64 压缩、新建/更新报表的 multipart/form-data 提交。

两段式创建链路（平台真实流程）：
  ① POST /api/bs/edc/report/baseInfo        新建报表外壳 -> data = reportId
  ② POST /api/bs/edc/report/saveReportDevInfo  携带 reportId 上传布局 workbook
  ③ GET  /api/bs/edc/report/getReportDevInfo?reportId=xxx  拉取线上报表详情做验证

约束遵循：
  1. 禁止直接用 saveReportDevInfo 新建报表，必须先走 baseInfo 拿 reportId
  2. 必须使用表单提交（multipart/form-data），禁止 JSON Body 请求
  3. 压缩顺序：原始 JSON -> gzip -> base64（不可颠倒）
  4. 请求头完整对齐浏览器 curl（origin / referer / timezoneoffset 等）
"""
import base64
import gzip
import json
import re
import ssl
import time
import uuid
import datetime
import http.client
import urllib.parse

from weaver_auth_headers import build_auth_headers
from json_snowflake import parse_json_snowflake_safe, extract_id_from_raw, stringify_id

# shareBrowser 对象类型 → API 字段（见 references/report-permission-guide.md §三）
SHARE_TYPE_META = {
    "resource": {"obj_type": "resource", "span": "人员", "entity": "resource", "target_type": 1, "value_key": "obj_id"},
    "user": {"obj_type": "resource", "span": "人员", "entity": "resource", "target_type": 1, "value_key": "obj_id"},
    "department": {"obj_type": "department", "span": "部门", "entity": "dept", "target_type": 2, "value_key": "obj_id_department"},
    "subcompany": {"obj_type": "subcompany", "span": "分部", "entity": "subcompany", "target_type": 4, "value_key": "obj_id_subcompany"},
    "role": {"obj_type": "role", "span": "角色", "entity": "role", "target_type": 10, "value_key": "obj_id_role"},
    "group": {"obj_type": "channel", "span": "群组", "entity": "channel", "target_type": 14, "value_key": "obj_id_channel"},
    "channel": {"obj_type": "channel", "span": "群组", "entity": "channel", "target_type": 14, "value_key": "obj_id_channel"},
    "position": {"obj_type": "position", "span": "岗位", "entity": "position", "target_type": 6, "value_key": "obj_id_position"},
    "external": {"obj_type": "external", "span": "外部联系人", "entity": "external", "target_type": 7, "value_key": "obj_id_external"},
    "all": {"obj_type": "all", "span": "所有人", "entity": "all", "target_type": 11, "target_id": 0, "value_key": None},
    "allExternal": {"obj_type": "allExternal", "span": "所有外部人", "entity": "allExternal", "target_type": 12, "target_id": 0, "value_key": None},
}

# 日志留痕：敏感头脱敏 + 超长表单值截断阈值
_SENSITIVE_HEADERS = {"cookie", "eteamsid", "ebbusinessid"}
_MAX_FIELD_LEN = 160


def _now_iso():
    """本地时区 ISO8601 时间戳（含毫秒与时区偏移），用于接口调用日志。"""
    return datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")


def _mask(value: str) -> str:
    """敏感值脱敏：保留首尾各 4 位，中间以长度占位。"""
    s = "" if value is None else str(value)
    if len(s) <= 10:
        return "***"
    return s[:4] + "***(len=" + str(len(s)) + ")***" + s[-4:]


def _safe_headers(headers: dict) -> dict:
    return {k: (_mask(v) if k.lower() in _SENSITIVE_HEADERS else v)
            for k, v in (headers or {}).items()}


def _safe_fields(fields) -> list:
    """表单参数留痕：超长值（如 workbook base64）只记录长度与首尾摘要。"""
    out = []
    for k, v in (fields or []):
        s = "" if v is None else str(v)
        if len(s) > _MAX_FIELD_LEN:
            out.append({"name": k, "length": len(s), "omitted": True,
                        "preview": s[:60] + " ... " + s[-20:]})
        else:
            out.append({"name": k, "value": s, "length": len(s)})
    return out


class ReportApiClient:
    def __init__(self, host: str, eteamsid: str, ebbusinessid: str, cookie_eteamsid: str,
                 group_id: str, app_id: str, agent_type: str = "WorkBuddy"):
        self.host = host
        self.eteamsid = eteamsid
        self.ebbusinessid = ebbusinessid
        # cookies.raw 完整原始串（来自 e10-login）；禁止在客户端内重拼 Cookie
        self.cookie = cookie_eteamsid
        self.agent_type = agent_type or "WorkBuddy"
        self.group_id = group_id
        self.app_id = app_id
        self.path = "/api/bs/edc/report/saveReportDevInfo"
        self.base_info_path = "/api/bs/edc/report/baseInfo"
        self.detail_path = "/api/bs/edc/report/getReportDevInfo"
        self.timeout = 30
        self.last_raw = ""
        self.last_status = None
        # 逐次请求留痕，便于写入 EBU_接口返回.json
        self.trace = []

    # ---------------- 通用底层能力 ----------------
    def _browser_headers(self, referer_suffix: str = "") -> dict:
        """约束 4：对齐浏览器标准头；Cookie/eteamsid/User-Agent 三项来自 e10-login。"""
        return build_auth_headers(
            host=self.host,
            eteamsid=self.eteamsid,
            cookie=self.cookie,
            agent_type=self.agent_type,
            ebbusinessid=self.ebbusinessid,
            referer_suffix=str(referer_suffix or ""),
        )

    @staticmethod
    def _build_multipart(fields):
        """构造 multipart/form-data 报文体，返回 (body_bytes, boundary)。"""
        boundary = "----PythonFormBoundary" + uuid.uuid4().hex[:12]
        parts = []
        for k, v in fields:
            parts.append('--' + boundary + '\r\nContent-Disposition: form-data; name="'
                         + k + '"\r\n\r\n' + ("" if v is None else str(v)) + '\r\n')
        parts.append("--" + boundary + "--\r\n")
        return "".join(parts).encode("utf-8"), boundary

    def _send(self, method, path, body, headers, tag, req_fields=None, query=None):
        """发送请求并写入完整调用留痕（请求参数 + 响应结果 + 时间戳 + 耗时）。"""
        seq = len(self.trace) + 1
        started = _now_iso()
        t0 = time.perf_counter()
        entry = {
            "seq": seq,
            "step": tag,
            "request": {
                "method": method,
                "url": "https://" + self.host + path,
                "path": path,
                "query": query or {},
                "headers": _safe_headers(headers),
                "content_type": (headers or {}).get("Content-Type", ""),
                "body_bytes": len(body) if body else 0,
                "form_fields": _safe_fields(req_fields),
            },
            "timestamps": {"request_at": started},
        }
        try:
            conn = http.client.HTTPSConnection(self.host, timeout=self.timeout,
                                               context=ssl.create_default_context())
            conn.request(method, path, body=body, headers=headers)
            resp = conn.getresponse()
            self.last_status = resp.status
            text = resp.read().decode("utf-8", errors="replace")
            self.last_raw = text
        except Exception as exc:
            entry["timestamps"]["response_at"] = _now_iso()
            entry["timestamps"]["duration_ms"] = round((time.perf_counter() - t0) * 1000, 2)
            entry["error"] = repr(exc)
            entry["http_status"] = None
            self.trace.append(entry)
            raise
        ended = _now_iso()
        entry["timestamps"]["response_at"] = ended
        entry["timestamps"]["duration_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        entry["http_status"] = resp.status
        entry["response_headers"] = dict(resp.getheaders())
        entry["response"] = text[:4000]
        try:
            entry["response_json"] = json.loads(text)
        except Exception:
            entry["response_json"] = None
        self.trace.append(entry)
        return resp.status, text

    # ---------------- ① 新建报表外壳 ----------------
    def create_report_shell(self, name, name_label_id="-1", group_id="0",
                            report_model="0", show_order="1", permission="[]",
                            system_type="1", quickly_param=None):
        """调用 baseInfo 新建报表外壳，返回 data 字段中的 reportId。

        三种模式（与列表页「新建报表」三卡片对齐，见 report-create-modes-guide.md）：
          · 从空白创建：report_model="0"，quickly_param=None
          · 模版创建：report_model=<模板报表ID>
          · 快速构建-列表式：quickly_param=QuicklyParam dict/JSON 串（report_model 保持 "0"）

        group_id 默认 **0**（未指定分组 = 默认分组，会出现在页面「全部」里）。
        禁止入库 group_id=-1：-1 是 list 接口「查全部」哨兵，写入库会与哨兵冲突。
        name / nameLabelId 禁止含 \\r\\n（脏 nameLabelId 会导致列表 500）。
        """
        if report_model in (None, ""):
            report_model = "0"
        fields = [
            ("name", name),
            ("nameLabelId", name_label_id),
            ("reportModel", str(report_model)),
            ("showOrder", show_order),
            ("permission", permission),
            ("appId", self.app_id),
            ("groupId", group_id),
            ("systemType", system_type),
            ("id", "0"),
        ]
        if quickly_param is not None and str(quickly_param).strip() != "":
            qp = quickly_param if isinstance(quickly_param, str) else json.dumps(
                quickly_param, ensure_ascii=False)
            fields.append(("quicklyParam", qp))
        body, boundary = self._build_multipart(fields)
        headers = self._browser_headers()
        headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
        status, text = self._send("POST", self.base_info_path, body, headers, "baseInfo",
                                  req_fields=fields)
        try:
            obj = json.loads(text)
        except Exception:
            obj = {}
        data = obj.get("data")
        if isinstance(data, dict):
            raw = str(data.get("reportId") or data.get("id") or "")
        else:
            raw = "" if data is None else str(data)
        # data 也可能承载业务错误码（如 SAME_NAME 表示同名报表已存在），
        # 必须校验其形态确为主键，避免把错误码当 reportId 继续调用。
        if re.fullmatch(r"\d{6,}", raw) or re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F\-]{20,}", raw):
            rid = raw
        else:
            rid = None
            obj["_biz_error"] = raw or "未返回 reportId"
        return rid, obj

    def get_report_models(self):
        """模版创建：GET /api/bs/edc/report/getReportModels"""
        return self._get_json("/api/bs/edc/report/getReportModels", "getReportModels",
                              {}, referer_suffix="")

    def create_from_model(self, name, model_id, **kwargs):
        """模版创建：reportModel=模板 ID（>0）。"""
        mid = str(model_id).strip()
        if not mid or mid == "0":
            raise ValueError("model_id must be a platform template report id (>0)")
        return self.create_report_shell(name, report_model=mid, quickly_param=None, **kwargs)

    def create_from_quickly_param(self, name, quickly_param, **kwargs):
        """快速构建-列表式：传 QuicklyParam（dict 或 JSON 串）。"""
        if quickly_param is None or (isinstance(quickly_param, str) and not quickly_param.strip()):
            raise ValueError("quickly_param required for quick-list create")
        return self.create_report_shell(
            name, report_model="0", quickly_param=quickly_param, **kwargs
        )

    # ---------------- ② 上传布局 workbook ----------------
    def save_report_layout(self, report_id, name, name_label_id, workbook_b64,
                           group_id=None, design_key=None):
        """携带 reportId 调用 saveReportDevInfo 上传布局。

        designKey 语义（实测）：服务端以其做乐观锁校验，提交值与线上不一致会返回
        「您当前的数据不是最新的，请重新打开获取最新的数据！」且布局不落库。
        因此 design_key=None 时自动从 getReportDevInfo 取线上当前值，取不到才回退全新 UUID。
        """
        if design_key is None:
            try:
                cur = self.get_report_detail(report_id)
                design_key = (cur.get("data") or {}).get("designKey")
            except Exception:
                design_key = None
        fields = [
            ("groupId", self.group_id if group_id is None else group_id),
            ("appId", self.app_id),
            ("reportId", report_id),
            ("name", name),
            ("nameLabelId", name_label_id),
            ("designKey", design_key or str(uuid.uuid4())),
            ("workbook", workbook_b64),
        ]
        body, boundary = self._build_multipart(fields)
        headers = self._browser_headers(report_id)
        headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
        status, text = self._send("POST", self.path, body, headers, "saveReportDevInfo",
                                  req_fields=fields)
        try:
            obj = json.loads(text)
        except Exception:
            obj = {"raw": text}
        # 注意：乐观锁失败时服务端仍返回 code=200，仅把提示写在 data 里，必须额外识别
        stale = "不是最新" in str(obj.get("data", ""))
        ok = (str(obj.get("code", "")) in ("0", "200") or obj.get("success") is True) and not stale
        obj["_stale_rejected"] = stale
        return ok, obj

    # ---------------- ③ 拉取线上报表详情 ----------------
    def get_report_detail(self, report_id):
        """GET getReportDevInfo?reportId=xxx，返回线上完整配置。"""
        qs = urllib.parse.urlencode({"reportId": report_id})
        headers = self._browser_headers(report_id)
        status, text = self._send("GET", self.detail_path + "?" + qs, None, headers,
                                  "getReportDevInfo", query={"reportId": str(report_id)})
        return self._parse_json(text)

    # ---------------- 设计区保护（safe-partial-save） ----------------

    @staticmethod
    def count_workbook_cells(workbook_props: dict) -> int:
        """统计 workbookProps.sheets 内 dataTable 单元格数。"""
        if not workbook_props:
            return 0
        total = 0
        for sheet in (workbook_props.get("sheets") or {}).values():
            dt = ((sheet or {}).get("data") or {}).get("dataTable") or {}
            for row in dt.values():
                total += len(row or {})
        return total

    @staticmethod
    def assert_layout_not_empty(dev_data: dict, allow_empty: bool = False) -> dict:
        """保存前断言：fields 与 workbook 不得同时为空（见 safe-partial-save-guide.md）。"""
        fields = dev_data.get("fields") or []
        cells = ReportApiClient.count_workbook_cells(dev_data.get("workbookProps") or {})
        n = len(fields)
        if not allow_empty and n == 0 and cells == 0:
            raise ValueError(
                "Layout guard: fields and workbook cells are both empty — aborting saveReportDevInfo"
            )
        return {"fields": n, "cells": cells}

    @staticmethod
    def verify_layout_preserved(before: dict, after_data: dict, min_fields=None) -> dict:
        after_n = len(after_data.get("fields") or [])
        floor = min_fields if min_fields is not None else before.get("fields", 0)
        if after_n < floor:
            raise ValueError(
                "Layout guard: fields dropped from %s to %s — run rollbackReport"
                % (floor, after_n)
            )
        return {"fields": after_n, "ok": True}

    def save_report_layout_safe(self, report_id, name, name_label_id, workbook_json: dict,
                                group_id=None, design_key=None, min_fields_before=None):
        """saveReportDevInfo + 保存前后 fields 数量校验。"""
        detail = self.get_report_detail(report_id)
        dev = detail.get("data") or {}
        before = self.assert_layout_not_empty(dev)
        ok, obj = self.save_report_layout(
            report_id, name, name_label_id, self._compress(workbook_json),
            group_id=group_id, design_key=design_key,
        )
        if not ok:
            return ok, obj, before
        after = self.get_report_detail(report_id)
        self.verify_layout_preserved(before, after.get("data") or {}, min_fields=min_fields_before)
        return ok, obj, before

    # ---------------- 报表列表页 · 生命周期管理 ----------------

    @staticmethod
    def _parse_json(text):
        try:
            return parse_json_snowflake_safe(text)
        except Exception:
            return {"raw": text}

    def _get_json(self, path, tag, query=None, referer_suffix=""):
        qs = ("?" + urllib.parse.urlencode(query)) if query else ""
        headers = self._browser_headers(referer_suffix)
        _, text = self._send("GET", path + qs, None, headers, tag, query=query or {})
        return self._parse_json(text)

    def _post_json(self, path, payload, tag, referer_suffix=""):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = self._browser_headers(referer_suffix)
        headers["Content-Type"] = "application/json;charset=UTF-8"
        _, text = self._send("POST", path, body, headers, tag)
        return self._parse_json(text)

    def _post_form(self, path, form_data, tag, referer_suffix=""):
        body = urllib.parse.urlencode(form_data).encode("utf-8")
        headers = self._browser_headers(referer_suffix)
        headers["Content-Type"] = "application/x-www-form-urlencoded;charset=UTF-8"
        _, text = self._send("POST", path, body, headers, tag, req_fields=list(form_data.items()))
        return self._parse_json(text)

    def _post_multipart(self, path, fields, tag, referer_suffix="", ebbusinessid=None):
        body, boundary = self._build_multipart(fields)
        headers = self._browser_headers(referer_suffix)
        headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
        if ebbusinessid is not None:
            headers["ebbusinessid"] = str(ebbusinessid)
        _, text = self._send("POST", path, body, headers, tag, req_fields=fields)
        return self._parse_json(text)

    def get_report_list(self, app_id=None, group_id="-1", obj_id="-1"):
        """报表列表页：GET /api/bs/edc/report/list"""
        aid = str(app_id or self.app_id)
        return self._get_json("/api/bs/edc/report/list", "reportList", {
            "appid": aid, "groupid": str(group_id), "objId": str(obj_id),
        }, referer_suffix="")

    def get_app_right(self, app_id=None):
        """GET /api/bs/edc/report/appRight"""
        aid = str(app_id or self.app_id)
        return self._get_json("/api/bs/edc/report/appRight", "appRight",
                              {"appId": aid}, referer_suffix="")

    def get_app_report_right(self, report_id, app_id=None):
        """单报表操作权限：GET /api/bs/edc/report/appReportRight"""
        aid = str(app_id or self.app_id)
        return self._get_json("/api/bs/edc/report/appReportRight", "appReportRight", {
            "appId": aid, "reportId": str(report_id),
        }, referer_suffix=str(report_id))

    def get_report_base_info(self, report_id, version="1.0.0", use_tag="backend"):
        """编辑前读基础信息：GET /api/bs/edc/report/baseInfo"""
        return self._get_json("/api/bs/edc/report/baseInfo", "getReportBaseInfo", {
            "id": str(report_id), "version": version, "useTag": use_tag,
        }, referer_suffix=str(report_id))

    def save_report_base_info(self, report_id, name, group_id=None, show_order="1",
                              permission="[]", name_label_id="-1"):
        """编辑报表元数据：POST /api/bs/edc/report/baseInfo（带 id）"""
        fields = [
            ("appId", self.app_id),
            ("id", str(report_id)),
            ("name", name),
            ("nameLabelId", name_label_id),
            ("groupId", str(group_id if group_id is not None else self.group_id)),
            ("showOrder", str(show_order)),
            ("permission", permission),
            ("reportModel", "0"),
        ]
        return self._post_multipart("/api/bs/edc/report/baseInfo", fields,
                                   "saveReportBaseInfo", referer_suffix=str(report_id))

    def get_permission(self, report_id):
        """GET /api/bs/edc/report/permission?id="""
        return self._get_json("/api/bs/edc/report/permission", "getPermission",
                              {"id": str(report_id)}, referer_suffix=str(report_id))

    def save_permission_simple(self, report_id, permission_json):
        """POST /api/bs/edc/report/permission（multipart：id + permission JSON 串）"""
        perm = permission_json if isinstance(permission_json, str) else json.dumps(
            permission_json, ensure_ascii=False)
        fields = [("id", str(report_id)), ("permission", perm)]
        return self._post_multipart("/api/bs/edc/report/permission", fields,
                                   "savePermission", referer_suffix=str(report_id))

    def list_permission_table(self, report_id, permission_id, app_id=None,
                              current=1, page_size=100, permission_type=1):
        """报表权限弹窗列表：POST /api/bs/edc/report/permission/table/list/new"""
        payload = {
            "permissionId": str(permission_id),
            "id": str(report_id),
            "current": current,
            "pageSize": page_size,
            "permissionType": permission_type,
            "params": {"appId": str(app_id or self.app_id)},
        }
        return self._post_json("/api/bs/edc/report/permission/table/list/new",
                               payload, "permissionTableList", referer_suffix=str(report_id))

    @staticmethod
    def build_share_entry(obj_type, target_id="", name="", report_id="", permission_type=1, **extra):
        """构建 savePermissions 用的 shareBrowser 行（通用 Tab）。

        obj_type: resource/user/department/subcompany/role/group/position/external/all/allExternal
        permission_type: 1=使用范围(viewRight), -1=禁用范围(disableRight)
        """
        meta = SHARE_TYPE_META.get(obj_type)
        if not meta:
            raise ValueError("unknown obj_type: %s" % obj_type)
        tid = meta.get("target_id", target_id)
        label = name or meta["span"]
        entry = {
            "sourceId": str(report_id),
            "permissionId": "report_view",
            "permissionType": permission_type,
            "targetType": meta["target_type"],
            "targetId": tid,
            "sourceType": 1,
            "objType": meta["obj_type"],
            "objTypeSpan": meta["span"],
            "_entityType": meta["entity"],
            "seclevel": {"min": -999, "max": 999},
            "shareKey": "tmp_%s_%s_%s" % (meta["obj_type"], tid, uuid.uuid4().hex[:6]),
        }
        if meta["obj_type"] == "all":
            entry.update({
                "obj_id_all": [{"content": "所有人", "icon": "Icon-all02", "id": "0"}],
                "obj_id_span": "所有人", "objIdList": ["所有人"],
                "content": "所有人", "name": "所有人", "title": "所有人", "icon": "Icon-all02",
            })
        elif meta["obj_type"] == "allExternal":
            entry.update({
                "obj_id_span": "所有外部人", "objIdList": ["所有外部人"],
                "content": "所有外部人", "name": "所有外部人", "title": "所有外部人",
            })
        elif meta["value_key"]:
            obj = {"id": str(target_id), "name": label, "content": label, "title": label}
            entry[meta["value_key"]] = [obj]
            entry.update({
                "obj_id_span": label, "objIdList": [label],
                "content": label, "name": label, "title": label,
            })
        entry.update(extra)
        return entry

    def list_matrix_rights(self, report_id, rights_type="1"):
        """矩阵权限列表：POST /api/bs/edc/report/permission/matrix/list"""
        payload = {"target": str(report_id), "type": str(rights_type)}
        return self._post_json("/api/bs/edc/report/permission/matrix/list",
                               payload, "matrixRightList", referer_suffix=str(report_id))

    # ---------------- 设计器 · 数据集侧栏（见 dataset-sidebar-ops-guide.md）----------------

    def rename_dataset(self, dataset_id, name, name_label_id="-1"):
        """自定义名称：GET /api/bs/edc/dataset/rename"""
        return self._get_json("/api/bs/edc/dataset/rename", "datasetRename", {
            "datasetId": str(dataset_id),
            "name": name,
            "nameLabelId": str(name_label_id),
        }, referer_suffix="")

    def aggregation_get(self, dataset_id):
        """侧栏数据聚合读：GET /api/bs/edc/dataset/aggregationGet"""
        return self._get_json("/api/bs/edc/dataset/aggregationGet", "aggregationGet", {
            "datasetId": str(dataset_id),
        }, referer_suffix="")

    def aggregation_save(self, dataset_id, aggre_data):
        """侧栏数据聚合写：POST aggregationSave（aggre_data=list 或 JSON 串）。≠ sheetConfig.dataPreAgg"""
        payload = aggre_data if isinstance(aggre_data, str) else json.dumps(
            aggre_data, ensure_ascii=False)
        return self._post_multipart("/api/bs/edc/dataset/aggregationSave", [
            ("datasetId", str(dataset_id)),
            ("aggreData", payload),
        ], "aggregationSave")

    def sort_get(self, dataset_id):
        """侧栏数据排序读：GET /api/bs/edc/dataset/sortGet"""
        return self._get_json("/api/bs/edc/dataset/sortGet", "sortGet", {
            "datasetId": str(dataset_id),
        }, referer_suffix="")

    def sort_save(self, dataset_id, sort_data):
        """侧栏数据排序写：POST sortSave"""
        payload = sort_data if isinstance(sort_data, str) else json.dumps(
            sort_data, ensure_ascii=False)
        return self._post_multipart("/api/bs/edc/dataset/sortSave", [
            ("datasetId", str(dataset_id)),
            ("sortData", payload),
        ], "sortSave")

    def replace_dataset(self, body):
        """替换数据集：POST /api/bs/edc/dataset/replaceDataset（JSON）。返回 data=新 datasetId"""
        return self._post_json("/api/bs/edc/dataset/replaceDataset", body, "replaceDataset")

    def check_dataset_used(self, report_id, dataset_id):
        """移除前引用检查：GET /api/bs/edc/dataset/checkDataSetUsed"""
        return self._get_json("/api/bs/edc/dataset/checkDataSetUsed", "checkDataSetUsed", {
            "reportId": str(report_id),
            "datasetId": str(dataset_id),
        }, referer_suffix=str(report_id))

    def del_dataset(self, report_id, dataset_id):
        """移除数据集：POST /api/bs/edc/report/delDataset。

        注意：表单字段名 sourceIds 实为 datasetId（历史命名）。
        """
        return self._post_multipart("/api/bs/edc/report/delDataset", [
            ("reportId", str(report_id)),
            ("sourceIds", str(dataset_id)),
        ], "delDataset", referer_suffix=str(report_id))

    def get_dataset_preview(self, dataset_id, is_front=True):
        """数据预览：GET /api/bs/edc/dataset/getPreviewData"""
        return self._get_json("/api/bs/edc/dataset/getPreviewData", "getPreviewData", {
            "dataSetId": str(dataset_id),
            "isFront": "true" if is_front else "false",
        }, referer_suffix="")

    def save_matrix_rights(self, matrix_rows):
        """矩阵权限保存（含禁用矩阵 rightsType=-1）：POST .../permission/matrix/save"""
        return self._post_json("/api/bs/edc/report/permission/matrix/save",
                               matrix_rows, "matrixRightSave")

    def delete_use_matrix_by_replace(self, report_id, remain_rows, view_right=None, disable_right=None):
        """删除使用范围矩阵：savePermissions 全量替换 viewMatrixRight（可传 [] 清空）。"""
        info = {
            "viewRight": view_right if view_right is not None else [],
            "disableRight": disable_right if disable_right is not None else [],
            "viewMatrixRight": remain_rows if remain_rows is not None else [],
        }
        return self.save_permissions(report_id, info)

    def soft_delete_matrix_row(self, row):
        """禁用矩阵等：matrix/save 且 deleteType=1。"""
        payload = dict(row)
        payload["deleteType"] = 1
        return self.save_matrix_rights([payload])

    def list_report_groups(self, app_id=None, group_type=0):
        """分组设置列表：GET /api/bs/edc/report/group/list"""
        aid = str(app_id or self.app_id)
        return self._get_json("/api/bs/edc/report/group/list", "groupList", {
            "appid": aid, "groupType": str(group_type),
        }, referer_suffix="")

    def save_report_groups(self, groups, app_id=None, group_type=0):
        """分组全量保存：POST /api/bs/edc/report/group/save（multipart groups JSON）。

        删除分组 = 从列表去掉后 save。勿包含哨兵 id=-1/-2/-3。
        """
        aid = str(app_id or self.app_id)
        cleaned = []
        for g in groups or []:
            gid = str(g.get("id") or g.get("groupId") or "")
            if gid in ("-1", "-2", "-3"):
                continue
            cleaned.append(g)
        fields = [
            ("appid", aid),
            ("groupType", str(group_type)),
            ("groups", json.dumps(cleaned, ensure_ascii=False)),
        ]
        return self._post_multipart("/api/bs/edc/report/group/save", fields,
                                   "groupSave", referer_suffix="")

    def movable_groups(self, app_id=None, group_type=0):
        """可「移动到」的自建分组（排除哨兵）。空列表 = 无可选移动位置。"""
        raw = self.list_report_groups(app_id=app_id, group_type=group_type)
        rows = raw.get("data") if isinstance(raw.get("data"), list) else []
        if not rows and isinstance(raw, list):
            rows = raw
        out = []
        for g in rows:
            gid = str(g.get("id") or g.get("groupId") or "")
            if not gid or gid in ("-1", "-2", "-3"):
                continue
            out.append({
                "id": gid,
                "name": g.get("name") or g.get("content") or g.get("groupName") or "",
                "showOrder": g.get("showOrder"),
            })
        return out

    def move_report(self, report_id, group_id, app_id=None):
        """移动到其他分组：POST /api/bs/edc/report/removeReport（改 group_id，非删除）。

        调用前应检查 movable_groups；无自建分组时不要调用。
        """
        fields = [
            ("reportId", str(report_id)),
            ("groupId", str(group_id)),
        ]
        return self._post_multipart("/api/bs/edc/report/removeReport", fields,
                                   "removeReport", referer_suffix=str(report_id),
                                   ebbusinessid=app_id or self.app_id)

    def list_eb_apps(self, name="", page_no=1, page_size=20):
        """转移应用选择框：GET /api/bs/ebuilder/app/list（按名称检索）。"""
        return self._get_json("/api/bs/ebuilder/app/list", "ebAppList", {
            "name": name or "",
            "pageNo": str(page_no),
            "pageSize": str(page_size),
        }, referer_suffix="")

    def transfer_report(self, report_ids, target_app_id):
        """转移到其他应用：POST /api/bs/edc/report/transferReport。

        目标侧 group_id 会被置为 -1。report_ids 可为单 id 或 list。
        """
        ids = report_ids if isinstance(report_ids, (list, tuple)) else [report_ids]
        fields = [("appId", str(target_app_id))]
        for rid in ids:
            fields.append(("reportIds", str(rid)))
        return self._post_multipart("/api/bs/edc/report/transferReport", fields,
                                   "transferReport", referer_suffix="")

    def save_permissions(self, report_id, permission_info):
        """报表权限保存：POST /api/bs/edc/report/permission/table/savePermissions"""
        rid = str(report_id)
        body = {rid: permission_info} if "viewRight" in permission_info else permission_info
        return self._post_json("/api/bs/edc/report/permission/table/savePermissions",
                               body, "savePermissions", referer_suffix=str(report_id))

    def save_as_version(self, report_id, version_name="", app_id=None):
        """存为新版本：POST /api/bs/edc/report/saveAsVersion（form: sheetId, versionName）"""
        rid = str(report_id)
        if not version_name:
            base = self.get_report_base_info(rid)
            name = (base.get("data") or {}).get("name") or "报表"
            now = datetime.datetime.now()
            version_name = "%s-%s-%s" % (
                name, now.strftime("%Y-%m-%d"), now.strftime("%H-%M-%S"))
        body = urllib.parse.urlencode({"sheetId": rid, "versionName": version_name}).encode("utf-8")
        headers = self._browser_headers(referer_suffix=rid)
        headers["Content-Type"] = "application/x-www-form-urlencoded;charset=UTF-8"
        status, text = self._send("POST", "/api/bs/edc/report/saveAsVersion", body, headers,
                                  "saveAsVersion", req_fields=[("sheetId", rid), ("versionName", version_name)])
        result = parse_json_snowflake_safe(text)
        new_id = extract_id_from_raw(text, ("id", "reportId"))
        if new_id:
            result["_newVersionReportId"] = new_id
        result["_httpStatus"] = status
        return result

    def copy_sheet(self, report_id):
        """复制报表：GET /api/bs/edc/report/copySheet?sheetId=

        返回体含 `_newReportId`（从 last_raw 提取，避免 JSON 大整数精度丢失）。
        """
        result = self._get_json("/api/bs/edc/report/copySheet", "copySheet",
                                {"sheetId": str(report_id)}, referer_suffix=str(report_id))
        new_id = extract_id_from_raw(self.last_raw, ("id", "reportId"))
        if not new_id and isinstance(result.get("data"), dict):
            new_id = stringify_id(result["data"].get("id") or result["data"].get("reportId"))
        if new_id:
            result["_newReportId"] = new_id
            if isinstance(result.get("data"), dict):
                result["data"]["id"] = new_id
        return result

    def delete_report(self, report_id):
        """删除报表（进回收站，delete_type=1）：GET /api/bs/edc/report/deleteReport?id="""
        return self._get_json("/api/bs/edc/report/deleteReport", "deleteReport",
                              {"id": str(report_id)}, referer_suffix=str(report_id))

    def list_recycle_reports(self, page_no=1, page_size=10, app_id=None, name="",
                             date_range=None, creators=None):
        """回收站分页列表：POST /api/bs/edc/report/getRecycleReportWithPage"""
        aid = str(app_id or self.app_id)
        dr = date_range if date_range is not None else ["", ""]
        cr = creators if creators is not None else []
        form = {
            "pageNo": str(page_no),
            "pageSize": str(page_size),
            "appId": aid,
            "dateRange": json.dumps(dr, ensure_ascii=False),
            "name": name or "",
            "creators": json.dumps(cr, ensure_ascii=False),
        }
        return self._post_form("/api/bs/edc/report/getRecycleReportWithPage",
                               form, "getRecycleReportWithPage", referer_suffix="")

    def revert_recycle_report(self, report_id):
        """回收站还原（delete_type 1→0）：GET /api/bs/edc/report/revertRecycleReport?id="""
        return self._get_json("/api/bs/edc/report/revertRecycleReport", "revertRecycleReport",
                              {"id": str(report_id)}, referer_suffix=str(report_id))

    def delete_recycle_report(self, report_id):
        """回收站彻底删除（delete_type=3，不可还原）：GET /api/bs/edc/report/deleteRecycleReport?id="""
        return self._get_json("/api/bs/edc/report/deleteRecycleReport", "deleteRecycleReport",
                              {"id": str(report_id)}, referer_suffix=str(report_id))

    @staticmethod
    def _default_menu_share_map():
        return [{
            "id": "0", "content": "所有人", "_entityType": "all", "objType": "all",
            "objTypeSpan": "所有人", "obj_id_span": "所有人", "permissionId": "sys_view",
            "targetId": 0, "targetType": 11, "icon": "Icon-all02",
            "seclevel": {"min": -999, "max": 999}, "sourceType": 1,
            "objIdList": ["所有人"],
            "shareKey": "temp_all_0_" + uuid.uuid4().hex[:6],
            "obj_id_all": [{"content": "所有人", "icon": "Icon-all02", "id": "0"}],
        }]

    def add_report_to_menu(self, report_id, menu_name, app_id=None, pid="0",
                           terminal_type="PC", menu_sys_id=""):
        """添加到菜单：POST /api/cusapp/app/savePublishMenu（pageType=REPORT）

        menu_sys_id: 空=新建；填已有菜单项 sysMenuId 则更新（勿填 navId）。
        """
        aid = str(app_id or self.app_id)
        rid = stringify_id(report_id)
        navigation = {
            "content": menu_name,
            "id": str(menu_sys_id or ""),
            "openMode": "1", "pid": str(pid), "type": "0",
            "params": [], "showType": "1", "showOrder": 1,
            "firstTabChange": False, "nameLabelId": "-1", "nameAlias": menu_name,
            "tabs": "{}", "combinationId": "",
            "shareMap": self._default_menu_share_map(),
            "excludeShareMap": [],
            "showRightBtn": "1", "urlLinkType": "0",
            "page": {
                "pageId": rid,
                "pageName": menu_name,
                "pageType": "REPORT",
                "terminalScopes": "",
                "appid": aid,
            },
            "unitFill": "0",
        }
        fields = [
            ("appId", aid),
            ("navigation", json.dumps(navigation, ensure_ascii=False)),
            ("isThirdParty", "true"),
            ("terminalType", terminal_type),
        ]
        return self._post_multipart(
            "/api/cusapp/app/savePublishMenu", fields, "savePublishMenu",
            referer_suffix="build/" + aid, ebbusinessid=aid)

    def _compress(self, obj: dict) -> str:
        """约束 3：原始 JSON -> gzip -> base64（顺序不可颠倒）。
        mtime=0 以对齐浏览器 pako 产物（部分网关对非零 mtime 的 gzip 头校验严格）。"""
        raw = json.dumps(obj, ensure_ascii=False)
        gz = gzip.compress(raw.encode("utf-8"), mtime=0)
        return base64.b64encode(gz).decode("ascii")

    def _post(self, report_id, name, name_label_id, design_key, workbook_b64: str):
        """约束 2：以 multipart/form-data 表单（非 JSON Body）提交。"""
        boundary = "----PythonFormBoundary" + uuid.uuid4().hex[:12]
        fields = [
            ("groupId", self.group_id),
            ("appId", self.app_id),
            ("name", name),
            ("nameLabelId", name_label_id),
            ("designKey", design_key),
        ]
        if report_id is not None:
            fields.append(("reportId", report_id))
        parts = []
        for k, v in fields:
            parts.append(
                f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'
            )
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="workbook"\r\n\r\n{workbook_b64}\r\n'
        )
        parts.append(f"--{boundary}--\r\n")
        body = "".join(parts).encode("utf-8")
        headers = self._browser_headers()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        conn = http.client.HTTPSConnection(self.host, timeout=self.timeout,
                                           context=ssl.create_default_context())
        conn.request("POST", self.path, body=body, headers=headers)
        resp = conn.getresponse()
        self.last_status = resp.status
        text = resp.read().decode("utf-8")
        self.last_raw = text
        m = re.search(r'"reportId"\s*:\s*"([^"]+)"', text)
        return m.group(1) if m else None

    def create_report(self, name, name_label_id, workbook_json: dict, report_id=None):
        """新建报表。report_id 为 None 时不带 reportId（部分网关会因缺少主键报系统错误）；
        传入字符串时将其作为新报表主键写入表单与 workbook。返回报表 reportId。"""
        rid = report_id if report_id else str(uuid.uuid4())
        return self._post(rid, name, name_label_id, str(uuid.uuid4()), self._compress(workbook_json))

    def update_report(self, report_id, name, name_label_id, workbook_json: dict):
        """编辑报表（携带 reportId）。"""
        return self._post(report_id, name, name_label_id, str(uuid.uuid4()), self._compress(workbook_json))


if __name__ == "__main__":
    import sys

    # 示例调用（需提供真实鉴权参数）：
    # python report_api_client.py <host> <eteamsid> <ebbusinessid> <cookie> <groupId> <appId>
    a = sys.argv[1:]
    cli = ReportApiClient(*a[:6])
    # 注：__main__ 仅完成客户端初始化，不自动发请求；
    # 调用方需显式执行 cli.create_report(...) / cli.update_report(...) 并传入真实 workbook JSON。
    print("ReportApiClient 就绪；以真实鉴权参数 + workbook JSON 调用 create_report/update_report 即可落库。")
