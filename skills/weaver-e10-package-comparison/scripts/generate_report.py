#!/usr/bin/env python3
"""生成三层产物中的计算分析层与中文报告表达层。"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any


SEVERITY_ORDER = {"LOW": 0, "MEDIUM": 1, "UNKNOWN": 2, "HIGH": 3}
CHANGE_ORDER = ["ADDED", "REMOVED", "UPDATED", "POSSIBLE_RENAME", "UNMATCHED", "UNCHANGED"]


def _highest_severity(values: list[str]) -> str:
    return max(values or ["LOW"], key=lambda value: SEVERITY_ORDER.get(value, 2))


def _feature_change_type(counts: Counter[str]) -> str:
    active = {key for key, value in counts.items() if value and key != "UNCHANGED"}
    if len(active) == 1:
        return next(iter(active))
    if active <= {"ADDED", "REMOVED"} and len(active) == 2:
        return "UPDATED"
    if "UNMATCHED" in active and not active - {"UNMATCHED", "POSSIBLE_RENAME"}:
        return "UNMATCHED"
    return "UPDATED"


def _limited_unique(values, limit=20):
    result = []
    seen = set()
    for value in values:
        marker = None
        if isinstance(value, dict):
            marker = next(
                (
                    f"{key}:{value[key]}"
                    for key in (
                        "validationId", "riskId", "impactGroupId",
                        "changeId", "businessChangeId",
                    )
                    if value.get(key) not in (None, "")
                ),
                None,
            )
        if marker is None:
            marker = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(value)
        if len(result) >= limit:
            break
    return result


def build_analysis(
    *,
    old_metadata: dict[str, Any],
    new_metadata: dict[str, Any],
    facts: list[dict[str, Any]],
    impact_groups: list[dict[str, Any]],
    risks: list[dict[str, Any]],
    validations: list[dict[str, Any]],
    limitations: list[str],
) -> dict[str, Any]:
    impact_by_source = {
        (item["sourceModule"], item["sourceTable"].lower()): item
        for item in impact_groups
    }
    risk_by_id = {item["riskId"]: item for item in risks}
    validations_by_change: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for validation in validations:
        for change_id in validation["relatedChangeIds"]:
            validations_by_change[change_id].append(validation)
    changed = [fact for fact in facts if fact["changeType"] != "UNCHANGED"]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in changed:
        feature_id = fact.get("feature", {}).get("featureGroupId")
        group_key = feature_id or f"{fact['object']['module']}::{fact['object']['table']}"
        groups[group_key].append(fact)

    feature_changes = []
    for ordinal, (group_key, group_facts) in enumerate(sorted(groups.items()), 1):
        counts = Counter(fact["changeType"] for fact in group_facts)
        group_risks = _limited_unique(
            [
                risk_by_id[risk_id]
                for fact in group_facts
                for risk_id in fact.get("riskIds") or []
                if risk_id in risk_by_id
            ],
            50,
        )
        group_validations = _limited_unique(
            [
                validation
                for fact in group_facts
                for validation in validations_by_change.get(fact["changeId"], [])
            ],
            30,
        )
        impacts = _limited_unique([
            impact_by_source.get((
                fact["object"]["module"],
                fact["object"]["table"].lower(),
            ))
            for fact in group_facts
            if impact_by_source.get((
                fact["object"]["module"],
                fact["object"]["table"].lower(),
            ))
        ], 20)
        direct = _limited_unique([
            impact
            for group in impacts
            for impact in group.get("directImpacts") or []
        ], 30)
        indirect = _limited_unique([
            impact
            for group in impacts
            for impact in group.get("indirectImpacts") or []
        ], 30)
        paths = _limited_unique([
            path
            for fact in group_facts
            for path in fact.get("changedPaths") or []
        ], 30)
        categories = {path.get("category") for path in paths}
        before_examples = _limited_unique(
            [fact.get("before") for fact in group_facts if fact.get("before") is not None],
            3,
        )
        after_examples = _limited_unique(
            [fact.get("after") for fact in group_facts if fact.get("after") is not None],
            3,
        )
        unknowns = []
        if any(fact["changeType"] == "UNMATCHED" for fact in group_facts):
            unknowns.append("部分对象缺少稳定业务键或存在多个候选，未强行匹配。")
        if any(fact["changeType"] == "POSSIBLE_RENAME" for fact in group_facts):
            unknowns.append("疑似重命名需要业务负责人确认同一业务身份。")
        if any(fact["object"].get("unresolvedReferences") for fact in group_facts):
            unknowns.append("部分 ID 或 JSON 内嵌引用无法由包内证据稳定解析。")
        business_name = group_facts[0].get("feature", {}).get("businessName")
        purpose = group_facts[0].get("feature", {}).get("businessPurpose") or ""
        user_visible = (
            group_facts[0].get("feature", {}).get("userVisibleFunctions")
            or f"用户可能感知到“{business_name}”相关配置、入口、数据或交互发生变化。"
        )
        data_impact = (
            "涉及字段、表结构、数据集或存量数据语义，应核对历史数据兼容与新写入约束。"
            if categories & {"DATA_SEMANTICS", "REFERENCE_ID"}
            or any("field" in fact["object"]["table"].lower() for fact in group_facts)
            else "未从字段路径直接观察到结构性数据变化；仍需按关联影响验证代表数据。"
        )
        feature_changes.append({
            "businessChangeId": f"BIZ-{ordinal:05d}",
            "groupKey": group_key,
            "module": group_facts[0]["object"]["module"],
            "moduleKind": group_facts[0]["object"]["moduleKind"],
            "businessFunction": business_name,
            "businessPurpose": purpose,
            "changeType": _feature_change_type(counts),
            "rawChangeCounts": dict(counts),
            "riskLevel": _highest_severity(
                [fact.get("riskLevel", "UNKNOWN") for fact in group_facts]
            ),
            "changeIds": sorted(fact["changeId"] for fact in group_facts),
            "tables": sorted({fact["object"]["table"] for fact in group_facts}),
            "before": before_examples,
            "after": after_examples,
            "changedPaths": paths,
            "userVisibleChange": user_visible,
            "directImpacts": direct,
            "inferredImpacts": indirect,
            "dataImpact": data_impact,
            "migrationRisks": [
                {
                    "riskId": risk["riskId"],
                    "severity": risk["severity"],
                    "title": risk["title"],
                    "evidenceLevel": risk["evidenceLevel"],
                }
                for risk in group_risks
            ],
            "configurationChecks": [
                validation
                for validation in group_validations
                if validation["type"] == "CONFIGURATION_CHECK"
            ],
            "businessTests": [
                validation
                for validation in group_validations
                if validation["type"] != "CONFIGURATION_CHECK"
            ],
            "packageEvidence": _limited_unique([
                {
                    "module": fact["object"]["module"],
                    "table": fact["object"]["table"],
                    "logicalKey": fact["object"]["logicalKey"],
                    "sourceEvidence": fact["object"].get("sourceEvidence"),
                }
                for fact in group_facts
            ], 30),
            "knowledgeEvidence": {
                "codexConfigIds": sorted({
                    config_id
                    for fact in group_facts
                    for config_id in fact.get("knowledgeEvidence", {}).get("codexConfigIds", [])
                }),
                "codexNodeIds": sorted({
                    node_id
                    for fact in group_facts
                    for node_id in fact.get("knowledgeEvidence", {}).get("codexNodeIds", [])
                    if node_id
                }),
                "claudeSemanticEvidenceIds": sorted({
                    evidence_id
                    for fact in group_facts
                    for evidence_id in fact.get("knowledgeEvidence", {}).get("claudeSemanticEvidenceIds", [])
                    if evidence_id
                }),
                "authorityPolicy": "Codex 事实决定计算；Claude 仅用于业务聚合和中文表达。",
            },
            "unknowns": unknowns,
        })

    counts = Counter(fact["changeType"] for fact in facts)
    module_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for fact in facts:
        module_counts[fact["object"]["module"]][fact["changeType"]] += 1
    unknown_items = [
        {
            "changeId": fact["changeId"],
            "module": fact["object"]["module"],
            "table": fact["object"]["table"],
            "logicalKey": fact["object"]["logicalKey"],
            "reason": (
                "无法稳定匹配"
                if fact["changeType"] == "UNMATCHED"
                else "疑似重命名，需确认"
            ),
            "candidates": fact.get("matchCandidates") or [],
        }
        for fact in changed
        if fact["changeType"] in {"UNMATCHED", "POSSIBLE_RENAME"}
    ]
    unknown_items.extend({
        "riskId": risk["riskId"],
        "reason": risk.get("uncertaintyStatement") or risk["title"],
        "affectedChangeIds": risk["affectedChangeIds"],
    } for risk in risks if risk["severity"] == "UNKNOWN")
    return {
        "schemaVersion": "ebuilder-comparison-analysis/v1.0",
        "analysisDirection": {
            "old": old_metadata,
            "new": new_metadata,
            "directionSource": "EXPLICIT_CLI_ARGUMENTS",
            "filenameInferenceUsed": False,
        },
        "summary": {
            "totalComparedObjects": len(facts),
            "byChangeType": {key: counts.get(key, 0) for key in CHANGE_ORDER},
            "changedObjects": sum(
                value for key, value in counts.items() if key != "UNCHANGED"
            ),
            "businessFeatureChanges": len(feature_changes),
            "risks": len(risks),
            "highRisks": sum(risk["severity"] == "HIGH" for risk in risks),
            "unknownRisks": sum(risk["severity"] == "UNKNOWN" for risk in risks),
            "validationPoints": len(validations),
            "sourceIdOnlyChangesSuppressed": sum(
                fact.get("sourceIdOnlyChange", False) for fact in facts
            ),
            "byModule": {
                module: {key: values.get(key, 0) for key in CHANGE_ORDER}
                for module, values in sorted(module_counts.items())
            },
        },
        "featureChanges": feature_changes,
        "risks": risks,
        "validationPoints": validations,
        "unknownItems": unknown_items,
        "limitations": limitations,
        "staticAnalysisDisclaimer": (
            "本结果来自两个离线包及内置知识的静态计算，未执行迁入，也未验证目标环境运行结果。"
        ),
    }


def _text(value: Any, limit: int = 1200) -> str:
    if value in (None, "", [], {}):
        return "无"
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return text if len(text) <= limit else text[:limit] + "…"


def _impact_text(items: list[dict[str, Any]]) -> str:
    if not items:
        return "未从关系图观察到明确影响路径"
    return "；".join(
        f"{item.get('targetModule')} / {item.get('targetTable')}（{item.get('direction')}，证据 {item.get('evidenceLevel')}）"
        for item in items[:12]
    )


def _validation_text(items: list[dict[str, Any]], field: str) -> str:
    if not items:
        return "无"
    values = []
    for item in items[:5]:
        value = item.get(field)
        if isinstance(value, list):
            values.extend(str(child) for child in value)
        elif value:
            values.append(str(value))
    return "；".join(values) if values else "无"


def render_markdown(analysis: dict[str, Any]) -> str:
    summary = analysis["summary"]
    direction = analysis["analysisDirection"]
    lines = [
        "# 应用版本功能差异报告",
        "",
        "## 一、领导与客户结论",
        "",
        f"- 本次明确以 **{direction['old']['name']}** 为旧版本、**{direction['new']['name']}** 为新版本；未根据文件名推断方向。",
        f"- 共比较 {summary['totalComparedObjects']} 个逻辑对象，其中新增 {summary['byChangeType']['ADDED']}、删除 {summary['byChangeType']['REMOVED']}、更新 {summary['byChangeType']['UPDATED']}、疑似重命名 {summary['byChangeType']['POSSIBLE_RENAME']}、无法匹配 {summary['byChangeType']['UNMATCHED']}、未变化 {summary['byChangeType']['UNCHANGED']}。",
        f"- 共聚合 {summary['businessFeatureChanges']} 项业务功能变化，触发 {summary['risks']} 个去重风险根因，其中高风险 {summary['highRisks']}、未知风险 {summary['unknownRisks']}；生成 {summary['validationPoints']} 个配置检查或业务验证点。",
        f"- 已识别并抑制 {summary['sourceIdOnlyChangesSuppressed']} 项仅源主键变化，避免把源环境 ID 变化误判为功能变化。",
        "- 本报告是迁入前静态分析，不能证明实际迁入结果，也不能替代目标环境运行验收。",
        "",
        "## 二、输入、方向与指纹",
        "",
        "| 角色 | 文件 | 大小（字节） | SHA-256 | 模块 | 解析错误 |",
        "|---|---|---:|---|---|---:|",
        f"| old | {direction['old']['name']} | {direction['old']['size']} | `{direction['old']['sha256']}` | {', '.join(direction['old']['modules'])} | {direction['old']['parseErrors']} |",
        f"| new | {direction['new']['name']} | {direction['new']['size']} | `{direction['new']['sha256']}` | {', '.join(direction['new']['modules'])} | {direction['new']['parseErrors']} |",
        "",
        "## 三、整体变化汇总",
        "",
        "| 类型 | 数量 |",
        "|---|---:|",
    ]
    for key in CHANGE_ORDER:
        lines.append(f"| {key} | {summary['byChangeType'][key]} |")
    lines.extend([
        "",
        "### 模块统计",
        "",
        "| 模块 | ADDED | REMOVED | UPDATED | POSSIBLE_RENAME | UNMATCHED | UNCHANGED |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for module, counts in summary["byModule"].items():
        lines.append(
            f"| {module} | {counts['ADDED']} | {counts['REMOVED']} | {counts['UPDATED']} | "
            f"{counts['POSSIBLE_RENAME']} | {counts['UNMATCHED']} | {counts['UNCHANGED']} |"
        )
    lines.extend(["", "## 四、业务功能变化明细", ""])
    for item in analysis["featureChanges"]:
        checks = item["configurationChecks"]
        tests = item["businessTests"]
        risk_text = "；".join(
            f"{risk['riskId']}({risk['severity']}) {risk['title']}"
            for risk in item["migrationRisks"][:12]
        ) or "未触发内置风险规则"
        lines.extend([
            f"### {item['businessChangeId']} {item['businessFunction']}",
            "",
            f"- **所属模块**：{item['module']}（{item['moduleKind']}）",
            f"- **变化类型**：{item['changeType']}；原始变化计数：{_text(item['rawChangeCounts'])}",
            f"- **风险等级**：{item['riskLevel']}",
            f"- **修改前**：{_text(item['before'])}",
            f"- **修改后**：{_text(item['after'])}",
            f"- **字段级变化**：{_text(item['changedPaths'])}",
            f"- **用户可感知变化**：{item['userVisibleChange']}",
            f"- **直接影响**：{_impact_text(item['directImpacts'])}",
            f"- **推断影响**：{_impact_text(item['inferredImpacts'])}",
            f"- **数据影响**：{item['dataImpact']}",
            f"- **迁入风险**：{risk_text}",
            f"- **配置检查点**：{_validation_text(checks, 'title')}；步骤：{_validation_text(checks, 'steps')}",
            f"- **业务测试前置条件**：{_validation_text(tests, 'preconditions')}",
            f"- **测试步骤**：{_validation_text(tests, 'steps')}",
            f"- **预期结果**：{_validation_text(tests, 'expectedResult')}",
            f"- **需要保留的截图或日志**：{_validation_text(tests, 'evidenceToKeep')}",
            f"- **适用终端、角色和分支**：{_validation_text(tests, 'applicability')}",
            f"- **包内证据**：{_text(item['packageEvidence'])}",
            f"- **知识库证据**：{_text(item['knowledgeEvidence'])}",
            f"- **未确认项**：{'；'.join(item['unknowns']) if item['unknowns'] else '无'}",
            "",
        ])
    lines.extend([
        "## 五、风险总览",
        "",
        "| 风险编号 | 等级 | 类型 | 受影响变化数 | 证据等级 | 说明 |",
        "|---|---|---|---:|---|---|",
    ])
    for risk in analysis["risks"]:
        title = str(risk["title"]).replace("|", "｜").replace("\n", " ")
        lines.append(
            f"| {risk['riskId']} | {risk['severity']} | {risk['riskType']} | "
            f"{len(risk['affectedChangeIds'])} | {risk['evidenceLevel']} | {title[:260]} |"
        )
    lines.extend([
        "",
        "## 六、配置检查与业务验证清单",
        "",
    ])
    for validation in analysis["validationPoints"]:
        lines.extend([
            f"### {validation['validationId']} {validation['title']}",
            "",
            f"- 类型：{validation['type']}",
            f"- 关联变化：{', '.join(validation['relatedChangeIds'][:50])}",
            f"- 前置条件：{'；'.join(validation['preconditions'])}",
            f"- 步骤：{'；'.join(validation['steps'])}",
            f"- 预期结果：{validation['expectedResult']}",
            f"- 保留证据：{'；'.join(validation['evidenceToKeep'])}",
            f"- 终端/角色/分支：{_text(validation['applicability'])}",
            "",
        ])
    lines.extend([
        "## 七、无法确认项与证据限制",
        "",
        f"- 无法确认项共 {len(analysis['unknownItems'])} 条，完整明细见 `无法确认项.jsonl`。",
    ])
    for limitation in analysis["limitations"]:
        lines.append(f"- {limitation}")
    lines.extend([
        "",
        "## 八、结论边界",
        "",
        f"- {analysis['staticAnalysisDisclaimer']}",
        "- 未提供目标环境、运行日志和迁入过程证据，因此不得据此宣称目标部署完成或业务运行已验收。",
        "- OBSERVED 表示离线包或内置 Codex 知识直接证据；INFERRED 表示关系传播或业务语义推断；UNKNOWN 表示需要目标映射、数据库或运行证据确认。",
        "",
    ])
    return "\n".join(lines)
