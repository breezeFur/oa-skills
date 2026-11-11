#!/usr/bin/env python3
"""Shared offline analysis for workflow-owned SQL datasource configuration."""

from __future__ import annotations

import hashlib
import re
from typing import Any


PROHIBITED_SQL_WORDS = {
    "insert", "update", "delete", "merge", "create", "alter", "drop",
    "truncate", "grant", "revoke", "call", "execute", "exec",
}


def sql_without_comments(sql: str) -> str:
    """Remove comments while preserving quoted literals."""

    result: list[str] = []
    index = 0
    quote = ""
    while index < len(sql):
        char = sql[index]
        if quote:
            result.append(char)
            if char == quote:
                if index + 1 < len(sql) and sql[index + 1] == quote:
                    result.append(sql[index + 1])
                    index += 1
                else:
                    quote = ""
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            result.append(char)
            index += 1
            continue
        if sql.startswith("--", index):
            end = sql.find("\n", index + 2)
            index = len(sql) if end < 0 else end + 1
            result.append(" ")
            continue
        if sql.startswith("/*", index):
            end = sql.find("*/", index + 2)
            index = len(sql) if end < 0 else end + 2
            result.append(" ")
            continue
        result.append(char)
        index += 1
    return "".join(result)


def sql_semantic_form(sql: str) -> str:
    """Normalize formatting outside literals without changing literal values."""

    sql = sql_without_comments(sql)
    parts: list[str] = []
    buffer: list[str] = []
    quote = ""

    def flush_plain() -> None:
        if not buffer:
            return
        plain = "".join(buffer).lower()
        plain = re.sub(r"\s+", " ", plain)
        plain = re.sub(r"\s*([(),=<>+*/-])\s*", r"\1", plain)
        parts.append(plain)
        buffer.clear()

    index = 0
    while index < len(sql):
        char = sql[index]
        if quote:
            parts.append(char)
            if char == quote:
                if index + 1 < len(sql) and sql[index + 1] == quote:
                    parts.append(sql[index + 1])
                    index += 1
                else:
                    quote = ""
            index += 1
            continue
        if char in {"'", '"'}:
            flush_plain()
            quote = char
            parts.append(char)
        else:
            buffer.append(char)
        index += 1
    flush_plain()
    return "".join(parts).strip().rstrip(";")


def output_type_label(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text or "undefined" in text:
        return "未明确"
    return {
        "text": "文本", "string": "文本", "number": "数值", "integer": "整数",
        "decimal": "小数", "date": "日期", "datetime": "日期时间", "boolean": "布尔值",
    }.get(text, "已明确")


def analyze_workflow_sql_dataset(
    config: dict[str, Any],
    bindings: list[dict[str, Any]],
    identity_hash: str | None,
) -> dict[str, Any]:
    """Return customer-safe semantics and deterministic offline static checks."""

    sql = str(config.get("sql") or "")
    semantic = sql_semantic_form(sql)
    outside_literals = re.sub(
        r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"", "", sql_without_comments(sql)
    )
    words = re.findall(r"[a-z_]+", outside_literals.lower())
    first_word = words[0] if words else ""
    prohibited = sorted(set(words) & PROHIBITED_SQL_WORDS)
    statements = [part for part in outside_literals.split(";") if part.strip()]
    placeholders = sorted(set(re.findall(r"\$\{([^}]+)\}", sql)))
    binding_hashes = {
        str(binding.get("placeholderHash") or "") for binding in bindings
        if binding.get("placeholderHash")
    }
    placeholder_hashes = {
        hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
        for value in placeholders
    }
    inputs = list(dict.fromkeys(
        str(field.get("showname") or "查询参数").strip() or "查询参数"
        for field in config.get("fields") or [] if isinstance(field, dict)
    ))
    aliases = [field for field in config.get("fieldAlias") or [] if isinstance(field, dict)]
    declared_aliases = {
        str(field.get("name") or "").lower() for field in aliases if field.get("name")
    }
    selected_aliases = {
        match.lower() for match in re.findall(
            r"\bas\s+([a-z_][a-z0-9_]*)", outside_literals, re.I
        )
    }
    output_types = list(dict.fromkeys(
        output_type_label(field.get("type")) for field in aliases
    )) or ["未明确"]
    where_match = re.search(r"\bwhere\b(.*)$", outside_literals, re.I | re.S)
    condition_count = 0
    if where_match and where_match.group(1).strip():
        condition_count = 1 + len(re.findall(
            r"\band\b|\bor\b", where_match.group(1), re.I
        ))
    fixed_count = max(0, condition_count - len(placeholders))
    returns_count = bool(re.search(r"\bcount\s*\(", outside_literals, re.I))
    if returns_count and inputs:
        query_summary = (
            f"按 {fixed_count} 项固定条件及“{'、'.join(inputs)}”参数过滤，"
            "返回符合条件的记录数量"
        )
    elif returns_count:
        query_summary = "按保存的筛选条件返回符合条件的记录数量"
    else:
        query_summary = "执行只读查询并返回配置的结果字段"
    database_settings_present = bool(
        config.get("sourceDBTypeList") or config.get("sourceSql")
    )
    read_only = first_word in {"select", "with"} and not prohibited
    return {
        "identityHash": identity_hash,
        "semanticHash": hashlib.sha256(semantic.encode("utf-8")).hexdigest() if semantic else None,
        "queryType": "只读查询" if read_only else "需人工复核",
        "querySummary": query_summary,
        "inputs": inputs or ["未声明输入参数"],
        "outputTypes": output_types,
        "staticChecks": {
            "configurationParsed": bool(config),
            "singleStatement": len(statements) == 1,
            "readOnlyQuery": read_only,
            "parametersResolved": bool(placeholders) and placeholder_hashes == binding_hashes,
            "outputAliasesDeclared": bool(declared_aliases) and selected_aliases.issubset(declared_aliases),
        },
        "databaseSettingsPresent": database_settings_present,
        "runtimePending": [
            "数据库类型和连接信息未随包提供"
            if not database_settings_present else "数据库连接需在目标环境复核",
            "数据库对象存在性、访问权限、真实执行结果和性能需在目标环境验证",
        ],
    }


def pair_workflow_sql_summaries(
    old_summaries: list[dict[str, Any]],
    new_summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Pair only inside an already matched workflow; never override IDM identity."""

    result: list[dict[str, Any]] = []
    used_old: set[int] = set()
    used_new: set[int] = set()
    for old_index, before in enumerate(old_summaries):
        candidates = [
            index for index, after in enumerate(new_summaries)
            if index not in used_new
            and before.get("semanticHash") == after.get("semanticHash")
            and before.get("inputs") == after.get("inputs")
        ]
        if not candidates and len(old_summaries) == len(new_summaries) == 1:
            candidates = [0]
        if not candidates:
            continue
        new_index = candidates[0]
        used_old.add(old_index)
        used_new.add(new_index)
        after = new_summaries[new_index]
        same_identity = bool(before.get("identityHash")) and (
            before.get("identityHash") == after.get("identityHash")
        )
        if before == after and same_identity:
            continue
        identity = "SAME_SOURCE" if same_identity else (
            "RECREATED_OR_REBOUND"
            if before.get("identityHash") and after.get("identityHash")
            else "IDENTITY_UNCONFIRMED"
        )
        result.append({
            "identityConclusion": identity,
            "querySemanticsChanged": before.get("semanticHash") != after.get("semanticHash"),
            "before": before,
            "after": after,
        })
    for index, after in enumerate(new_summaries):
        if index not in used_new:
            result.append({
                "identityConclusion": "ADDED", "querySemanticsChanged": True,
                "before": None, "after": after,
            })
    for index, before in enumerate(old_summaries):
        if index not in used_old:
            result.append({
                "identityConclusion": "REMOVED", "querySemanticsChanged": True,
                "before": before, "after": None,
            })
    return result
