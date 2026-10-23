#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Detect whether report sheetConfig.dataPreAgg should be enabled.

Usage:
  python check_preaggregate_support.py --fields-json fields.json [--layout-json layout.json]
  python check_preaggregate_support.py --stdin   # read combined JSON from stdin

fields-json: output of fieldsAndOriginFields (list or {fieldsKey, originFields})
layout-json: optional report field configs from getReportDevInfo.fields
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

NO_GROUP_COMP_TYPES = {"TextArea", "RichText"}
ALLOWED_USAGE = {"", "all", "char", "aggregate"}


def _origin_comp(field: Dict[str, Any]) -> str:
    origin = field.get("originField") or {}
    if isinstance(origin, dict):
        return str(origin.get("compType") or "")
    return ""


def _field_usage(field: Dict[str, Any]) -> str:
    return str(field.get("usage") or "")


def _normalize_fields_blob(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("fieldsKey", "originFields", "fields", "data"):
            v = data.get(key)
            if isinstance(v, list):
                return v
    return []


def check_fields(fields: List[Dict[str, Any]], layout: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    reasons: List[str] = []

    for f in fields:
        label = f.get("text") or f.get("name") or "?"
        usage = _field_usage(f)
        if usage == "list":
            reasons.append(f"字段[{label}] usage=list 不支持预聚合")
        if f.get("gdBySelf") is True:
            reasons.append(f"字段[{label}] gdBySelf=true 不支持预聚合")
        comp = _origin_comp(f)
        if comp in NO_GROUP_COMP_TYPES:
            reasons.append(f"字段[{label}] compType={comp} 不可作为预分组字段")

    if layout:
        for cell in layout:
            label = cell.get("text") or cell.get("cellText") or "?"
            disp = cell.get("displayType") or ""
            if disp == "List":
                reasons.append(f"单元格[{label}] displayType=List(排列) 阻断预聚合")
            for key in ("customFilterField", "dataFilterField", "leftFilterField", "topFilterField"):
                raw = cell.get(key)
                if not raw:
                    continue
                if isinstance(raw, str):
                    try:
                        raw = json.loads(raw)
                    except json.JSONDecodeError:
                        raw = [raw]
                if isinstance(raw, list) and len(raw) > 0:
                    if key in ("leftFilterField", "topFilterField"):
                        reasons.append(f"单元格[{label}] 含父格筛选，涉及数据集跳过预聚合")
                    else:
                        reasons.append(f"单元格[{label}] 含{key}，阻断预聚合")

    data_pre_agg = len(reasons) == 0
    sheet_config = json.dumps(
        {"dataPreAgg": data_pre_agg, "simpleList": False},
        ensure_ascii=False,
    )
    return {
        "dataPreAgg": data_pre_agg,
        "reasons": reasons,
        "sheetConfig": sheet_config,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Check dataPreAgg eligibility")
    ap.add_argument("--fields-json", help="fieldsAndOriginFields JSON file")
    ap.add_argument("--layout-json", help="report fields layout JSON file")
    ap.add_argument("--stdin", action="store_true", help="read JSON from stdin")
    args = ap.parse_args()

    if args.stdin:
        payload = json.load(sys.stdin)
        fields = _normalize_fields_blob(payload.get("fields") or payload)
        layout = payload.get("layout")
    else:
        if not args.fields_json:
            ap.error("need --fields-json or --stdin")
        with open(args.fields_json, encoding="utf-8") as f:
            fields = _normalize_fields_blob(json.load(f))
        layout = None
        if args.layout_json:
            with open(args.layout_json, encoding="utf-8") as f:
                layout_data = json.load(f)
            layout = layout_data if isinstance(layout_data, list) else layout_data.get("fields")

    result = check_fields(fields, layout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["dataPreAgg"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
