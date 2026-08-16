#!/usr/bin/env python3
"""Fail-closed non-desktop verifier for Graphium G06, preserving G00-G05 invariants."""
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
EXPECTED_TESTS = 266
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
        "G06",
        "View Menu Core / Compact Status / Lightweight Presentation",
        "0.0.7-g06",
        "io.github.leviagravia.Graphium",
    )
    actual = (WORK_ITEM, WORK_ITEM_DESCRIPTION, VERSION, DESKTOP_APPLICATION_ID)
    if actual != expected:
        fail(f"unexpected G06 identity: {actual}")
    print("G06_RUNTIME_IDENTITY=PASS")
    print("G06_DESKTOP_APPLICATION_ID=PASS")


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
    # High-risk DOCUMENT namespace mutation primitives remain confined to the writer.
    # G06 may atomically replace its own product-local XDG settings file; that store is
    # explicitly non-document authority and must not import document persistence code.
    config_store_rel = "graphium/infrastructure/view_settings_store.py"
    for path in sorted(PACKAGE.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if rel in (writer_rel, config_store_rel):
            continue
        text = path.read_text(encoding="utf-8")
        for marker in ("os.replace(", "os.link(", "os.rename(", "os.fsync(", ".write_bytes("):
            if marker in text:
                fail(f"document-writer marker outside authority: {rel}: {marker}")
    config_store = ROOT / config_store_rel
    if config_store.is_file():
        text = config_store.read_text(encoding="utf-8")
        for forbidden in ("GuardedFileWriter", "DocumentSave", "load_document", "logical_target_path"):
            if forbidden in text:
                fail(f"XDG settings store crossed into document authority: {forbidden}")
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
            fail(f"G06 out-of-scope UI/runtime marker: {forbidden}")
    from graphium.application.commands import COMMANDS
    expected = [
        "new", "open", "save", "save-as", "quit",
        "undo", "redo", "cut", "copy", "paste", "delete", "select-all",
        "find", "find-next", "find-previous", "replace", "go-to-line",
        "status-bar", "line-numbers", "word-wrap", "font",
        "zoom-in", "zoom-out", "zoom-reset", "full-screen",
        "user-guide", "keyboard-shortcuts", "about",
    ]
    if [c.action for c in COMMANDS] != expected:
        fail(f"unexpected G06 command surface: {[c.action for c in COMMANDS]}")
    by_action = {c.action: c for c in COMMANDS}
    for action in ("status-bar", "line-numbers", "word-wrap", "full-screen"):
        if not by_action[action].stateful:
            fail(f"G06 View action must be stateful: {action}")
    if any(c.action in ("toolbar", "appearance") for c in COMMANDS):
        fail("G06 prematurely added toolbar or appearance command")
    for rel in ("docs/user/GRAPHIUM_USER_GUIDE.txt", "docs/user/GRAPHIUM_KEYBOARD_SHORTCUTS.txt"):
        if not (ROOT / rel).is_file():
            fail(f"Help product file missing: {rel}")
    print("G06_COMMAND_SURFACE=PASS")
    print("G06_TOOLBAR_ABSENT=PASS")
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
    for rel in (
        "bin/graphium",
        "tools/g04_shortcut_audit.py", "tools/g04_true_gtk_gate.py",
        "tools/g05_shortcut_audit.py", "tools/g05_true_gtk_gate.py",
        "tools/g05_search_performance.py",
        "tools/g06_shortcut_audit.py", "tools/g06_true_gtk_gate.py",
        "tools/g06_view_performance.py",
        "tools/g06_startup_regression.py",
    ):
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


def verify_g05_search_architecture() -> None:
    domain = (ROOT / "graphium/domain/text_search.py").read_text(encoding="utf-8")
    search = (ROOT / "graphium/application/search.py").read_text(encoding="utf-8")
    native = (ROOT / "graphium/application/native_editor.py").read_text(encoding="utf-8")
    buffer = (ROOT / "graphium/adapters/gtk/editor_buffer.py").read_text(encoding="utf-8")
    window = (ROOT / "graphium/adapters/gtk/window.py").read_text(encoding="utf-8")
    performance = (TOOLS / "g05_search_performance.py").read_text(encoding="utf-8")
    true_gtk = (TOOLS / "g05_true_gtk_gate.py").read_text(encoding="utf-8")
    for marker in (
        "class SearchScaleError", "def find_next", "def find_previous",
        "max_matches", "_fold_line", "casefold()",
    ):
        if marker not in domain:
            fail(f"G05 search-domain marker missing: {marker}")
    if "find_all(text, query" in domain:
        fail("G05 navigation appears to route through full match materialization")
    for marker in (
        "MAX_REPLACE_ALL_MATCHES = 50_000",
        "max_matches=MAX_REPLACE_ALL_MATCHES",
        "DEFAULT_MAX_HISTORY_PAYLOAD_CHARS",
        "ensure_interactive_text_renderable(final_text)",
        "for match in reversed(matches)",
    ):
        if marker not in search:
            fail(f"G05 replacement-plan marker missing: {marker}")
    for marker in (
        "apply_prevalidated_programmatic_group",
        "stale programmatic edit plan",
        "bounded Undo payload budget",
        "_inverse_operations",
    ):
        if marker not in native:
            fail(f"G05 programmatic transaction marker missing: {marker}")
    if "def apply_operations" not in buffer or "_delete_expected" not in buffer:
        fail("G05 expected-delete/inverse buffer authority missing")
    for marker in (
        "self._search_bar: Gtk.SearchBar | None = None",
        "def _ensure_search_bar", "Gtk.SearchBar()",
        "_perform_replace_all", "choose_line_number",
    ):
        if marker not in window:
            fail(f"G05 GTK search projection marker missing: {marker}")
    for forbidden in ("threading", "Thread(", "background_search", "search_index"):
        if forbidden in domain + search + window:
            fail(f"G05 forbidden background-search marker: {forbidden}")
    for marker in (
        '"find-ci-10m"', '"replace-all-10m"', '"replace-cap-refusal"',
        "LIGHTWEIGHT_BUDGET_SEARCH_GATE=PASS",
    ):
        if marker not in performance:
            fail(f"G05 performance gate marker missing: {marker}")
    for marker in (
        "G05_TRUE_GTK_UNICODE_FIND_WRAP=PASS",
        "G05_TRUE_GTK_REPLACE_ALL_ONE_UNDO=PASS",
        "G05_TRUE_GTK_RENDERABILITY_PREFLIGHT=PASS",
        "G05_TRUE_GTK_LARGE_MULTILINE_SEARCH=PASS",
    ):
        if marker not in true_gtk:
            fail(f"G05 True-GTK marker missing: {marker}")
    print("G05_LITERAL_SEARCH_AUTHORITY=PASS")
    print("G05_REPLACE_ATOMICITY_SOURCE_GATE=PASS")
    print("G05_SEARCH_LIGHTWEIGHT_ARCHITECTURE=PASS")


def verify_g06_view_architecture() -> None:
    settings = (ROOT / "graphium/application/view_settings.py").read_text(encoding="utf-8")
    status = (ROOT / "graphium/application/view_status.py").read_text(encoding="utf-8")
    store = (ROOT / "graphium/infrastructure/view_settings_store.py").read_text(encoding="utf-8")
    view = (ROOT / "graphium/adapters/gtk/editor_view.py").read_text(encoding="utf-8")
    window = (ROOT / "graphium/adapters/gtk/window.py").read_text(encoding="utf-8")
    composition = (ROOT / "graphium/composition.py").read_text(encoding="utf-8")
    perf = (TOOLS / "g06_view_performance.py").read_text(encoding="utf-8")
    startup = (TOOLS / "g06_startup_regression.py").read_text(encoding="utf-8")
    true_gtk = (TOOLS / "g06_true_gtk_gate.py").read_text(encoding="utf-8")

    for marker in (
        "class ViewSettings", "class ViewSettingsController",
        "word_wrap: bool = False", "line_numbers: bool = False",
        "status_bar: bool = True", "font_family", "font_size_points",
    ):
        if marker not in settings:
            fail(f"G06 view-settings marker missing: {marker}")
    settings_tree = ast.parse(settings, filename="graphium/application/view_settings.py")
    persistent_fields: set[str] = set()
    for node in settings_tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "ViewSettings":
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    persistent_fields.add(item.target.id)
    if persistent_fields != {
        "word_wrap", "line_numbers", "status_bar", "font_family", "font_size_points"
    }:
        fail(f"unexpected G06 persistent View fields: {sorted(persistent_fields)}")
    if persistent_fields & {"zoom", "zoom_percent", "fullscreen", "full_screen"}:
        fail(f"transient G06 state leaked into persistent model: {sorted(persistent_fields)}")

    for marker in ("class JsonViewSettingsStore", "tempfile.mkstemp", "os.fsync", "os.replace"):
        if marker not in store:
            fail(f"G06 XDG settings-store marker missing: {marker}")
    for forbidden in ("GuardedFileWriter", "DocumentSaveService", "load_document", "logical_target_path"):
        if forbidden in store:
            fail(f"G06 config store crossed document authority: {forbidden}")

    for marker in (
        "class GraphiumTextView(Gtk.TextView)",
        "Gtk.TextWindowType.LEFT",
        "get_visible_rect()",
        "get_line_at_y",
        "get_line_yrange",
        "forward_line()",
        "Gtk.render_layout",
        "Gtk.CssProvider",
    ):
        if marker not in view:
            fail(f"G06 thin view marker missing: {marker}")
    view_imports = imports_in(ROOT / "graphium/adapters/gtk/editor_view.py")
    for forbidden_import in ("threading", "concurrent.futures", "multiprocessing"):
        if any(name == forbidden_import or name.startswith(forbidden_import + ".") for name in view_imports):
            fail(f"G06 forbidden view worker infrastructure: {forbidden_import}")
    for forbidden in ("GtkSourceView", "Gtk.Toolbar", "Thread("):
        if forbidden in view:
            fail(f"G06 forbidden view infrastructure: {forbidden}")
    if "set_border_window_size(Gtk.TextWindowType.LEFT, 0)" not in view:
        fail("G06 line-number gutter does not have native disable path")

    for marker in ("project_compact_status", "Ln {self.line}, Col {self.column}", "Saved", "Modified"):
        if marker not in status:
            fail(f"G06 compact-status marker missing: {marker}")
    for forbidden in ("get_text(", "get_char_count(", "split(", "word_count", "character_count"):
        if forbidden in status:
            fail(f"G06 status projection appears document-scanning: {forbidden}")
    refresh = window[window.index("def _refresh_status"):window.index("def _action_new")]
    for forbidden in ("capture_text", "get_text(", "get_char_count("):
        if forbidden in refresh:
            fail(f"G06 status refresh scans/copies document: {forbidden}")

    if "ViewSettingsController" not in composition or composition.count("ViewSettingsController(") != 1:
        fail("G06 persistent View settings authority is not composed exactly once")
    for marker in ("Gtk.WrapMode.WORD_CHAR", "set_line_numbers_visible", "set_base_font", "zoom_in", "zoom_out", "reset_zoom", "fullscreen()", "unfullscreen()"):
        if marker not in window:
            fail(f"G06 GTK View projection marker missing: {marker}")
    for forbidden in ("override_font", "modify_font"):
        if forbidden in view + window:
            fail(f"deprecated G06 font path detected: {forbidden}")

    for marker in (
        "G06_TRUE_GTK_VIEW_ACTIONS=PASS",
        "G06_TRUE_GTK_SETTINGS_PERSISTENCE=PASS",
        "G06_TRUE_GTK_LINE_NUMBERS_NATIVE_GUTTER=PASS",
        "G06_TRUE_GTK_WORD_WRAP=PASS",
        "G06_TRUE_GTK_FONT_ZOOM_SPLIT=PASS",
        "G06_TRUE_GTK_COMPACT_STATUS=PASS",
        "G06_TRUE_GTK_VIEW_CONTENT_NEUTRAL=PASS",
        "G06_TRUE_GTK_LARGE_MULTILINE_VIEW=PASS",
        "G06_TRUE_GTK_TOOLBAR_ABSENT=PASS",
        "G06_TRUE_GTK_MODAL_OWNERSHIP=PASS",
        "G06_TRUE_GTK_LIFECYCLE_BOUNDARIES=PASS",
    ):
        if marker not in true_gtk:
            fail(f"G06 True-GTK marker missing: {marker}")
    for marker in (
        "LIGHTWEIGHT_BUDGET_VIEW_GATE=PASS",
        "G06_VIEW_PERFORMANCE_LIFECYCLE_BOUNDARIES=PASS",
        "G06_VIEW_PERFORMANCE_ORACLE=SINGLE_TRANSITION_FRESH_PROCESS",
        "PRIMING_PROCESSES = 1",
        "MEASURED_PROCESSES = 7",
        "WORKER_TIMEOUT_SECONDS = 30",
        "FRAME_DEADLINE_SECONDS = 15.0",
        "after-paint",
        "line-numbers-10m",
        "wrap-10m",
        "zoom-10m",
        "font-apply-10m",
        "status-1000-updates",
        "MAX_FONT_APPLY_10M_P90_MS",
        "G06_VIEW_PERFORMANCE_FRESH_PROCESS_PROTOCOL=PASS",
        "G06_VIEW_PERFORMANCE_FIRST_POST_TRANSITION_FRAME=PASS",
    ):
        if marker not in perf:
            fail(f"G06 View performance marker missing: {marker}")
    for retired in ("def benchmark_toggle", "def benchmark_zoom"):
        if retired in perf:
            fail(f"retired cumulative G06 performance oracle returned: {retired}")
    if perf.index("import gi") < perf.index("def run_worker("):
        fail("G06 performance parent imported GTK instead of remaining GTK-free")
    for marker in (
        "G04_FIRST_EDITABLE_BASELINE_MS",
        "G04_FIRST_VISIBLE_GRAPHIUM_BASELINE_MS",
        "G06_STARTUP_REGRESSION_GATE=PASS",
        "G06_FIRST_EDITABLE_CROSS_PRODUCT_CLAIM=FORBIDDEN_UNTIL_G12",
    ):
        if marker not in startup:
            fail(f"G06 startup regression marker missing: {marker}")

    print("G06_VIEW_SETTINGS_AUTHORITY=PASS")
    print("G06_NATIVE_LINE_NUMBER_GUTTER=PASS")
    print("G06_COMPACT_STATUS_CHEAP_PROJECTION=PASS")
    print("G06_FONT_ZOOM_TRANSIENT_SPLIT=PASS")
    print("G06_VIEW_LIGHTWEIGHT_ARCHITECTURE=PASS")


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
        "evidence/G05_SOURCE_AUDIT.txt",
        "evidence/G05_MATURE_SOURCE_AUDIT.txt",
        "evidence/G05_SCALE_HARDENING_RECEIPT.txt",
        "evidence/G05_DEAD_CODE_AUDIT.txt",
        "evidence/G05_SCOPE_AND_BUILD_RECEIPT.txt",
        "evidence/G06_SOURCE_AUDIT.txt",
        "evidence/G06_MATURE_SOURCE_AUDIT.txt",
        "evidence/G06_LINE_NUMBERS_NONCANDIDATE_PROBE_RECEIPT_20260815.txt",
        "evidence/G06_DEAD_CODE_AUDIT.txt",
        "evidence/G06_SCOPE_AND_BUILD_RECEIPT.txt",
        "evidence/G06_INTEGRATED_CHECKPOINT_FAILURE_REAUDIT_20260815.txt",
        "evidence/G06_TRUE_GTK_MODAL_LIFECYCLE_TIMEOUT_OWNERSHIP_AUDIT_20260815.txt",
        "evidence/G06_VIEW_PERFORMANCE_TIMEOUT_REAUDIT_20260815.txt",
    )
    for rel in required:
        if not (ROOT / rel).is_file():
            fail(f"required evidence missing: {rel}")
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
    g06_audit = (ROOT / "evidence/G06_MATURE_SOURCE_AUDIT.txt").read_text(encoding="utf-8")
    for marker in (
        "ASSUMPTION UNDER TEST", "CONTRADICTORY / STRESSING EVIDENCE",
        "ALTERNATIVE MATURE MODEL", "GRAPHIUM CONSEQUENCE", "DECISION",
        "Leafpad", "L3afpad", "Mousepad", "Gtk.TextView",
        "REJECT v1", "MATURE_AUDIT=PASS", "CONFIRMATION_BIAS_COUNTERMEASURE=PASS",
    ):
        if marker not in g06_audit:
            fail(f"G06 mature audit marker missing: {marker}")
    g06_probe = (ROOT / "evidence/G06_LINE_NUMBERS_NONCANDIDATE_PROBE_RECEIPT_20260815.txt").read_text(encoding="utf-8")
    for marker in (
        "PRE_PRODUCT_PROBE_HARNESS_IMPORT_DEFECT",
        "G06_LINE_NUMBERS_NONCANDIDATE_PROBE=PASS",
        "FINAL_PHASE=G06_LINE_NUMBERS_NONCANDIDATE_PROBE_PASS",
        "G06_LINE_NUMBERS=ADOPT",
    ):
        if marker not in g06_probe:
            fail(f"G06 line-number probe receipt marker missing: {marker}")
    g06_ownership = (ROOT / "evidence/G06_TRUE_GTK_MODAL_LIFECYCLE_TIMEOUT_OWNERSHIP_AUDIT_20260815.txt").read_text(encoding="utf-8")
    for marker in (
        "Mousepad 0.7.0", "Leafpad", "L3afpad",
        "G06_INTEGRATED_CHECKPOINT_LINE=RETIRED",
        "G06_TRUE_GTK_EXPECTED_MODAL_COUNT=0",
        "G06_TRUE_GTK_UNEXPECTED_MODAL=UNWIND_THEN_FAIL",
        "G06_FIXTURE_OPEN_REQUIRES_EXACT_SAVED_STATE=YES",
        "G06_EXPECTED_DIALOG_RESPONSE_OWNERSHIP=SCHEDULE_BEFORE_TRIGGER",
        "G06_GLIB_SOURCE_OWNERSHIP=EXPLICIT_CLEANUP_REQUIRED",
        "G06_OUTER_TIMEOUT_ROLE=LAST_RESORT_PROCESS_CONTAINMENT_ONLY",
        "G06_QUALIFICATION_TOPOLOGY=FRESH_PROCESS_GATE_MATRIX",
        "G06_NEXT_T480_RUN=PRODUCT_CANDIDATE_ONLY_AFTER_SEPARATE_AUTHORIZATION",
        "MATURE_SOURCE_AUDIT=PASS",
        "CONFIRMATION_BIAS_COUNTERMEASURE=PASS",
    ):
        if marker not in g06_ownership:
            fail(f"G06 modal/lifecycle/timeout ownership audit marker missing: {marker}")
    g06_perf_audit = (ROOT / "evidence/G06_VIEW_PERFORMANCE_TIMEOUT_REAUDIT_20260815.txt").read_text(encoding="utf-8")
    for marker in (
        "OLD_ORACLE=RETIRED",
        "SINGLE_TRANSITION_PER_FRESH_PROCESS=ADOPT",
        "FIRST_POST_TRANSITION_FRAME=ADOPT",
        "PRIMING_PROCESSES=1",
        "MEASURED_PROCESSES_PER_SCENARIO=7",
        "MAX_FONT_APPLY_10M_P90_MS=500",
        "BUDGETS_WEAKENED=NO",
        "MATURE_SOURCE_REAUDIT=PASS",
        "CONFIRMATION_BIAS_COUNTERMEASURE=PASS",
    ):
        if marker not in g06_perf_audit:
            fail(f"G06 View performance timeout re-audit marker missing: {marker}")
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
    print("G05_SOURCE_AND_MATURE_AUDIT=PASS")
    print("G05_DEAD_CODE_AUDIT=PASS")
    print("G06_SOURCE_AND_MATURE_AUDIT=PASS")
    print("G06_LINE_NUMBERS_PROBE_EVIDENCE=PASS")
    print("G06_MODAL_LIFECYCLE_TIMEOUT_OWNERSHIP_AUDIT=PASS")
    print("G06_VIEW_PERFORMANCE_TIMEOUT_REAUDIT=PASS")
    print("G06_DEAD_CODE_AUDIT=PASS")


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
    for marker in (
        "G05_CONTRACT=FROZEN",
        "G05_SEARCH_SCOPE=LITERAL_CURRENT_DOCUMENT_ONLY",
        "G05_HIGHLIGHT_ALL=REJECT",
        "G05_BACKGROUND_SEARCH=REJECT",
        "G05_REPLACE_ALL_UNDO_GROUPS=1",
        "G05_GENERIC_RENDER_GUARD_BYPASS=FORBIDDEN",
        "G05_REPLACE_UNDO_PAYLOAD_MAX=DELTA_HISTORY_MAX_PAYLOAD",
        "G05_CASEFOLD_WORKING_SET=LOGICAL_LINE_BOUNDED",
        "G05_REPLACE_ALL_MATCH_CAP=50000",
    ):
        if marker not in contract:
            fail(f"G05 contract marker missing: {marker}")
    for marker in (
        "G06_CONTRACT=FROZEN",
        "G06_IMPLEMENTATION_AUTHORIZED=YES",
        "G06_VIEW_MENU=STATUS_BAR,LINE_NUMBERS,WORD_WRAP,FONT,ZOOM_IN,ZOOM_OUT,ZOOM_RESET,FULL_SCREEN",
        "G06_APPEARANCE=DEFER_G10",
        "G06_TOOLBAR=REJECT_V1",
        "G06_WORD_WRAP=GTK_WORD_CHAR",
        "G06_LINE_NUMBERS=GTK_TEXTVIEW_LEFT_BORDER_WINDOW",
        "G06_LINE_NUMBER_DRAW_SCOPE=VISIBLE_LOGICAL_LINES_ONLY",
        "G06_WRAPPED_CONTINUATION_NUMBERS=NO",
        "G06_GTKSOURCEVIEW=FORBIDDEN",
        "G06_STATUS_FIELDS=LINE_COLUMN,ENCODING_EOL,SAVED_MODIFIED",
        "G06_LIVE_WORD_CHAR_COUNT=DEFER_G07_STATISTICS",
        "G06_FONT=PERSISTENT_FAMILY_SIZE_VIA_CSS_PROVIDER",
        "G06_ZOOM=TRANSIENT_RELATIVE_TO_BASE_FONT",
        "G06_FULL_SCREEN=TRANSIENT",
        "G06_SETTINGS_STORAGE=XDG_SMALL_ATOMIC_JSON",
        "G06_SETTINGS_BACKGROUND_WRITE=FORBIDDEN",
        "G06_LIGHTWEIGHT_BUDGET_GATE=REQUIRED",
        "G06_STARTUP_REGRESSION_BASELINE=G04_CERTIFIED_T480",
        "G06_STARTUP_TIME_REGRESSION_LIMIT=MAX_25_PERCENT_OR_75_MS",
        "G06_STARTUP_RSS_REGRESSION_LIMIT=MAX_25_PERCENT_OR_20_MIB",
        "G06_FIRST_EDITABLE_CROSS_PRODUCT_CLAIM=DEFER_G12_COMMON_EXTERNAL_ORACLE",
        "G06_INTEGRATED_CHECKPOINT_LINE=RETIRED",
        "G06_TRUE_GTK_EXPECTED_MODAL_COUNT=0",
        "G06_TRUE_GTK_UNEXPECTED_MODAL=UNWIND_THEN_FAIL",
        "G06_FIXTURE_OPEN_REQUIRES_EXACT_SAVED_STATE=YES",
        "G06_EXPECTED_DIALOG_RESPONSE_OWNERSHIP=SCHEDULE_BEFORE_TRIGGER",
        "G06_GLIB_SOURCE_OWNERSHIP=EXPLICIT_CLEANUP_REQUIRED",
        "G06_OUTER_TIMEOUT_ROLE=LAST_RESORT_PROCESS_CONTAINMENT_ONLY",
        "G06_VIEW_PERFORMANCE_ORACLE=SINGLE_TRANSITION_FRESH_PROCESS",
        "G06_VIEW_PERFORMANCE_PRIMING_PROCESSES=1",
        "G06_VIEW_PERFORMANCE_MEASURED_PROCESSES=7",
        "G06_VIEW_PERFORMANCE_TRANSITIONS_PER_WORKER=1",
        "G06_VIEW_PERFORMANCE_FRAME_ORACLE=FIRST_POST_TRANSITION_AFTER_PAINT",
        "G06_VIEW_PERFORMANCE_FONT_APPLY_10M_P90_MAX_MS=500",
        "G06_VIEW_PERFORMANCE_BUDGETS_WEAKENED=NO",
        "G06_QUALIFICATION_TOPOLOGY=FRESH_PROCESS_GATE_MATRIX",
    ):
        if marker not in contract:
            fail(f"G06 contract marker missing: {marker}")
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
    print("G05_CONTRACT_MARKERS=PASS")
    print("G06_CONTRACT_MARKERS=PASS")


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
    verify_g05_search_architecture()
    verify_g06_view_architecture()
    verify_shortcuts()
    verify_evidence()
    verify_contracts()
    verify_text_integrity()
    run_tests()
    print("STRICT_GATES=PASS")
    print("GTK_DESKTOP_VALIDATION=PENDING")
    print("G06_VIEW_PERFORMANCE_DESKTOP=PENDING_T480")
    print("FINAL_PHASE=G06_NONDESKTOP_VERIFIED")


if __name__ == "__main__":
    main()
