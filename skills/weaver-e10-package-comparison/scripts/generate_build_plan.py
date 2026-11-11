#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from ir_common import dump_json, load_json


def batch(items, size=20):
    return [
        [item["logicalKey"] for item in items[index:index + size]]
        for index in range(0, len(items), size)
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("application_ir")
    parser.add_argument("--output", required=True)
    parser.add_argument("--report")
    parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args()
    ir = load_json(args.application_ir)
    unresolved_dependencies = [
        x for x in ir.get("dependencies", [])
        if x.get("status") in {"unresolved", "unsupported"}
    ]
    external_dependencies = [
        x for x in ir.get("dependencies", []) if x.get("status") == "external"
    ]
    adapters = ir.get("build", {}).get("adapterRequirements", [])
    import_requirements = ir.get("importRequirements", {})
    required_import_inputs = import_requirements.get("requiredInputs", [])
    unresolved_required_inputs = [
        item for item in required_import_inputs
        if item.get("status") == "USER_INPUT_REQUIRED"
    ]
    optional_import_mappings = import_requirements.get("optionalMappings", [])
    structural_services = [
        item for item in ir.get("serviceInventory", [])
        if item.get("analysisLevel") == "STRUCTURAL"
    ]
    evidence_only_services = [
        item for item in ir.get("serviceInventory", [])
        if item.get("analysisLevel") == "EVIDENCE_ONLY"
    ]
    stages = [
        {
            "order": 1,
            "key": "preflight",
            "name": "目标环境与能力预检",
            "objects": [],
            "requires": [],
            "gates": ["target-builder-contract", "conflict-scan", "capability-matrix"],
        },
        {
            "order": 2,
            "key": "application-shell-and-roles",
            "name": "应用骨架、角色与组织前置项",
            "objects": [ir["application"]["logicalKey"]],
            "requires": ["preflight"],
            "gates": ["application-logical-key-unique", "organization-resolution"],
        },
        {
            "order": 3,
            "key": "data-model-and-forms",
            "name": "数据模型、数据集与表单",
            "objects": [x["logicalKey"] for x in ir.get("dataModel", {}).get("entities", [])]
            + [x["logicalKey"] for x in ir.get("dataModel", {}).get("datasets", [])]
            + [x["logicalKey"] for x in ir.get("forms", [])],
            "batches": batch(ir.get("forms", []), args.batch_size),
            "requires": ["application-shell-and-roles"],
            "gates": ["no-source-id-writes", "form-relations-resolved", "option-mapping-resolved"],
        },
        {
            "order": 4,
            "key": "action-flows-and-extensions",
            "name": "动作流与服务端扩展",
            "objects": [x["logicalKey"] for x in ir.get("actionFlows", [])],
            "batches": batch(ir.get("actionFlows", []), args.batch_size),
            "requires": ["data-model-and-forms"],
            "gates": ["component-config-resolved", "branch-integrity", "integration-safety"],
        },
        {
            "order": 5,
            "key": "ai-applications-and-agents",
            "name": "AI 应用、智能体、提示词与知识能力",
            "objects": [x["logicalKey"] for x in ir.get("aiApplications", [])],
            "batches": batch(ir.get("aiApplications", []), args.batch_size),
            "requires": ["data-model-and-forms", "action-flows-and-extensions"],
            "gates": [
                "ai-model-resolution",
                "ai-function-bindings-resolved",
                "ai-sensitive-config-reviewed",
                "ai-import-disabled-until-verified",
            ],
        },
        {
            "order": 6,
            "key": "pages-and-navigation",
            "name": "页面、嵌入式视图与导航",
            "objects": [x["logicalKey"] for x in ir.get("pages", [])],
            "batches": batch(ir.get("pages", []), args.batch_size),
            "requires": ["data-model-and-forms", "action-flows-and-extensions"],
            "gates": ["dataset-bindings-resolved", "component-tree-valid", "terminal-parity-reviewed"],
        },
        {
            "order": 7,
            "key": "workflows",
            "name": "BPM 与 Workflow PathDef 审批定义、版本、节点及绑定",
            "objects": [x["logicalKey"] for x in ir.get("workflows", [])],
            "batches": batch(ir.get("workflows", []), args.batch_size),
            "requires": ["data-model-and-forms", "action-flows-and-extensions"],
            "gates": [
                "workflow-version-groups-valid",
                "approver-resolution",
                "subworkflow-resolution",
                "callback-bindings-resolved",
            ],
        },
        {
            "order": 8,
            "key": "reports-and-integrations",
            "name": "报表与外部集成",
            "objects": [x["logicalKey"] for x in ir.get("reports", [])]
            + [x["logicalKey"] for x in ir.get("integrations", [])],
            "requires": ["data-model-and-forms"],
            "gates": ["data-source-resolution", "credential-policy", "retry-idempotency"],
        },
        {
            "order": 9,
            "key": "multi-filling",
            "name": "EDC 多级填报任务与运行编排",
            "objects": [
                x["logicalKey"] for x in ir.get("multiFillingTasks", [])
            ],
            "batches": batch(ir.get("multiFillingTasks", []), args.batch_size),
            "requires": ["data-model-and-forms", "reports-and-integrations"],
            "gates": [
                "task-graph-valid",
                "filling-targets-resolved",
                "execution-permissions-resolved",
            ],
        },
        {
            "order": 10,
            "key": "cusapp-navigation-and-menus",
            "name": "CusApp 导航、系统菜单与前台菜单",
            "objects": [
                x["logicalKey"]
                for section in (
                    "applicationShells",
                    "navigations",
                    "combinations",
                    "menus",
                )
                for x in ir.get("navigation", {}).get(section, [])
            ],
            "requires": [
                "pages-and-navigation",
                "workflows",
                "reports-and-integrations",
                "multi-filling",
            ],
            "gates": [
                "terminal-navigation-reviewed",
                "menu-trees-valid",
                "menu-targets-resolved",
            ],
        },
        {
            "order": 11,
            "key": "permissions-and-cross-bindings",
            "name": "权限与跨模块绑定",
            "objects": [x["logicalKey"] for x in ir.get("permissions", [])]
            + [x["logicalKey"] for x in ir.get("dependencies", [])],
            "requires": [
                "pages-and-navigation",
                "workflows",
                "reports-and-integrations",
                "multi-filling",
                "cusapp-navigation-and-menus",
            ],
            "gates": ["all-target-ids-resolved", "permission-matrix-tested", "no-dangling-reference"],
        },
        {
            "order": 12,
            "key": "verification-and-publication",
            "name": "验收、修复与发布",
            "objects": [],
            "requires": ["permissions-and-cross-bindings"],
            "gates": [
                "static-counts-match",
                "semantic-bindings-pass",
                "business-report-coverage-pass",
                "business-prompt-summary-consistent",
                "runtime-scenarios-pass",
                "explicit-publication-authorization",
            ],
        },
    ]
    for stage in stages[1:]:
        stage["order"] += 1
    stages.insert(1, {
        "order": 2,
        "key": "import-requirements-resolution",
        "name": "迁入必填配置与目标映射确认",
        "objects": [
            item.get("requirementId")
            for item in required_import_inputs
            if item.get("requirementId")
        ],
        "requires": ["preflight"],
        "gates": [
            "required-import-inputs-resolved",
            "secret-values-runtime-only",
            "optional-message-account-mapping-nonblocking",
        ],
        "optionalMappings": optional_import_mappings,
    })
    next(
        stage for stage in stages
        if stage["key"] == "application-shell-and-roles"
    )["requires"] = ["import-requirements-resolution"]
    blockers = []
    if unresolved_dependencies:
        blockers.append({
            "kind": "unresolved-dependencies",
            "count": len(unresolved_dependencies),
            "publishBlocking": True,
        })
    if ir.get("evidence", {}).get("parseErrors"):
        blockers.append({
            "kind": "parse-errors",
            "count": len(ir["evidence"]["parseErrors"]),
            "publishBlocking": True,
        })
    if unresolved_required_inputs:
        blockers.append({
            "kind": "required-import-inputs",
            "count": len(unresolved_required_inputs),
            "buildBlocking": True,
            "publishBlocking": True,
        })
    status = "ADAPTER_REQUIRED" if adapters else ("BLOCKED" if blockers else "READY")
    plan = {
        "planVersion": "1.0",
        "application": ir["application"],
        "sourceIR": str(Path(args.application_ir).resolve()),
        "status": status,
        "stages": stages,
        "adapterRequirements": adapters,
        "blockers": blockers,
        "externalDependencies": external_dependencies,
        "serviceCoverage": {
            "services": ir.get("serviceInventory", []),
            "structuralOnly": [x.get("service") for x in structural_services],
            "evidenceOnly": [x.get("service") for x in evidence_only_services],
            "policy": "Only branches requiring unavailable dedicated semantics are deferred; confirmed modules continue.",
        },
        "importRequirements": {
            "requiredInputs": required_import_inputs,
            "unresolvedRequiredInputs": unresolved_required_inputs,
            "optionalMappings": optional_import_mappings,
            "messageAccountMappingPolicy": "NON_BLOCKING_ACTION_FLOW_CREATION",
        },
        "acceptance": {
            "static": [
                "target object counts and stable logical keys match",
                "no source-environment identity leaks into target writes",
                "all cross-module bindings resolve to target IDs",
                "business-readable reports cover every tracked Application IR object",
                "both AI prompt formats use the same status and object-count summary",
            ],
            "runtime": [
                "normal path",
                "each branch and failure path",
                "permission roles and data scopes",
                "repeat execution and idempotency",
                "external dependency failure and recovery",
            ],
            "publishRule": "Never publish while a publish-blocking item remains or without explicit authorization.",
        },
    }
    dump_json(args.output, plan)
    if args.report:
        stage_names = {stage["key"]: stage["name"] for stage in stages}
        gate_names = {
            "target-builder-contract": "目标搭建器协议已确认",
            "conflict-scan": "名称与逻辑键冲突扫描通过",
            "capability-matrix": "目标能力矩阵已确认",
            "required-import-inputs-resolved": "迁入必填配置已由用户提供目标值",
            "secret-values-runtime-only": "敏感值仅通过运行时安全输入传递",
            "optional-message-account-mapping-nonblocking": "企业/应用映射缺失仅挂起消息渠道绑定",
            "application-logical-key-unique": "应用逻辑键唯一",
            "organization-resolution": "组织与角色映射已解析",
            "no-source-id-writes": "目标写入不含源环境身份",
            "form-relations-resolved": "表单关系已解析",
            "option-mapping-resolved": "选项映射已解析",
            "component-config-resolved": "动作组件配置已解析",
            "branch-integrity": "分支和连线完整",
            "integration-safety": "外部集成安全检查通过",
            "ai-model-resolution": "AI 模型和鉴权资源已在目标环境解析",
            "ai-function-bindings-resolved": "AI 函数、动作流、MCP 与子智能体绑定已解析",
            "ai-sensitive-config-reviewed": "AI 敏感规则、文件和跨应用配置已复核",
            "ai-import-disabled-until-verified": "AI 应用在完成回读与运行验收前保持禁用",
            "dataset-bindings-resolved": "数据集绑定已解析",
            "component-tree-valid": "页面组件树有效",
            "terminal-parity-reviewed": "PC/移动差异已复核",
            "approver-resolution": "审批操作者已解析",
            "workflow-version-groups-valid": "审批流程 fixed_version_id 版本组与活动版本有效",
            "subworkflow-resolution": "子流程和流程变量引用已解析",
            "callback-bindings-resolved": "流程回调绑定已解析",
            "data-source-resolution": "报表和集成数据源已解析",
            "credential-policy": "凭据策略符合要求",
            "retry-idempotency": "重试和幂等策略已确认",
            "task-graph-valid": "多级填报任务图完整",
            "filling-targets-resolved": "填报表单、报表、布局和汇总目标已解析",
            "execution-permissions-resolved": "填报执行操作者与权限已解析",
            "terminal-navigation-reviewed": "PC/H5 导航差异已复核",
            "menu-trees-valid": "系统菜单树与前台菜单树有效",
            "menu-targets-resolved": "菜单跨模块目标已解析",
            "all-target-ids-resolved": "全部目标 ID 已回填",
            "permission-matrix-tested": "权限矩阵已测试",
            "no-dangling-reference": "不存在悬空引用",
            "static-counts-match": "静态对象数量一致",
            "semantic-bindings-pass": "语义绑定校验通过",
            "business-report-coverage-pass": "业务报告对象覆盖门禁通过",
            "business-prompt-summary-consistent": "两套提示词与业务报告状态及对象数量一致",
            "runtime-scenarios-pass": "运行场景验收通过",
            "explicit-publication-authorization": "已取得明确发布授权",
        }
        lines = [
            f"# {ir['application']['name']}应用还原计划",
            "",
            f"- 状态：`{status}`",
            f"- Application IR：`{Path(args.application_ir).resolve()}`",
            f"- 目标适配项：{len(adapters)}",
            f"- 未解决依赖：{len(unresolved_dependencies)}",
            f"- 外部依赖：{len(external_dependencies)}",
            f"- 迁入必填配置：{len(required_import_inputs)}",
            f"- 尚待用户提供：{len(unresolved_required_inputs)}",
            f"- 可选消息账号映射：{len(optional_import_mappings)}",
            "",
            "## 执行阶段",
            "",
        ]
        for stage in stages:
            lines.extend([
                f"### {stage['order']}. {stage['name']}",
                "",
                f"- 对象数：{len(stage.get('objects', []))}",
                "- 前置阶段："
                + (
                    "、".join(
                        stage_names.get(item, item)
                        for item in stage.get("requires", [])
                    )
                    or "无"
                ),
                "- 阶段门禁："
                + "、".join(
                    gate_names.get(item, item)
                    for item in stage.get("gates", [])
                ),
                "",
            ])
        lines.extend(["## 阻断项", ""])
        if blockers:
            blocker_names = {
                "unresolved-dependencies": "未解决依赖",
                "parse-errors": "解析错误",
                "required-import-inputs": "迁入必填配置尚未提供",
            }
            lines.extend(
                f"- {blocker_names.get(x['kind'], x['kind'])}：{x['count']}"
                for x in blockers
            )
        else:
            lines.append("- 无结构性阻断；仍需完成目标搭建器适配和运行验收。")
        lines.extend([
            "",
            "## 发布规则",
            "",
            "静态对账、语义绑定、权限路径和运行场景全部通过，并取得明确发布授权后才能发布。",
            "",
        ])
        Path(args.report).write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "output": str(Path(args.output).resolve()),
        "report": str(Path(args.report).resolve()) if args.report else None,
        "status": status,
        "stages": len(stages),
        "blockers": len(blockers),
        "adapterRequirements": len(adapters),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
