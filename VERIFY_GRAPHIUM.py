#!/usr/bin/env python3
"""Fail-closed non-desktop verifier for Graphium G09, preserving G00-G08 invariants."""
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
EXPECTED_TESTS = 354
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
        "G09",
        "Explicit Text Transformations Only / No Format-Menu Expansion",
        "0.0.10-g09",
        "io.github.leviagravia.Graphium",
    )
    actual = (WORK_ITEM, WORK_ITEM_DESCRIPTION, VERSION, DESKTOP_APPLICATION_ID)
    if actual != expected:
        fail(f"unexpected G09 identity: {actual}")
    print("G09_RUNTIME_IDENTITY=PASS")
    print("G09_DESKTOP_APPLICATION_ID=PASS")


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
    # G06/G07/G08 may atomically replace their own narrow product-local XDG configuration
    # files; these stores are explicitly non-document authority and must not import document
    # persistence.  The allow-list is exact and source-audited.
    config_store_rel = "graphium/infrastructure/view_settings_store.py"
    recent_store_rel = "graphium/infrastructure/recent_files_store.py"
    print_store_rel = "graphium/adapters/gtk/printing.py"
    non_document_stores = (config_store_rel, recent_store_rel, print_store_rel)
    for path in sorted(PACKAGE.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if rel == writer_rel or rel in non_document_stores:
            continue
        text = path.read_text(encoding="utf-8")
        for marker in ("os.replace(", "os.link(", "os.rename(", "os.fsync(", ".write_bytes("):
            if marker in text:
                fail(f"document-writer marker outside authority: {rel}: {marker}")
    for store_rel in non_document_stores:
        store_path = ROOT / store_rel
        if store_path.is_file():
            text = store_path.read_text(encoding="utf-8")
            for forbidden in ("GuardedFileWriter", "DocumentSave", "load_document", "logical_target_path"):
                if forbidden in text:
                    fail(f"XDG convenience store crossed into document authority: {store_rel}: {forbidden}")
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
        "new", "open", "open-recent", "clear-recent", "save", "save-as",
        "save-copy", "save-version-copy", "properties", "page-setup",
        "print-preview", "print", "quit",
        "undo", "redo", "cut", "copy", "paste", "delete", "select-all",
        "uppercase", "lowercase", "duplicate-line-selection",
        "move-lines-up", "move-lines-down", "trim-trailing-spaces",
        "find", "find-next", "find-previous", "replace", "go-to-line",
        "status-bar", "line-numbers", "word-wrap", "font",
        "zoom-in", "zoom-out", "zoom-reset", "full-screen",
        "statistics", "user-guide", "keyboard-shortcuts", "about",
    ]
    if [c.action for c in COMMANDS] != expected:
        fail(f"unexpected G09 command surface: {[c.action for c in COMMANDS]}")
    by_action = {c.action: c for c in COMMANDS}
    for action in ("status-bar", "line-numbers", "word-wrap", "full-screen"):
        if not by_action[action].stateful:
            fail(f"G06 View action must be stateful: {action}")
    if any(c.action in ("toolbar", "appearance") for c in COMMANDS):
        fail("G06 prematurely added toolbar or appearance command")
    for rel in ("docs/user/GRAPHIUM_USER_GUIDE.txt", "docs/user/GRAPHIUM_KEYBOARD_SHORTCUTS.txt"):
        if not (ROOT / rel).is_file():
            fail(f"Help product file missing: {rel}")
    print("G09_COMMAND_SURFACE=PASS")
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
        "tools/g07_statistics_performance.py", "tools/g07_true_gtk_gate.py",
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


def verify_g07_architecture() -> None:
    recent = (ROOT / "graphium/application/recent_files.py").read_text(encoding="utf-8")
    recent_store = (ROOT / "graphium/infrastructure/recent_files_store.py").read_text(encoding="utf-8")
    copy = (ROOT / "graphium/application/document_copy.py").read_text(encoding="utf-8")
    props = (ROOT / "graphium/application/document_properties.py").read_text(encoding="utf-8")
    observer = (ROOT / "graphium/infrastructure/document_observer.py").read_text(encoding="utf-8")
    loader = (ROOT / "graphium/infrastructure/document_loader.py").read_text(encoding="utf-8")
    stats = (ROOT / "graphium/application/text_statistics.py").read_text(encoding="utf-8")
    composition = (ROOT / "graphium/composition.py").read_text(encoding="utf-8")
    lifecycle = (ROOT / "graphium/application/file_lifecycle.py").read_text(encoding="utf-8")
    window = (ROOT / "graphium/adapters/gtk/window.py").read_text(encoding="utf-8")
    perf = (TOOLS / "g07_statistics_performance.py").read_text(encoding="utf-8")
    true_gtk = (TOOLS / "g07_true_gtk_gate.py").read_text(encoding="utf-8")

    for marker in ("MAX_RECENT_FILES = 10", "_ensure_loaded", "self.store.save(candidate)"):
        if marker not in recent:
            fail(f"G07 Recent marker missing: {marker}")
    for marker in ('{"version": 1, "paths": list(values)}', "0o600", "os.replace"):
        if marker not in recent_store:
            fail(f"G07 Recent store marker missing: {marker}")
    if "os.fsync" in recent_store:
        fail("G07 Recent convenience state must not impose document-grade fsync barriers")
    for marker in ("DocumentCopyService", "self.writer.commit", "plan_named_version_copy", "_v"):
        if marker not in copy:
            fail(f"G07 copy marker missing: {marker}")
    if "accept_committed_save" in copy:
        fail("G07 non-binding copy entered savepoint acceptance lane")
    for marker in ("CheckNowStatus", "CONTENT_CHANGED", "REPLACED_OR_RETARGETED", "self.session.snapshot() != before"):
        if marker not in props:
            fail(f"G07 Properties marker missing: {marker}")
    for marker in ("hashlib.sha256", "os.fstat", "stat.S_ISREG", "capture_bytes"):
        if marker not in observer:
            fail(f"G07 strong observer marker missing: {marker}")
    if "observe_document(path, capture_bytes=True" not in loader:
        fail("G07 loader does not delegate to shared strong observer")
    for marker in ("def count_text_statistics", ".isspace()", "text.count(\"\\n\") + 1"):
        if marker not in stats:
            fail(f"G07 Statistics marker missing: {marker}")
    for rel in (
        "graphium/application/recent_files.py", "graphium/application/document_copy.py",
        "graphium/application/document_properties.py", "graphium/application/text_statistics.py",
        "graphium/infrastructure/document_observer.py", "graphium/infrastructure/recent_files_store.py",
    ):
        imports = imports_in(ROOT / rel)
        if any(name == "gi" or name.startswith("gi.") for name in imports):
            fail(f"G07 GTK leaked outside adapter boundary: {rel}")
    if composition.count("GuardedFileWriter()") != 1 or "DocumentCopyService(session=session, writer=writer)" not in composition:
        fail("G07 composition did not preserve one physical writer")
    if '_touch_recent_nonfatal(result.file_state.binding.logical_path)' not in lifecycle or '_touch_recent_nonfatal(self.session.logical_path)' not in lifecycle:
        fail("G07 lifecycle Recent hooks missing")
    for marker in ("open-recent", "save-copy", "save-version-copy", "properties", "statistics", "self.core.lifecycle.open_document(path)"):
        if marker not in window:
            fail(f"G07 GTK wiring marker missing: {marker}")
    for forbidden in ("Gio.FileMonitor", "sqlite3", "SessionManager", "Thread(", "threading"):
        if forbidden in recent + copy + props + stats + observer:
            fail(f"G07 forbidden background/heavy authority marker: {forbidden}")
    for marker in ("G07_STATISTICS_PERFORMANCE=PASS", "1024*1024,1000.0", "10*1024*1024,1500.0", "RSS_MAX_MIB=260.0"):
        if marker not in perf:
            fail(f"G07 Statistics performance marker missing: {marker}")
    for marker in (
        "G07_TRUE_GTK_RECENT=PASS", "G07_TRUE_GTK_COPY=PASS", "G07_TRUE_GTK_VERSION_COPY=PASS",
        "G07_TRUE_GTK_PROPERTIES=PASS", "G07_TRUE_GTK_STATISTICS=PASS",
        "G07_TRUE_GTK_MODAL_LIFECYCLE=PASS", "G07_TRUE_GTK_1M_RESPONSIVENESS=PASS",
    ):
        if marker not in true_gtk:
            fail(f"G07 True-GTK marker missing: {marker}")
    print("G07_RECENT_GTK_FREE=PASS")
    print("G07_COPY_GTK_FREE=PASS")
    print("G07_PROPERTIES_GTK_FREE=PASS")
    print("G07_STATISTICS_GTK_FREE=PASS")
    print("G07_SHARED_STRONG_OBSERVER=PASS")
    print("G07_ONE_WRITER_COMPOSITION=PASS")
    print("G07_NO_BACKGROUND_OR_MONITOR=PASS")


def verify_g08_architecture() -> None:
    window_path = ROOT / "graphium/adapters/gtk/window.py"
    printing_path = ROOT / "graphium/adapters/gtk/printing.py"
    pagination_path = ROOT / "graphium/adapters/gtk/print_pagination.py"
    probe_path = TOOLS / "g08_print_binding_probe.py"
    for path in (printing_path, pagination_path, probe_path):
        if not path.is_file():
            fail(f"G08 required implementation file missing: {path.relative_to(ROOT)}")

    window = window_path.read_text(encoding="utf-8")
    printing = printing_path.read_text(encoding="utf-8")
    pagination = pagination_path.read_text(encoding="utf-8")
    probe = probe_path.read_text(encoding="utf-8")

    tree = ast.parse(window, filename=str(window_path))
    top_level_imports = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            top_level_imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            top_level_imports.append(node.module)
    if any("printing" in name for name in top_level_imports):
        fail(f"G08 printing adapter imported on startup path: {top_level_imports}")
    for marker in (
        "self._print_controller = None",
        "from .printing import GraphiumPrintController",
        "from .printing import PrintSnapshot",
        "self.buffer_port.capture_full()",
        "self.text_view.base_font",
    ):
        if marker not in window:
            fail(f"G08 lazy window marker missing: {marker}")

    for marker in (
        'resolve_xdg_paths().config / "page-setup.ini"',
        "os.lstat(self.path)", "stat.S_ISREG", "Gtk.PageSetup.new_from_file",
        "tempfile.mkstemp", "0o600", "setup.to_file(temp_name)", "os.fsync",
        "os.replace(temp_name, self.path)", "Gtk.PrintOperation()",
        "operation.set_allow_async(True)", 'operation.connect("done", self._on_done)',
        "Gtk.PrintOperationResult.IN_PROGRESS", "self._active_operation = operation",
        "if operation is not self._active_operation", "def _reject_if_busy",
        "Gtk.PrintOperationAction.PREVIEW", "Gtk.PrintOperationAction.PRINT_DIALOG",
        "PangoCairo.show_layout_line",
        'operation.connect("paginate", job.paginate)',
        "def paginate(self, operation, context)",
        "IncrementalVisualPaginator",
        "_PAGINATION_CHUNK_TARGET_CHARS = 16 * 1024",
        "layout.get_line_readonly(index)", "line.get_extents()",
    ):
        if marker not in printing:
            fail(f"G08 print architecture marker missing: {marker}")
    for forbidden in (
        "GtkSourceView", "GtkSourcePrintCompositor", "threading", "Thread(",
        "concurrent.futures", "timeout_add", "idle_add", 'connect("preview"',
    ):
        if forbidden in printing:
            fail(f"G08 forbidden print architecture marker: {forbidden}")
    for forbidden in ("splitlines()", "characters_per_page", "get_visible_rect()"):
        if forbidden in printing:
            fail(f"G08 heuristic/viewport pagination detected: {forbidden}")
    for marker in (
        "class VisualLinePage", "def paginate_visual_line_heights", "usable_height",
        "class VisualLineSpan", "class IncrementalVisualPage",
        "class IncrementalVisualPaginator", "def add_chunk", "def finish",
        "def logical_line_chunk_end",
    ):
        if marker not in pagination:
            fail(f"G08 pagination helper marker missing: {marker}")
    for marker in (
        'gi.require_version("Gtk", "3.0")', "Gtk.print_run_page_setup_dialog",
        "Gtk.PrintOperationAction.EXPORT", "G08_PRINT_BINDING_PROBE=PASS",
        "CANDIDATE_ATTEMPT_CONSUMED=NO", "GIT_MUTATION=NO",
    ):
        if marker not in probe:
            fail(f"G08 binding probe marker missing: {marker}")

    print("G08_PRINT_ADAPTER_LAZY_IMPORT=PASS")
    print("G08_PAGE_SETUP_CONFIG_AUTHORITY=PASS")
    print("G08_NATIVE_PREVIEW_ASYNC_PRINT=PASS")
    print("G08_PANGO_VISUAL_LINE_PAGINATION=PASS")
    print("G08_NO_BACKGROUND_PRINT_ARCHITECTURE=PASS")
    print("G08_BINDING_PROBE_TOOL=PASS_NOT_RUN_LOCAL")



def verify_g09_architecture() -> None:
    planner_path = ROOT / "graphium/application/text_transform.py"
    planner = planner_path.read_text(encoding="utf-8")
    window = (ROOT / "graphium/adapters/gtk/window.py").read_text(encoding="utf-8")
    commands = (ROOT / "graphium/application/commands.py").read_text(encoding="utf-8")
    native = (ROOT / "graphium/application/native_editor.py").read_text(encoding="utf-8")
    if not planner_path.is_file():
        fail("G09 GTK-free planner missing")
    for forbidden in ("import gi", "gi.repository", "GtkSourceView", "threading", "concurrent.futures"):
        if forbidden in planner:
            fail(f"G09 planner crossed frozen boundary: {forbidden}")
    for marker in (
        "class TransformationPlan", "MAX_TRANSFORM_CHANGED_SPANS = 50_000",
        "plan_uppercase", "plan_lowercase", "plan_duplicate_line_selection",
        "plan_move_lines_up", "plan_move_lines_down", "plan_trim_trailing_spaces",
        "ensure_interactive_text_renderable", "DEFAULT_MAX_HISTORY_PAYLOAD_CHARS",
    ):
        if marker not in planner:
            fail(f"G09 planner marker missing: {marker}")
    if 'section.append_submenu("Transform Text", transform_menu)' not in window:
        fail("G09 nested Transform Text menu missing")
    if 'root.append_submenu("Format"' in window or '"Format"' in commands:
        fail("G09 illegally introduced a top-level Format menu")
    if "apply_prevalidated_programmatic_group" not in window:
        fail("G09 window does not route mutation through G05 authority")
    if native.count("def apply_prevalidated_programmatic_group") != 1:
        fail("G09 mutation authority count changed")
    from graphium.application.commands import COMMANDS
    transforms = [c for c in COMMANDS if c.submenu == "Transform Text"]
    expected = [
        ("uppercase", None), ("lowercase", None),
        ("duplicate-line-selection", None), ("move-lines-up", "<Alt>Up"),
        ("move-lines-down", "<Alt>Down"), ("trim-trailing-spaces", None),
    ]
    if [(c.action, c.accelerator) for c in transforms] != expected:
        fail(f"G09 transform command surface mismatch: {transforms}")
    for rel in ("tools/g09_performance.py", "tools/g09_true_gtk_gate.py", "tools/g09_shortcut_audit.py"):
        if not (ROOT / rel).is_file():
            fail(f"G09 qualification tool missing: {rel}")
    print("G09_GTK_FREE_PLANNER=PASS")
    print("G09_SINGLE_MUTATION_AUTHORITY=PASS")
    print("G09_TRANSFORM_MENU_AND_ACTIONS=PASS")
    print("G09_CHANGED_SPAN_CAP=PASS limit=50000")


def verify_shortcuts() -> None:
    from graphium.application.commands import FORBIDDEN_ACCELERATORS, accelerator_map
    if "<Ctrl><Alt>L" not in FORBIDDEN_ACCELERATORS:
        fail("Ctrl+Alt+L forbidden marker missing")
    amap = accelerator_map()
    if "<Ctrl><Alt>L" in amap.values():
        fail("Ctrl+Alt+L assigned")
    if amap.get("move-lines-up") != "<Alt>Up" or amap.get("move-lines-down") != "<Alt>Down":
        fail("G09 Move Lines accelerators mismatch")
    normalized = [value.lower().replace("<primary>", "<ctrl>") for value in amap.values()]
    if len(normalized) != len(set(normalized)):
        fail("internal Graphium accelerator collision")
    print("KNOWN_SHORTCUT_COLLISION_GATE=PASS")
    print("G09_INTERNAL_ACCELERATOR_GATE=PASS")


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
        "evidence/G07_SOURCE_AUDIT.txt",
        "evidence/G07_MATURE_SOURCE_AUDIT.txt",
        "evidence/G07_LIGHTWEIGHT_BUDGET_AND_CONTRACT_FREEZE.txt",
        "evidence/G07_FEATHERPAD_SOURCE_RECEIPT.txt",
        "evidence/G07_R1_STARTUP_FAILURE_MATURE_REAUDIT_20260816.txt",
        "evidence/G07_COMPARATOR_FAILURE_MATURE_SOURCE_REAUDIT_20260817.txt",
        "evidence/G08_SOURCE_AUDIT_20260818.txt",
        "evidence/G08_MATURE_SOURCE_AUDIT_20260818.txt",
        "evidence/G08_DECISION_MATRIX_AND_LIGHTWEIGHT_BUDGET_20260818.txt",
        "evidence/G08_LIGHTWEIGHT_BUDGET_AND_CONTRACT_FREEZE_20260818.txt",
        "evidence/G08_IMPLEMENTATION_NONCANDIDATE_RECEIPT_20260818.txt",
        "evidence/G09_SOURCE_AUDIT_20260820.txt",
        "evidence/G09_MATURE_SOURCE_AUDIT_20260820.txt",
        "evidence/G09_DECISION_MATRIX_AND_LIGHTWEIGHT_BUDGET_20260820.txt",
        "evidence/G09_CONTRACT_FREEZE_20260820.txt",
        "evidence/G09_IMPLEMENTATION_NONCANDIDATE_RECEIPT_20260820.txt",
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
    g07_source = (ROOT / "evidence/G07_SOURCE_AUDIT.txt").read_text(encoding="utf-8")
    for marker in (
        "Baseline commit: aae14ef000ea44674cb9bbb7b3a87e3af00c0b18",
        "Verdict: PASS", "physical_writer_authority_count=1",
        "GTK-free non-binding copy service", "strong observation",
    ):
        if marker not in g07_source:
            fail(f"G07 source audit marker missing: {marker}")
    g07_mature = (ROOT / "evidence/G07_MATURE_SOURCE_AUDIT.txt").read_text(encoding="utf-8")
    for marker in ("Verdict: PASS", "Mousepad 0.7.0", "FeatherPad", "GNOME Text Editor", "L3afpad", "Graphium disposition: ADAPT"):
        if marker not in g07_mature:
            fail(f"G07 mature audit marker missing: {marker}")
    g07_budget = (ROOT / "evidence/G07_LIGHTWEIGHT_BUDGET_AND_CONTRACT_FREEZE.txt").read_text(encoding="utf-8")
    for marker in (
        "G07_CONTRACT=FROZEN", "QUICK-EDIT VALUE: PASS", "PERSISTENT/BACKGROUND COST: PASS",
        'JSON schema: {"version": 1, "paths":',
        "NO second physical writer", "NO second document/session authority",
    ):
        if marker not in g07_budget:
            fail(f"G07 lightweight/contract audit marker missing: {marker}")
    startup_reaudit = (ROOT / "evidence/G07_R1_STARTUP_FAILURE_MATURE_REAUDIT_20260816.txt").read_text(encoding="utf-8")
    for marker in (
        "G06_STARTUP_REGRESSION_GATE=FAIL", "FeatherPad", "GNOME Text Editor", "Mousepad 0.7.0",
        "gedit", "NEdit", "G07_RECENT_DURABILITY=ATOMIC_CONVENIENCE_NO_FSYNC",
        "MATURE_REAUDIT=PASS", "CONFIRMATION_BIAS_COUNTERMEASURE=PASS",
    ):
        if marker not in startup_reaudit:
            fail(f"G07 startup failure mature re-audit marker missing: {marker}")
    comparator_reaudit = (ROOT / "evidence/G07_COMPARATOR_FAILURE_MATURE_SOURCE_REAUDIT_20260817.txt").read_text(encoding="utf-8")
    for marker in (
        "MATURE SOURCE: LEAFPAD 0.8.19", "MATURE SOURCE: L3AFPAD", "MATURE SOURCE: MOUSEPAD 0.7.0",
        "MATURE SOURCE: FEATHERPAD", "CURRENT_STOP=COMPARATOR_OR_X11_INFRASTRUCTURE_BLOCK",
        "PRODUCT_RUNTIME_CHANGE_REQUIRED=NO", "HARNESS_REPAIR_REQUIRED=YES",
        "MATURE_REAUDIT=PASS", "CONFIRMATION_BIAS_COUNTERMEASURE=PASS",
    ):
        if marker not in comparator_reaudit:
            fail(f"G07 comparator failure mature re-audit marker missing: {marker}")
    feather = (ROOT / "evidence/G07_FEATHERPAD_SOURCE_RECEIPT.txt").read_text(encoding="utf-8")
    if (
        "1651a43c8541d6921f6ece30a82bcb38e1341fbee2e17be9081468fe6ea548ac" not in feather
        or "ZIP integrity:" not in feather
        or "PASS" not in feather
    ):
        fail("G07 FeatherPad source receipt mismatch")

    g08_source = (ROOT / "evidence/G08_SOURCE_AUDIT_20260818.txt").read_text(encoding="utf-8")
    for marker in (
        "Verdict: PASS", "G08 can be added without changing G01-G07 document/write authorities",
        "CURRENT STARTUP PATH", "Source-audit result: PASS",
    ):
        if marker not in g08_source:
            fail(f"G08 source audit marker missing: {marker}")
    g08_mature = (ROOT / "evidence/G08_MATURE_SOURCE_AUDIT_20260818.txt").read_text(encoding="utf-8")
    for marker in (
        "Verdict: PASS", "Leafpad", "L3afpad", "Mousepad", "gedit", "GNOME TEXT EDITOR",
        "GtkPrintOperation", "Pango/Cairo", "ADOPT STRICT LAZY STARTUP ISOLATION",
    ):
        if marker not in g08_mature:
            fail(f"G08 mature source audit marker missing: {marker}")
    g08_matrix = (ROOT / "evidence/G08_DECISION_MATRIX_AND_LIGHTWEIGHT_BUDGET_20260818.txt").read_text(encoding="utf-8")
    for marker in (
        "LIGHTWEIGHT_BUDGET_GATE=PASS", "QUICK-EDIT VALUE: PASS",
        "PERSISTENT/BACKGROUND COST: PASS", "STARTUP PATH: PASS BY FROZEN CONTRACT",
    ):
        if marker not in g08_matrix:
            fail(f"G08 decision/budget marker missing: {marker}")
    g08_freeze = (ROOT / "evidence/G08_LIGHTWEIGHT_BUDGET_AND_CONTRACT_FREEZE_20260818.txt").read_text(encoding="utf-8")
    for marker in (
        "G08_CONTRACT=FROZEN", "Thin GTK3 print adapter with Pango/Cairo",
        "STARTUP-ISOLATION GATE", "T480 NON-CANDIDATE binding",
        "This freeze consumes NO candidate attempt",
    ):
        if marker not in g08_freeze:
            fail(f"G08 freeze marker missing: {marker}")
    g08_impl = (ROOT / "evidence/G08_IMPLEMENTATION_NONCANDIDATE_RECEIPT_20260818.txt").read_text(encoding="utf-8")
    for marker in (
        "G08_IMPLEMENTATION=BUILT_IN_ISOLATED_COPY", "G08_DESKTOP_CANDIDATE=NOT_DECLARED",
        "CANDIDATE_ATTEMPTS_CONSUMED=0/2", "local headless baseline: 304/304 PASS",
        "301 PASS / 3 FAIL", "gedit/gedit-app.c", "leafpad/src/gtkprint.c",
    ):
        if marker not in g08_impl:
            fail(f"G08 implementation receipt marker missing: {marker}")

    g09_source = (ROOT / "evidence/G09_SOURCE_AUDIT_20260820.txt").read_text(encoding="utf-8")
    g09_mature = (ROOT / "evidence/G09_MATURE_SOURCE_AUDIT_20260820.txt").read_text(encoding="utf-8")
    g09_matrix = (ROOT / "evidence/G09_DECISION_MATRIX_AND_LIGHTWEIGHT_BUDGET_20260820.txt").read_text(encoding="utf-8")
    g09_freeze = (ROOT / "evidence/G09_CONTRACT_FREEZE_20260820.txt").read_text(encoding="utf-8")
    g09_impl = (ROOT / "evidence/G09_IMPLEMENTATION_NONCANDIDATE_RECEIPT_20260820.txt").read_text(encoding="utf-8")
    for marker in ("SOURCE_ARCHITECTURE_FINDING=G05_PROGRAMMATIC_AUTHORITY_REUSABLE", "GTK_FREE_PURE_PLANNER=ADOPT"):
        if marker not in g09_source: fail(f"G09 source audit marker missing: {marker}")
    for marker in ("Mousepad", "FeatherPad", "Graphium consequence", "FALSIFICATION RESULTS", "SUPPORTED"):
        if marker not in g09_mature: fail(f"G09 mature audit marker missing: {marker}")
    for marker in ("LIGHTWEIGHT_BUDGET_GATE=PASS", "ADOPT", "REJECT G09/V1", "DEFER"):
        if marker not in g09_matrix: fail(f"G09 matrix marker missing: {marker}")
    for marker in ("G09_CONTRACT=FROZEN", "50,000", "3.0 s", "apply_prevalidated_programmatic_group"):
        if marker not in g09_freeze: fail(f"G09 freeze marker missing: {marker}")
    for marker in ("G09_IMPLEMENTATION=BUILT_IN_ISOLATED_COPY", "G09_FOCUSED_TESTS=35/35 PASS", "FULL_HEADLESS_SUITE=354/354 PASS"):
        if marker not in g09_impl: fail(f"G09 implementation receipt marker missing: {marker}")

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
    print("G07_SOURCE_AND_MATURE_AUDIT=PASS")
    print("G07_LIGHTWEIGHT_BUDGET_AUDIT=PASS")
    print("G07_FEATHERPAD_DIRECT_SOURCE=PASS")
    print("G07_COMPARATOR_FAILURE_MATURE_REAUDIT=PASS")
    print("G08_SOURCE_AND_MATURE_AUDIT=PASS")
    print("G08_LIGHTWEIGHT_BUDGET_AUDIT=PASS")
    print("G08_IMPLEMENTATION_RECEIPT=PASS")
    print("G09_SOURCE_AND_MATURE_AUDIT=PASS")
    print("G09_LIGHTWEIGHT_BUDGET_AUDIT=PASS")
    print("G09_IMPLEMENTATION_RECEIPT=PASS")


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
    for marker in (
        "G07_CONTRACT=FROZEN",
        "G07_IMPLEMENTATION_AUTHORIZED=YES",
        "G07_RECENT_CAP=10",
        "G07_RECENT_STORAGE=XDG_STATE_ATOMIC_JSON_0600",
        "G07_RECENT_DURABILITY=ATOMIC_CONVENIENCE_NO_FSYNC",
        "G07_RECENT_JSON_SCHEMA=VERSION_1_PATHS_ONLY",
        "G07_RECENT_SESSION_RESTORE=FORBIDDEN",
        "G07_COPY_WRITER=EXISTING_GUARDED_FILE_WRITER_ONLY",
        "G07_COPY_BINDING_CHANGE=FORBIDDEN",
        "G07_COPY_SAVEPOINT_HISTORY_CHANGE=FORBIDDEN",
        "G07_VERSION_COPY_PATTERN=STEM_vNNNN_SUFFIX_MAX_PLUS_ONE",
        "G07_CHECK_NOW=STRONG_READ_ONLY_OBSERVATION",
        "G07_CHECK_NOW_ACCEPT_BASELINE=FORBIDDEN",
        "G07_CHECK_NOW_RELOAD=FORBIDDEN",
        "G07_STRONG_OBSERVER=SHARED_BY_LOADER_AND_PROPERTIES",
        "G07_STATISTICS=EXPLICIT_ON_DEMAND_ONLY",
        "G07_STATISTICS_WORKER_TIMER_CACHE=FORBIDDEN",
        "G07_DOCUMENT_AUTHORITY_COUNT=1",
        "G07_PHYSICAL_WRITER_AUTHORITY_COUNT=1",
        "G07_LIGHTWEIGHT_BUDGET_GATE=REQUIRED",
    ):
        if marker not in contract:
            fail(f"G07 contract marker missing: {marker}")
    for marker in (
        "G08_CONTRACT=FROZEN",
        "G08_BASELINE_COMMIT=7a3f49218dbabdbd6e47114a5fde2f4999f9c841",
        "G08_BASELINE_TREE=198164be38e77538b92f45d5d53fe4b0c1929955",
        "G08_IMPLEMENTATION=BUILT_NONCANDIDATE",
        "G08_DESKTOP_CANDIDATE=NOT_DECLARED",
        "G08_VALID_CANDIDATE_ATTEMPTS_CONSUMED=0/2",
        "G08_FILE_PRINT_GROUP=PAGE_SETUP,PRINT_PREVIEW,PRINT",
        "G08_PAGE_SETUP_PATH=XDG_CONFIG_HOME/graphium/page-setup.ini",
        "G08_PAGE_SETUP_SERIALIZATION=GTK_NATIVE_GtkPageSetup_FILE",
        "G08_PAGE_SETUP_MODE=0600",
        "G08_PAGE_SETUP_WRITE=COMPLETE_TEMP_FSYNC_ATOMIC_REPLACE",
        "G08_PAGE_SETUP_LOAD=FIRST_PRINT_FAMILY_ACTION_ONLY",
        "G08_PRINT_SETTINGS=PERSISTENCE_FORBIDDEN_PROCESS_MEMORY_ONLY",
        "G08_PRINT_OPERATION=FRESH_PER_PREVIEW_OR_PRINT",
        "G08_PRINT_OPERATION_ASYNC=GTK_NATIVE_ALLOW_ASYNC",
        "G08_PRINT_INFLIGHT_AUTHORITY=ONE_OPERATION_PER_WINDOW",
        "G08_PRINT_COMPLETION=GTK_DONE_SIGNAL_OR_SYNCHRONOUS_RUN_RESULT",
        "G08_PRINT_OVERLAP=REJECT_WHILE_INFLIGHT",
        "G08_PREVIEW=NATIVE_GTK_PREVIEW",
        "G08_CUSTOM_PREVIEW=FORBIDDEN",
        "G08_RENDERING=PANGO_CAIRO",
        "G08_PAGINATION=GTK_ASYNC_INCREMENTAL_PANGO_CHUNKS",
        "G08_BEGIN_PRINT_DOCUMENT_SCAN=FORBIDDEN",
        "G08_PAGINATION_SIGNAL=GTK_NATIVE_PAGINATE",
        "G08_PAGINATION_CHUNK_TARGET_CHARS=16384",
        "G08_PAGINATION_CHUNK_MAX_LOGICAL_LINES=64",
        "G08_PAGINATION_CHUNK_BOUNDARY=LOGICAL_LINE_ONLY",
        "G08_PAGINATION_GLOBAL_PANGO_LAYOUT=FORBIDDEN",
        "G08_INCREMENTAL_PAGINATION_REPAIR=BUILT_NONCANDIDATE",
        "G08_INCREMENTAL_PAGINATION_REQUALIFICATION=PENDING_T480",
        "G08_VISUAL_LINE_SPLIT_ACROSS_PAGES=FORBIDDEN",
        "G08_GTK_SOURCE_VIEW_DEPENDENCY=FORBIDDEN",
        "G08_PRINT_WORKER_THREAD_TIMER_QUEUE=FORBIDDEN",
        "G08_STARTUP_PAGE_SETUP_IO=ZERO",
        "G08_T480_PYGOBJECT_PRINT_BINDING_PROBE=REQUIRED_BEFORE_CANDIDATE",
        "G08_T480_PYGOBJECT_PRINT_BINDING_PROBE_STATUS=PENDING",
        "G08_LIGHTWEIGHT_BUDGET_GATE=REQUIRED",
    ):
        if marker not in contract:
            fail(f"G08 contract marker missing: {marker}")
    for marker in (
        "G09_CONTRACT=FROZEN",
        "G09_BASELINE_COMMIT=5d1c342eafbff8b4b38f0656e0dbc1fe315362b4",
        "G09_BASELINE_TREE=6535bf7d560ceaed3e31f407317fde0a8618ba47",
        "G09_IMPLEMENTATION=BUILT_NONCANDIDATE",
        "G09_DESKTOP_CANDIDATE=NOT_DECLARED",
        "G09_VALID_CANDIDATE_ATTEMPTS_CONSUMED=0/2",
        "G09_MENU=EDIT_TRANSFORM_TEXT_SUBMENU",
        "G09_TOP_LEVEL_FORMAT_MENU=FORBIDDEN",
        "G09_CHANGED_SPAN_CAP=50000",
        "G09_UNDO_GROUPS_PER_ACTUAL_TRANSFORM=1",
        "G09_OPEN_SAVE_IMPLICIT_TRANSFORM=FORBIDDEN",
        "G09_T480_PRE_CANDIDATE_QUALIFICATION=PENDING",
    ):
        if marker not in contract:
            fail(f"G09 contract marker missing: {marker}")
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
    print("G07_CONTRACT_MARKERS=PASS")
    print("G08_CONTRACT_MARKERS=PASS")
    print("G09_CONTRACT_MARKERS=PASS")


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
    verify_g07_architecture()
    verify_g08_architecture()
    verify_g09_architecture()
    verify_shortcuts()
    verify_evidence()
    verify_contracts()
    verify_text_integrity()
    run_tests()
    print("STRICT_GATES=PASS")
    print("GTK_DESKTOP_VALIDATION=PENDING_T480_PRE_CANDIDATE")
    print("G08_REGRESSION_AUTHORITY=PRESERVED")
    print("G09_TRUE_GTK_DESKTOP=PENDING_T480")
    print("G09_SHORTCUT_CINNAMON_AUDIT=PENDING_T480")
    print("G09_T480_PRE_CANDIDATE_QUALIFICATION=PENDING")
    print("FINAL_PHASE=G09_NONDESKTOP_IMPLEMENTATION_VERIFIED_T480_PRE_CANDIDATE_PENDING")


if __name__ == "__main__":
    main()
