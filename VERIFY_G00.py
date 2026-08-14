#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import py_compile
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
CANON = ROOT / "docs" / "canonical"
EXPECTED_CANON = {
    "GRAPHIUM_PRODUCT_ARCHITECTURE_CONTRACT.md",
    "GRAPHIUM_ROADMAP.md",
    "GRAPHIUM_MEMORIA_OPERATIVA.txt",
}


def fail(msg: str) -> None:
    print(f"VERIFY_G00=FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)

# Verify the packaged payload manifest before running semantic gates.
manifest = ROOT / "evidence" / "SHA256SUMS.txt"
if not manifest.is_file():
    fail("missing evidence/SHA256SUMS.txt")
manifest_count = 0
for raw in manifest.read_text(encoding="utf-8").splitlines():
    if not raw.strip():
        continue
    try:
        expected, rel = raw.split("  ", 1)
    except ValueError:
        fail(f"invalid manifest row: {raw!r}")
    target = ROOT / rel
    if not target.is_file():
        fail(f"manifest target missing: {rel}")
    actual_hash = hashlib.sha256(target.read_bytes()).hexdigest()
    if actual_hash != expected:
        fail(f"manifest hash mismatch: {rel}")
    manifest_count += 1
print(f"PAYLOAD_MANIFEST=PASS files={manifest_count}")

actual = {p.name for p in CANON.iterdir() if p.is_file()}
if actual != EXPECTED_CANON or len(actual) > 3:
    fail(f"canonical document set mismatch: {sorted(actual)}")
print("CANONICAL_DOCUMENT_CAP=PASS count=3")

for path in sorted((ROOT / "graphium").rglob("*.py")) + sorted((ROOT / "tests").glob("test_*.py")):
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError as exc:
        fail(str(exc))
print("PY_COMPILE=PASS")

proc = subprocess.run(
    [sys.executable, str(ROOT / "bin" / "graphium-g00-selftest")],
    cwd=ROOT,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
print(proc.stdout, end="")
if proc.returncode != 0:
    fail(f"selftest rc={proc.returncode}")
if "Ran 16 tests" not in proc.stdout or "OK" not in proc.stdout:
    fail("unexpected selftest receipt")
print("G00_SELFTEST=PASS tests=16")

provenance = json.loads((ROOT / "evidence" / "W116_PROVENANCE_G00.json").read_text(encoding="utf-8"))
if provenance.get("canonical") is not False:
    fail("provenance evidence incorrectly marked canonical")
if provenance.get("source_commit") != "33331672f5ba8fcc6a7e1ede9ab849638579f0c7":
    fail("wrong W116 source commit")
print("W116_PROVENANCE=PASS")

# Enforce the runtime no-Calamus-import rule independently of unittest.
offenders=[]
for path in sorted((ROOT / "graphium").rglob("*.py")):
    tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
    for node in ast.walk(tree):
        names=[]
        if isinstance(node,ast.Import): names=[a.name for a in node.names]
        elif isinstance(node,ast.ImportFrom) and node.module: names=[node.module]
        for name in names:
            if name == 'calamus' or name.startswith('calamus.') or name.startswith('calamus_'):
                offenders.append((path.relative_to(ROOT).as_posix(),name))
if offenders:
    fail(f"Calamus runtime imports: {offenders}")
print("NO_CALAMUS_RUNTIME_IMPORTS=PASS")

print("G00_BOOTSTRAP_VERIFY=PASS")
print("FINAL_PHASE=G00_HEADLESS_VERIFIED")
