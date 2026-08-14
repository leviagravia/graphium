#!/usr/bin/env python3
"""Current fail-closed non-desktop verifier for Graphium G03."""
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
EXPECTED_TESTS = 129
EXPECTED_W116 = {
    "calamus_document_save.py": "921378e5e89ae49c3226534d6bcd8b46a4eee2895b49d1944f120e34884f911f",
    "calamus_guarded_file_writer.py": "7cbc782325447a946f4a0f231b0861a77f1eb99b29b92c5f69626a1355d68564",
    "calamus_document_session_controller.py": "72b443c1802e20191522847c69d70596ddbea6134c7ed9128bd0e93c8e3f0e18",
    "calamus_document_session.py": "c2bd6e591dc02b3ce6ccb8b60a30bb178d19683ec4697c92e0bb337bb4d5af79",
    "calamus_document_serializer.py": "814a65449240f10627c0685ab28b269bb5c6bb1a17ee199a70b723560945a943",
    "calamus_document_identity.py": "f53291c156ed39dca0acec2dd8d7f29491b1dfde8971dbeed76a1a7972c7613a",
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
        "G03", "Guarded Save / Save As", "0.0.4-g03"
    ):
        fail(f"unexpected product identity: {(WORK_ITEM, WORK_ITEM_DESCRIPTION, VERSION)}")
    print("G03_RUNTIME_IDENTITY=PASS")


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


def verify_g03_writer_scope() -> None:
    writer_rel = "graphium/infrastructure/guarded_file_writer.py"
    writer = ROOT / writer_rel
    if not writer.is_file():
        fail("G03 GuardedFileWriter authority missing")
    writer_text = writer.read_text(encoding="utf-8")
    for marker in ("class GuardedFileWriter", "os.replace(", "os.link(", "os.fsync("):
        if marker not in writer_text:
            fail(f"writer marker missing: {marker}")

    namespace_markers = (
        "os.replace(", "os.link(", "os.write(", "os.fsync(",
        ".write_bytes(", "Path.write_bytes(",
    )
    offenders: list[tuple[str, str]] = []
    for path in sorted(PACKAGE.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if rel == writer_rel:
            continue
        text = path.read_text(encoding="utf-8")
        for marker in namespace_markers:
            if marker in text:
                offenders.append((rel, marker))
    if offenders:
        fail(f"duplicate physical writer markers: {offenders}")

    runtime_text = "\n".join(p.read_text(encoding="utf-8") for p in sorted(PACKAGE.rglob("*.py")))
    for forbidden in (
        "GtkFileChooser", "Gtk.FileChooser", "Gio.FileMonitor", "FileMonitor(",
        "DirectWriteFallback", "setDirectWriteFallback", "AtomicDocumentWriter",
    ):
        if forbidden in runtime_text:
            fail(f"G03 future/fallback authority detected: {forbidden}")

    writer_classes = []
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.endswith("Writer"):
                writer_classes.append((path.relative_to(ROOT).as_posix(), node.name))
    if writer_classes != [(writer_rel, "GuardedFileWriter")]:
        fail(f"unexpected Writer authorities: {writer_classes}")

    for rel in (
        "graphium/domain/document_save.py",
        "graphium/application/document_save_service.py",
        writer_rel,
    ):
        for imported in imports_in(ROOT / rel):
            if imported == "gi" or imported.startswith("gi."):
                fail(f"G03 GTK import in {rel}: {imported}")
    print("SINGLE_PHYSICAL_WRITER=PASS count=1")
    print("G03_ANTI_SCOPE=PASS")


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
    path = ROOT / "evidence/G03_W116_PROVENANCE.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("work_item") != "G03":
        fail("G03 provenance identity missing")
    actual = {entry["file"]: entry["sha256"] for entry in data.get("direct_sources", [])}
    if actual != EXPECTED_W116:
        fail(f"W116 provenance mismatch: {actual}")
    if data.get("runtime_imports_from_calamus_allowed") is not False:
        fail("Calamus runtime-import prohibition missing")
    for rel in (
        "evidence/G03_SOURCE_AUDIT.txt",
        "evidence/G03_MATURE_SOURCE_AUDIT.txt",
        "evidence/G03_DEAD_CODE_AUDIT.txt",
        "evidence/G03_SCOPE_AND_BUILD_RECEIPT.txt",
    ):
        if not (ROOT / rel).is_file():
            fail(f"G03 evidence missing: {rel}")
    print(f"W116_PROVENANCE=PASS files={len(actual)}")
    print("MATURE_SOURCE_AUDIT=PASS")
    print("DEAD_CODE_AUDIT=PASS")


def verify_contract_markers() -> None:
    architecture = (CANON / "GRAPHIUM_PRODUCT_ARCHITECTURE_CONTRACT.md").read_text(encoding="utf-8")
    roadmap = (CANON / "GRAPHIUM_ROADMAP.md").read_text(encoding="utf-8")
    mo = (CANON / "GRAPHIUM_MEMORIA_OPERATIVA.txt").read_text(encoding="utf-8")
    markers = (
        "G03_CONTRACT=FROZEN",
        "G03_SCOPE=GUARDED_SAVE_SAVE_AS",
        "G03_GTK_REQUIRED=NO",
        "G03_SINGLE_PHYSICAL_WRITER=GuardedFileWriter",
        "G03_DIRECT_WRITE_FALLBACK=FORBIDDEN",
        "G03_HARDLINK_POLICY=FAIL_CLOSED",
        "G03_SAVE_AS_REBIND_BEFORE_COMMIT=FORBIDDEN",
        "G03_TARGET_USERS=Leafpad,L3afpad,Mousepad_quick_edit",
    )
    for marker in markers:
        if marker not in architecture:
            fail(f"architecture marker missing: {marker}")
    if "b91af48a5688772ceffc7eac202c68e1815d7a36" not in roadmap:
        fail("published G02 commit missing from roadmap")
    if "ENTRY G02-005" not in mo or "ENTRY G03-001" not in mo or "ENTRY G03-004" not in mo:
        fail("G02 publication/G03 MO entries missing")
    if "FAST + SIMPLE + SAFE + NATIVE GTK" not in architecture:
        fail("target positioning missing")
    if "Ctrl+Alt+L" not in mo or "GUI / HELP / SHORTCUT / DEAD-CODE MEMORANDUM" not in mo:
        fail("standing GUI/Help/shortcut/dead-code memorandum missing")
    print("G03_CONTRACT_MARKERS=PASS")
    print("G03_TARGET_USER_MARKERS=PASS")


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
    verify_g03_writer_scope()
    verify_text_integrity()
    verify_provenance()
    verify_contract_markers()
    run_tests()
    print("STRICT_GATES=PASS")
    print("GTK_DESKTOP_VALIDATION=N/A")
    print("FINAL_PHASE=G03_HEADLESS_VERIFIED")


if __name__ == "__main__":
    main()
