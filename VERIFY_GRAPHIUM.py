#!/usr/bin/env python3
"""Fail-closed non-desktop verifier for rebuilt Graphium G04."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import py_compile
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "graphium"
TESTS = ROOT / "tests"
TOOLS = ROOT / "tools"
CANON = ROOT / "docs" / "canonical"
EXPECTED_CANONICAL = {
    "GRAPHIUM_PRODUCT_ARCHITECTURE_CONTRACT.md",
    "GRAPHIUM_ROADMAP.md",
    "GRAPHIUM_MEMORIA_OPERATIVA.txt",
}
EXPECTED_TESTS = 196
EXPECTED_W116 = {
    "calamus_command_catalog.py": "687332708c5323f0639bdfc8e74f5638ed412534677e96e788fa5efcd2e647c3",
    "calamus_dialogs.py": "68a6fcc44d02c8534841ebe24bd53f69134f9b626529759bc648835e1aba4de2",
    "calamus_document_session_controller.py": "72b443c1802e20191522847c69d70596ddbea6134c7ed9128bd0e93c8e3f0e18",
    "calamus_editor.py": "8d84e828e17a965ea994d0bd6f25276ea23a4aa203c5d8a111dca119f2cff378",
    "calamus_editor_buffer_adapter.py": "12a828525f988fac25d5cd3e40e4741555e5a2435a7a3787ea281ab7df3c95c6",
    "calamus_editor_composition.py": "da573e76b67d706f3a54d9495f41b968a4706b1ce5aa8f58a3a5d1f8213f9222",
    "calamus_file_lifecycle.py": "9d1e5c014a1093278fb5ede057d664bafb73831118f32fd9f1c2689c582d6d1a",
    "calamus_menu_model.py": "6ac08303ce5300cf736a2ffda00905a8c683d79a56d5eee954b37e043d3404dc",
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


def verify_identity() -> None:
    sys.path.insert(0, str(ROOT))
    from graphium.product import DESKTOP_APPLICATION_ID, VERSION, WORK_ITEM, WORK_ITEM_DESCRIPTION
    expected = (
        "G04",
        "Native Edit Hardening / Thin GTK Shell / Core File Lifecycle",
        "0.0.5-g04",
        "io.github.leviagravia.Graphium",
    )
    actual = (WORK_ITEM, WORK_ITEM_DESCRIPTION, VERSION, DESKTOP_APPLICATION_ID)
    if actual != expected:
        fail(f"unexpected G04 identity: {actual}")
    print("G04_RUNTIME_IDENTITY=PASS")
    print("G04_DESKTOP_APPLICATION_ID=PASS")


def verify_compile() -> None:
    files = sorted(PACKAGE.rglob("*.py")) + sorted(TESTS.glob("*.py")) + sorted(TOOLS.glob("*.py")) + [Path(__file__)]
    for path in files:
        py_compile.compile(str(path), doraise=True)
    for rel in ("bin/graphium", "bin/graphium-selftest"):
        compile((ROOT / rel).read_text(encoding="utf-8"), rel, "exec")
    print(f"PY_COMPILE=PASS files={len(files)+2}")


def verify_boundaries() -> None:
    calamus = []
    gtk = []
    for path in sorted(PACKAGE.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        for imported in imports_in(path):
            if imported == "calamus" or imported.startswith("calamus.") or imported.startswith("calamus_"):
                calamus.append((rel, imported))
            if imported == "gi" or imported.startswith("gi."):
                if not rel.startswith("graphium/adapters/gtk/"):
                    gtk.append((rel, imported))
    if calamus:
        fail(f"Calamus runtime imports: {calamus}")
    if gtk:
        fail(f"GTK outside adapter boundary: {gtk}")
    print("NO_CALAMUS_RUNTIME_IMPORTS=PASS")
    print("GTK_BOUNDARY=PASS")

    outer = ("graphium.application", "graphium.adapters", "graphium.infrastructure", "graphium.composition")
    for path in sorted((PACKAGE / "domain").rglob("*.py")):
        for imported in imports_in(path):
            if imported.startswith(outer):
                fail(f"domain outer-layer import: {path.name}: {imported}")
    for path in sorted((PACKAGE / "application").rglob("*.py")):
        for imported in imports_in(path):
            if imported.startswith("graphium.adapters"):
                fail(f"application adapter import: {path.name}: {imported}")
    print("LAYER_BOUNDARIES=PASS")


def verify_single_writer() -> None:
    writer_rel = "graphium/infrastructure/guarded_file_writer.py"
    writer = ROOT / writer_rel
    if not writer.is_file() or "class GuardedFileWriter" not in writer.read_text(encoding="utf-8"):
        fail("sole GuardedFileWriter missing")
    writer_classes = []
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.endswith("Writer"):
                writer_classes.append((path.relative_to(ROOT).as_posix(), node.name))
    if writer_classes != [(writer_rel, "GuardedFileWriter")]:
        fail(f"unexpected writer authorities: {writer_classes}")
    # High-risk namespace/document mutation primitives remain confined to the writer.
    for path in sorted(PACKAGE.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if rel == writer_rel:
            continue
        text = path.read_text(encoding="utf-8")
        for marker in ("os.replace(", "os.link(", "os.rename(", "os.fsync(", ".write_bytes("):
            if marker in text:
                fail(f"document-writer marker outside authority: {rel}: {marker}")
    print("SINGLE_PHYSICAL_WRITER=PASS count=1")


def verify_native_edit_architecture() -> None:
    composition = (ROOT / "graphium/composition.py").read_text(encoding="utf-8")
    history = (ROOT / "graphium/domain/edit_history.py").read_text(encoding="utf-8")
    native = (ROOT / "graphium/application/native_editor.py").read_text(encoding="utf-8")
    window = (ROOT / "graphium/adapters/gtk/window.py").read_text(encoding="utf-8")
    app = (ROOT / "graphium/adapters/gtk/application.py").read_text(encoding="utf-8")
    session = (ROOT / "graphium/application/document_session.py").read_text(encoding="utf-8")

    if "DeltaHistory()" not in composition or "TextHistory()" in composition:
        fail("active G04 composition is not delta-based")
    for marker in ("class DeltaHistory", "class EditDelta", "stored_payload_chars"):
        if marker not in history:
            fail(f"delta history marker missing: {marker}")
    for marker in ("prepare_for_save", "advance_editor_state", "apply_replay"):
        if marker not in native:
            fail(f"native editor marker missing: {marker}")
    if "text_editor_state_id" not in session or "text_is_current" not in session:
        fail("session live-text synchronization markers missing")
    for forbidden in ("_NATIVE_COMMIT_DELAY_MS", "timeout_add(", "timeout_add_seconds("):
        if forbidden in window:
            fail(f"time-based native edit authority detected: {forbidden}")
    for marker in ('"begin-user-action"', '"end-user-action"', '"insert-text"', '"delete-range"'):
        if marker not in window:
            fail(f"native Gtk signal marker missing: {marker}")
    if "Gio.ApplicationFlags.NON_UNIQUE" not in app or "_spawn_additional_files" not in app:
        fail("NON_UNIQUE one-file/process topology missing")
    print("G04_NATIVE_DELTA_HISTORY=PASS")
    print("G04_NO_TIMER_UNDO_AUTHORITY=PASS")
    print("G04_NON_UNIQUE_TOPOLOGY_SOURCE_GATE=PASS")


def verify_ui_scope() -> None:
    runtime = "\n".join(p.read_text(encoding="utf-8") for p in sorted(PACKAGE.rglob("*.py")))
    for forbidden in ("GtkSourceView", "Gtk.Toolbar", "Gio.FileMonitor", "Gtk.Notebook"):
        if forbidden in runtime:
            fail(f"G04 out-of-scope UI/runtime marker: {forbidden}")
    from graphium.application.commands import COMMANDS
    expected = [
        "new", "open", "save", "save-as", "quit", "undo", "redo", "cut", "copy",
        "paste", "delete", "select-all", "user-guide", "keyboard-shortcuts", "about",
    ]
    if [c.action for c in COMMANDS] != expected:
        fail(f"unexpected command surface: {[c.action for c in COMMANDS]}")
    for rel in ("docs/user/GRAPHIUM_USER_GUIDE.txt", "docs/user/GRAPHIUM_KEYBOARD_SHORTCUTS.txt"):
        if not (ROOT / rel).is_file():
            fail(f"Help product file missing: {rel}")
    print("G04_THIN_GTK_SHELL_SCOPE=PASS")
    print("HELP_INCREMENTAL=PASS")


def verify_content_neutrality() -> None:
    # Loader/serializer must remain explicit representation authorities; G04 lifecycle may
    # not smuggle cleanup transformations into Open/Save.
    lifecycle = (ROOT / "graphium/application/file_lifecycle.py").read_text(encoding="utf-8")
    for forbidden in ("rstrip(", "strip(", "trim", "trailing", "final_newline", "normalize_whitespace"):
        if forbidden in lifecycle.lower():
            fail(f"implicit content transform marker in G04 lifecycle: {forbidden}")
    print("G04_CONTENT_NEUTRALITY_SOURCE_GATE=PASS")


def verify_renderability_policy() -> None:
    renderability = (ROOT / "graphium/application/renderability.py").read_text(encoding="utf-8")
    lifecycle = (ROOT / "graphium/application/file_lifecycle.py").read_text(encoding="utf-8")
    window = (ROOT / "graphium/adapters/gtk/window.py").read_text(encoding="utf-8")
    true_gtk = (TOOLS / "g04_true_gtk_gate.py").read_text(encoding="utf-8")
    for marker in (
        "MAX_INTERACTIVE_LINE_CHARS = 20_000",
        "ensure_interactive_text_renderable",
        "ensure_insert_renderable",
        "ensure_join_renderable",
    ):
        if marker not in renderability:
            fail(f"renderability policy marker missing: {marker}")
    if lifecycle.index("ensure_interactive_text_renderable(result.text)") > lifecycle.index("self.editor.initialize_open(result)"):
        fail("renderability guard does not precede Gtk buffer installation")
    for marker in (
        '_on_insert_text_guard',
        '_on_delete_range_guard',
        'GObject.signal_stop_emission_by_name',
    ):
        if marker not in window:
            fail(f"native renderability mutation guard missing: {marker}")
    for forbidden in ("HUGE LINE TRUNCATED", "set_wrap_mode(Gtk.WrapMode.CHAR)"):
        if forbidden in renderability or forbidden in lifecycle:
            fail(f"content-mutating/pathology workaround forbidden: {forbidden}")
    for marker in (
        "one-mib-multiline.txt",
        "scroll_to_mark",
        "pathological huge-line Open",
        "pathological insertion guard",
    ):
        if marker not in true_gtk:
            fail(f"True-GTK renderability regression missing: {marker}")
    print("G04_RENDERABILITY_POLICY=PASS")
    print("G04_PATHOLOGICAL_LINE_GUARD_SOURCE=PASS")


def verify_entrypoints() -> None:
    for rel in ("bin/graphium", "tools/g04_shortcut_audit.py", "tools/g04_true_gtk_gate.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        if "Path(__file__).resolve()" not in text or "sys.path.insert(0" not in text:
            fail(f"entrypoint self-root missing: {rel}")
        if 'os.environ["PYTHONPATH"]' in text:
            fail(f"global PYTHONPATH workaround forbidden: {rel}")
    print("G04_ENTRYPOINT_CWD_INDEPENDENCE=PASS")


def verify_performance_protocol() -> None:
    exact = (TOOLS / "g04_performance.py").read_text(encoding="utf-8")
    common = (TOOLS / "g04_comparator_proxy.py").read_text(encoding="utf-8")
    topology = (TOOLS / "g04_topology_gate.py").read_text(encoding="utf-8")
    window = (ROOT / "graphium/adapters/gtk/window.py").read_text(encoding="utf-8")
    for marker in ("os.pipe()", "pass_fds=(wfd,)", "GRAPHIUM_BENCHMARK_READY_FD", "parse_ready_line"):
        if marker not in exact:
            fail(f"exact performance protocol marker missing: {marker}")
    if "READY_FILE" in exact or "ready_file" in exact:
        fail("filesystem ready marker returned")
    if "os.write(fd, payload)" not in window:
        fail("atomic child pipe READY emission missing")
    if '"cross_product_comparable": False' not in exact:
        fail("exact FIRST_EDITABLE comparison classification missing")
    if '"cross_product_comparable": True' not in common or '"metric": "FIRST_VISIBLE"' not in common:
        fail("common FIRST_VISIBLE protocol classification missing")
    for name in ("Graphium", "Leafpad", "L3afpad", "Mousepad", "FeatherPad"):
        if name not in common:
            fail(f"comparator missing from common metric: {name}")
    if "G04_ONE_PROCESS_ONE_WINDOW_ONE_DOCUMENT=PASS" not in topology:
        fail("topology desktop gate missing")
    print("G04_PERFORMANCE_PROTOCOL=PASS")
    print("G04_TOPOLOGY_GATE_SOURCE=PASS")


def verify_shortcuts() -> None:
    from graphium.application.commands import FORBIDDEN_ACCELERATORS, accelerator_map
    if "<Ctrl><Alt>L" not in FORBIDDEN_ACCELERATORS:
        fail("Ctrl+Alt+L forbidden marker missing")
    if "<Ctrl><Alt>L" in accelerator_map().values():
        fail("Ctrl+Alt+L assigned")
    print("KNOWN_SHORTCUT_COLLISION_GATE=PASS")


def verify_evidence() -> None:
    required = (
        "evidence/G04_SOURCE_AUDIT.txt",
        "evidence/G04_DEEP_MATURE_SOURCE_AUDIT.txt",
        "evidence/G04_FAILURE_AND_REDESIGN_RECEIPT.txt",
        "evidence/G04_SCOPE_AND_BUILD_RECEIPT.txt",
        "evidence/G04_DEAD_CODE_AUDIT.txt",
        "evidence/G04_W116_PROVENANCE.json",
        "evidence/G04_SEVEN_EDITOR_COMPETITIVE_SYNTHESIS.txt",
        "evidence/G04_HUGE_LINE_PRODUCT_FAIL_REAUDIT.txt",
    )
    for rel in required:
        if not (ROOT / rel).is_file():
            fail(f"G04 evidence missing: {rel}")
    audit = (ROOT / "evidence/G04_DEEP_MATURE_SOURCE_AUDIT.txt").read_text(encoding="utf-8")
    for marker in (
        "ASSUMPTION UNDER TEST",
        "CONTRADICTORY / STRESSING EVIDENCE",
        "ALTERNATIVE MATURE MODEL",
        "GRAPHIUM CONSEQUENCE",
        "DECISION",
        "Leafpad",
        "L3afpad",
        "Airpad",
        "Mousepad",
        "NEdit",
        "JOE",
        "gedit",
        "GNOME Text Editor",
    ):
        if marker not in audit:
            fail(f"deep mature audit marker missing: {marker}")
    huge_audit = (ROOT / "evidence/G04_HUGE_LINE_PRODUCT_FAIL_REAUDIT.txt").read_text(encoding="utf-8")
    for marker in (
        "VALID MANUAL PRODUCT FAIL",
        "PATHOLOGICAL HUGE-LINE",
        "FeatherPad",
        "NEdit",
        "JOE 4.8",
        "G04_INTERACTIVE_LINE_BUDGET_CHARS=20000",
        "REFUSE_BEFORE_GTK_BUFFER_INSTALL",
        "ADOPT / ADAPT / REJECT",
    ):
        if marker not in huge_audit:
            fail(f"huge-line mature audit marker missing: {marker}")
    data = json.loads((ROOT / "evidence/G04_W116_PROVENANCE.json").read_text(encoding="utf-8"))
    if data.get("calamus_commit") != "33331672f5ba8fcc6a7e1ede9ab849638579f0c7":
        fail("wrong Calamus W116 provenance commit")
    actual = {e["file"]: e["sha256"] for e in data.get("direct_sources", [])}
    if actual != EXPECTED_W116:
        fail("G04 W116 provenance source hashes mismatch")
    if data.get("runtime_imports_from_calamus_allowed") is not False:
        fail("Calamus runtime import prohibition missing")
    print(f"W116_PROVENANCE=PASS files={len(actual)}")
    print("G04_MATURE_SOURCE_AUDIT=PASS")
    print("G04_DEAD_CODE_AUDIT=PASS")


def verify_contracts() -> None:
    contract = (CANON / "GRAPHIUM_PRODUCT_ARCHITECTURE_CONTRACT.md").read_text(encoding="utf-8")
    roadmap = (CANON / "GRAPHIUM_ROADMAP.md").read_text(encoding="utf-8")
    mo = (CANON / "GRAPHIUM_MEMORIA_OPERATIVA.txt").read_text(encoding="utf-8")
    for marker in (
        "G04_CONTRACT=FROZEN",
        "G04_NATIVE_HISTORY=DELTA_BASED",
        "G04_NATIVE_EDIT_TIMER_AUTHORITY=FORBIDDEN",
        "G04_FULL_BUFFER_CAPTURE_PER_NATIVE_EDIT=FORBIDDEN",
        "G04_APPLICATION_TOPOLOGY=ONE_PROCESS_ONE_WINDOW_ONE_DOCUMENT",
        "G04_APPLICATION_UNIQUENESS=NON_UNIQUE",
        "G04_PERFORMANCE_COMMON_METRIC=FIRST_VISIBLE",
        "G04_PERFORMANCE_EXACT_INTERNAL_METRIC=FIRST_EDITABLE",
        "G04_HETEROGENEOUS_READINESS_RATIO=FORBIDDEN",
        "PERMANENT_COMPARATORS=Leafpad,L3afpad,Mousepad,FeatherPad",
        "PRODUCT_CATEGORY=LIGHTWEIGHT_TRUST_EDITOR",
        "NORMAL_SAVE_IS_CONTENT_NEUTRAL=YES",
        "G04_INTERACTIVE_LINE_BUDGET_CHARS=20000",
        "G04_PATHOLOGICAL_LINE_POLICY=REFUSE_BEFORE_GTK_BUFFER_INSTALL",
        "G04_PATHOLOGICAL_LINE_CONTENT_MUTATION=FORBIDDEN",
    ):
        if marker not in contract:
            fail(f"G04 contract marker missing: {marker}")
    if "e7045e0ce1c79da71c9968bdfa052df25a5378b7" not in roadmap:
        fail("published G03 baseline missing from roadmap")
    if "Native Edit Integration Hardening" not in roadmap:
        fail("rebuilt G04 roadmap routing missing")
    for marker in (
        "ENTRY G03-006",
        "ENTRY G04-002",
        "ENTRY G04-003",
        "CONFIRMATION-BIAS COUNTERMEASURE",
        "ENTRY G04-005",
        "ENTRY G04-006",
        "ENTRY G04-007",
        "ENTRY G04-008",
        "ENTRY G04-009",
        "ENTRY G04-010",
        "ENTRY G04-011",
        "ENTRY G04-012",
        "ENTRY G04-013",
    ):
        if marker not in mo:
            fail(f"MO marker missing: {marker}")
    print("G04_CONTRACT_MARKERS=PASS")
    print("G04_ROADMAP_REBASELINE=PASS")
    print("G04_TARGET_USER_MARKERS=PASS")


def verify_text_integrity() -> None:
    suffixes = {".py", ".md", ".txt", ".json", ".tsv"}
    offenders = []
    for base in (PACKAGE, TESTS, TOOLS, ROOT / "docs", ROOT / "evidence"):
        for path in sorted(p for p in base.rglob("*") if p.is_file() and p.suffix in suffixes):
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for lineno, line in enumerate(lines, 1):
                if line.endswith((" ", "\t")):
                    offenders.append(f"{path.relative_to(ROOT)}:{lineno}")
    if offenders:
        fail(f"trailing whitespace: {offenders[:30]}")
    print("TEXT_INTEGRITY=PASS")


def run_tests() -> None:
    suite = unittest.defaultTestLoader.discover(str(TESTS))
    count = suite.countTestCases()
    if count != EXPECTED_TESTS:
        fail(f"unexpected test count: {count}, expected {EXPECTED_TESTS}")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        fail("unittest suite failed")
    print(f"GRAPHIUM_SELFTEST=PASS tests={count}")


def main() -> None:
    verify_canonical_cap()
    verify_identity()
    verify_compile()
    verify_boundaries()
    verify_single_writer()
    verify_native_edit_architecture()
    verify_ui_scope()
    verify_content_neutrality()
    verify_renderability_policy()
    verify_entrypoints()
    verify_performance_protocol()
    verify_shortcuts()
    verify_evidence()
    verify_contracts()
    verify_text_integrity()
    run_tests()
    print("STRICT_GATES=PASS")
    print("GTK_DESKTOP_VALIDATION=PENDING")
    print("PERFORMANCE_BASELINE=PENDING_T480")
    print("FINAL_PHASE=G04_NONDESKTOP_VERIFIED")


if __name__ == "__main__":
    main()
