#!/usr/bin/env python3
"""Resolve old/new package roles without filename or file-metadata guesses."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DirectionResolutionError(ValueError):
    """Raised when package direction cannot be resolved without guessing."""


def parse_export_time(value: Any) -> dict[str, Any]:
    """Parse common eBuilder exportTime representations into a comparable value."""
    if value in (None, ""):
        raise DirectionResolutionError("profile.json 缺少 exportTime")
    raw = str(value).strip()
    if not raw:
        raise DirectionResolutionError("profile.json 的 exportTime 为空")

    numeric_value: float | None = None
    try:
        numeric_value = float(raw)
    except ValueError:
        pass
    if numeric_value is not None:
        if abs(numeric_value) >= 10_000_000_000:
            numeric_value /= 1000.0
        try:
            parsed = datetime.fromtimestamp(numeric_value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError) as exc:
            raise DirectionResolutionError(
                f"profile.json 的 exportTime 超出可解析范围: {raw}"
            ) from exc
        return {
            "raw": raw,
            "canonical": parsed.isoformat(),
            "timezoneMode": "AWARE",
            "orderValue": parsed.timestamp(),
        }

    normalized = raw[:-1] + "+00:00" if raw.endswith(("Z", "z")) else raw
    parsed: datetime | None = None
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        pass
    if parsed is None:
        for pattern in (
            "%Y/%m/%d %H:%M:%S.%f",
            "%Y/%m/%d %H:%M:%S",
            "%Y%m%d%H%M%S",
        ):
            try:
                parsed = datetime.strptime(raw, pattern)
                break
            except ValueError:
                continue
    if parsed is None:
        raise DirectionResolutionError(
            f"profile.json 的 exportTime 无法解析: {raw}"
        )

    if parsed.tzinfo is None:
        order_value = (
            parsed - datetime(1970, 1, 1)
        ).total_seconds()
        timezone_mode = "NAIVE"
    else:
        order_value = parsed.timestamp()
        timezone_mode = "AWARE"
    return {
        "raw": raw,
        "canonical": parsed.isoformat(),
        "timezoneMode": timezone_mode,
        "orderValue": order_value,
    }


def _profile_time(package_path: Path, ir: dict[str, Any]) -> dict[str, Any]:
    profile = ir.get("packageProfile") or {}
    status = profile.get("status")
    if status != "AVAILABLE":
        reason = {
            "MISSING": "未找到带 exportTime 的最外层 profile.json",
            "CONFLICT": "最外层存在多个 profile.json 且 exportTime 冲突",
        }.get(str(status), "最外层 profile.json 状态不可用")
        raise DirectionResolutionError(
            f"无法判断 {package_path.name} 的版本时间：{reason}；"
            "请改用 --old 与 --new 明确指定方向"
        )
    try:
        parsed = parse_export_time(profile.get("selectedExportTime"))
    except DirectionResolutionError as exc:
        raise DirectionResolutionError(
            f"无法判断 {package_path.name} 的版本时间：{exc}；"
            "请改用 --old 与 --new 明确指定方向"
        ) from exc
    return {
        **parsed,
        "name": package_path.name,
        "evidenceFiles": profile.get("evidenceFiles") or [],
        "profileDepth": profile.get("selectedDepth"),
    }


def explicit_direction(
    old_path: Path,
    old_ir: dict[str, Any],
    new_path: Path,
    new_ir: dict[str, Any],
) -> tuple[Path, dict[str, Any], Path, dict[str, Any], dict[str, Any]]:
    """Keep caller-supplied roles even when profile times appear inverted."""
    return old_path, old_ir, new_path, new_ir, {
        "directionSource": "EXPLICIT_CLI_ARGUMENTS",
        "rule": "--old/--new roles take precedence over profile exportTime",
        "filenameInferenceUsed": False,
        "fileMetadataInferenceUsed": False,
        "exportTimeComparisonUsed": False,
        "inputOrder": [old_path.name, new_path.name],
    }


def automatic_direction(
    first_path: Path,
    first_ir: dict[str, Any],
    second_path: Path,
    second_ir: dict[str, Any],
) -> tuple[Path, dict[str, Any], Path, dict[str, Any], dict[str, Any]]:
    """Use outermost profile exportTime when the caller supplied no roles."""
    first_time = _profile_time(first_path, first_ir)
    second_time = _profile_time(second_path, second_ir)
    if first_time["timezoneMode"] != second_time["timezoneMode"]:
        raise DirectionResolutionError(
            "两个包的 exportTime 时区表达不一致，无法安全比较；"
            "请改用 --old 与 --new 明确指定方向"
        )
    if first_time["orderValue"] == second_time["orderValue"]:
        raise DirectionResolutionError(
            "两个包的 profile.json.exportTime 相同，无法判断新旧；"
            "请改用 --old 与 --new 明确指定方向"
        )

    pairs = [
        (first_time["orderValue"], first_path, first_ir, first_time),
        (second_time["orderValue"], second_path, second_ir, second_time),
    ]
    pairs.sort(key=lambda item: item[0])
    _, old_path, old_ir, old_time = pairs[0]
    _, new_path, new_ir, new_time = pairs[1]
    resolution = {
        "directionSource": "PROFILE_EXPORT_TIME",
        "rule": "earlier outermost profile.json.exportTime is old; later is new",
        "filenameInferenceUsed": False,
        "fileMetadataInferenceUsed": False,
        "exportTimeComparisonUsed": True,
        "inputOrder": [first_path.name, second_path.name],
        "oldProfile": {
            key: value
            for key, value in old_time.items()
            if key != "orderValue"
        },
        "newProfile": {
            key: value
            for key, value in new_time.items()
            if key != "orderValue"
        },
    }
    return old_path, old_ir, new_path, new_ir, resolution
