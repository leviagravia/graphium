#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "graphium"
CANON = ROOT / "docs" / "canonical"
EXPECTED_CANON = {
    "GRAPHIUM_PRODUCT_ARCHITECTURE_CONTRACT.md",
    "GRAPHIUM_ROADMAP.md",
    "GRAPHIUM_MEMORIA_OPERATIVA.txt",
}
G01_MODULES = (
    ROOT / "graphium/domain/document_identity.py",
    ROOT / "graphium/domain/document_serialization.py",
    ROOT / "graphium/infrastructure/document_loader.py",
)
EXPECTED_W116_SOURCE_HASHES = {
    "calamus/calamus_document_identity.py": "f53291c156ed39dca0acec2dd8d7f29491b1dfde8971dbeed76a1a7972c7613a",
    "calamus/calamus_document_loader.py": "980578975cf83ae1acd967045370da521694b163f5d50bfe815fc6508edd06b5",
    "calamus/calamus_document_serializer.py": "814a65449240f10627c0685ab28b269bb5c6bb1a17ee199a70b723560945a943",
}


def fail(message: str) -> None:
    print(f"VERIFY_G01=FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


actual = {p.name for p in CANON.iterdir() if p.is_file()}
if actual != EXPECTED_CANON or len(actual) != 3:
    fail(f"canonical document set mismatch: {sorted(actual)}")
print("CANONICAL_DOCUMENT_CAP=PASS count=3")

from graphium.product import VERSION, WORK_ITEM, WORK_ITEM_DESCRIPTION  # noqa: E402
if WORK_ITEM != "G01" or not VERSION.endswith("-g01"):
    fail(f"runtime identity mismatch: {WORK_ITEM=} {VERSION=}")
if WORK_ITEM_DESCRIPTION != "Document Identity / Load / Serialize Foundation":
    fail("work-item description mismatch")
print("G01_RUNTIME_IDENTITY=PASS")

for path in sorted(PACKAGE.rglob("*.py")) + sorted((ROOT / "tests").glob("test_*.py")):
    try:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    except (SyntaxError, UnicodeError) as exc:
        fail(str(exc))
print("PY_COMPILE=PASS")

# Independent static import gates.
calamus_offenders = []
gtk_offenders = []
for path in sorted(PACKAGE.rglob("*.py")):
    rel = path.relative_to(ROOT).as_posix()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        imported = []
        if isinstance(node, ast.Import):
            imported = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported = [node.module]
        for name in imported:
            if name == "calamus" or name.startswith("calamus.") or name.startswith("calamus_"):
                calamus_offenders.append((rel, name))
            if name == "gi" or name.startswith("gi."):
                if not rel.startswith("graphium/adapters/gtk/"):
                    gtk_offenders.append((rel, name))
if calamus_offenders:
    fail(f"Calamus runtime imports: {calamus_offenders}")
if gtk_offenders:
    fail(f"GTK imports outside adapter boundary: {gtk_offenders}")
print("NO_CALAMUS_RUNTIME_IMPORTS=PASS")
print("GTK_BOUNDARY=PASS")

for path in G01_MODULES:
    if not path.is_file():
        fail(f"missing G01 module: {path.relative_to(ROOT)}")
    source = path.read_text(encoding="utf-8")
    for forbidden in ("DocumentSession", "GuardedFileWriter", "Gio.FileMonitor"):
        if forbidden in source:
            fail(f"future authority leaked into {path.name}: {forbidden}")
    if ".md" in source:
        fail(f"Markdown extension policy leaked into G01 runtime: {path.name}")
print("G01_ANTI_SCOPE=PASS")

# Domain modules may not perform filesystem I/O.
for rel in ("graphium/domain/document_identity.py", "graphium/domain/document_serialization.py"):
    path = ROOT / rel
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    if any(name in {"os", "pathlib", "stat"} for name in imports):
        fail(f"filesystem dependency in domain module: {rel}")
print("G01_DOMAIN_PURITY=PASS")

provenance_path = ROOT / "evidence/G01_W116_PROVENANCE.json"
provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
if provenance.get("canonical") is not False:
    fail("G01 provenance incorrectly marked canonical")
if provenance.get("source_commit") != "33331672f5ba8fcc6a7e1ede9ab849638579f0c7":
    fail("wrong W116 provenance commit")
if provenance.get("source_tree") != "db11fee424273c0a383145c132b645c15581b30a":
    fail("wrong W116 provenance tree")
seen = {item["source_path"]: item["source_sha256"] for item in provenance.get("extractions", [])}
if seen != EXPECTED_W116_SOURCE_HASHES:
    fail(f"W116 source hash map mismatch: {seen}")
print("W116_PROVENANCE=PASS files=3")

architecture = (CANON / "GRAPHIUM_PRODUCT_ARCHITECTURE_CONTRACT.md").read_text(encoding="utf-8")
for marker in (
    "G01_CONTRACT=FROZEN",
    "no BOM means strict UTF-8",
    "extension-neutral",
    "LF-normalized",
    "G02",
    "G03",
    "PERFORMANCE_PERCEIVED_LATENCY_BUDGET=FROZEN",
    "PERMANENT_COMPARATORS=Leafpad,L3afpad,Mousepad",
):
    if marker not in architecture:
        fail(f"missing G01 architecture marker: {marker}")
print("G01_CONTRACT_MARKERS=PASS")

roadmap = (CANON / "GRAPHIUM_ROADMAP.md").read_text(encoding="utf-8")
for marker in (
    "First Performance Baseline",
    "Leafpad / L3afpad / Mousepad",
    "G12 — V1 Product Closure / Competitive Qualification",
    "HEADLESS VALIDATED — FINALIZATION READY",
):
    if marker not in roadmap:
        fail(f"missing performance roadmap marker: {marker}")
mo = (CANON / "GRAPHIUM_MEMORIA_OPERATIVA.txt").read_text(encoding="utf-8")
for marker in (
    "ENTRY G01-003",
    "ENTRY G01-005",
    "ENTRY G01-006",
    "ENTRY G01-007",
    "Performance & Perceived Latency Budget",
):
    if marker not in mo:
        fail(f"missing MO research/performance marker: {marker}")
print("G01_PERFORMANCE_AUTHORITY_MARKERS=PASS")

proc = subprocess.run(
    [sys.executable, str(ROOT / "bin/graphium-selftest")],
    cwd=ROOT,
    env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"},
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
print(proc.stdout, end="")
if proc.returncode != 0:
    fail(f"selftest rc={proc.returncode}")
if "Ran 44 tests" not in proc.stdout or "OK" not in proc.stdout:
    fail("unexpected G01 selftest receipt")
print("G01_SELFTEST=PASS tests=44")
print("G01_HEADLESS_VERIFY=PASS")
print("FINAL_PHASE=G01_HEADLESS_VERIFIED")
