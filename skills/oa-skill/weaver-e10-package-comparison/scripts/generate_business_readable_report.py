#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from business_report_common import (
    CARD_STATUSES,
    TYPE_LABELS,
    build_reference_graph,
    collect_objects,
    concept_from_name,
    dependency_counts,
    domain_for_object,
    dump_json,
    evidence_level,
    import_requirement_counts,
    load_json,
    operation_from_name,
    public_object,
    safe_display,
    safe_file_name,
    shortest_path,
    stable_slug,
    summarize_counts,
)


TYPE_TO_CARD_FIELD = {
    "entity": "entities",
    "dataset": "datasets",
    "form": "forms",
    "page": "pages",
    "pageComponent": "pages",
    "actionFlow": "actionFlows",
    "workflow": "workflows",
    "menu": "menus",
    "navigation": "menus",
    "applicationShell": "menus",
    "menuCombination": "menus",
    "permission": "permissions",
    "integration": "integrations",
    "externalResource": "dependencies",
    "dependency": "dependencies",
    "businessObject": "entities",
    "serviceFragment": "dependencies",
    "aiApplication": "integrations",
    "multiFillingTask": "workflows",
    "report": "pages",
    "relation": "entities",
}
CARD_FIELDS = (
    "entities", "datasets", "forms", "pages", "actionFlows", "workflows", "menus",
    "permissions", "integrations", "dependencies",
)
ENTRY_TYPES = {"menu", "navigation", "applicationShell", "menuCombination", "page"}
CORE_TYPES = {"form", "page", "actionFlow", "workflow", "menu", "report", "multiFillingTask", "aiApplication"}
END_TYPES = {"form", "entity", "workflow", "integration", "actionFlow", "report"}


def md(value):
    return safe_display(value).replace("|", "\\|").replace("\n", " ")


def source_label(item):
    ref = item.get("sourceRef", {})
    service = ref.get("service") or "Application IR"
    table = ref.get("table") or item.get("sourcePath") or "配置对象"
    return f"{service}/{table}"


def make_domain(name):
    return {
        "logicalKey": f"business-domain:{stable_slug(name, 'domain')}",
        "name": name,
        "description": f"聚合与“{name}”相关的用户入口、业务数据、自动化、流程、权限和依赖。",
        "evidenceLevel": "BUSINESS_INFERRED",
        "functionCards": [],
    }


def make_card(domain, operation):
    domain_name = domain["name"]
    name = domain_name if operation == "业务处理" else f"{domain_name}—{operation}"
    key = f"business-function:{stable_slug(domain_name)}:{stable_slug(operation)}"
    card = {
        "logicalKey": key,
        "name": name,
        "domain": domain["logicalKey"],
        "purpose": f"支持{domain_name}相关的{operation}。",
        "status": "PARTIAL",
        "evidenceLevel": "BUSINESS_INFERRED",
        "roles": [],
        "terminals": [],
        "entries": [],
        "userActions": [],
        "entities": [],
        "datasets": [],
        "forms": [],
        "pages": [],
        "actionFlows": [],
        "workflows": [],
        "menus": [],
        "permissions": [],
        "integrations": [],
        "dependencies": [],
        "successOutcome": [],
        "failurePaths": [],
        "unresolved": [],
        "evidence": [],
    }
    return card


def assignment_priority(method):
    return {
        "EXPLICIT_DEPENDENCY": 8,
        "MENU_TARGET": 7,
        "WORKFLOW_FORM_BINDING": 6,
        "FORM_ACTION_BINDING": 6,
        "PAGE_DATASET_BINDING": 6,
        "EXPLICIT_BINDING": 5,
        "FEATURE_GROUP": 4,
        "NAME_CLUSTER_INFERRED": 1,
        "UNMAPPED": 0,
    }.get(method, 0)


def select_domain_vocabulary(objects, application_name, seed_types):
    concepts = [
        concept_from_name(item["name"], application_name)
        for item in objects
        if item["objectType"] in seed_types
        and item["objectType"] not in {"serviceFragment", "integration"}
    ]
    counts = Counter(
        value for value in concepts
        if value and not re.search(r"ebuilder|esb|service|component|嵌入式|表单列表视图|视图设置", value, re.I)
    )
    if not counts:
        return []
    domain_limit = min(18, max(6, round(len(concepts) ** 0.5 / 3)))
    ranked = sorted(counts, key=lambda value: (-counts[value], -min(len(value), 12), value))
    selected = []
    for concept in ranked:
        if any(concept == value for value in selected):
            continue
        if any((concept in value or value in concept) and min(counts[concept], counts[value]) > 1 for value in selected):
            continue
        selected.append(concept)
        if len(selected) >= domain_limit:
            break
    return selected


def select_domain_name(inferred_name, vocabulary):
    if inferred_name in {"系统支撑能力", "外部协作与系统集成"}:
        return inferred_name
    if not inferred_name:
        return "其他业务能力"
    if inferred_name in vocabulary:
        return inferred_name
    candidates = [value for value in vocabulary if value in inferred_name or inferred_name in value]
    if candidates:
        return sorted(candidates, key=lambda value: (-len(value), value))[0]
    return "其他业务能力"


def build_mapping(ir, build_plan=None, import_requirements=None):
    application = ir.get("application", {})
    application_name = application.get("name") or "未命名应用"
    objects = collect_objects(ir)
    by_key = {item["logicalKey"]: item for item in objects}
    adjacency = build_reference_graph(objects)
    domains_by_name = {}
    cards = {}
    assignments = {}

    seed_types = {
        "businessObject", "serviceFragment", "entity", "dataset", "form", "page",
        "actionFlow", "aiApplication", "multiFillingTask", "workflow", "report", "menu",
        "navigation", "applicationShell", "menuCombination", "integration",
    }
    domain_vocabulary = select_domain_vocabulary(objects, application_name, seed_types)
    for item in objects:
        if item["objectType"] not in seed_types:
            continue
        domain_name, method, level = domain_for_object(item, application_name)
        if not domain_name:
            continue
        domain_name = select_domain_name(domain_name, domain_vocabulary)
        domain = domains_by_name.setdefault(domain_name, make_domain(domain_name))
        operation = operation_from_name(item["name"], item["objectType"])
        card = cards.setdefault((domain["logicalKey"], operation), make_card(domain, operation))
        assignments[item["logicalKey"]] = {
            "primaryDomain": domain["logicalKey"],
            "primaryCard": card["logicalKey"],
            "assignmentMethod": method,
            "evidenceLevel": level,
        }

    card_key_to_card = {card["logicalKey"]: card for card in cards.values()}
    for _ in range(12):
        changed = False
        for item in objects:
            key = item["logicalKey"]
            if key in assignments:
                continue
            candidates = []
            for neighbor, method in adjacency.get(key, {}).items():
                assigned = assignments.get(neighbor)
                if assigned:
                    candidates.append((assignment_priority(method), method, neighbor, assigned))
            if not candidates:
                continue
            candidates.sort(key=lambda value: (-value[0], value[3]["primaryCard"], value[2]))
            _, method, _, selected = candidates[0]
            assignments[key] = {
                "primaryDomain": selected["primaryDomain"],
                "primaryCard": selected["primaryCard"],
                "assignmentMethod": method,
                "evidenceLevel": "CONFIG_OBSERVED",
            }
            changed = True
        if not changed:
            break

    object_assignments = []
    unmapped = []
    for item in objects:
        key = item["logicalKey"]
        assigned = assignments.get(key)
        related_cards = set()
        if assigned:
            related_cards.add(assigned["primaryCard"])
        for neighbor in adjacency.get(key, {}):
            neighbor_assignment = assignments.get(neighbor)
            if neighbor_assignment:
                related_cards.add(neighbor_assignment["primaryCard"])
        if assigned:
            record = {
                "logicalKey": key,
                "objectType": item["objectType"],
                "primaryDomain": assigned["primaryDomain"],
                "functionCards": sorted(related_cards),
                "assignmentMethod": assigned["assignmentMethod"],
                "evidenceLevel": assigned["evidenceLevel"],
            }
        else:
            record = {
                "logicalKey": key,
                "objectType": item["objectType"],
                "primaryDomain": None,
                "functionCards": [],
                "assignmentMethod": "UNMAPPED",
                "evidenceLevel": "UNRESOLVED",
            }
            unmapped.append({
                **public_object(item),
                "reason": "缺少可闭合的显式关系或稳定业务名称；保留对象证据，禁止强行归类。",
                "evidenceLevel": "UNRESOLVED",
            })
        object_assignments.append(record)

    for assignment in object_assignments:
        if assignment["assignmentMethod"] == "UNMAPPED":
            continue
        item = by_key[assignment["logicalKey"]]
        card = card_key_to_card[assignments[assignment["logicalKey"]]["primaryCard"]]
        field = TYPE_TO_CARD_FIELD.get(item["objectType"])
        if field and item["logicalKey"] not in card[field]:
            card[field].append(item["logicalKey"])
        if item["objectType"] in ENTRY_TYPES and item["logicalKey"] not in card["entries"]:
            card["entries"].append(item["logicalKey"])
        if item["objectType"] in {"form", "page", "menu"}:
            action = operation_from_name(item["name"], item["objectType"])
            if action not in card["userActions"]:
                card["userActions"].append(action)
        terminal = item["raw"].get("terminal") or item["raw"].get("platform")
        if terminal and str(terminal) not in card["terminals"]:
            card["terminals"].append(str(terminal))
        level = assignment["evidenceLevel"]
        card["evidence"].append({
            "logicalKey": item["logicalKey"],
            "objectType": item["objectType"],
            "level": level,
            "source": source_label(item),
        })

    unresolved_dependencies = {
        item.get("logicalKey"): item
        for item in ir.get("dependencies", [])
        if item.get("status") in {"unresolved", "unsupported"}
    }
    external_dependencies = {
        item.get("logicalKey"): item
        for item in ir.get("dependencies", [])
        if item.get("status") == "external"
    }
    adapters = list((build_plan or {}).get("adapterRequirements", ir.get("build", {}).get("adapterRequirements", [])))
    for card in card_key_to_card.values():
        for field in CARD_FIELDS:
            card[field] = sorted(set(card[field]))
        card["entries"] = sorted(set(card["entries"]))
        card["terminals"] = sorted(set(card["terminals"])) or ["终端范围待目标环境确认"]
        card["roles"] = ["受相关权限对象约束的业务人员"] if card["permissions"] else ["使用角色待目标组织映射确认"]
        card["userActions"] = sorted(set(card["userActions"])) or ["根据保存态配置执行相关业务处理"]
        card["successOutcome"] = ["保存态配置表明相关数据或流程结果可被后续页面、表单或自动化继续使用。"]
        related_unresolved = [key for key in card["dependencies"] if key in unresolved_dependencies]
        related_external = [key for key in card["dependencies"] if key in external_dependencies]
        if related_unresolved:
            card["status"] = "UNRESOLVED"
            card["evidenceLevel"] = "UNRESOLVED"
            card["unresolved"].extend(related_unresolved)
            card["failurePaths"].append("依赖目标无法唯一解析时在断点停止，不得猜测绑定。")
        elif adapters and (card["actionFlows"] or card["integrations"] or card["menus"]):
            card["status"] = "ADAPTER_REQUIRED"
            card["evidenceLevel"] = "CONFIG_OBSERVED"
            card["unresolved"].extend(f"adapter:{value}" for value in adapters)
            card["failurePaths"].append("目标 Builder 或组件适配器未满足时，只能保留禁用或待绑定状态。")
        elif any(item["level"] == "BUSINESS_INFERRED" for item in card["evidence"]):
            card["status"] = "PARTIAL"
            card["evidenceLevel"] = "BUSINESS_INFERRED"
        else:
            card["status"] = "CONFIRMED"
            card["evidenceLevel"] = "CONFIG_OBSERVED"
        if related_external:
            card["failurePaths"].append("目标外部资源未映射时，相关绑定或启用路径保持待处理。")
        card["evidence"] = card["evidence"][:100]
        assert card["status"] in CARD_STATUSES

    domains = sorted(domains_by_name.values(), key=lambda item: item["name"])
    for domain in domains:
        domain_cards = sorted(
            card["logicalKey"] for card in card_key_to_card.values()
            if card["domain"] == domain["logicalKey"]
        )
        domain["functionCards"] = domain_cards
        levels = {card_key_to_card[key]["evidenceLevel"] for key in domain_cards}
        domain["evidenceLevel"] = "BUSINESS_INFERRED" if "BUSINESS_INFERRED" in levels else "CONFIG_OBSERVED"

    chains = build_chains(card_key_to_card, by_key, adjacency)
    risks = build_risks(ir, build_plan, card_key_to_card, object_assignments, import_requirements)
    counts = summarize_counts(objects)
    mapped_count = sum(item["assignmentMethod"] != "UNMAPPED" for item in object_assignments)
    mapping = {
        "schemaVersion": "business-function-map/v1.0",
        "application": application,
        "businessDomains": domains,
        "functionCards": sorted(card_key_to_card.values(), key=lambda item: (item["domain"], item["name"])),
        "endToEndChains": chains,
        "objectAssignments": sorted(object_assignments, key=lambda item: (item["objectType"], item["logicalKey"])),
        "unmappedObjects": sorted(unmapped, key=lambda item: (item["objectType"], item["logicalKey"])),
        "risks": risks,
        "summary": {
            "businessDomainCount": len(domains),
            "functionCardCount": len(card_key_to_card),
            "endToEndChainCount": len(chains),
            "trackedObjectCount": len(objects),
            "mappedObjectCount": mapped_count,
            "unmappedObjectCount": len(unmapped),
            "objectCounts": counts,
            "applicationIRSummary": ir.get("summary", {}),
            "dependencyCounts": dependency_counts(ir),
            "importRequirementCounts": import_requirement_counts(ir, import_requirements),
            "parseErrorCount": len(ir.get("evidence", {}).get("parseErrors", [])),
            "businessUnresolvedCount": sum(card["status"] == "UNRESOLVED" for card in card_key_to_card.values()),
            "adapterRequirementCount": len(adapters),
            "publishBlockerCount": sum(risk.get("blocksPublication", False) for risk in risks),
        },
        "evidence": {
            "levels": ["CONFIG_OBSERVED", "CODE_CONFIRMED", "BUSINESS_INFERRED", "UNRESOLVED", "RUNTIME_VERIFIED"],
            "runtimeVerified": False,
            "boundary": "业务聚合是 Application IR 的派生解释；名称聚类均标记 BUSINESS_INFERRED，未获得目标运行证据。",
            "sourceApplicationIR": str(Path(ir.get("evidence", {}).get("sources", [{}])[0].get("canonicalIR", ""))),
        },
    }
    return mapping, objects, adjacency


def build_chains(cards, by_key, adjacency):
    chains = []
    for card in sorted(cards.values(), key=lambda value: value["logicalKey"]):
        relevant = [key for field in CARD_FIELDS for key in card[field] if key in by_key]
        entries = [key for key in card["entries"] if key in by_key]
        if not entries:
            entries = [key for key in relevant if by_key[key]["objectType"] in ENTRY_TYPES][:1]
        goals = [key for key in relevant if by_key[key]["objectType"] in END_TYPES]
        if not entries or not goals:
            continue
        path = shortest_path(adjacency, entries[0], goals, max_depth=12)
        breaks = []
        if not path:
            path = [entries[0]]
            representative = next((key for key in goals if key != entries[0]), None)
            if representative:
                breaks.append({
                    "after": entries[0],
                    "before": representative,
                    "missingObject": "显式跨模块依赖",
                    "impact": "无法确认入口到业务结果的完整运行链。",
                    "recommendation": "补充页面事件、菜单目标或动作流绑定证据后重新生成。",
                    "evidenceLevel": "UNRESOLVED",
                })
                path.append(representative)
        nodes = [{
            "logicalKey": key,
            "objectType": by_key[key]["objectType"],
            "name": by_key[key]["name"],
            "evidenceLevel": evidence_level(by_key[key]),
        } for key in path]
        chains.append({
            "logicalKey": f"business-chain:{stable_slug(card['logicalKey'])}",
            "name": f"{card['name']}端到端业务链",
            "functionCard": card["logicalKey"],
            "entryKind": "用户入口" if by_key[path[0]]["objectType"] in ENTRY_TYPES else "后台自动化",
            "nodes": nodes,
            "branches": [],
            "failurePaths": card["failurePaths"],
            "breakpoints": breaks,
            "evidenceLevel": "UNRESOLVED" if breaks else "CONFIG_OBSERVED",
        })
        if len(chains) >= 36:
            break
    return chains


def build_risks(ir, build_plan, cards, assignments, import_requirements):
    assignment_by_key = {item["logicalKey"]: item for item in assignments}
    risks = []
    category_by_status = {
        "resolved": "已解决内部依赖",
        "external": "目标环境外部依赖",
        "unresolved": "未解决依赖",
        "unsupported": "未解决依赖",
    }
    grouped = defaultdict(list)
    for dependency in ir.get("dependencies", []):
        grouped[category_by_status.get(dependency.get("status"), "未解决依赖")].append(dependency)
    for category, items in grouped.items():
        affected = sorted({
            card
            for dependency in items
            for endpoint in (dependency.get("logicalKey"), dependency.get("from"), dependency.get("to"))
            for card in assignment_by_key.get(endpoint, {}).get("functionCards", [])
        })
        unresolved = category == "未解决依赖"
        external = category == "目标环境外部依赖"
        risks.append({
            "logicalKey": f"risk:{stable_slug(category)}",
            "category": category,
            "name": f"{category}（{len(items)} 项）",
            "affectedDomains": sorted({cards[key]["domain"] for key in affected if key in cards}),
            "affectedFunctions": affected,
            "source": "application-ir.dependencies",
            "requiredTargetResource": "唯一目标对象或目标环境资源" if unresolved or external else "包内对象",
            "status": "UNRESOLVED" if unresolved else ("TARGET_MAPPING_REQUIRED" if external else "RESOLVED"),
            "blocksCreation": False,
            "blocksBinding": unresolved or external,
            "blocksEnablement": unresolved or external,
            "blocksPublication": unresolved,
            "recommendation": "逐项解析目标资源并回读验证。" if unresolved or external else "保持 logicalKey 映射并在搭建后静态对账。",
            "count": len(items),
        })
    adapters = list((build_plan or {}).get("adapterRequirements", ir.get("build", {}).get("adapterRequirements", [])))
    adapter_categories = {
        "esb-component-registry": "ESB 组件适配",
        "external-cusapp-menu-target-resolution": "外部菜单目标解析",
        "target-builder-contract": "Builder 适配器缺口",
    }
    for adapter in adapters:
        category = adapter_categories.get(adapter, "Builder 适配器缺口")
        risks.append({
            "logicalKey": f"risk:adapter:{stable_slug(adapter)}",
            "category": category,
            "name": str(adapter),
            "affectedDomains": [],
            "affectedFunctions": [],
            "source": "build-plan.adapterRequirements",
            "requiredTargetResource": str(adapter),
            "status": "ADAPTER_REQUIRED",
            "blocksCreation": adapter == "target-builder-contract",
            "blocksBinding": True,
            "blocksEnablement": True,
            "blocksPublication": True,
            "recommendation": "实现并验证目标适配器契约；不能以源 ID 或保存态配置代替目标回读。",
            "count": 1,
        })
    runtime_pages = [page for page in ir.get("pages", []) if page.get("sourceCodeLength") or page.get("runtimeCodeCount")]
    if runtime_pages:
        risks.append({
            "logicalKey": "risk:runtime-code-adaptation",
            "category": "运行时代码适配",
            "name": f"含运行时扩展的页面或对象（{len(runtime_pages)} 项）",
            "affectedDomains": [],
            "affectedFunctions": [],
            "source": "application-ir.pages",
            "requiredTargetResource": "目标运行时 API、依赖库和安全审查",
            "status": "RUNTIME_REVIEW_REQUIRED",
            "blocksCreation": False,
            "blocksBinding": False,
            "blocksEnablement": True,
            "blocksPublication": True,
            "recommendation": "逐段审查运行时代码并在隔离环境执行回归。",
            "count": len(runtime_pages),
        })
    requirements = import_requirements or ir.get("importRequirements", {})
    optional_mappings = requirements.get("optionalMappings", [])
    if optional_mappings:
        risks.append({
            "logicalKey": "risk:message-account-local-mapping",
            "category": "消息企业/应用映射",
            "name": f"消息渠道局部映射（{len(optional_mappings)} 项）",
            "affectedDomains": [],
            "affectedFunctions": [],
            "source": "import-required-inputs.optionalMappings",
            "requiredTargetResource": "目标消息企业与应用账号",
            "status": "OPTIONAL_MAPPING",
            "blocksCreation": False,
            "blocksBinding": True,
            "blocksEnablement": True,
            "blocksPublication": False,
            "blockingScope": "MESSAGE_CHANNEL_BINDING_ONLY",
            "recommendation": "允许先创建禁用动作流；映射补齐后仅修复消息渠道绑定。",
            "count": len(optional_mappings),
        })
    if ir.get("permissions"):
        risks.append({
            "logicalKey": "risk:organization-person-role-mapping",
            "category": "组织、人员及角色映射",
            "name": f"权限对象目标映射（{len(ir.get('permissions', []))} 项）",
            "affectedDomains": [],
            "affectedFunctions": [],
            "source": "application-ir.permissions",
            "requiredTargetResource": "目标组织、人员、角色和数据范围",
            "status": "TARGET_MAPPING_REQUIRED",
            "blocksCreation": False,
            "blocksBinding": True,
            "blocksEnablement": True,
            "blocksPublication": True,
            "recommendation": "按权限主体类型建立源证据到目标 logicalKey 的映射并执行越权测试。",
            "count": len(ir.get("permissions", [])),
        })
    return risks


def render_overview(mapping, objects):
    app = mapping["application"]
    app_name = safe_display(app.get("name"), "未命名应用")
    by_key = {item["logicalKey"]: item for item in objects}
    summary = mapping["summary"]
    lines = [
        f"# {app_name}应用功能全景报告", "",
        "## 1. 阅读说明和证据边界", "",
        "本报告把 Application IR 中分散的页面、表单、动作流、流程、菜单、权限、数据和依赖聚合为业务视角。业务名称聚类只作为 `BUSINESS_INFERRED`，显式配置关系为 `CONFIG_OBSERVED`；当前没有目标环境 `RUNTIME_VERIFIED` 证据。", "",
        "报告不重新解析原始 ZIP，不把源环境身份当作目标身份，也不代表应用已经搭建、迁入、启用、发布或运行验证通过。", "",
        "## 2. 应用定位与业务目标", "",
        f"应用名称：{app_name}。根据已观察的业务对象、入口和依赖，该应用用于承载下列业务域中的数据处理、页面交互、自动化、审批和协作能力。具体运行效果仍受目标适配器、组织权限和外部资源约束。", "",
        "## 3. 用户角色、终端和使用入口", "",
        f"共识别 {summary['objectCounts'].get('permission', 0)} 个权限对象、{summary['objectCounts'].get('menu', 0)} 个菜单对象和 {summary['objectCounts'].get('page', 0)} 个页面对象。角色名称和数据范围以保存态权限为证据，迁入目标环境后必须重新解析组织、人员与角色。PC/H5 范围以页面和导航配置为准，未观察到的终端不作推断。", "",
        "## 4. 应用业务能力全景", "",
        "| 业务域 | 功能卡片 | 证据等级 |", "|---|---:|---|",
    ]
    card_by_key = {card["logicalKey"]: card for card in mapping["functionCards"]}
    for domain in mapping["businessDomains"]:
        lines.append(f"| {md(domain['name'])} | {len(domain['functionCards'])} | `{domain['evidenceLevel']}` |")
    lines.extend([
        "", "## 5. 业务生命周期", "",
        "生命周期入口由菜单、导航或页面开始，经数据读取、表单处理、动作流与审批推进，最终回到结果页面、报表或消息渠道。若显式依赖无法闭合，链路在断点处保持 `UNRESOLVED`，不会依据相似名称强行补齐。", "",
        "## 6. 业务域及其主要功能", "",
    ])
    for domain in mapping["businessDomains"]:
        names = "、".join(md(card_by_key[key]["name"]) for key in domain["functionCards"][:12]) or "暂无已确认功能"
        lines.extend([f"### {md(domain['name'])}", "", f"主要功能：{names}。", ""])
    lines.extend(["## 7. 业务功能卡片", ""])
    for card in mapping["functionCards"]:
        domain = next(item for item in mapping["businessDomains"] if item["logicalKey"] == card["domain"])
        def names(field, limit=8):
            values = [safe_display(by_key[key]["name"]) for key in card[field] if key in by_key]
            return "、".join(values[:limit]) + (f"等 {len(values)} 项" if len(values) > limit else "") or "未观察到明确对象"
        evidence_keys = [entry["logicalKey"] for entry in card["evidence"] if not re.search(r"\d{16,}", entry["logicalKey"])][:8]
        lines.extend([
            f"### {md(card['name'])}", "",
            f"- 业务域：{md(domain['name'])}",
            f"- 业务目标：{md(card['purpose'])}",
            f"- 使用角色：{'、'.join(md(x) for x in card['roles'])}",
            f"- 使用入口：{names('menus')}；相关页面：{names('pages')}",
            f"- PC/H5 范围：{'、'.join(md(x) for x in card['terminals'])}",
            f"- 用户操作：{'、'.join(md(x) for x in card['userActions'])}",
            f"- 核心页面：{names('pages')}",
            f"- 核心表单和数据实体：{names('forms')}；{names('entities')}",
            f"- 触发动作流：{names('actionFlows')}",
            f"- 审批流程：{names('workflows')}",
            f"- 数据读取：{names('datasets')}；{names('entities')}",
            f"- 数据写入：以表单、动作流和集成对象中的显式写入配置为准；未闭合写入目标保持待解析。",
            f"- 成功结果：{'、'.join(md(x) for x in card['successOutcome'])}",
            f"- 失败和异常路径：{'、'.join(md(x) for x in card['failurePaths']) or '保存态未观察到明确失败分支，运行行为待验证。'}",
            f"- 权限及数据范围：{names('permissions')}；目标组织映射后复核。",
            f"- 外部依赖：{names('dependencies')}",
            f"- 当前状态：`{card['status']}`",
            f"- 未解决事项：{'、'.join(md(x) for x in card['unresolved'][:8]) or '无功能级明确未解决项；仍需运行验证。'}",
            f"- 证据等级：`{card['evidenceLevel']}`",
            f"- 技术证据索引：{'、'.join(f'`{md(x)}`' for x in evidence_keys) or '详见应用对象索引'}",
            "",
        ])
    lines.extend(["## 8. 关键端到端业务链", ""])
    for chain in mapping["endToEndChains"]:
        lines.extend([f"### {md(chain['name'])}", ""])
        segments = []
        breakpoint_pairs = {(item.get("after"), item.get("before")) for item in chain["breakpoints"]}
        for index, node in enumerate(chain["nodes"]):
            segments.append(f"{TYPE_LABELS.get(node['objectType'], node['objectType'])}“{safe_display(node['name'])}”")
            if index + 1 < len(chain["nodes"]) and (node["logicalKey"], chain["nodes"][index + 1]["logicalKey"]) in breakpoint_pairs:
                segments.append("【待解析：缺少显式跨模块依赖】")
        lines.extend([" → ".join(segments), ""])
        for point in chain["breakpoints"]:
            lines.append(f"- 断点影响：{md(point['impact'])} 建议：{md(point['recommendation'])} `UNRESOLVED`")
        if chain["breakpoints"]:
            lines.append("")
    lines.extend([
        "## 9. 页面、表单、菜单入口关系", "",
        "入口关系只采用菜单目标、页面数据集绑定、表单动作绑定和 Application IR dependency。菜单名称相似但没有显式目标时，不描述为已打开某页面；完整映射见对象索引和业务功能映射 JSON。", "",
        "## 10. 自动化和审批流程", "",
        f"应用包含 {summary['objectCounts'].get('actionFlow', 0)} 个动作流和 {summary['objectCounts'].get('workflow', 0)} 个流程对象。正文按业务功能聚合，节点、条件、分支和保存态绑定在技术对象索引中追溯；目标运行结果待验证。", "",
        "## 11. 权限和数据范围", "",
        "权限配置说明资源与主体之间存在保存态约束，不等于目标环境已获得相同人员、部门、角色或数据范围。发布前必须完成目标组织映射、最小权限验证和越权场景测试。", "",
        "## 12. 外部系统及目标资源依赖", "",
        f"依赖统计：已解决 {summary['dependencyCounts']['resolved']}、外部 {summary['dependencyCounts']['external']}、未解决 {summary['dependencyCounts']['unresolved']}、不支持 {summary['dependencyCounts']['unsupported']}。外部连接、消息账号和组件适配必须在目标环境重新解析，敏感值不写入报告。", "",
        "## 13. 未解决事项和业务影响", "",
        f"当前有 {summary['unmappedObjectCount']} 个对象因缺少可靠业务归属进入 `unmappedObjects`，有 {summary['businessUnresolvedCount']} 张功能卡片包含明确业务断点。未映射不等于解析错误；解析错误单独统计为 {summary['parseErrorCount']}。", "",
        "## 14. 搭建、启用和发布门禁", "",
        "主体创建、跨对象绑定、功能启用和正式发布采用不同门禁。消息企业/应用映射只影响消息渠道绑定及相关启用，不升级为应用级创建阻断。任何发布阻断项、源身份泄漏、适配器缺口或未验证运行时代码存在时均不得声称发布就绪。", "",
        "## 15. 应用功能总结", "",
        f"本次共形成 {summary['businessDomainCount']} 个业务域、{summary['functionCardCount']} 张功能卡片和 {summary['endToEndChainCount']} 条可追溯业务链；{summary['mappedObjectCount']} 个对象已获得主要业务归属，{summary['unmappedObjectCount']} 个对象被显式保留为未映射。报告是应用设计全景，不替代目标搭建、回读和运行验收。", "",
    ])
    return "\n".join(lines)


def render_object_index(mapping, objects, adjacency):
    by_key = {item["logicalKey"]: item for item in objects}
    domain_by_key = {item["logicalKey"]: item for item in mapping["businessDomains"]}
    card_by_key = {item["logicalKey"]: item for item in mapping["functionCards"]}
    assignments = mapping["objectAssignments"]
    groups = defaultdict(list)
    for assignment in assignments:
        domain = assignment.get("primaryDomain") or "unmapped"
        groups[domain].append(assignment)
    lines = [
        f"# {safe_display(mapping['application'].get('name'))}应用对象索引", "",
        "本索引覆盖业务对象、服务片段、实体、关系、数据集、表单、页面、页面组件、动作流、流程、导航菜单、权限、集成、外部资源和依赖。源 ID 仅作为技术证据保留，不是目标身份。", "",
    ]
    ordered_domains = [item["logicalKey"] for item in mapping["businessDomains"]] + ["unmapped"]
    for domain_key in ordered_domains:
        items = groups.get(domain_key, [])
        if not items:
            continue
        domain_name = "未可靠归类对象" if domain_key == "unmapped" else domain_by_key[domain_key]["name"]
        lines.extend([
            f"## {md(domain_name)}", "",
            "| 对象类型 | 业务名称 | logicalKey | 关联功能卡片 | 关联对象 | 状态 | 证据等级 | 分配方式 |",
            "|---|---|---|---|---|---|---|---|",
        ])
        for assignment in sorted(items, key=lambda value: (value["objectType"], value["logicalKey"])):
            item = by_key[assignment["logicalKey"]]
            cards = "、".join(card_by_key[key]["name"] for key in assignment["functionCards"] if key in card_by_key) or "未映射"
            related = "、".join(list(adjacency.get(item["logicalKey"], {}))[:3]) or "无已确认显式关联"
            status = "待解析" if assignment["assignmentMethod"] == "UNMAPPED" else "已编入索引"
            lines.append(
                f"| {TYPE_LABELS.get(item['objectType'], item['objectType'])} | {md(item['name'])} | "
                f"`{item['logicalKey']}` | {md(cards)} | {md(related)} | {status} | "
                f"`{assignment['evidenceLevel']}` | `{assignment['assignmentMethod']}` |"
            )
        lines.append("")
    return "\n".join(lines)


def render_risks(mapping):
    lines = [
        f"# {safe_display(mapping['application'].get('name'))}依赖与风险清单", "",
        "解析错误、业务语义未解决、目标外部依赖和运行未验证分别统计。消息企业/应用映射仅阻断消息渠道绑定和相关启用，不是应用级创建阻断。", "",
    ]
    categories = [
        "已解决内部依赖", "目标环境外部依赖", "未解决依赖", "Builder 适配器缺口",
        "ESB 组件适配", "外部菜单目标解析", "运行时代码适配", "组织、人员及角色映射",
        "表单字段和选项映射", "审批操作者和子流程映射", "外部连接器及接口",
        "消息企业/应用映射", "启用阻断项", "发布阻断项",
    ]
    for category in categories:
        items = [item for item in mapping["risks"] if item["category"] == category]
        lines.extend([f"## {category}", ""])
        if not items:
            lines.extend(["- 未观察到独立条目；不代表目标运行已验证。", ""])
            continue
        lines.extend([
            "| 风险或依赖 | 影响业务域/功能 | 依赖来源 | 所需目标资源 | 当前状态 | 阻断创建 | 阻断绑定 | 阻断启用 | 阻断发布 | 建议处理 |",
            "|---|---|---|---|---|---:|---:|---:|---:|---|",
        ])
        for item in items:
            affected = "、".join(item.get("affectedFunctions", [])[:6]) or "按对象映射逐项确认"
            lines.append(
                f"| {md(item['name'])} | {md(affected)} | {md(item['source'])} | {md(item['requiredTargetResource'])} | "
                f"`{item['status']}` | {'是' if item['blocksCreation'] else '否'} | {'是' if item['blocksBinding'] else '否'} | "
                f"{'是' if item['blocksEnablement'] else '否'} | {'是' if item['blocksPublication'] else '否'} | {md(item['recommendation'])} |"
            )
        lines.append("")
    publish = [item for item in mapping["risks"] if item.get("blocksPublication")]
    lines.extend(["## 发布阻断项汇总", "", f"共 {len(publish)} 个聚合发布阻断项。必须逐项解除并取得明确发布授权后才能发布。", ""])
    return "\n".join(lines)


def write_outputs(mapping, objects, adjacency, output_dir):
    app_name = safe_file_name(mapping["application"].get("name"))
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "overviewReport": output / f"{app_name}_应用功能全景报告.md",
        "objectIndex": output / f"{app_name}_应用对象索引.md",
        "dependencyRiskReport": output / f"{app_name}_依赖与风险清单.md",
        "businessFunctionMap": output / f"{app_name}_业务功能映射.json",
        "validation": output / f"{app_name}_业务可读版报告校验.json",
    }
    paths["overviewReport"].write_text(render_overview(mapping, objects) + "\n", encoding="utf-8")
    paths["objectIndex"].write_text(render_object_index(mapping, objects, adjacency) + "\n", encoding="utf-8")
    paths["dependencyRiskReport"].write_text(render_risks(mapping) + "\n", encoding="utf-8")
    dump_json(paths["businessFunctionMap"], mapping)
    return paths


def main():
    parser = argparse.ArgumentParser(description="Generate business-readable reports from an existing Application IR.")
    parser.add_argument("application_ir")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--build-plan")
    parser.add_argument("--import-requirements")
    args = parser.parse_args()
    ir = load_json(args.application_ir)
    build_plan = load_json(args.build_plan) if args.build_plan else None
    import_requirements = load_json(args.import_requirements) if args.import_requirements else None
    mapping, objects, adjacency = build_mapping(ir, build_plan, import_requirements)
    paths = write_outputs(mapping, objects, adjacency, args.output_dir)
    result = {
        "status": "generated",
        "outputs": {key: str(value.resolve()) for key, value in paths.items()},
        "summary": mapping["summary"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
