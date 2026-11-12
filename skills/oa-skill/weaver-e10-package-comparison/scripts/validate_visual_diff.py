#!/usr/bin/env python3
"""验证 V8 可视化数据一致性、确定性和单文件离线可用性。"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import html as html_module
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from build_visual_diff_model import build_visual_diff_model
from render_visual_diff_html import client_model_projection


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _evidence_path(output: Path, name: str) -> Path:
    plain = output / name
    zipped = output / (name + ".gz")
    if plain.is_file() and not zipped.exists():
        return plain
    if zipped.is_file() and not plain.exists():
        return zipped
    raise ValueError(f"缺少或重复输出: {name}[.gz]")


def _embedded_model(html: str) -> dict[str, Any]:
    match = re.search(
        r'<script id="visual-diff-data" type="application/json">(.*?)</script>',
        html,
        flags=re.DOTALL,
    )
    if not match:
        raise ValueError("HTML 缺少内嵌 visual model")
    return json.loads(html_module.unescape(match.group(1)))


def validate_visual_consistency(
    model: dict[str, Any],
    business_diff: dict[str, Any],
    analysis: dict[str, Any],
    impact_groups: list[dict[str, Any]],
    html: str,
) -> dict[str, Any]:
    nodes = model.get("nodes") or []
    node_by_identity = {
        (
            str(item.get("packageUnitKey") or item.get("packageUnit")),
            str(item.get("objectType")),
            str(item.get("logicalKey")),
        ): item
        for item in nodes
    }
    expected_objects = business_diff.get("objects") or []
    active_expected = [
        item for item in expected_objects
        if item.get("changeType") in {
            "ADDED", "REMOVED", "UPDATED", "POSSIBLE_RENAME", "UNMATCHED"
        }
    ]
    object_coverage = all(
        (
            str(item.get("packageUnitKey") or item.get("packageUnit") or "未分配应用"),
            str(item.get("objectType")),
            str(item.get("logicalKey")),
        ) in node_by_identity
        for item in active_expected
    )
    model_counts = Counter(str(item.get("changeType")) for item in nodes)
    expected_counts = Counter(str(item.get("changeType")) for item in expected_objects)
    package_units_match = all(
        node_by_identity.get((
            str(item.get("packageUnitKey") or item.get("packageUnit") or "未分配应用"),
            str(item.get("objectType")),
            str(item.get("logicalKey")),
        ), {}).get("packageUnitKey")
        == str(item.get("packageUnitKey") or item.get("packageUnit") or "未分配应用")
        for item in active_expected
    )
    field_owners = {item.get("ownerNodeId") for item in model.get("fieldLineage") or []}
    risks = model.get("risks") or []
    validations = {item.get("validationId") for item in model.get("validations") or []}
    high_risk_traceable = all(
        risk.get("affectedChangeCount", 0) > 0
        and bool(risk.get("affectedChangeIds"))
        and bool(risk.get("validationIds"))
        and all(value in validations for value in risk.get("validationIds") or [])
        for risk in risks
        if risk.get("severity") == "HIGH"
    )
    unknown_uncertain = all(
        risk.get("evidenceLevel") == "UNKNOWN"
        or "不表示" in str(risk.get("uncertaintyStatement") or "")
        or "确认" in str(risk.get("uncertaintyStatement") or "")
        for risk in risks
        if risk.get("severity") == "UNKNOWN"
    )
    rebuilt = build_visual_diff_model(business_diff, analysis, impact_groups)
    embedded = _embedded_model(html)
    node_ids = [str(item.get("nodeId")) for item in nodes]
    edge_ids = [str(item.get("edgeId")) for item in model.get("edges") or []]
    field_ids = [str(item.get("fieldId")) for item in model.get("fieldLineage") or []]
    risk_node_ids = [str(item.get("nodeId")) for item in risks]
    validation_node_ids = [
        str(item.get("nodeId")) for item in model.get("validations") or []
    ]
    impact_ids = [str(item.get("impactId")) for item in model.get("impacts") or []]
    known_endpoints = set(node_ids + field_ids + risk_node_ids + validation_node_ids + impact_ids)
    checks = {
        "summaryMatchesBusinessObjectDiff": model.get("summary", {}).get("businessObjects") == business_diff.get("summary"),
        "packagesAndDirectionMatchAnalysis": (
            model.get("packages", {}).get("old") == (analysis.get("analysisDirection") or {}).get("old")
            and model.get("packages", {}).get("new") == (analysis.get("analysisDirection") or {}).get("new")
            and model.get("directionResolution") == {
                key: value for key, value in (analysis.get("analysisDirection") or {}).items()
                if key not in {"old", "new"}
            }
        ),
        "allChangedBusinessObjectsRepresented": object_coverage,
        "businessChangeCountsMatch": all(
            model_counts.get(key, 0) == expected_counts.get(key, 0)
            for key in ("ADDED", "REMOVED", "UPDATED", "POSSIBLE_RENAME", "UNMATCHED", "UNCHANGED")
        ),
        "updatedExistsOnBothSides": all(
            item.get("oldExists") and item.get("newExists")
            for item in nodes if item.get("changeType") == "UPDATED"
        ),
        "removedExistsOnlyInOld": all(
            item.get("oldExists") and not item.get("newExists")
            for item in nodes if item.get("changeType") == "REMOVED"
        ),
        "addedExistsOnlyInNew": all(
            not item.get("oldExists") and item.get("newExists")
            for item in nodes if item.get("changeType") == "ADDED"
        ),
        "possibleRenameNotCountedAsUpdated": not any(
            item.get("changeType") == "UPDATED" and "POSSIBLE_RENAME" in (item.get("searchableText") or "")
            for item in nodes
        ),
        "packageUnitIsolationPreserved": package_units_match,
        "updatedFieldsHaveBeforeAndAfter": all(
            item.get("nodeId") in field_owners
            for item in nodes if item.get("changeType") == "UPDATED"
        ) and all(
            "before" in field and "after" in field
            for field in model.get("fieldLineage") or []
        ),
        "highRiskHasChangeEvidenceAndValidation": high_risk_traceable,
        "unknownUsesUncertainExpression": unknown_uncertain,
        "stableNodeIdsUniqueAndSorted": len(node_ids) == len(set(node_ids)) and node_ids == sorted(node_ids),
        "stableEdgeIdsUniqueAndSorted": len(edge_ids) == len(set(edge_ids)) and edge_ids == sorted(edge_ids),
        "allEdgeEndpointsResolve": all(
            edge.get("source") in known_endpoints and edge.get("target") in known_endpoints
            for edge in model.get("edges") or []
        ),
        "deterministicRebuildMatches": _canonical(rebuilt) == _canonical(model),
        "htmlEmbeddedModelMatchesFile": _canonical(embedded) == _canonical(client_model_projection(model)),
        "generationDoesNotUseCurrentTimeForIdentity": (
            (model.get("generationMetadata") or {}).get("currentTimeUsedForIdentityOrOrdering") is False
        ),
    }
    return {
        "schemaVersion": "ebuilder-visual-consistency-check/v1.0",
        "metrics": {
            "businessNodes": len(nodes),
            "edges": len(edge_ids),
            "businessChains": len(model.get("businessChains") or []),
            "fieldLineage": len(model.get("fieldLineage") or []),
            "risks": len(risks),
            "validations": len(model.get("validations") or []),
            "unknownItems": (model.get("unknownItems") or {}).get("total", 0),
            "modelSha256": hashlib.sha256(_canonical(model)).hexdigest(),
        },
        "checks": checks,
        "result": "PASS" if all(checks.values()) else "FAIL",
    }


def validate_visual_usability(html: str, model: dict[str, Any]) -> dict[str, Any]:
    lower = html.lower()
    remote_reference = bool(re.search(
        r'(?:src|href)\s*=\s*["\']\s*(?:https?:)?//',
        html,
        flags=re.IGNORECASE,
    ))
    absolute_path = bool(re.search(
        r'/Users/[^/]+/|[A-Za-z]:\\|file://|/private/tmp/|/var/folders/', html
    ))
    required_controls = [
        "packageFilter", "typeFilter", "changeFilter", "riskFilter",
        "searchInput", "resetButton", "drawer", "before-after",
    ]
    required_views = ["overview", "chains", "fields", "impacts"]
    checks = {
        "singleFileContainsCssAndJavaScript": "<style>" in lower and "<script>" in lower,
        "noRemoteOrCdnReferences": not remote_reference,
        "noLocalAbsolutePaths": not absolute_path,
        "noNetworkOrModuleLoading": all(token not in html for token in ("fetch(", "XMLHttpRequest", "import(", "type=\"module\"")),
        "embeddedModelPresent": 'id="visual-diff-data"' in html,
        "fourRequiredViewsPresent": all(f'id="{value}"' in html for value in required_views),
        "filtersSearchResetAndDetailPresent": all(value in html for value in required_controls),
        "beforeAndAfterVisible": "修改前" in html and "修改后" in html,
        "evidenceAndConfidenceVisible": all(value in html for value in ("已观察", "关系推断", "待确认", "待确认表示")),
        "largeDataAggregatedOnFirstScreen": "slice(0,80)" in html and "slice(0,100)" in html,
        "explicitEmptyStatesPresent": html.count("empty") >= 4 and "关系待确认" in html,
        "colorNotOnlySignal": all(value in html for value in ("新增", "删除", "更新", "疑似替代", "高风险")),
        "directOpenReadinessMarkerPresent": "window.__VISUAL_DIFF_READY__=true" in html,
        "htmlModelParseable": bool(model.get("schemaVersion")),
    }
    return {
        "schemaVersion": "ebuilder-visual-usability-check/v1.0",
        "metrics": {
            "htmlBytes": len(html.encode("utf-8")),
            "businessNodes": len(model.get("nodes") or []),
            "initialBusinessListLimit": 80,
            "initialFieldListLimit": 100,
            "views": len(required_views),
        },
        "checks": checks,
        "result": "PASS" if all(checks.values()) else "FAIL",
    }


def validate_visual_output(output: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    model = _read_json(_evidence_path(output, "visual-diff-model.json"))
    business_diff = _read_json(output / "business-object-diff.json")
    analysis = _read_json(_evidence_path(output, "comparison-analysis.json"))
    impacts = _read_jsonl(_evidence_path(output, "影响传播明细.jsonl"))
    html = (output / "应用版本差异可视化.html").read_text(encoding="utf-8")
    return (
        validate_visual_consistency(model, business_diff, analysis, impacts, html),
        validate_visual_usability(html, model),
    )


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    consistency, usability = validate_visual_output(args.output)
    _write_json(args.output / "可视化数据一致性校验.json", consistency)
    _write_json(args.output / "可视化可用性检查.json", usability)
    result = {
        "status": "PASS" if consistency["result"] == usability["result"] == "PASS" else "FAIL",
        "consistency": consistency,
        "usability": usability,
    }
    print(json.dumps(result, ensure_ascii=False))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
