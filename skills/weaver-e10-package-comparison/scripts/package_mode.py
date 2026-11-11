#!/usr/bin/env python3
"""Classify two parsed eBuilder packages into application or workflow mode."""

from __future__ import annotations

from typing import Any


class PackageModeError(ValueError):
    pass


APPLICATION_TYPES = {"ebuilder", "application", "app"}
WORKFLOW_TYPES = {"workflow"}


def package_mode(ir: dict[str, Any]) -> str:
    profile = ir.get("packageProfile") or {}
    value = str(profile.get("selectedIetype") or "").strip().lower()
    if value in WORKFLOW_TYPES:
        return "workflow"
    if value in APPLICATION_TYPES:
        return "application"

    # Old application packages did not always expose ietype consistently.
    # Preserve V12 behavior only when the package has an application root.
    tables = {
        str(table).lower()
        for module in (ir.get("modules") or {}).values()
        for table in (module.get("tables") or {})
    }
    if tables & {"ebda_app", "t_cus_app", "ebdf_obj"}:
        return "application"
    if value:
        raise PackageModeError(f"不支持的 profile.json.ietype：{value}")
    raise PackageModeError(
        "无法从最外层 profile.json 唯一识别包类型；请确认 ietype 为 ebuilder 或 workflow"
    )


def resolve_pair_mode(old_ir: dict[str, Any], new_ir: dict[str, Any]) -> str:
    old_mode, new_mode = package_mode(old_ir), package_mode(new_ir)
    if old_mode != new_mode:
        raise PackageModeError(
            f"两个包类型不一致：旧包为 {old_mode}，新包为 {new_mode}；禁止跨类型比较"
        )
    return old_mode
