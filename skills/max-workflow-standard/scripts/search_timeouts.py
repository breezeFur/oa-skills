"""Query retained MAX timeout snapshots without contacting OA."""
import argparse
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "references" / "data"


def search(name, kind="all", node=None, version=None, contains=False):
    results = []
    for current_kind, filename in [("node", "timeout-nodes.json"), ("workflow", "timeout-workflows.json")]:
        if kind not in ("all", current_kind):
            continue
        rows = json.loads((DATA / filename).read_text(encoding="utf-8"))["rows"]
        for line, values in enumerate(rows[4:], 5):
            if not values or not values[0].strip():
                continue
            actual_name = values[0].strip()
            if not ((name in actual_name) if contains else (name == actual_name)):
                continue
            if version is not None and values[1].strip() != version:
                continue
            if node is not None and (current_kind != "node" or values[5].strip() != node):
                continue
            result = {
                "kind": current_kind, "workflow_name": values[0], "version": values[1],
                "legacy_workflow_id": values[2], "group_name": values[3],
                "legacy_group_id": values[4], "value_raw": values[8] if current_kind == "node" else values[5],
                "unit": "unknown" if current_kind == "node" else "hours",
                "snapshot_date": "2025-09-28", "source_file": filename, "source_row": line,
            }
            if current_kind == "node":
                result.update(node_name=values[5], legacy_node_id=values[6], stage=values[7])
            results.append(result)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Exact workflow name by default")
    parser.add_argument("--kind", choices=["all", "node", "workflow"], default="all")
    parser.add_argument("--node", help="Exact node name; excludes workflow-level records")
    parser.add_argument("--version", help="Exact legacy workflow version")
    parser.add_argument("--contains", action="store_true", help="Discovery only: substring workflow name")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    if not args.name.strip():
        parser.error("--name must contain a non-whitespace name")
    if args.limit < 1:
        parser.error("--limit must be positive")
    if args.kind == "workflow" and args.node:
        parser.error("--node requires --kind node or all")
    results = search(args.name.strip(), args.kind, args.node, args.version, args.contains)
    output = {
        "match_mode": "candidate_only" if args.contains else "exact_name",
        "total_matches": len(results), "returned": min(len(results), args.limit),
        "truncated": len(results) > args.limit, "results": results[:args.limit],
        "notice": "Historical snapshot only; validate current workflow identity, version and units before configuration.",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
