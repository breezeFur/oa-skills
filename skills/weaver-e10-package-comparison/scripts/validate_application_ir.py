#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ir_common import load_json


REQUIRED_TOP = [
    "irVersion", "kind", "application", "modules", "dataModel", "forms", "pages",
    "actionFlows", "aiApplications", "workflows", "permissions", "reports", "navigation",
    "integrations", "dependencies", "evidence", "build", "serviceInventory",
    "serviceFragments", "businessObjects", "externalResources", "migrationRules",
]
LIST_SECTIONS = [
    "modules", "forms", "pages", "actionFlows", "aiApplications", "workflows", "permissions",
    "reports", "integrations", "dependencies",
]
OPTIONAL_LIST_SECTIONS = ["multiFillingTasks"]
EXTENDED_LIST_SECTIONS = [
    "serviceInventory", "serviceFragments", "businessObjects", "externalResources"
]
STATUSES = {"READY", "ADAPTER_REQUIRED", "BLOCKED"}


def validate(data):
    errors, warnings = [], []
    for key in REQUIRED_TOP:
        if key not in data:
            errors.append(f"missing top-level field: {key}")
    if errors:
        return errors, warnings
    if data["irVersion"] != "1.0":
        errors.append("irVersion must equal 1.0")
    if data["kind"] != "ebuilder.application-ir":
        errors.append("kind must equal ebuilder.application-ir")
    for key in LIST_SECTIONS:
        if not isinstance(data.get(key), list):
            errors.append(f"{key} must be an array")
    for key in OPTIONAL_LIST_SECTIONS:
        if key in data and not isinstance(data.get(key), list):
            errors.append(f"{key} must be an array")
    for key in EXTENDED_LIST_SECTIONS:
        if not isinstance(data.get(key), list):
            errors.append(f"{key} must be an array")
    if not isinstance(data.get("dataModel"), dict):
        errors.append("dataModel must be an object")
    else:
        for key in ("entities", "relations"):
            if not isinstance(data["dataModel"].get(key), list):
                errors.append(f"dataModel.{key} must be an array")
        if "datasets" in data["dataModel"] and not isinstance(
            data["dataModel"].get("datasets"), list
        ):
            errors.append("dataModel.datasets must be an array")
    if not isinstance(data.get("navigation"), dict):
        errors.append("navigation must be an object")
    elif not isinstance(data["navigation"].get("menus"), list):
        errors.append("navigation.menus must be an array")
    if data.get("build", {}).get("status") not in STATUSES:
        errors.append("build.status must be READY, ADAPTER_REQUIRED, or BLOCKED")

    all_items = {
        "application": [data.get("application", {})],
        "modules": data.get("modules", []),
        "entities": data.get("dataModel", {}).get("entities", []),
        "relations": data.get("dataModel", {}).get("relations", []),
        "datasets": data.get("dataModel", {}).get("datasets", []),
        **{key: data.get(key, []) for key in LIST_SECTIONS if key != "modules"},
        **{key: data.get(key, []) for key in OPTIONAL_LIST_SECTIONS},
        **{key: data.get(key, []) for key in EXTENDED_LIST_SECTIONS},
    }
    for section in ("applicationShells", "navigations", "combinations", "menus"):
        all_items[f"navigation.{section}"] = data.get("navigation", {}).get(
            section, []
        )
    known_keys = set()
    for section, items in all_items.items():
        seen = set()
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"{section}[{index}] must be an object")
                continue
            logical_key = item.get("logicalKey")
            if not logical_key:
                errors.append(f"{section}[{index}] lacks logicalKey")
                continue
            if logical_key in seen:
                errors.append(f"duplicate logicalKey in {section}: {logical_key}")
            seen.add(logical_key)
            known_keys.add(logical_key)
            source = item.get("sourceRef")
            if section != "dependencies" and not isinstance(source, dict):
                errors.append(f"{section}[{logical_key}] lacks sourceRef")
            elif isinstance(source, dict) and source.get("sourceId") is not None and not isinstance(source.get("sourceId"), str):
                errors.append(f"{section}[{logical_key}] sourceRef.sourceId must be a string")

    for dependency in data.get("dependencies", []):
        if not isinstance(dependency, dict):
            continue
        key = dependency.get("logicalKey", "<unknown>")
        if not isinstance(dependency.get("sourceRef"), dict):
            errors.append(f"dependency {key} lacks sourceRef")
        if dependency.get("status") not in {"resolved", "unresolved", "external", "unsupported"}:
            errors.append(f"dependency {key} has invalid status")
        if dependency.get("status") == "resolved":
            if dependency.get("from") not in known_keys:
                warnings.append(f"resolved dependency {key} has unknown from key: {dependency.get('from')}")
            if dependency.get("to") not in known_keys:
                errors.append(f"resolved dependency {key} has unknown to key: {dependency.get('to')}")

    for entity in data.get("dataModel", {}).get("entities", []):
        field_seen = set()
        for field in entity.get("fields", []):
            key = field.get("logicalKey")
            if not key:
                errors.append(f"entity {entity.get('logicalKey')} contains field without logicalKey")
            elif key in field_seen:
                errors.append(f"entity {entity.get('logicalKey')} has duplicate field key {key}")
            field_seen.add(key)
            source_id = field.get("sourceRef", {}).get("sourceId")
            if source_id is not None and not isinstance(source_id, str):
                errors.append(f"field {key} sourceRef.sourceId must be a string")

    unresolved_count = len(data.get("evidence", {}).get("unresolved", []))
    if unresolved_count and data.get("build", {}).get("status") == "READY":
        warnings.append("build.status is READY while evidence.unresolved is non-empty")
    module_services = {item.get("service") for item in data.get("modules", [])}
    inventory_services = {item.get("service") for item in data.get("serviceInventory", [])}
    fragment_services = {item.get("service") for item in data.get("serviceFragments", [])}
    if module_services != inventory_services:
        errors.append("modules and serviceInventory services must match")
    if module_services != fragment_services:
        errors.append("modules and serviceFragments services must match")
    for item in data.get("modules", []) + data.get("serviceInventory", []) + data.get("serviceFragments", []):
        if item.get("analysisLevel") not in {"FULL_SEMANTIC", "STRUCTURAL", "EVIDENCE_ONLY"}:
            errors.append(f"invalid analysisLevel for service {item.get('service')}")
    return errors, warnings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("application_ir")
    parser.add_argument("--report")
    args = parser.parse_args()
    data = load_json(args.application_ir)
    errors, warnings = validate(data)
    result = {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "source": str(Path(args.application_ir).resolve()),
    }
    if args.report:
        Path(args.report).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
