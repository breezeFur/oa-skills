#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

from ir_common import dump_json, load_json
from service_analysis import analyze_services, load_knowledge


def from_ir(ir):
    analysis = analyze_services(ir)
    fragments = {x["service"]: x for x in analysis["serviceFragments"]}
    modules = []
    for item in analysis["serviceInventory"]:
        fragment = fragments[item["service"]]
        modules.append({
            **item,
            "knownAdapter": item["dedicatedParser"],
            "tables": {x["table"]: x["recordCount"] for x in fragment["tables"]},
            "featureGroupCount": len(fragment.get("featureGroupRefs", [])),
            "relationshipCount": len(fragment.get("relationships", [])),
            "externalReferenceCount": len(fragment.get("externalReferences", [])),
            "archives": ir.get("modules", {}).get(item["service"], {}).get("archives", []),
        })
    return modules


def from_zip(path):
    catalog = load_knowledge()["catalog"]
    counts = Counter()
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            lowered = name.lower()
            observed = set(re.findall(r"weaver-[a-z0-9-]+-service", lowered))
            observed.update(service for service in catalog if service in lowered)
            for service in observed:
                counts[service] += 1
    return [{
        "service": service,
        "capability": catalog.get(service, {}).get("capability", "unclassified-package-service"),
        "analysisLevel": catalog.get(service, {}).get("analysisLevel", "EVIDENCE_ONLY"),
        "knownInConfiguration": service in catalog,
        "dedicatedParser": bool(catalog.get(service, {}).get("dedicatedParser")),
        "knownAdapter": bool(catalog.get(service, {}).get("dedicatedParser")),
        "archiveEntryEvidenceCount": count,
    } for service, count in sorted(counts.items())]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--output")
    args = parser.parse_args()
    path = Path(args.input)
    if path.suffix.lower() == ".zip":
        modules = from_zip(path)
        source_type = "zip-name-scan"
    else:
        modules = from_ir(load_json(path))
        source_type = "canonical-ir"
    result = {
        "source": str(path.resolve()),
        "sourceType": source_type,
        "moduleCount": len(modules),
        "modules": modules,
        "structuralModules": [x["service"] for x in modules if x.get("analysisLevel") == "STRUCTURAL"],
        "evidenceOnlyModules": [x["service"] for x in modules if x.get("analysisLevel") == "EVIDENCE_ONLY"],
        "dedicatedSemanticModules": [x["service"] for x in modules if x.get("dedicatedParser")],
        "semanticOwnerServices": sorted({
            owner
            for item in modules
            for owner in item.get("semanticOwnerServices", [item["service"]])
        }),
    }
    if args.output:
        dump_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
