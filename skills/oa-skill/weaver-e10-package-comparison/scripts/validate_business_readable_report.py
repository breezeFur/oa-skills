#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from business_report_common import (
    ASSIGNMENT_METHODS,
    CARD_STATUSES,
    EVIDENCE_LEVELS,
    LONG_ID_RE,
    collect_objects,
    dependency_counts,
    import_requirement_counts,
    load_json,
    safe_file_name,
    summarize_counts,
)


SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA = SKILL_DIR / "assets" / "business-function-map-v1.0.schema.json"
SENSITIVE_KEYS = re.compile(r"password|passwd|pwd|secret|token|cookie|private.?key|access.?key|credential", re.I)
SUCCESS_PHRASES = ("已搭建成功", "已迁入成功", "已运行成功", "运行通过", "已经发布成功")
NEGATIONS = ("不", "未", "不得", "并非", "不代表", "没有")


def schema_validate(mapping, schema_path):
    errors, warnings = [], []
    schema = load_json(schema_path)
    try:
        import jsonschema
    except ImportError:
        errors.extend(validate_schema_subset(mapping, schema, schema))
        warnings.append("validated with bundled JSON Schema subset engine because jsonschema package is unavailable")
        return errors, warnings
    validator = jsonschema.Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(mapping), key=lambda item: list(item.absolute_path)):
        location = ".".join(str(value) for value in error.absolute_path) or "$"
        errors.append(f"schema[{location}]: {error.message}")
    return errors, warnings


def validate_schema_subset(instance, schema, root_schema, path="$"):
    errors = []
    if "$ref" in schema:
        reference = schema["$ref"]
        if not reference.startswith("#/"):
            return [f"schema[{path}]: unsupported external reference {reference}"]
        target = root_schema
        for part in reference[2:].split("/"):
            target = target[part.replace("~1", "/").replace("~0", "~")]
        return validate_schema_subset(instance, target, root_schema, path)
    if "const" in schema and instance != schema["const"]:
        errors.append(f"schema[{path}]: value must equal {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"schema[{path}]: value {instance!r} is outside enum")
    expected_type = schema.get("type")
    if expected_type:
        allowed = expected_type if isinstance(expected_type, list) else [expected_type]
        type_checks = {
            "object": lambda value: isinstance(value, dict),
            "array": lambda value: isinstance(value, list),
            "string": lambda value: isinstance(value, str),
            "null": lambda value: value is None,
            "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
            "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
            "boolean": lambda value: isinstance(value, bool),
        }
        if not any(type_checks[name](instance) for name in allowed):
            return [f"schema[{path}]: expected type {'|'.join(allowed)}"]
    if isinstance(instance, str) and len(instance) < schema.get("minLength", 0):
        errors.append(f"schema[{path}]: string is shorter than minLength")
    if isinstance(instance, dict):
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"schema[{path}]: missing required property {key}")
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in properties:
                    errors.append(f"schema[{path}]: unexpected property {key}")
        for key, value in instance.items():
            if key in properties:
                errors.extend(validate_schema_subset(value, properties[key], root_schema, f"{path}.{key}"))
    if isinstance(instance, list):
        if schema.get("uniqueItems"):
            markers = [json.dumps(value, ensure_ascii=False, sort_keys=True) for value in instance]
            if len(markers) != len(set(markers)):
                errors.append(f"schema[{path}]: array items are not unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, value in enumerate(instance):
                errors.extend(validate_schema_subset(value, item_schema, root_schema, f"{path}[{index}]"))
    return errors


def duplicate_values(values):
    counter = Counter(values)
    return sorted(key for key, count in counter.items() if count > 1)


def find_sensitive_values(value, path="$", results=None):
    results = results if results is not None else []
    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if SENSITIVE_KEYS.search(str(key)) and item not in (None, "", "***REDACTED***", "MASKED", "REDACTED"):
                results.append(child_path)
            find_sensitive_values(item, child_path, results)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            find_sensitive_values(item, f"{path}[{index}]", results)
    return results


def positive_success_claims(text):
    hits = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for phrase in SUCCESS_PHRASES:
            if phrase not in line:
                continue
            prefix = line[max(0, line.find(phrase) - 16):line.find(phrase)]
            if not any(negation in prefix for negation in NEGATIONS):
                hits.append({"line": line_number, "phrase": phrase})
    return hits


def infer_reports(mapping_path, mapping):
    directory = mapping_path.parent
    app_name = safe_file_name(mapping.get("application", {}).get("name"))
    return {
        "overview": directory / f"{app_name}_应用功能全景报告.md",
        "index": directory / f"{app_name}_应用对象索引.md",
        "risks": directory / f"{app_name}_依赖与风险清单.md",
    }


def validate(ir, mapping, overview_text=None, object_index_text=None, import_requirements=None, schema_path=DEFAULT_SCHEMA):
    errors, warnings = [], []
    checks = {}
    schema_errors, schema_warnings = schema_validate(mapping, schema_path)
    errors.extend(schema_errors)
    warnings.extend(schema_warnings)
    checks["schemaValid"] = not schema_errors

    objects = collect_objects(ir)
    expected_by_key = {item["logicalKey"]: item for item in objects}
    expected_keys = set(expected_by_key)
    assignments = mapping.get("objectAssignments", [])
    assignment_keys = [item.get("logicalKey") for item in assignments]
    duplicate_assignments = duplicate_values(assignment_keys)
    if duplicate_assignments:
        errors.append(f"duplicate objectAssignments logicalKey: {duplicate_assignments[:10]}")
    checks["objectAssignmentLogicalKeysUnique"] = not duplicate_assignments

    assigned_key_set = set(assignment_keys)
    missing = sorted(expected_keys - assigned_key_set)
    extra = sorted(assigned_key_set - expected_keys)
    if missing:
        errors.append(f"Application IR objects missing from objectAssignments: {missing[:20]} (total {len(missing)})")
    if extra:
        errors.append(f"objectAssignments reference unknown objects: {extra[:20]} (total {len(extra)})")
    checks["allApplicationIRObjectsAssignedOrUnmapped"] = not missing and not extra

    unmapped_keys = {item.get("logicalKey") for item in mapping.get("unmappedObjects", [])}
    assignment_unmapped = {
        item.get("logicalKey") for item in assignments
        if item.get("assignmentMethod") == "UNMAPPED"
    }
    if unmapped_keys != assignment_unmapped:
        errors.append("unmappedObjects and objectAssignments[UNMAPPED] are inconsistent")
    checks["unmappedObjectsConsistent"] = unmapped_keys == assignment_unmapped

    domain_keys = [item.get("logicalKey") for item in mapping.get("businessDomains", [])]
    card_keys = [item.get("logicalKey") for item in mapping.get("functionCards", [])]
    chain_keys = [item.get("logicalKey") for item in mapping.get("endToEndChains", [])]
    for label, values in (("businessDomains", domain_keys), ("functionCards", card_keys), ("endToEndChains", chain_keys)):
        duplicates = duplicate_values(values)
        if duplicates:
            errors.append(f"duplicate {label} logicalKey: {duplicates[:10]}")
    checks["derivedLogicalKeysUnique"] = not any(duplicate_values(values) for values in (domain_keys, card_keys, chain_keys))

    domain_set, card_set = set(domain_keys), set(card_keys)
    reference_errors = []
    for domain in mapping.get("businessDomains", []):
        for card_key in domain.get("functionCards", []):
            if card_key not in card_set:
                reference_errors.append(f"domain {domain.get('logicalKey')} -> unknown card {card_key}")
    object_reference_fields = (
        "entries", "entities", "datasets", "forms", "pages", "actionFlows", "workflows",
        "menus", "permissions", "integrations", "dependencies",
    )
    for card in mapping.get("functionCards", []):
        if card.get("domain") not in domain_set:
            reference_errors.append(f"card {card.get('logicalKey')} -> unknown domain {card.get('domain')}")
        if card.get("status") not in CARD_STATUSES:
            reference_errors.append(f"card {card.get('logicalKey')} has invalid status")
        if card.get("evidenceLevel") not in EVIDENCE_LEVELS:
            reference_errors.append(f"card {card.get('logicalKey')} has invalid evidence level")
        for field in object_reference_fields:
            for key in card.get(field, []):
                if key.startswith("adapter:"):
                    continue
                if key not in expected_keys:
                    reference_errors.append(f"card {card.get('logicalKey')}.{field} -> unknown object {key}")
    for assignment in assignments:
        if assignment.get("assignmentMethod") not in ASSIGNMENT_METHODS:
            reference_errors.append(f"assignment {assignment.get('logicalKey')} has invalid method")
        if assignment.get("primaryDomain") is not None and assignment.get("primaryDomain") not in domain_set:
            reference_errors.append(f"assignment {assignment.get('logicalKey')} -> unknown domain")
        for card_key in assignment.get("functionCards", []):
            if card_key not in card_set:
                reference_errors.append(f"assignment {assignment.get('logicalKey')} -> unknown card {card_key}")
    for chain in mapping.get("endToEndChains", []):
        if chain.get("functionCard") not in card_set:
            reference_errors.append(f"chain {chain.get('logicalKey')} -> unknown card")
        for node in chain.get("nodes", []):
            if node.get("logicalKey") not in expected_keys:
                reference_errors.append(f"chain {chain.get('logicalKey')} -> unknown node {node.get('logicalKey')}")
    if reference_errors:
        errors.extend(reference_errors[:100])
    checks["allReferencesClose"] = not reference_errors

    expected_counts = summarize_counts(objects)
    actual_counts = mapping.get("summary", {}).get("objectCounts", {})
    if expected_counts != actual_counts:
        errors.append(f"object count mismatch: expected={expected_counts}, actual={actual_counts}")
    checks["objectCountsMatchApplicationIR"] = expected_counts == actual_counts

    expected_ir_summary = ir.get("summary", {})
    actual_ir_summary = mapping.get("summary", {}).get("applicationIRSummary", {})
    if expected_ir_summary != actual_ir_summary:
        errors.append("business function map does not preserve the complete Application IR summary")
    checks["applicationIRSummaryPreserved"] = expected_ir_summary == actual_ir_summary

    expected_dependencies = dependency_counts(ir)
    actual_dependencies = mapping.get("summary", {}).get("dependencyCounts", {})
    if expected_dependencies != actual_dependencies:
        errors.append(f"dependency count mismatch: expected={expected_dependencies}, actual={actual_dependencies}")
    checks["dependencyCountsMatch"] = expected_dependencies == actual_dependencies

    expected_imports = import_requirement_counts(ir, import_requirements)
    actual_imports = mapping.get("summary", {}).get("importRequirementCounts", {})
    if expected_imports != actual_imports:
        errors.append(f"import requirement count mismatch: expected={expected_imports}, actual={actual_imports}")
    checks["importRequirementCountsMatch"] = expected_imports == actual_imports

    expected_parse_errors = len(ir.get("evidence", {}).get("parseErrors", []))
    actual_parse_errors = mapping.get("summary", {}).get("parseErrorCount")
    checks["parseErrorsSeparatedFromBusinessUnresolved"] = actual_parse_errors == expected_parse_errors and "businessUnresolvedCount" in mapping.get("summary", {})
    if not checks["parseErrorsSeparatedFromBusinessUnresolved"]:
        errors.append("parse errors and business unresolved counts are not independently preserved")

    sensitive_hits = find_sensitive_values(mapping)
    if sensitive_hits:
        errors.append(f"sensitive values found at: {sensitive_hits[:20]}")
    checks["noSensitiveValues"] = not sensitive_hits

    if overview_text is not None:
        long_id_hits = LONG_ID_RE.findall(overview_text)
        success_hits = positive_success_claims(overview_text)
        if long_id_hits:
            errors.append(f"overview report leaks {len(long_id_hits)} source-like long IDs")
        if success_hits:
            errors.append(f"overview report contains unsupported success claims: {success_hits[:10]}")
        inferred_needed = any(card.get("evidenceLevel") == "BUSINESS_INFERRED" for card in mapping.get("functionCards", []))
        unresolved_needed = bool(mapping.get("unmappedObjects")) or any(card.get("status") == "UNRESOLVED" for card in mapping.get("functionCards", []))
        labels_ok = (not inferred_needed or "BUSINESS_INFERRED" in overview_text) and (not unresolved_needed or "UNRESOLVED" in overview_text)
        if not labels_ok:
            errors.append("overview report does not explicitly label BUSINESS_INFERRED or UNRESOLVED conclusions")
        heading_count = len(re.findall(r"^### ", overview_text, flags=re.M))
        aggregation_ok = heading_count <= len(mapping.get("functionCards", [])) + len(mapping.get("endToEndChains", [])) + len(mapping.get("businessDomains", [])) + 12
        if not aggregation_ok:
            errors.append("overview report appears to mechanically flatten technical objects")
        checks.update({
            "overviewHasNoSourceLongIds": not long_id_hits,
            "overviewHasNoUnsupportedSuccessClaim": not success_hits,
            "inferredAndUnresolvedAreLabeled": labels_ok,
            "overviewUsesBusinessAggregation": aggregation_ok,
        })
    else:
        warnings.append("overview report was not provided; wording and long-ID checks were skipped")

    if object_index_text is not None:
        missing_from_index = [key for key in expected_keys if key not in object_index_text]
        if missing_from_index:
            errors.append(f"object index omits logical keys: {missing_from_index[:20]} (total {len(missing_from_index)})")
        checks["objectIndexCoversAllTrackedObjects"] = not missing_from_index
    else:
        warnings.append("object index was not provided; index coverage check was skipped")

    core_cards = [
        card for card in mapping.get("functionCards", [])
        if any(card.get(field) for field in ("forms", "pages", "actionFlows", "workflows", "menus"))
    ]
    evidence_ok = all(card.get("evidence") for card in core_cards)
    if not evidence_ok:
        errors.append("one or more core function cards lack explicit evidence objects")
    checks["everyCoreFunctionHasEvidence"] = evidence_ok

    summary = mapping.get("summary", {})
    conservation_ok = summary.get("trackedObjectCount") == len(objects) and summary.get("mappedObjectCount", 0) + summary.get("unmappedObjectCount", 0) == len(objects)
    if not conservation_ok:
        errors.append("tracked = mapped + unmapped object conservation failed")
    checks["objectConservation"] = conservation_ok

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
        "coverage": {
            "expectedObjects": len(objects),
            "assignedObjects": len(assignments),
            "mappedObjects": sum(item.get("assignmentMethod") != "UNMAPPED" for item in assignments),
            "unmappedObjects": len(unmapped_keys),
            "byType": expected_counts,
        },
        "countConsistency": {
            "dependencies": {"expected": expected_dependencies, "actual": actual_dependencies},
            "importRequirements": {"expected": expected_imports, "actual": actual_imports},
        },
        "unmappedObjects": {
            "count": len(unmapped_keys),
            "byType": dict(sorted(Counter(expected_by_key[key]["objectType"] for key in unmapped_keys if key in expected_by_key).items())),
        },
        "evidenceBoundary": {
            "runtimeVerified": False,
            "parseErrorCount": expected_parse_errors,
            "businessUnresolvedCount": summary.get("businessUnresolvedCount", 0),
            "statement": "保存态配置和业务推断不等于目标环境运行成功。",
        },
        "aiPromptConsistency": {
            "status": "DEFERRED_TO_PROMPT_COMPILER",
            "requiredSummary": {
                "businessDomainCount": summary.get("businessDomainCount"),
                "functionCardCount": summary.get("functionCardCount"),
                "trackedObjectCount": summary.get("trackedObjectCount"),
                "dependencyCounts": summary.get("dependencyCounts"),
            },
            "rule": "两套提示词编译器必须复制并校验以上摘要；未提供提示词产物时不伪造已校验结论。",
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Validate business-readable eBuilder application reports.")
    parser.add_argument("application_ir")
    parser.add_argument("business_function_map")
    parser.add_argument("--report", required=True)
    parser.add_argument("--overview")
    parser.add_argument("--object-index")
    parser.add_argument("--risk-report")
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    parser.add_argument("--import-requirements")
    args = parser.parse_args()
    ir = load_json(args.application_ir)
    mapping_path = Path(args.business_function_map)
    mapping = load_json(mapping_path)
    inferred = infer_reports(mapping_path, mapping)
    overview_path = Path(args.overview) if args.overview else inferred["overview"]
    index_path = Path(args.object_index) if args.object_index else inferred["index"]
    risk_path = Path(args.risk_report) if args.risk_report else inferred["risks"]
    required_paths = [overview_path, index_path, risk_path]
    missing_files = [str(path) for path in required_paths if not path.is_file() or path.stat().st_size == 0]
    overview_text = overview_path.read_text(encoding="utf-8") if overview_path.is_file() else None
    index_text = index_path.read_text(encoding="utf-8") if index_path.is_file() else None
    import_requirements = load_json(args.import_requirements) if args.import_requirements else None
    result = validate(ir, mapping, overview_text, index_text, import_requirements, Path(args.schema))
    if missing_files:
        result["errors"].append(f"required report files missing or empty: {missing_files}")
        result["valid"] = False
    result["checks"]["requiredFilesPresent"] = not missing_files
    result["sources"] = {
        "applicationIR": str(Path(args.application_ir).resolve()),
        "businessFunctionMap": str(mapping_path.resolve()),
        "overviewReport": str(overview_path.resolve()),
        "objectIndex": str(index_path.resolve()),
        "dependencyRiskReport": str(risk_path.resolve()),
        "schema": str(Path(args.schema).resolve()),
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "valid": result["valid"],
        "errors": len(result["errors"]),
        "warnings": len(result["warnings"]),
        "report": str(report_path.resolve()),
        "coverage": result["coverage"],
    }, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
