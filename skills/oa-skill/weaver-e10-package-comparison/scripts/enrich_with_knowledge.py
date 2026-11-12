#!/usr/bin/env python3
"""将原始差异绑定到 Codex 配置事实与 Claude 业务表达补充。"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from knowledge_io import iter_jsonl

def _tables_from_semantic(record: dict[str, Any]) -> set[str]:
    result = set()
    for key in ("config_tables", "table_names", "tables"):
        for table in record.get(key) or []:
            result.add(str(table).lower())
    for side in ("source", "target"):
        value = record.get(side)
        if isinstance(value, dict):
            table = value.get("table") or value.get("sourceTable")
            if table:
                result.add(str(table).lower())
    return result


def enrich_with_knowledge(
    facts_document: dict[str, Any],
    knowledge_dir: Path,
) -> dict[str, Any]:
    features = list(iter_jsonl(knowledge_dir / "feature-groups.jsonl"))
    nodes = list(iter_jsonl(knowledge_dir / "config-nodes.jsonl"))
    semantics = list(iter_jsonl(knowledge_dir / "handler-semantics.jsonl"))
    by_table_feature: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_table_nodes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_table_semantics: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for feature in features:
        for table in feature.get("memberTables") or []:
            by_table_feature[str(table).lower()].append(feature)
        if feature.get("rootTable"):
            by_table_feature[str(feature["rootTable"]).lower()].append(feature)
    for node in nodes:
        by_table_nodes[str(node.get("table") or "").lower()].append(node)
    for semantic in semantics:
        for table in _tables_from_semantic(semantic):
            by_table_semantics[table].append(semantic)

    enriched = []
    for fact in facts_document["facts"]:
        table = str(fact["object"]["table"]).lower()
        module = fact["object"]["module"]
        candidates = by_table_feature.get(table, [])
        candidates = sorted(
            candidates,
            key=lambda item: (
                0 if str(item.get("rootTable") or "").lower() == table else 1,
                0 if item.get("module") == module else 1,
                len(item.get("memberTables") or []),
                str(item.get("featureGroupId")),
            ),
        )
        feature = candidates[0] if candidates else None
        node_matches = [
            node for node in by_table_nodes.get(table, [])
            if node.get("moduleName") == module or module in (node.get("services") or [])
        ] or by_table_nodes.get(table, [])
        semantic_matches = [
            item for item in by_table_semantics.get(table, [])
            if item.get("service") in (None, "", module)
        ][:8]
        config_ids = sorted(set(
            list(fact["object"].get("configIds") or [])
            + [str(node.get("configId")) for node in node_matches if node.get("configId")]
        ))
        fact = dict(fact)
        fact["object"] = dict(fact["object"])
        fact["object"]["configIds"] = config_ids
        fact["feature"] = {
            "featureGroupId": feature.get("featureGroupId") if feature else None,
            "businessName": (
                feature.get("businessName")
                if feature
                else f"{fact['object']['moduleKind']}中的 {fact['object']['table']} 配置"
            ),
            "businessPurpose": feature.get("businessPurpose") if feature else "",
            "userVisibleFunctions": feature.get("userVisibleFunctions") if feature else "",
            "confidence": feature.get("confidence") if feature else "unknown",
            "sourceAuthority": "CLAUDE" if feature else "GENERATED_FROM_CODEX_FACT",
            "semanticOnly": bool(feature),
        }
        fact["knowledgeEvidence"] = {
            "codexConfigIds": config_ids,
            "codexNodeIds": [
                node.get("nodeId") for node in node_matches if node.get("nodeId")
            ],
            "claudeSemanticEvidenceIds": [
                item.get("evidence_id")
                or (item.get("source") or {}).get("recordId")
                for item in semantic_matches
            ],
            "handlerSummaries": [
                item.get("summary") or item.get("evidence_summary")
                for item in semantic_matches
                if item.get("summary") or item.get("evidence_summary")
            ],
            "authorityPolicy": "CODEX_FACTS_WITH_CLAUDE_EXPRESSION_ONLY",
        }
        enriched.append(fact)
    return {
        **facts_document,
        "facts": enriched,
    }
