#!/usr/bin/env python3
"""基于 Codex 配置关系图计算最多三层的直接与间接影响。"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from knowledge_io import iter_jsonl

def propagate_impacts(
    facts: list[dict[str, Any]],
    knowledge_dir: Path,
    max_depth: int = 3,
) -> list[dict[str, Any]]:
    max_depth = max(1, min(int(max_depth), 3))
    nodes = list(iter_jsonl(knowledge_dir / "config-nodes.jsonl"))
    edges = list(iter_jsonl(knowledge_dir / "relation-edges.jsonl"))
    node_by_id = {str(node.get("nodeId")): node for node in nodes}
    graph: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        child_key = (
            str(edge.get("childModule") or ""),
            str(edge.get("childTable") or "").lower(),
        )
        parent_node = node_by_id.get(str(edge.get("parentNodeId") or ""), {})
        parent_module = (
            parent_node.get("moduleName")
            or (parent_node.get("services") or [""])[0]
            or edge.get("childModule")
            or ""
        )
        parent_key = (
            str(parent_module),
            str(edge.get("parentTable") or "").lower(),
        )
        link = {
            "edgeId": edge.get("edgeId"),
            "relationType": edge.get("relationType"),
            "scope": edge.get("scope"),
        }
        graph[child_key].append({
            "target": parent_key,
            "direction": "UPSTREAM_DEPENDENCY",
            **link,
        })
        graph[parent_key].append({
            "target": child_key,
            "direction": "DOWNSTREAM_CONSUMER",
            **link,
        })

    changed_by_source: dict[tuple[str, str], list[str]] = defaultdict(list)
    for fact in facts:
        if fact["changeType"] == "UNCHANGED":
            continue
        changed_by_source[(
            fact["object"]["module"],
            fact["object"]["table"].lower(),
        )].append(fact["changeId"])

    results = []
    for source, change_ids in sorted(changed_by_source.items()):
        queue = deque([(source, 0, [])])
        visited = {source}
        paths: list[dict[str, Any]] = []
        while queue:
            current, depth, path = queue.popleft()
            if depth >= max_depth:
                continue
            for link in graph.get(current, []):
                target = tuple(link["target"])
                if not target[1] or target in visited:
                    continue
                visited.add(target)
                next_path = path + [link["edgeId"]]
                next_depth = depth + 1
                paths.append({
                    "depth": next_depth,
                    "impactLevel": "DIRECT" if next_depth == 1 else "INDIRECT",
                    "targetModule": target[0],
                    "targetTable": target[1],
                    "direction": link["direction"],
                    "relationType": link["relationType"],
                    "scope": link["scope"],
                    "edgePath": next_path,
                    "evidenceLevel": "OBSERVED" if next_depth == 1 else "INFERRED",
                })
                queue.append((target, next_depth, next_path))
        seed = f"{source[0]}|{source[1]}"
        results.append({
            "impactGroupId": "IMP-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16].upper(),
            "sourceModule": source[0],
            "sourceTable": source[1],
            "changeIds": sorted(change_ids),
            "maxDepth": max_depth,
            "directImpacts": [item for item in paths if item["depth"] == 1],
            "indirectImpacts": [item for item in paths if item["depth"] > 1],
            "cycleDeduplicated": True,
        })
    return results
