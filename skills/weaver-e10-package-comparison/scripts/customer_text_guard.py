#!/usr/bin/env python3
"""共享的客户正文技术泄漏扫描器。

业务全景 Markdown 和客户可视化必须使用同一套更严格的泄漏口径；否则
“实验校验通过、可视化校验失败”的分裂状态会把问题留到交付末端。
"""

from __future__ import annotations

import re


# 这些规则只用于客户展示层门禁，不用于技术附录或机器模型。
MARKDOWN_PATTERNS: tuple[tuple[str, str], ...] = (
    ("dataset-source", r"\bdataset[-_]source\b"),
    ("long-numeric-id", r"(?<![0-9])\d{16,}(?![0-9])"),
    ("long-hex-id", r"(?<![A-Za-z0-9])[0-9a-f]{16,}(?![A-Za-z0-9])"),
    ("technical-object-token", r"\b(?:entity|form|page|menu|permission|dataset|integration|flow)-[A-Za-z0-9_-]+"),
    ("technical-object-suffix", r"\b(?:report|page|form|menu|dataset|entity|permission)[-_](?:view|source)\b"),
    ("source-or-environment-marker", r"\b(?:source_id|import_id|eid|migration-source|profile-lineage|idm-lineage|idm-context|content=|parent=|target-builder-contract)\b"),
    ("service-or-adapter-token", r"(?:weaver-[a-z0-9-]+-service|adapter:[a-z0-9_-]+)"),
    ("json-reference-path", r"\.\$ref\b"),
)

# HTML 自身包含 type=、script 等语法，不能直接复用 Markdown 的全部规则；
# 仍必须拦截业务数据中可能被原样嵌入的技术对象、长 ID 和服务标识。
HTML_PATTERNS: tuple[tuple[str, str], ...] = tuple(
    (name, pattern)
    for name, pattern in MARKDOWN_PATTERNS
    if name not in {"json-reference-path"}
)


def find_customer_text_leaks(text: str, *, html: bool = False) -> list[str]:
    """返回命中的规则名称，结果稳定排序且不回显敏感原文。"""
    patterns = HTML_PATTERNS if html else MARKDOWN_PATTERNS
    return [name for name, pattern in patterns if re.search(pattern, text, re.IGNORECASE)]


def has_customer_text_leaks(text: str, *, html: bool = False) -> bool:
    return bool(find_customer_text_leaks(text, html=html))


__all__ = ["find_customer_text_leaks", "has_customer_text_leaks"]
