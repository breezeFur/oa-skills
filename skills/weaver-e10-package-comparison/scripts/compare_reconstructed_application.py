#!/usr/bin/env python3
"""Compare two reconstruct-ebuilder-application business maps.

This is an intentionally separate experiment.  It consumes the business-function
map and Application IR produced by reconstruct-ebuilder-application; it does not
change either skill and it does not compare raw service/table records.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from customer_text_guard import find_customer_text_leaks


FIELD_LABELS = {
    "entries": "入口",
    "pages": "页面",
    "forms": "表单和业务数据",
    "entities": "业务数据对象",
    "datasets": "查询和统计数据",
    "actionFlows": "动作流",
    "workflows": "审批流程",
    "menus": "菜单",
    "permissions": "权限范围",
    "integrations": "协作和系统集成",
    "dependencies": "关联功能",
    "terminals": "使用终端",
    "userActions": "用户操作",
    "successOutcome": "业务结果",
    "failurePaths": "异常处理",
    "unresolved": "待确认事项",
    "workflowBrowserDataScopes": "审批浏览数据范围",
    "workflowNodePostValidations": "审批节点后校验",
    "workflowSqlDatasources": "工作流 SQL 数据源",
}
COMPARE_FIELDS = tuple(FIELD_LABELS)
MAX_NAMES_PER_LINE = 12
PLACEHOLDER_PATTERNS = (
    "未观察到明确对象", "终端范围待目标环境确认", "使用角色待目标组织映射确认",
    "根据保存态配置执行相关业务处理", "保存态配置表明", "目标 Builder 或组件适配器",
    "目标外部资源未映射", "无功能级明确未解决项", "仍需运行验证",
    "adapter:", "external-page-reference-resolution", "target-builder-contract",
)


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def find_file(folder: Path, pattern: str) -> Path:
    matches = sorted(folder.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"{folder} 中未找到 {pattern}")
    return matches[0]


def load_side(folder: Path) -> dict[str, Any]:
    report_dir = folder / "应用业务报告"
    mapping_path = find_file(report_dir, "*业务功能映射.json")
    report_path = find_file(report_dir, "*应用功能全景报告.md")
    ir_path = folder / "application-ir.json"
    mapping = read_json(mapping_path)
    ir = read_json(ir_path) if ir_path.exists() else {}
    return {
        "folder": str(folder),
        "mappingPath": str(mapping_path),
        "reportPath": str(report_path),
        "mapping": mapping,
        "ir": ir,
        "nameMap": build_name_map(ir),
        "workflowMap": {
            item.get("logicalKey"): item
            for item in ir.get("workflows", [])
            if item.get("logicalKey")
        },
    }


def build_name_map(value: Any) -> dict[str, str]:
    result: dict[str, str] = {}

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            key = node.get("logicalKey")
            name = node.get("name")
            if isinstance(key, str) and isinstance(name, str) and name.strip():
                result.setdefault(key, name.strip())
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    return result


def strip_ids(text: str) -> str:
    text = text.replace("~`~`", "").replace("`", "").replace("~", "")
    # 环境当前 ID 可能位于冒号、斜线或括号之后，不能只清理 `-123` 形态。
    text = re.sub(r"(?<![0-9])\d{16,}(?![0-9])", "", text)
    text = re.sub(r"/[0-9a-f]{16,}", "", text, flags=re.I)
    text = re.sub(r"[-_][0-9]{12,}", "", text)
    text = re.sub(r"[-_][0-9a-f]{16,}", "", text, flags=re.I)
    # dataset-source 是报表/数据集关系的内部后缀，不是客户业务名称。
    text = re.sub(r"(?:[-_:/ ]+)?dataset[-_]source\b", "", text, flags=re.I)
    text = re.sub(r"(?:[-_: ]+)(?:report|page|form|menu|dataset|entity|permission)[-_](?:view|source)\b", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" -_/:：")
    return text


def clean_business_name(text: str) -> str:
    text = strip_ids(text)
    text = re.sub(r"^(?:SUP|GOTS|ESB)-[\w.]+\s*", "", text, flags=re.I)
    text = re.sub(r"^(?:report|entity|form|page|menu|flow|dataset|permission|integration)-", "", text, flags=re.I)
    text = re.sub(r"[(_ -]?\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}:\d{2})?\)?", "", text)
    text = re.sub(r"(?:[-_:/ ]+)(?:source[_-]?id|import[_-]?id)\b", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" -_")
    return text


def friendly(ref: Any, name_map: dict[str, str]) -> str:
    if not isinstance(ref, str):
        return str(ref)
    if ref in name_map:
        name = clean_business_name(name_map[ref])
        name = re.sub(r"^(?:pc-mobile|pc|mobile)-", "", name, flags=re.I)
        if name and re.search(r"[\u3400-\u9fff]", name):
            return name
    # Most logical keys use a business name after the first colon.  Keep Chinese
    # names, but never expose a long source identifier in the customer report.
    candidate = ref.split(":", 1)[1] if ":" in ref else ref
    candidate = clean_business_name(candidate)
    candidate = re.sub(r"/component:.*$", "", candidate)
    candidate = re.sub(r"/node:.*$", "", candidate)
    # Do not leak opaque source labels such as entity-uf_xxx, form-reference,
    # page-component or adapter names into the customer-facing comparison.
    if not candidate or not re.search(r"[\u3400-\u9fff]", candidate):
        return "未命名业务对象"
    candidate = re.sub(r"^(?:entity|form|page|menu|flow|dataset|permission|integration)-", "", candidate, flags=re.I)
    candidate = re.sub(r"^(?:pc-mobile|pc|mobile)-", "", candidate, flags=re.I)
    candidate = re.sub(r"-(?:field|component|node|detail|to|from)-.*$", "", candidate, flags=re.I)
    return candidate


def display_set(values: Iterable[Any], name_map: dict[str, str]) -> set[str]:
    result = set()
    for value in values or []:
        name = friendly(value, name_map)
        if name and name != "未命名业务对象" and not any(p in name for p in PLACEHOLDER_PATTERNS):
            result.add(name)
    return result


def domain_key(domain: dict[str, Any]) -> str:
    return str(domain.get("logicalKey", ""))


def card_kind(card: dict[str, Any]) -> str:
    key = str(card.get("logicalKey", ""))
    return key.rsplit(":", 1)[-1]


def card_signature(card: dict[str, Any], name_map: dict[str, str]) -> set[str]:
    signature: set[str] = set()
    for field in ("entries", "pages", "forms", "entities", "datasets", "actionFlows", "workflows", "menus", "integrations"):
        signature |= display_set(card.get(field, []), name_map)
    return signature


def similarity(a: str, b: str) -> float:
    a = re.sub(r"[\s（）()\-—_]+", "", a)
    b = re.sub(r"[\s（）()\-—_]+", "", b)
    return difflib.SequenceMatcher(None, a, b).ratio()


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def match_domains(old: dict[str, Any], new: dict[str, Any]) -> tuple[list[dict[str, Any]], set[str], set[str]]:
    od = {domain_key(x): x for x in old["mapping"].get("businessDomains", [])}
    nd = {domain_key(x): x for x in new["mapping"].get("businessDomains", [])}
    pairs: list[dict[str, Any]] = []
    old_unmatched = set(od) - set(nd)
    new_unmatched = set(nd) - set(od)
    for key in sorted(set(od) & set(nd)):
        pairs.append({"old": od[key], "new": nd[key], "match": "same"})

    # A domain renamed by the reconstructor (for example 督办类型 -> 督办) is
    # not reported as a false delete+add when its card kinds/objects agree.
    candidates: list[tuple[float, str, str]] = []
    old_cards = {c["logicalKey"]: c for c in old["mapping"].get("functionCards", [])}
    new_cards = {c["logicalKey"]: c for c in new["mapping"].get("functionCards", [])}
    for ok in old_unmatched:
        odomain = od[ok]
        for nk in new_unmatched:
            ndomain = nd[nk]
            oname, nname = odomain.get("name", ""), ndomain.get("name", "")
            name_score = similarity(oname, nname)
            osuffix = {card_kind(old_cards[c]) for c in odomain.get("functionCards", []) if c in old_cards}
            nsuffix = {card_kind(new_cards[c]) for c in ndomain.get("functionCards", []) if c in new_cards}
            kind_score = jaccard(osuffix, nsuffix)
            score = 0.65 * name_score + 0.35 * kind_score
            if score >= 0.58 and (osuffix & nsuffix):
                candidates.append((score, ok, nk))
    used_old: set[str] = set()
    used_new: set[str] = set()
    for score, ok, nk in sorted(candidates, reverse=True):
        if ok in used_old or nk in used_new:
            continue
        pairs.append({"old": od[ok], "new": nd[nk], "match": "renamed", "score": round(score, 3)})
        used_old.add(ok)
        used_new.add(nk)
    return pairs, old_unmatched - used_old, new_unmatched - used_new


def object_name_list(values: Iterable[Any], name_map: dict[str, str]) -> list[str]:
    return sorted(display_set(values, name_map), key=lambda x: (len(x), x))


def list_delta(old_values: Iterable[Any], new_values: Iterable[Any], old_names: dict[str, str], new_names: dict[str, str]) -> dict[str, Any]:
    old_set = display_set(old_values, old_names)
    new_set = display_set(new_values, new_names)
    return {"added": sorted(new_set - old_set), "removed": sorted(old_set - new_set), "oldCount": len(old_set), "newCount": len(new_set)}


def workflow_scope_delta(old_card: dict[str, Any], new_card: dict[str, Any], old_side: dict[str, Any], new_side: dict[str, Any]) -> dict[str, Any] | None:
    old_refs = set(old_card.get("workflows", []))
    new_refs = set(new_card.get("workflows", []))
    old_values, new_values = set(), set()
    changed_objects: list[dict[str, Any]] = []
    for ref in old_refs & new_refs:
        old_workflow = old_side.get("workflowMap", {}).get(ref, {})
        new_workflow = new_side.get("workflowMap", {}).get(ref, {})
        old_name = old_workflow.get("name") or new_workflow.get("name") or "未命名审批流程"
        new_name = new_workflow.get("name") or old_workflow.get("name") or "未命名审批流程"
        old_scopes = {
            str(item.get("businessDescription"))
            for item in old_workflow.get("browserDataScopes", [])
            if item.get("businessDescription")
        }
        new_scopes = {
            str(item.get("businessDescription"))
            for item in new_workflow.get("browserDataScopes", [])
            if item.get("businessDescription")
        }
        if old_scopes == new_scopes:
            continue
        old_values.update(f"{old_name}：{value}" for value in old_scopes)
        new_values.update(f"{new_name}：{value}" for value in new_scopes)
        changed_objects.append({
            "objectType": "WORKFLOW",
            "objectTypeLabel": "审批流程",
            "logicalKey": ref,
            "oldName": old_name,
            "newName": new_name,
            "differences": {
                "workflowBrowserDataScopes": {
                    "added": sorted(new_scopes - old_scopes),
                    "removed": sorted(old_scopes - new_scopes),
                    "oldCount": len(old_scopes),
                    "newCount": len(new_scopes),
                }
            },
        })
    if old_values == new_values:
        return None
    return {
        "delta": {
            "added": sorted(new_values - old_values),
            "removed": sorted(old_values - new_values),
            "oldCount": len(old_values),
            "newCount": len(new_values),
        },
        "changedObjects": sorted(changed_objects, key=lambda x: (x.get("newName") or x.get("oldName") or "", x.get("logicalKey") or "")),
    }


def load_workflow_node_validations(path: Path | None) -> dict[str, list[dict[str, Any]]]:
    if not path:
        return {}
    model = read_json(path)
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in model.get("objects") or []:
        if item.get("objectType") != "WORKFLOW" or item.get("changeType") != "UPDATED":
            continue
        name = str(item.get("businessName") or item.get("name") or "").strip()
        if not name:
            continue
        for change in item.get("internalChanges") or []:
            if change.get("kind") == "NODE_POST_VALIDATION_CHANGED":
                result[name].append(change)
    return dict(result)


def load_workflow_sql_datasources(path: Path | None) -> dict[str, list[dict[str, Any]]]:
    if not path:
        return {}
    model = read_json(path)
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in model.get("objects") or []:
        if item.get("objectType") != "WORKFLOW" or item.get("changeType") != "UPDATED":
            continue
        name = str(item.get("businessName") or item.get("name") or "").strip()
        if not name:
            continue
        for change in item.get("internalChanges") or []:
            if change.get("kind") == "WORKFLOW_SQL_DATASOURCE_CHANGED":
                result[name].append(change)
    return dict(result)


def _validation_side_text(workflow_name: str, change: dict[str, Any], side: str) -> str:
    old_side = side == "old"
    rule_count = change.get("oldRuleCount" if old_side else "newRuleCount", 0)
    enabled_count = change.get("oldEnabledCount" if old_side else "newEnabledCount", 0)
    rules = change.get("effectiveBefore" if old_side else "effectiveAfter") or []
    details = []
    for rule in rules:
        name = str(rule.get("name") or "未命名校验规则")
        condition = str(rule.get("condition") or "条件内容待确认")
        failure = str(rule.get("failureHandling") or "")
        details.append(f"“{name}”：{condition}" + (f"（不通过时{failure}）" if failure else ""))
    effective = "；".join(details) if details else "无启用规则"
    return (
        f"{workflow_name}：{change.get('nodeName') or '未命名流程节点'}节点，"
        f"规则 {rule_count} 条（启用 {enabled_count} 条），有效校验：{effective}"
    )


def workflow_post_validation_delta(
    old_card: dict[str, Any],
    new_card: dict[str, Any],
    old_side: dict[str, Any],
    new_side: dict[str, Any],
    workflow_changes: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    old_refs = set(old_card.get("workflows", []))
    new_refs = set(new_card.get("workflows", []))
    old_values, new_values = set(), set()
    changed_objects = []
    for ref in old_refs & new_refs:
        old_workflow = old_side.get("workflowMap", {}).get(ref, {})
        new_workflow = new_side.get("workflowMap", {}).get(ref, {})
        old_name = old_workflow.get("name") or new_workflow.get("name") or "未命名审批流程"
        new_name = new_workflow.get("name") or old_workflow.get("name") or "未命名审批流程"
        changes = workflow_changes.get(str(new_name)) or workflow_changes.get(str(old_name)) or []
        if not changes:
            continue
        object_old, object_new = [], []
        for change in changes:
            before = _validation_side_text(str(old_name), change, "old")
            after = _validation_side_text(str(new_name), change, "new")
            old_values.add(before)
            new_values.add(after)
            object_old.append(before)
            object_new.append(after)
        changed_objects.append({
            "objectType": "WORKFLOW",
            "objectTypeLabel": "审批流程",
            "logicalKey": ref,
            "oldName": old_name,
            "newName": new_name,
            "differences": {
                "workflowNodePostValidations": {
                    "added": sorted(set(object_new) - set(object_old)),
                    "removed": sorted(set(object_old) - set(object_new)),
                    "oldCount": len(object_old),
                    "newCount": len(object_new),
                }
            },
        })
    if old_values == new_values:
        return None
    return {
        "delta": {
            "added": sorted(new_values - old_values),
            "removed": sorted(old_values - new_values),
            "oldCount": len(old_values),
            "newCount": len(new_values),
        },
        "changedObjects": changed_objects,
    }


def _sql_datasource_side_text(workflow_name: str, change: dict[str, Any], side: str) -> str:
    summary = change.get("before" if side == "old" else "after") or {}
    if not summary:
        return f"{workflow_name}：无工作流 SQL 数据源"
    identity = change.get("identityConclusion")
    identity_text = {
        "SAME_SOURCE": "同源配置",
        "RECREATED_OR_REBOUND": "数据集记录疑似重建或重新绑定",
        "IDENTITY_UNCONFIRMED": "同源身份未确认，按配置重建候选处理",
        "ADDED": "新增数据源",
        "REMOVED": "已移除数据源",
    }.get(identity, "身份待确认")
    checks = summary.get("staticChecks") or {}
    static_text = "离线静态校验通过" if all(checks.values()) else "部分静态检查待复核"
    inputs = "、".join(summary.get("inputs") or []) or "未声明参数"
    outputs = "、".join(summary.get("outputTypes") or []) or "未声明类型"
    runtime = "运行待验证" if summary.get("runtimePending") else "运行信息已提供"
    return (
        f"{workflow_name}：{identity_text}；{summary.get('querySummary') or '查询语义待确认'}；"
        f"输入参数：{inputs}；输出类型：{outputs}；{static_text}；{runtime}"
    )


def workflow_sql_datasource_delta(
    old_card: dict[str, Any],
    new_card: dict[str, Any],
    old_side: dict[str, Any],
    new_side: dict[str, Any],
    workflow_changes: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    old_refs = set(old_card.get("workflows", []))
    new_refs = set(new_card.get("workflows", []))
    old_values, new_values = set(), set()
    changed_objects = []
    for ref in old_refs & new_refs:
        old_workflow = old_side.get("workflowMap", {}).get(ref, {})
        new_workflow = new_side.get("workflowMap", {}).get(ref, {})
        old_name = old_workflow.get("name") or new_workflow.get("name") or "未命名审批流程"
        new_name = new_workflow.get("name") or old_workflow.get("name") or "未命名审批流程"
        changes = workflow_changes.get(str(new_name)) or workflow_changes.get(str(old_name)) or []
        if not changes:
            continue
        object_old, object_new = [], []
        for change in changes:
            before = _sql_datasource_side_text(str(old_name), change, "old")
            after = _sql_datasource_side_text(str(new_name), change, "new")
            old_values.add(before)
            new_values.add(after)
            object_old.append(before)
            object_new.append(after)
        changed_objects.append({
            "objectType": "WORKFLOW",
            "objectTypeLabel": "审批流程",
            "logicalKey": ref,
            "oldName": old_name,
            "newName": new_name,
            "differences": {
                "workflowSqlDatasources": {
                    "added": sorted(set(object_new) - set(object_old)),
                    "removed": sorted(set(object_old) - set(object_new)),
                    "oldCount": len(object_old),
                    "newCount": len(object_new),
                }
            },
        })
    if old_values == new_values:
        return None
    return {
        "delta": {
            "added": sorted(new_values - old_values),
            "removed": sorted(old_values - new_values),
            "oldCount": len(old_values),
            "newCount": len(new_values),
        },
        "changedObjects": changed_objects,
    }


def _merge_changed_objects(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for group in groups:
        for item in group:
            key = str(item.get("logicalKey") or item.get("newName") or item.get("oldName") or "")
            if key not in merged:
                merged[key] = dict(item)
                merged[key]["differences"] = dict(item.get("differences") or {})
            else:
                merged[key]["differences"].update(item.get("differences") or {})
    return sorted(merged.values(), key=lambda x: (x.get("newName") or x.get("oldName") or "", x.get("logicalKey") or ""))


def compare_card(
    old_card: dict[str, Any] | None,
    new_card: dict[str, Any] | None,
    old_side: dict[str, Any],
    new_side: dict[str, Any],
    change_type: str,
    workflow_validations: dict[str, list[dict[str, Any]]] | None = None,
    workflow_sql_datasources: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    old_card = old_card or {}
    new_card = new_card or {}
    diffs: dict[str, Any] = {}
    for field in COMPARE_FIELDS:
        delta = list_delta(old_card.get(field, []), new_card.get(field, []), old_side["nameMap"], new_side["nameMap"])
        if delta["added"] or delta["removed"] or delta["oldCount"] != delta["newCount"]:
            diffs[field] = delta
    changed_objects: list[dict[str, Any]] = []
    if old_card and new_card:
        scope_change = workflow_scope_delta(old_card, new_card, old_side, new_side)
        if scope_change:
            diffs["workflowBrowserDataScopes"] = scope_change["delta"]
            changed_objects = scope_change["changedObjects"]
        validation_change = workflow_post_validation_delta(
            old_card, new_card, old_side, new_side, workflow_validations or {}
        )
        if validation_change:
            diffs["workflowNodePostValidations"] = validation_change["delta"]
            changed_objects = _merge_changed_objects(
                changed_objects, validation_change["changedObjects"]
            )
        sql_change = workflow_sql_datasource_delta(
            old_card, new_card, old_side, new_side, workflow_sql_datasources or {}
        )
        if sql_change:
            diffs["workflowSqlDatasources"] = sql_change["delta"]
            changed_objects = _merge_changed_objects(
                changed_objects, sql_change["changedObjects"]
            )
    business_function_name = new_card.get("name") or old_card.get("name") or "未命名业务功能"
    display_name = business_function_name
    subject_type = "业务功能"
    if changed_objects and set(diffs).issubset({
        "workflowBrowserDataScopes", "workflowNodePostValidations", "workflowSqlDatasources",
    }):
        display_name = "、".join(
            item.get("newName") or item.get("oldName") or "未命名审批流程"
            for item in changed_objects
        )
        subject_type = "审批流程"
    return {
        "changeType": change_type,
        "oldLogicalKey": old_card.get("logicalKey"),
        "newLogicalKey": new_card.get("logicalKey"),
        "oldName": old_card.get("name"),
        "newName": new_card.get("name"),
        "displayName": display_name,
        "businessFunctionName": business_function_name,
        "subjectType": subject_type,
        "changedObjects": changed_objects,
        "oldDomain": old_card.get("domain"),
        "newDomain": new_card.get("domain"),
        "purpose": new_card.get("purpose") or old_card.get("purpose"),
        "differences": diffs,
        "status": new_card.get("status") or old_card.get("status"),
        "unresolved": sorted(display_set(set(old_card.get("unresolved", [])) | set(new_card.get("unresolved", [])), new_side["nameMap"])),
    }


def make_test_points(change: dict[str, Any]) -> list[dict[str, Any]]:
    name = change.get("displayName") or change.get("newName") or change.get("oldName") or "该业务功能"
    kind = change["changeType"]
    points: list[dict[str, Any]] = []
    if kind == "新增":
        points.append({"priority": "高", "title": f"验证{name}可以从新增入口正常进入", "scenario": "检查菜单/页面入口可见，按主要操作完成一次完整业务处理，确认页面展示、保存结果和权限范围符合预期。"})
    elif kind == "删除":
        points.append({"priority": "高", "title": f"确认{name}下线后的入口和关联功能", "scenario": "检查旧入口不再向用户展示；同时检查原有菜单、页面、表单和自动化没有出现空白页、失效跳转或异常提示。"})
    else:
        points.append({"priority": "高", "title": f"回归{name}的主业务路径", "scenario": "从用户入口进入，完成新增或调整后的主要操作，确认页面、表单、动作流/审批和业务结果能够连贯完成。"})
    aspect_text = {
        "entries": "入口和菜单可见性",
        "pages": "页面打开、组件展示和页面跳转",
        "forms": "表单录入、保存、查询和字段展示",
        "entities": "业务数据新增、修改、查询及关联关系",
        "datasets": "列表、统计和查询结果",
        "actionFlows": "动作流触发、分支、失败提示和重复执行",
        "workflows": "提交、审批节点、操作者、退回和状态回写",
        "workflowBrowserDataScopes": "流程表单浏览字段的数据过滤范围",
        "workflowNodePostValidations": "审批节点提交后的规则校验、失败提示和阻断方式",
        "workflowSqlDatasources": "工作流 SQL 数据源的查询语义、参数绑定、输出类型和运行条件",
        "menus": "菜单层级、可见范围和权限",
        "permissions": "不同角色的数据和操作权限",
        "integrations": "外部协作、消息或跨模块调用",
        "dependencies": "关联功能是否仍能正常联动",
        "terminals": "PC/H5端展示和操作一致性",
        "userActions": "用户操作路径和按钮行为",
    }
    for field, delta in change.get("differences", {}).items():
        if field not in aspect_text:
            continue
        added = "、".join(delta["added"][:MAX_NAMES_PER_LINE])
        removed = "、".join(delta["removed"][:MAX_NAMES_PER_LINE])
        detail = []
        if added:
            detail.append(("新版：" if field == "workflowSqlDatasources" else "新增：") + added)
        if removed:
            detail.append(("前版：" if field == "workflowSqlDatasources" else "取消或移除：") + removed)
        suffix = f"（{'；'.join(detail)}）" if detail else ""
        title = f"检查{aspect_text[field]}"
        if field == "workflowBrowserDataScopes" and change.get("subjectType") == "审批流程":
            title = f"检查审批流程“{name}”的浏览数据范围"
        elif field == "workflowNodePostValidations" and change.get("subjectType") == "审批流程":
            title = f"检查审批流程“{name}”的节点后校验"
        elif field == "workflowSqlDatasources" and change.get("subjectType") == "审批流程":
            title = f"检查审批流程“{name}”的 SQL 数据源"
        points.append({"priority": "中", "title": title, "scenario": f"针对{name}，{aspect_text[field]}发生变化{suffix}，逐项验证正常、异常和权限边界。"})
    if change.get("unresolved"):
        points.append({"priority": "中", "title": f"确认{name}的待确认关联", "scenario": "在测试环境补充确认尚未闭合的页面、外部资源或目标环境映射，避免仅凭配置存在就判定业务可用。"})
    # de-duplicate identical titles while retaining order
    seen: set[str] = set()
    return [p for p in points if not (p["title"] in seen or seen.add(p["title"]))]


def compare_features(
    old_side: dict[str, Any],
    new_side: dict[str, Any],
    domain_pairs: list[dict[str, Any]],
    workflow_validations: dict[str, list[dict[str, Any]]] | None = None,
    workflow_sql_datasources: dict[str, list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    old_cards = {c["logicalKey"]: c for c in old_side["mapping"].get("functionCards", [])}
    new_cards = {c["logicalKey"]: c for c in new_side["mapping"].get("functionCards", [])}
    old_to_new_domain = {p["old"]["logicalKey"]: p["new"]["logicalKey"] for p in domain_pairs}
    pairs: list[tuple[dict[str, Any] | None, dict[str, Any] | None, str]] = []
    for key in sorted(set(old_cards) & set(new_cards)):
        pairs.append((old_cards[key], new_cards[key], "更新"))
    # Match the same function kind under a renamed business domain.
    used_old, used_new = set(old_cards) & set(new_cards), set(old_cards) & set(new_cards)
    for p in domain_pairs:
        if p["match"] != "renamed":
            continue
        old_domain, new_domain = p["old"]["logicalKey"], p["new"]["logicalKey"]
        oc = [c for c in old_cards.values() if c.get("domain") == old_domain and c["logicalKey"] not in used_old]
        nc = [c for c in new_cards.values() if c.get("domain") == new_domain and c["logicalKey"] not in used_new]
        by_kind = {card_kind(c): c for c in nc}
        for c in oc:
            counterpart = by_kind.get(card_kind(c))
            if counterpart:
                pairs.append((c, counterpart, "归属调整"))
                used_old.add(c["logicalKey"]); used_new.add(counterpart["logicalKey"])
    # Exact pairs were already added; unmatched cards remain add/delete.
    result: list[dict[str, Any]] = []
    paired_old = {x[0]["logicalKey"] for x in pairs if x[0]}
    paired_new = {x[1]["logicalKey"] for x in pairs if x[1]}
    for old_card, new_card, kind in pairs:
        change = compare_card(
            old_card, new_card, old_side, new_side, kind,
            workflow_validations, workflow_sql_datasources,
        )
        if kind == "更新" and not change["differences"] and old_card.get("name") == new_card.get("name"):
            continue
        change["testPoints"] = make_test_points(change)
        result.append(change)
    for key in sorted(set(old_cards) - paired_old):
        change = compare_card(
            old_cards[key], None, old_side, new_side, "删除",
            workflow_validations, workflow_sql_datasources,
        )
        change["testPoints"] = make_test_points(change)
        result.append(change)
    for key in sorted(set(new_cards) - paired_new):
        change = compare_card(
            None, new_cards[key], old_side, new_side, "新增",
            workflow_validations, workflow_sql_datasources,
        )
        change["testPoints"] = make_test_points(change)
        result.append(change)
    order = {"新增": 0, "删除": 1, "归属调整": 2, "更新": 3}
    return sorted(result, key=lambda x: (order.get(x["changeType"], 9), x.get("displayName") or x.get("newName") or x.get("oldName") or ""))


def chain_name(chain: dict[str, Any]) -> str:
    return chain.get("name") or "未命名业务链路"


def compare_chains(old_side: dict[str, Any], new_side: dict[str, Any]) -> dict[str, Any]:
    old = {x.get("logicalKey"): x for x in old_side["mapping"].get("endToEndChains", [])}
    new = {x.get("logicalKey"): x for x in new_side["mapping"].get("endToEndChains", [])}
    added = [chain_name(new[k]) for k in sorted(set(new) - set(old))]
    removed = [chain_name(old[k]) for k in sorted(set(old) - set(new))]
    changed = []
    for key in sorted(set(old) & set(new)):
        on = [friendly(x.get("logicalKey"), old_side["nameMap"]) for x in old[key].get("nodes", [])]
        nn = [friendly(x.get("logicalKey"), new_side["nameMap"]) for x in new[key].get("nodes", [])]
        if on != nn or old[key].get("breakpoints") != new[key].get("breakpoints"):
            changed.append({"name": chain_name(new[key]), "oldNodes": on, "newNodes": nn, "oldBreakpointCount": len(old[key].get("breakpoints", [])), "newBreakpointCount": len(new[key].get("breakpoints", []))})
    return {"added": added, "removed": removed, "updated": changed}


def signed(delta: int) -> str:
    return f"+{delta}" if delta > 0 else str(delta)


def count_summary(side: dict[str, Any]) -> dict[str, int]:
    s = side["mapping"].get("summary", {})
    obj = s.get("objectCounts", {})
    return {
        "业务域": s.get("businessDomainCount", len(side["mapping"].get("businessDomains", []))),
        "功能卡片": s.get("functionCardCount", len(side["mapping"].get("functionCards", []))),
        "端到端链路": s.get("endToEndChainCount", len(side["mapping"].get("endToEndChains", []))),
        "页面": obj.get("page", 0),
        "表单": obj.get("form", 0),
        "动作流": obj.get("actionFlow", 0),
        "菜单": obj.get("menu", 0),
        "审批流程": obj.get("workflow", 0),
        "权限对象": obj.get("permission", 0),
        "业务数据对象": obj.get("entity", 0),
        "查询数据集": obj.get("dataset", 0),
        "集成": obj.get("integration", 0),
    }


def root_object_changes(old_side: dict[str, Any], new_side: dict[str, Any]) -> dict[str, Any]:
    """Compare lineage-stable business roots without exposing logical keys."""
    result: dict[str, Any] = {}
    for field, label in (("actionFlows", "动作流"),):
        old_items = {
            item.get("logicalKey"): item
            for item in old_side.get("ir", {}).get(field, [])
            if item.get("logicalKey")
        }
        new_items = {
            item.get("logicalKey"): item
            for item in new_side.get("ir", {}).get(field, [])
            if item.get("logicalKey")
        }
        added = sorted(
            clean_business_name(str(new_items[key].get("name") or "未命名业务对象"))
            for key in set(new_items) - set(old_items)
        )
        removed = sorted(
            clean_business_name(str(old_items[key].get("name") or "未命名业务对象"))
            for key in set(old_items) - set(new_items)
        )
        renamed = []
        for key in sorted(set(old_items) & set(new_items)):
            old_name = clean_business_name(str(old_items[key].get("name") or "未命名业务对象"))
            new_name = clean_business_name(str(new_items[key].get("name") or "未命名业务对象"))
            if old_name != new_name:
                renamed.append({"before": old_name, "after": new_name})
        result[field] = {
            "label": label,
            "oldCount": len(old_items),
            "newCount": len(new_items),
            "added": added,
            "removed": removed,
            "renamed": renamed,
        }
    return result


def short_list(values: list[str], limit: int = MAX_NAMES_PER_LINE) -> str:
    if not values:
        return "无"
    if len(values) <= limit:
        return "、".join(values)
    return "、".join(values[:limit]) + f"等 {len(values)} 项"


def render_markdown(old_side: dict[str, Any], new_side: dict[str, Any], result: dict[str, Any]) -> str:
    old_count, new_count = result["oldSummary"], result["newSummary"]
    lines = [
        f"# {result['applicationName']}应用版本功能差异报告",
        "",
        "> 本报告先分别还原旧版和新版应用，再比较两份业务功能全景；正文只展示业务功能变化和可执行验证建议。",
        "> 报告基于离线包保存态配置生成，不代表目标环境已经迁入、启用或运行通过。",
        "",
        "## 1. 先看总体变化",
        "",
        "| 业务视角指标 | 旧版 | 新版 | 变化 |",
        "|---|---:|---:|---:|",
    ]
    for label in ["业务域", "功能卡片", "端到端链路", "页面", "表单", "动作流", "菜单", "审批流程", "权限对象", "业务数据对象", "查询数据集", "集成"]:
        lines.append(f"| {label} | {old_count[label]} | {new_count[label]} | {signed(new_count[label]-old_count[label])} |")
    changes = result["featureChanges"]
    stat = result["changeSummary"]
    lines += [
        "",
        f"本次识别为：新增功能 {stat['新增']} 项、删除功能 {stat['删除']} 项、功能归属调整 {stat['归属调整']} 项、已有功能内容更新 {stat['更新']} 项。",
        "",
        "## 2. 业务功能变化总览",
        "",
        "### 新增功能",
        "",
    ]
    added = [x.get("newName") for x in changes if x["changeType"] == "新增"]
    lines.append("- " + (short_list(added) if added else "无"))
    lines += ["", "### 删除功能", ""]
    removed = [x.get("oldName") for x in changes if x["changeType"] == "删除"]
    lines.append("- " + (short_list(removed) if removed else "无"))
    lines += ["", "### 功能归属调整", ""]
    reclassified = [x for x in changes if x["changeType"] == "归属调整"]
    if reclassified:
        for x in reclassified:
            lines.append(f"- **{x['oldName']}**：业务域从“{friendly_domain(x.get('oldDomain'), old_side)}”调整到“{friendly_domain(x.get('newDomain'), new_side)}”。")
    else:
        lines.append("- 无")
    action_roots = (result.get("rootObjectChanges") or {}).get("actionFlows") or {}
    lines += ["", "### 动作流对象变化", ""]
    lines.append(
        f"- 动作流总数：旧版 {action_roots.get('oldCount', 0)} 个，"
        f"新版 {action_roots.get('newCount', 0)} 个。"
    )
    lines.append(f"- 新增动作流：{short_list(action_roots.get('added', []))}。")
    lines.append(f"- 删除动作流：{short_list(action_roots.get('removed', []))}。")
    renamed = action_roots.get("renamed") or []
    lines.append(
        "- 同源动作流名称调整：" + (
            "；".join(f"{item['before']} → {item['after']}" for item in renamed)
            if renamed else "无"
        ) + "。"
    )
    lines += ["", "## 3. 按业务域看变化", ""]
    for domain in result["domainChanges"]:
        if domain["changeType"] == "无变化":
            continue
        old_name = domain.get("oldName") or "无"
        new_name = domain.get("newName") or "无"
        title = new_name if new_name != "无" else old_name
        lines.append(f"### {title}")
        if domain["changeType"] == "新增":
            lines.append(f"- 新增业务域，包含：{short_list(domain.get('newFunctions', []))}。")
        elif domain["changeType"] == "删除":
            lines.append(f"- 旧版业务域下线，原有功能：{short_list(domain.get('oldFunctions', []))}。")
        elif domain["changeType"] == "名称调整":
            lines.append(f"- 业务域名称由“{old_name}”调整为“{new_name}”；功能继续按下方明细核对。")
        if domain.get("addedFunctions"):
            lines.append(f"- 新增功能：{short_list(domain['addedFunctions'])}。")
        if domain.get("removedFunctions"):
            lines.append(f"- 删除功能：{short_list(domain['removedFunctions'])}。")
        if domain.get("updatedFunctions"):
            lines.append(f"- 内容更新：{short_list(domain['updatedFunctions'])}。")
        lines.append("")
    lines += ["## 4. 具体功能变化和验证点", ""]
    if not changes:
        lines.append("本次没有识别到业务功能层面的变化。")
    for idx, change in enumerate(changes, 1):
        name = change.get("displayName") or change.get("newName") or change.get("oldName") or "未命名业务功能"
        tag = change["changeType"]
        lines += [f"### {idx}. 【{tag}】{name}", ""]
        business_function_name = change.get("businessFunctionName")
        if business_function_name and business_function_name != name:
            lines.append(f"- 对象类型：{change.get('subjectType') or '业务对象'}；所属业务功能：{business_function_name}。")
        changed_objects = change.get("changedObjects") or []
        if changed_objects:
            object_names = [item.get("newName") or item.get("oldName") for item in changed_objects]
            lines.append(f"- 实际变化对象：{short_list([x for x in object_names if x])}。")
        if tag == "新增":
            lines.append("- 功能变化：新版出现，旧版未观察到。")
        elif tag == "删除":
            lines.append("- 功能变化：旧版存在，新版未观察到。")
        elif tag == "归属调整":
            lines.append(f"- 功能变化：功能保留，但业务域从“{friendly_domain(change.get('oldDomain'), old_side)}”调整到“{friendly_domain(change.get('newDomain'), new_side)}”。")
        else:
            lines.append("- 功能变化：已有业务功能仍保留，但其入口、页面、表单、动作流、审批、数据或权限范围发生变化。")
        for field, delta in change.get("differences", {}).items():
            label = FIELD_LABELS.get(field, field)
            detail = []
            if delta.get("added"):
                detail.append(
                    ("新版：" if field == "workflowSqlDatasources" else "新增：")
                    + short_list(delta["added"])
                )
            if delta.get("removed"):
                detail.append(
                    ("前版：" if field == "workflowSqlDatasources" else "移除：")
                    + short_list(delta["removed"])
                )
            if not detail and delta.get("oldCount") != delta.get("newCount"):
                detail.append(f"数量由 {delta.get('oldCount')} 项变为 {delta.get('newCount')} 项")
            if detail:
                lines.append(f"- {label}：" + "；".join(detail) + "。")
        lines.append("- 建议验证：")
        for p in change.get("testPoints", []):
            lines.append(f"  - 【{p['priority']}】{p['title']}：{p['scenario']}")
        lines.append("")
    chain = result["chainChanges"]
    lines += ["## 5. 端到端业务链路变化", ""]
    lines.append(f"- 新增链路：{short_list(chain['added'])}。")
    lines.append(f"- 删除链路：{short_list(chain['removed'])}。")
    if chain["updated"]:
        lines.append(f"- 调整链路：共 {len(chain['updated'])} 条，建议按对应业务功能逐条走通入口、处理、审批和结果回写。")
    else:
        lines.append("- 调整链路：无。")
    lines += ["", "## 6. 本次建议优先验证清单", ""]
    for idx, p in enumerate(result["testPoints"], 1):
        lines.append(f"{idx}. 【{p['priority']}】{p['title']}：{p['scenario']}")
    lines += [
        "",
        "## 7. 阅读口径和限制",
        "",
        "1. 本报告比较的是两次应用还原后的业务域、功能卡片和端到端链路，不是原始配置记录数量对账。",
        "2. 业务名称来自配置中的可读名称和已确认的功能聚合；无法还原名称的对象不会在客户正文逐条展示，而只影响机器统计。",
        "3. 同一功能被重新归类或改名时，报告优先标记为“功能归属调整”；若两边无法建立可靠对应关系，才分别列为新增或删除。",
        "4. 验证点是基于保存态配置推导的测试建议，仍需在目标环境补充组织、权限、外部资源和实际运行验证。",
        "",
        "---",
        "旧版和新版完整《应用功能全景报告》及机器明细保留在本实验目录的 old/、new/ 子目录中。",
        "",
    ]
    return "\n".join(lines)


def friendly_domain(key: str | None, side: dict[str, Any]) -> str:
    if not key:
        return "未确认业务域"
    for d in side["mapping"].get("businessDomains", []):
        if d.get("logicalKey") == key:
            return d.get("name") or "未确认业务域"
    return "未确认业务域"


def build_domain_changes(old_side: dict[str, Any], new_side: dict[str, Any], pairs: list[dict[str, Any]], old_only: set[str], new_only: set[str], feature_changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    by_domain: dict[tuple[str | None, str | None], list[dict[str, Any]]] = defaultdict(list)
    for c in feature_changes:
        by_domain[(c.get("oldDomain"), c.get("newDomain"))].append(c)
    for p in pairs:
        od, nd = p["old"], p["new"]
        key = (od["logicalKey"], nd["logicalKey"])
        cards = by_domain.get(key, [])
        result.append({
            "changeType": "名称调整" if p["match"] == "renamed" else ("更新" if cards else "无变化"),
            "oldLogicalKey": od["logicalKey"], "newLogicalKey": nd["logicalKey"],
            "oldName": od.get("name"), "newName": nd.get("name"),
            "oldFunctions": [x.get("name") for x in old_side["mapping"].get("functionCards", []) if x.get("domain") == od["logicalKey"]],
            "newFunctions": [x.get("name") for x in new_side["mapping"].get("functionCards", []) if x.get("domain") == nd["logicalKey"]],
            "addedFunctions": [x.get("newName") for x in cards if x["changeType"] == "新增"],
            "removedFunctions": [x.get("oldName") for x in cards if x["changeType"] == "删除"],
            "updatedFunctions": [x.get("displayName") or x.get("newName") or x.get("oldName") for x in cards if x["changeType"] in ("更新", "归属调整")],
        })
    for key in sorted(old_only):
        od = next(x for x in old_side["mapping"].get("businessDomains", []) if x.get("logicalKey") == key)
        result.append({"changeType": "删除", "oldLogicalKey": key, "newLogicalKey": None, "oldName": od.get("name"), "newName": None, "oldFunctions": [x.get("name") for x in old_side["mapping"].get("functionCards", []) if x.get("domain") == key], "newFunctions": [], "addedFunctions": [], "removedFunctions": [], "updatedFunctions": []})
    for key in sorted(new_only):
        nd = next(x for x in new_side["mapping"].get("businessDomains", []) if x.get("logicalKey") == key)
        result.append({"changeType": "新增", "oldLogicalKey": None, "newLogicalKey": key, "oldName": None, "newName": nd.get("name"), "oldFunctions": [], "newFunctions": [x.get("name") for x in new_side["mapping"].get("functionCards", []) if x.get("domain") == key], "addedFunctions": [], "removedFunctions": [], "updatedFunctions": []})
    return sorted(result, key=lambda x: x.get("newName") or x.get("oldName") or "")


def validate_concrete_object_names(feature_changes: list[dict[str, Any]]) -> dict[str, Any]:
    """Ensure customer-facing aggregation never hides the concrete changed object name."""
    errors: list[str] = []
    checked = 0
    for change in feature_changes:
        changed_objects = change.get("changedObjects") or []
        if not changed_objects:
            continue
        checked += len(changed_objects)
        names = [item.get("newName") or item.get("oldName") for item in changed_objects]
        if any(not name or str(name).startswith("未命名") for name in names):
            errors.append(f"{change.get('businessFunctionName') or '未命名业务功能'}：存在未还原名称的实际变化对象")
            continue
        if change.get("subjectType") != "业务功能":
            expected = "、".join(names)
            if change.get("displayName") != expected:
                errors.append(f"{change.get('businessFunctionName')}：标题未使用实际变化对象名（期望：{expected}）")
        for item, name in zip(changed_objects, names):
            for field in (item.get("differences") or {}):
                delta = (change.get("differences") or {}).get(field, {})
                aggregate_text = " ".join(str(value) for value in (delta.get("added", []) + delta.get("removed", [])))
                if name not in aggregate_text:
                    errors.append(f"{change.get('businessFunctionName')}：{field} 明细未标明所属对象“{name}”")
    return {"valid": not errors, "checkedObjectCount": checked, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare reconstructed eBuilder application panoramas")
    parser.add_argument("old_dir", type=Path)
    parser.add_argument("new_dir", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--report-output", type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--validation-output", type=Path)
    parser.add_argument(
        "--business-object-diff",
        type=Path,
        help="可选的业务对象差异；用于把节点后校验等流程子配置同步到应用全景报告",
    )
    args = parser.parse_args()
    old_side, new_side = load_side(args.old_dir), load_side(args.new_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pairs, old_only_domains, new_only_domains = match_domains(old_side, new_side)
    workflow_validations = load_workflow_node_validations(args.business_object_diff)
    workflow_sql_datasources = load_workflow_sql_datasources(args.business_object_diff)
    business_object_model = (
        read_json(args.business_object_diff)
        if args.business_object_diff and args.business_object_diff.is_file()
        else {}
    )
    feature_changes = compare_features(
        old_side, new_side, pairs, workflow_validations, workflow_sql_datasources
    )
    object_name_validation = validate_concrete_object_names(feature_changes)
    chain_changes = compare_chains(old_side, new_side)
    summary_old, summary_new = count_summary(old_side), count_summary(new_side)
    change_summary = {k: sum(1 for x in feature_changes if x["changeType"] == k) for k in ("新增", "删除", "归属调整", "更新")}
    test_points = []
    seen = set()
    for c in feature_changes:
        for p in c.get("testPoints", []):
            if p["title"] not in seen:
                seen.add(p["title"]); test_points.append(p)
    result = {
        "schemaVersion": "reconstructed-application-comparison-experiment-v1",
        "applicationName": business_object_model.get("applicationName") or new_side["mapping"].get("application", {}).get("name") or old_side["mapping"].get("application", {}).get("name") or "eBuilder应用",
        "method": "分别重建应用全景后，比较业务功能映射、功能卡片和端到端链路",
        "old": {"folder": old_side["folder"], "mapping": old_side["mappingPath"], "report": old_side["reportPath"]},
        "new": {"folder": new_side["folder"], "mapping": new_side["mappingPath"], "report": new_side["reportPath"]},
        "oldSummary": summary_old, "newSummary": summary_new,
        "changeSummary": change_summary,
        "rootObjectChanges": root_object_changes(old_side, new_side),
        "domainChanges": build_domain_changes(old_side, new_side, pairs, old_only_domains, new_only_domains, feature_changes),
        "featureChanges": feature_changes,
        "concreteObjectNameValidation": object_name_validation,
        "chainChanges": chain_changes,
        "testPoints": test_points,
        "limitations": [
            "两次重建的业务聚合名称或归属发生变化时，比较结果可能包含名称调整；无法可靠匹配时不强行合并。",
            "保存态配置可以推导验证场景，但不能替代目标环境中的真实运行、组织权限和外部系统联调。",
        ],
    }
    json_path = (args.json_output or args.output_dir / "应用全景对比实验结果.json").expanduser().resolve()
    md_path = (args.report_output or args.output_dir / "应用全景对比实验报告.md").expanduser().resolve()
    validation_path = (args.validation_output or args.output_dir / "应用全景对比实验校验.json").expanduser().resolve()
    for path in (json_path, md_path, validation_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    report_text = render_markdown(old_side, new_side, result)
    md_path.write_text(report_text, encoding="utf-8")
    technical_leaks = find_customer_text_leaks(report_text)
    validation = {
        "valid": bool(
            (feature_changes or chain_changes or summary_old != summary_new)
            and not technical_leaks
            and object_name_validation["valid"]
        ),
        "report": str(md_path), "json": str(json_path),
        "customerReportNoTechnicalEvidence": not technical_leaks,
        "technicalLeakMarkers": technical_leaks,
        "concreteObjectNamesPreserved": object_name_validation["valid"],
        "concreteObjectNameErrors": object_name_validation["errors"],
        "concreteObjectNameCount": object_name_validation["checkedObjectCount"],
        "featureChangeCount": len(feature_changes),
        "testPointCount": len(test_points),
        "oldPanoramaExists": Path(old_side["reportPath"]).exists(),
        "newPanoramaExists": Path(new_side["reportPath"]).exists(),
    }
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(md_path), "json": str(json_path), "validation": validation}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
