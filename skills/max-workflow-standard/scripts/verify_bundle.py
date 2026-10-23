"""Verify retained evidence, links and packaged file hashes. No OA access."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote
from zipfile import ZipFile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify(root=ROOT):
    errors = []
    inventory = json.loads((root / "references/source-inventory.json").read_text(encoding="utf-8"))
    source = root / "assets/source" / inventory["source_filename"]
    if digest(source.read_bytes()) != inventory["source_sha256"]:
        errors.append("DOCX hash mismatch")
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with ZipFile(source) as z:
        doc = ET.fromstring(z.read("word/document.xml"))
        counts = inventory["counts"]
        for key, nodes in [("body_paragraphs", doc.findall("w:body/w:p", ns)), ("body_tables", doc.findall("w:body/w:tbl", ns))]:
            if len(nodes) != counts[key]:
                errors.append(key + " count mismatch")
        for item in inventory["media"] + inventory["embeddings"]:
            if digest(z.read(item["part"])) != item["sha256"]:
                errors.append("Original object hash mismatch: " + item["part"])
        for item in inventory["embeddings"]:
            if (root / "assets/source" / Path(item["part"]).name).read_bytes() != z.read(item["part"]):
                errors.append("Retained OLE mismatch: " + item["part"])
        comments = ET.fromstring(z.read("word/comments.xml")).findall("w:comment", ns)
        if len(comments) != counts["comments"]:
            errors.append("Comment count mismatch")
        for figure in inventory["image_occurrences"]:
            preview = root / "assets/images" / f"image{figure['figure']}.png"
            if not preview.is_file():
                errors.append("Missing image preview: " + preview.name)
            elif figure["source_part"].endswith(".png") and preview.read_bytes() != z.read(figure["source_part"]):
                errors.append("Image occurrence mapping mismatch: " + preview.name)
    index = json.loads((root / "references/data/timeout-index.json").read_text(encoding="utf-8"))
    row_counts = {}
    for item in index:
        rows = json.loads((root / "references/data" / item["data_json"]).read_text(encoding="utf-8"))["rows"]
        row_counts[item["data_json"]] = len(rows)
        if len(rows) != item["rows_including_metadata"] or rows[:5] != item["header_preview"]:
            errors.append("Timeout snapshot row/header mismatch: " + item["data_json"])
    # Check references without requiring a network or user-specific source paths.
    for path in root.rglob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8-sig")):
            target = target.strip("<>")
            if re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", target) or target.startswith("#"):
                continue
            target = unquote(target.split("#", 1)[0])
            if target and not (path.parent / target).is_file():
                errors.append("Broken reference: " + str(path.relative_to(root)) + " -> " + target)
    manifest_path = root / "references/bundle-manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p != manifest_path}
        expected = {x["path"] for x in manifest["files"]}
        if actual != expected:
            errors.append("Manifest file list mismatch")
        for item in manifest["files"]:
            path = root / item["path"]
            if not path.is_file() or digest(path.read_bytes()) != item["sha256"]:
                errors.append("Manifest hash mismatch: " + item["path"])
    else:
        errors.append("Missing bundle manifest")
    return {"ok": not errors, "errors": errors, "source_counts": inventory["counts"], "timeout_rows": row_counts}


if __name__ == "__main__":
    result = verify()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["ok"] else 1)
