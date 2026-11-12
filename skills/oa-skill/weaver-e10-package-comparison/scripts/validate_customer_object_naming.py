#!/usr/bin/env python3
"""Self-test that customer reports preserve concrete child-object names after aggregation."""

from __future__ import annotations

import json

from compare_reconstructed_application import compare_card, validate_concrete_object_names
from render_panorama_visual_html import public_model


def side(workflows: list[dict]) -> dict:
    return {
        "nameMap": {item["logicalKey"]: item["name"] for item in workflows},
        "workflowMap": {item["logicalKey"]: item for item in workflows},
    }


def workflow(key: str, name: str, scopes: list[str]) -> dict:
    return {
        "logicalKey": key,
        "name": name,
        "browserDataScopes": [{"businessDescription": value} for value in scopes],
    }


def card(name: str, refs: list[str]) -> dict:
    return {
        "logicalKey": f"business-function:{name}:业务处理",
        "name": name,
        "domain": "business-domain:测试",
        "purpose": f"支持{name}相关的业务处理。",
        "workflows": refs,
    }


def comparison_model(changes: list[dict]) -> dict:
    return {
        "applicationName": "名称回归测试",
        "oldSummary": {},
        "newSummary": {},
        "changeSummary": {"新增": 0, "删除": 0, "归属调整": 0, "更新": len(changes)},
        "domainChanges": [],
        "featureChanges": changes,
        "chainChanges": {"added": [], "removed": [], "updated": []},
        "testPoints": [],
        "limitations": [],
    }


def main() -> None:
    old = side([workflow("workflow:hours", "工时填报", [])])
    new = side([workflow("workflow:hours", "工时填报", ["项目任务：所属项目编码等于工时明细.项目编码"])])
    change = compare_card(card("工时填报单", ["workflow:hours"]), card("工时填报单", ["workflow:hours"]), old, new, "更新")
    change["testPoints"] = []
    assert change["displayName"] == "工时填报"
    assert change["businessFunctionName"] == "工时填报单"
    assert [item["newName"] for item in change["changedObjects"]] == ["工时填报"]
    assert change["differences"]["workflowBrowserDataScopes"]["added"] == ["工时填报：项目任务：所属项目编码等于工时明细.项目编码"]

    old_multi = side([
        workflow("workflow:delivery", "交付项目立项", []),
        workflow("workflow:research", "研发项目立项", []),
    ])
    new_multi = side([
        workflow("workflow:delivery", "交付项目立项", ["合同名称：合同状态等于履行中"]),
        workflow("workflow:research", "研发项目立项", ["项目类型：类型编码不等于YF"]),
    ])
    multi = compare_card(card("立项", ["workflow:delivery", "workflow:research"]), card("立项", ["workflow:delivery", "workflow:research"]), old_multi, new_multi, "更新")
    multi["testPoints"] = []
    assert multi["displayName"] == "交付项目立项、研发项目立项"
    validation = validate_concrete_object_names([change, multi])
    assert validation["valid"] and validation["checkedObjectCount"] == 3

    visual = public_model(comparison_model([change, multi]))
    assert visual["features"][0]["name"] == "工时填报"
    assert visual["features"][0]["businessFunctionName"] == "工时填报单"
    assert visual["features"][0]["changedObjects"] == [{"type": "审批流程", "name": "工时填报"}]
    assert [item["name"] for item in visual["features"][1]["changedObjects"]] == ["交付项目立项", "研发项目立项"]
    print(json.dumps({
        "status": "PASS",
        "singleObjectTitlePreserved": True,
        "multiObjectNamesPreserved": True,
        "businessFunctionOwnershipPreserved": True,
        "visualModelPreserved": True,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
