#!/usr/bin/env python3
"""Current fail-closed non-desktop verifier for Graphium G02."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import py_compile
import sys
import unittest

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "graphium"
CANON = ROOT / "docs" / "canonical"
EXPECTED_CANONICAL = {
    "GRAPHIUM_PRODUCT_ARCHITECTURE_CONTRACT.md",
    "GRAPHIUM_ROADMAP.md",
    "GRAPHIUM_MEMORIA_OPERATIVA.txt",
}
EXPECTED_TESTS = 81
EXPECTED_W116 = {
    "calamus_history.py": "eec76da61c78a141f743432f4505d0d6570a90f9960d1ff3a18291b3349cf7d4",
    "calamus_editor_transaction.py": "fab2e80320b2ce3ab1ab1e9f5b6a0ba950a899214cee5dd86f3d27f9f9dce911",
    "calamus_document_session.py": "c2bd6e591dc02b3ce6ccb8b60a30bb178d19683ec4697c92e0bb337bb4d5af79",
    "calamus_document_session_controller.py": "72b443c1802e20191522847c69d70596ddbea6134c7ed9128bd0e93c8e3f0e18",
    "calamus_history_runtime.py": "849a61e17d9cc1ba0df8dea33ed2010fc9e14deaaf95537474c0e914701074ff",
    "calamus_editor_buffer_adapter.py": "12a828525f988fac25d5cd3e40e4741555e5a2435a7a3787ea281ab7df3c95c6",
}


def fail(message: str) -> None:
    raise SystemExit(f"VERIFY_FAIL: {message}")


def imports_in(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append(node.module)
    return found


def verify_canonical_cap() -> None:
    actual = {p.name for p in CANON.iterdir() if p.is_file()}
    if actual != EXPECTED_CANONICAL:
        fail(f"canonical docs mismatch: {sorted(actual)}")
    print("CANONICAL_DOCUMENT_CAP=PASS count=3")


def verify_runtime_identity() -> None:
    sys.path.insert(0, str(ROOT))
    from graphium.product import VERSION, WORK_ITEM, WORK_ITEM_DESCRIPTION
    if (WORK_ITEM, WORK_ITEM_DESCRIPTION, VERSION) != (
        "G02", "History / Editor Transaction / Savepoint Session", "0.0.3-g02"
    ):
        fail(f"unexpected product identity: {(WORK_ITEM, WORK_ITEM_DESCRIPTION, VERSION)}")
    print("G02_RUNTIME_IDENTITY=PASS")


def verify_compile() -> None:
    files = sorted(PACKAGE.rglob("*.py")) + sorted((ROOT / "tests").glob("*.py")) + [Path(__file__)]
    for path in files:
        py_compile.compile(str(path), doraise=True)
    compile((ROOT / "bin" / "graphium-selftest").read_text(encoding="utf-8"), "bin/graphium-selftest", "exec")
    print(f"PY_COMPILE=PASS files={len(files)+1}")


def verify_boundaries() -> None:
    calamus_offenders = []
    gtk_offenders = []
    for path in sorted(PACKAGE.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        for imported in imports_in(path):
            if imported == "calamus" or imported.startswith("calamus.") or imported.startswith("calamus_"):
                calamus_offenders.append((rel, imported))
            if imported == "gi" or imported.startswith("gi."):
                if not rel.startswith("graphium/adapters/gtk/"):
                    gtk_offenders.append((rel, imported))
    if calamus_offenders:
        fail(f"Calamus runtime imports: {calamus_offenders}")
    if gtk_offenders:
        fail(f"GTK outside adapter boundary: {gtk_offenders}")
    print("NO_CALAMUS_RUNTIME_IMPORTS=PASS")
    print("GTK_BOUNDARY=PASS")

    domain_forbidden = ("graphium.application", "graphium.adapters", "graphium.infrastructure", "graphium.composition")
    for path in sorted((PACKAGE / "domain").rglob("*.py")):
        for imported in imports_in(path):
            if imported.startswith(domain_forbidden):
                fail(f"domain outer-layer import: {path.name}: {imported}")
    for path in sorted((PACKAGE / "application").rglob("*.py")):
        for imported in imports_in(path):
            if imported.startswith("graphium.adapters"):
                fail(f"application adapter import: {path.name}: {imported}")
    print("LAYER_BOUNDARIES=PASS")


def verify_g02_anti_scope() -> None:
    g02 = [
        ROOT / "graphium/domain/history.py",
        ROOT / "graphium/application/document_session.py",
        ROOT / "graphium/application/editor_transaction.py",
    ]
    forbidden_roots = {"gi", "os", "pathlib", "tempfile", "shutil", "subprocess"}
    for path in g02:
        roots = {name.split(".", 1)[0] for name in imports_in(path)}
        if roots & forbidden_roots:
            fail(f"G02 IO/GTK import in {path.name}: {sorted(roots & forbidden_roots)}")
    runtime_text = "\n".join(p.read_text(encoding="utf-8") for p in sorted(PACKAGE.rglob("*.py")))
    for marker in (
        "GuardedFileWriter", "os.replace(", ".write_bytes(", ".write_text(",
        "Gtk.PrintOperation", "Gio.FileMonitor",
    ):
        if marker in runtime_text:
            fail(f"future writer/desktop authority detected: {marker}")
    for stale in ("VERIFY_G00.py", "VERIFY_G01.py", "bin/graphium-g00-selftest"):
        if (ROOT / stale).exists():
            fail(f"obsolete current verifier remains: {stale}")
    if not (ROOT / "VERIFY_GRAPHIUM.py").is_file():
        fail("current verifier missing")
    print("G02_ANTI_SCOPE=PASS")
    print("DEAD_CODE_CURRENT_VERIFIER_CLEANUP=PASS")


def verify_text_integrity() -> None:
    suffixes = {".py", ".md", ".txt", ".json", ".tsv"}
    offenders: list[str] = []
    for base in (PACKAGE, ROOT / "tests", ROOT / "docs", ROOT / "evidence"):
        for path in sorted(p for p in base.rglob("*") if p.is_file() and p.suffix in suffixes):
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for lineno, line in enumerate(lines, 1):
                if line.endswith((" ", "\t")):
                    offenders.append(f"{path.relative_to(ROOT)}:{lineno}")
    if offenders:
        fail(f"trailing whitespace: {offenders[:20]}")
    print("TEXT_INTEGRITY=PASS")


def verify_provenance() -> None:
    path = ROOT / "evidence/G02_W116_PROVENANCE.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("work_item") != "G02":
        fail("G02 provenance identity missing")
    actual = {entry["file"]: entry["sha256"] for entry in data.get("direct_sources", [])}
    if actual != EXPECTED_W116:
        fail(f"W116 provenance mismatch: {actual}")
    if data.get("runtime_imports_from_calamus_allowed") is not False:
        fail("Calamus runtime-import prohibition missing")
    if not (ROOT / "evidence/G02_MATURE_SOURCE_AUDIT.txt").is_file():
        fail("mature-source audit evidence missing")
    if not (ROOT / "evidence/G02_DEAD_CODE_AUDIT.txt").is_file():
        fail("dead-code audit evidence missing")
    print(f"W116_PROVENANCE=PASS files={len(actual)}")
    print("MATURE_SOURCE_AUDIT=PASS")


def verify_contract_markers() -> None:
    architecture = (CANON / "GRAPHIUM_PRODUCT_ARCHITECTURE_CONTRACT.md").read_text(encoding="utf-8")
    roadmap = (CANON / "GRAPHIUM_ROADMAP.md").read_text(encoding="utf-8")
    mo = (CANON / "GRAPHIUM_MEMORIA_OPERATIVA.txt").read_text(encoding="utf-8")
    markers = (
        "G02_CONTRACT=FROZEN",
        "G02_SCOPE=HISTORY_TRANSACTION_SAVEPOINT_SESSION",
        "G02_GTK_REQUIRED=NO",
        "G02_DIRTY_AUTHORITY=EDITOR_STATE_ID_RELATION",
        "G02_PHYSICAL_WRITER=FORBIDDEN",
        "G02_TARGET_USERS=Leafpad,L3afpad,Mousepad_quick_edit",
        "never reused",
        "late save",
    )
    for marker in markers:
        if marker not in architecture:
            fail(f"architecture marker missing: {marker}")
    if "bf7878c3cdc5cf895b0ffba86b854860c34936a4" not in roadmap:
        fail("published G01 commit missing from roadmap")
    if "ENTRY G02-001" not in mo or "ENTRY G02-003" not in mo:
        fail("G02 MO entries missing")
    if "FAST + SIMPLE + SAFE + NATIVE GTK" not in architecture:
        fail("target positioning missing")
    print("G02_CONTRACT_MARKERS=PASS")
    print("G02_TARGET_USER_MARKERS=PASS")


def run_tests() -> None:
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    count = suite.countTestCases()
    if count != EXPECTED_TESTS:
        fail(f"unexpected test count: {count}, expected {EXPECTED_TESTS}")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        fail("unittest suite failed")
    print(f"GRAPHIUM_SELFTEST=PASS tests={count}")


def main() -> None:
    verify_canonical_cap()
    verify_runtime_identity()
    verify_compile()
    verify_boundaries()
    verify_g02_anti_scope()
    verify_text_integrity()
    verify_provenance()
    verify_contract_markers()
    run_tests()
    print("STRICT_GATES=PASS")
    print("GTK_DESKTOP_VALIDATION=N/A")
    print("FINAL_PHASE=G02_HEADLESS_VERIFIED")


if __name__ == "__main__":
    main()
