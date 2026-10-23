#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build leftFilterField / subordination with full fieldKeys (eteams 2026-09 verified).

Usage:
  from left_filter_builder import build_cross_dataset_filter

  lf, sub = build_cross_dataset_filter(
      parent_ds_id, parent_src_id, parent_field_name,
      child_ds_id, child_src_id, child_field_name,
  )
"""
from __future__ import annotations

from typing import Dict, List, Tuple


def field_key(ds_id: str, src_id: str, field_name: str) -> str:
    return f"{ds_id}.{src_id}.{field_name}"


def build_cross_dataset_filter(
    parent_ds_id: str,
    parent_src_id: str,
    parent_field_name: str,
    child_ds_id: str,
    child_src_id: str,
    child_field_name: str,
    *,
    match_type: str = "Equals",
) -> Tuple[List[Dict[str, str]], List[str]]:
    """Return (leftFilterField list, subordination pair) for workbook + fields table."""
    pk = field_key(parent_ds_id, parent_src_id, parent_field_name)
    ck = field_key(child_ds_id, child_src_id, child_field_name)
    left_filter = [
        {
            "parentField": pk,
            "currentField": ck,
            "type": match_type,
            "id": ck,
        }
    ]
    subordination = [pk, ck]
    return left_filter, subordination


def apply_to_cell_field(
    field: dict,
    left_filter: list,
    subordination: list,
    left_x: int,
    left_y: int,
) -> dict:
    """Patch a getReportDevInfo-style field record (JSON-serializable)."""
    import json

    field = dict(field)
    field["leftX"] = left_x
    field["leftY"] = left_y
    field["leftFilterField"] = json.dumps(left_filter, ensure_ascii=False)
    field["subordination"] = json.dumps(subordination, ensure_ascii=False)
    return field
