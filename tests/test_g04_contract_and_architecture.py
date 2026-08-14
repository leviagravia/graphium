from __future__ import annotations

from pathlib import Path
import unittest

from graphium.application.commands import COMMANDS, FORBIDDEN_ACCELERATORS
from graphium.composition import describe_composition
from graphium.product import DESKTOP_APPLICATION_ID, VERSION, WORK_ITEM, WORK_ITEM_DESCRIPTION


ROOT = Path(__file__).resolve().parents[1]


class G04ContractArchitectureTests(unittest.TestCase):
    def test_published_g04_identity_is_retained_as_regression_authority(self):
        roadmap = (ROOT / "docs/canonical/GRAPHIUM_ROADMAP.md").read_text(encoding="utf-8")
        self.assertIn("283f1aa5352c2403ac9e0a945b87cc82cd08cff0", roadmap)
        self.assertIn("5e2aa256a47739c45f9c79f39a9685b5c6a454d6", roadmap)
        self.assertEqual(DESKTOP_APPLICATION_ID, "io.github.leviagravia.Graphium")
        self.assertTrue(WORK_ITEM.startswith("G"))
        self.assertTrue(VERSION.startswith("0.0."))
        self.assertTrue(WORK_ITEM_DESCRIPTION)

    def test_active_composition_uses_delta_history_not_snapshot_history(self):
        descriptor = describe_composition()
        self.assertEqual(descriptor.native_history_storage, "delta")
        text = (ROOT / "graphium/composition.py").read_text(encoding="utf-8")
        self.assertIn("DeltaHistory()", text)
        self.assertNotIn("TextHistory()", text)

    def test_native_window_has_no_time_based_undo_authority(self):
        text = (ROOT / "graphium/adapters/gtk/window.py").read_text(encoding="utf-8")
        for forbidden in (
            "_NATIVE_COMMIT_DELAY_MS",
            "timeout_add",
            "timeout_add_seconds",
            "commit_native_group_later",
        ):
            self.assertNotIn(forbidden, text)
        self.assertIn('"begin-user-action"', text)
        self.assertIn('"end-user-action"', text)
        self.assertIn('"insert-text"', text)
        self.assertIn('"delete-range"', text)

    def test_application_is_non_unique_one_window_per_process(self):
        text = (ROOT / "graphium/adapters/gtk/application.py").read_text(encoding="utf-8")
        self.assertIn("Gio.ApplicationFlags.NON_UNIQUE", text)
        self.assertIn("_spawn_additional_files", text)
        self.assertNotIn("get_active_window", text)
        self.assertNotIn("get_windows()[0]", text)


    def test_pathological_line_guard_is_content_neutral_and_precedes_gtk_install(self):
        renderability = (ROOT / "graphium/application/renderability.py").read_text(encoding="utf-8")
        lifecycle = (ROOT / "graphium/application/file_lifecycle.py").read_text(encoding="utf-8")
        window = (ROOT / "graphium/adapters/gtk/window.py").read_text(encoding="utf-8")
        self.assertIn("MAX_INTERACTIVE_LINE_CHARS = 20_000", renderability)
        self.assertIn("ensure_interactive_text_renderable(result.text)", lifecycle)
        self.assertLess(
            lifecycle.index("ensure_interactive_text_renderable(result.text)"),
            lifecycle.index("self.editor.initialize_open(result)"),
        )
        self.assertIn('connect("insert-text", self._on_insert_text_guard)', window)
        self.assertIn('connect("delete-range", self._on_delete_range_guard)', window)
        for forbidden in ("HUGE LINE TRUNCATED", "truncate", "insert line break", "auto-wrap"):
            self.assertNotIn(forbidden, renderability)

    def test_shell_is_plain_textview_and_toolbar_absent(self):
        runtime = "\n".join(
            p.read_text(encoding="utf-8")
            for p in sorted((ROOT / "graphium").rglob("*.py"))
        )
        self.assertIn("Gtk.TextView", runtime)
        self.assertNotIn("GtkSourceView", runtime)
        self.assertNotIn("Gtk.Toolbar", runtime)

    def test_command_surface_is_small_classic_and_help_is_lazy(self):
        actual = [(c.menu, c.action) for c in COMMANDS]
        required_g04 = [
            ("File", "new"), ("File", "open"), ("File", "save"),
            ("File", "save-as"), ("File", "quit"),
            ("Edit", "undo"), ("Edit", "redo"), ("Edit", "cut"),
            ("Edit", "copy"), ("Edit", "paste"), ("Edit", "delete"),
            ("Edit", "select-all"),
            ("Help", "user-guide"), ("Help", "keyboard-shortcuts"),
            ("Help", "about"),
        ]
        for item in required_g04:
            self.assertIn(item, actual)
        dialogs = (ROOT / "graphium/adapters/gtk/dialogs.py").read_text(encoding="utf-8")
        self.assertIn("def show_text_document", dialogs)
        self.assertIn("Path(path).read_text", dialogs)

    def test_help_documents_exist_and_track_current_scope(self):
        guide = (ROOT / "docs/user/GRAPHIUM_USER_GUIDE.txt").read_text(encoding="utf-8")
        keys = (ROOT / "docs/user/GRAPHIUM_KEYBOARD_SHORTCUTS.txt").read_text(encoding="utf-8")
        for marker in (
            "one process owns one window and one active document",
            "does not silently trim spaces",
            "insertion/deletion deltas",
            "FIRST_VISIBLE",
            "FIRST_EDITABLE",
        ):
            self.assertIn(marker, guide)
        self.assertIn("Ctrl+Alt+L", keys)

    def test_known_linux_mint_collision_is_forbidden(self):
        self.assertIn("<Ctrl><Alt>L", FORBIDDEN_ACCELERATORS)
        accelerators = {c.accelerator for c in COMMANDS if c.accelerator}
        self.assertNotIn("<Ctrl><Alt>L", accelerators)

    def test_performance_protocol_separates_comparable_metrics(self):
        exact = (ROOT / "tools/g04_performance.py").read_text(encoding="utf-8")
        common = (ROOT / "tools/g04_comparator_proxy.py").read_text(encoding="utf-8")
        window = (ROOT / "graphium/adapters/gtk/window.py").read_text(encoding="utf-8")
        self.assertIn("os.pipe()", exact)
        self.assertIn("pass_fds=(wfd,)", exact)
        self.assertIn("GRAPHIUM_BENCHMARK_READY_FD", exact)
        self.assertNotIn("READY_FILE", exact)
        self.assertIn("os.write(fd, payload)", window)
        self.assertIn('"cross_product_comparable": False', exact)
        self.assertIn('"cross_product_comparable": True', common)
        self.assertIn('"Graphium"', common)
        self.assertIn('("Leafpad", "leafpad")', common)
        self.assertIn('("L3afpad", "l3afpad")', common)
        self.assertIn('("Mousepad", "mousepad")', common)
        self.assertIn('("FeatherPad", "featherpad")', common)

    def test_canonical_documents_record_rebuild_contract(self):
        contract = (ROOT / "docs/canonical/GRAPHIUM_PRODUCT_ARCHITECTURE_CONTRACT.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "docs/canonical/GRAPHIUM_ROADMAP.md").read_text(encoding="utf-8")
        mo = (ROOT / "docs/canonical/GRAPHIUM_MEMORIA_OPERATIVA.txt").read_text(encoding="utf-8")
        for marker in (
            "G04_NATIVE_HISTORY=DELTA_BASED",
            "G04_NATIVE_EDIT_TIMER_AUTHORITY=FORBIDDEN",
            "G04_APPLICATION_TOPOLOGY=ONE_PROCESS_ONE_WINDOW_ONE_DOCUMENT",
            "G04_APPLICATION_UNIQUENESS=NON_UNIQUE",
            "G04_PERFORMANCE_COMMON_METRIC=FIRST_VISIBLE",
            "G04_PERFORMANCE_EXACT_INTERNAL_METRIC=FIRST_EDITABLE",
        ):
            self.assertIn(marker, contract)
        self.assertIn("Native Edit Integration Hardening", roadmap)
        self.assertIn("CONFIRMATION-BIAS COUNTERMEASURE", mo)
        self.assertIn("LIGHTWEIGHT TRUST EDITOR", mo)
        self.assertIn("FeatherPad", roadmap)
        self.assertIn("PERMANENT_COMPARATORS=Leafpad,L3afpad,Mousepad,FeatherPad", contract)


if __name__ == "__main__":
    unittest.main()
