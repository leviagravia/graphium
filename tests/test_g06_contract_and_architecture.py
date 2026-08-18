from __future__ import annotations

from pathlib import Path
import unittest

from graphium.application.commands import COMMANDS
from graphium.product import VERSION, WORK_ITEM, WORK_ITEM_DESCRIPTION

ROOT = Path(__file__).resolve().parents[1]


class G06ContractArchitectureTests(unittest.TestCase):
    def test_published_g06_identity_is_retained_as_regression_authority(self):
        roadmap = (ROOT / "docs/canonical/GRAPHIUM_ROADMAP.md").read_text(encoding="utf-8")
        self.assertIn("aae14ef000ea44674cb9bbb7b3a87e3af00c0b18", roadmap)
        self.assertIn("c2b372082cf44280f9717045578822e7b92bef12", roadmap)
        self.assertTrue(WORK_ITEM.startswith("G"))
        self.assertTrue(VERSION.startswith("0.0."))
        self.assertTrue(WORK_ITEM_DESCRIPTION)

    def test_view_commands_are_exact_and_toolbar_appearance_are_absent(self):
        view = [(c.action, c.label, c.accelerator, c.stateful) for c in COMMANDS if c.menu == "View"]
        self.assertEqual(view, [
            ("status-bar", "Status Bar", None, True),
            ("line-numbers", "Line Numbers", None, True),
            ("word-wrap", "Word Wrap", None, True),
            ("font", "Font…", None, False),
            ("zoom-in", "Zoom In", "<Ctrl>plus", False),
            ("zoom-out", "Zoom Out", "<Ctrl>minus", False),
            ("zoom-reset", "Reset Zoom", "<Ctrl>0", False),
            ("full-screen", "Full Screen", "F11", True),
        ])
        actions = {c.action for c in COMMANDS}
        self.assertNotIn("toolbar", actions)
        self.assertNotIn("appearance", actions)

    def test_settings_authority_is_gtk_free_composed_once_and_xdg_local(self):
        application = (ROOT / "graphium/application/view_settings.py").read_text(encoding="utf-8")
        store = (ROOT / "graphium/infrastructure/view_settings_store.py").read_text(encoding="utf-8")
        composition = (ROOT / "graphium/composition.py").read_text(encoding="utf-8")
        self.assertNotIn("import gi", application + store)
        self.assertEqual(composition.count("ViewSettingsController("), 1)
        self.assertIn('resolve_xdg_paths().config / "view.json"', composition)
        self.assertIn("os.replace(temp_name, self.path)", store)
        self.assertIn("os.fsync", store)
        for forbidden in ("threading", "Thread(", "watch", "monitor", "sqlite"):
            self.assertNotIn(forbidden, application + store)

    def test_line_numbers_use_native_textview_left_border_and_visible_lines_only(self):
        view = (ROOT / "graphium/adapters/gtk/editor_view.py").read_text(encoding="utf-8")
        self.assertIn("class GraphiumTextView(Gtk.TextView)", view)
        self.assertIn("Gtk.TextWindowType.LEFT", view)
        self.assertIn("get_visible_rect()", view)
        self.assertIn("get_line_at_y(visible.y)", view)
        self.assertIn("get_line_yrange(it)", view)
        self.assertIn("it.forward_line()", view)
        self.assertNotIn('gi.require_version("GtkSourceView"', view)
        self.assertNotIn("from gi.repository import GtkSourceView", view)
        for forbidden in ("threading", "Thread(", "timeout_add", "line_index", "cache"):
            self.assertNotIn(forbidden, view)

    def test_compact_status_is_event_driven_and_does_not_capture_document(self):
        window = (ROOT / "graphium/adapters/gtk/window.py").read_text(encoding="utf-8")
        status = (ROOT / "graphium/application/view_status.py").read_text(encoding="utf-8")
        self.assertIn('connect("notify::cursor-position", self._on_cursor_position_changed)', window)
        self.assertIn("project_compact_status", window)
        refresh = window[window.index("    def _refresh_status"):window.index("    def _action_new")]
        for forbidden in ("get_text(", "capture_full", "get_char_count", "word"):
            self.assertNotIn(forbidden, refresh)
        self.assertNotIn("import gi", status)

    def test_font_zoom_and_fullscreen_respect_persistent_transient_split(self):
        window = (ROOT / "graphium/adapters/gtk/window.py").read_text(encoding="utf-8")
        view = (ROOT / "graphium/adapters/gtk/editor_view.py").read_text(encoding="utf-8")
        self.assertIn("choose_font", window)
        self.assertIn("font_family=family", window)
        self.assertIn("font_size_points=size_points", window)
        self.assertIn("Gtk.CssProvider()", view)
        self.assertNotIn("override_font", view + window)
        self.assertIn("reset_zoom", view)
        self.assertIn("self.fullscreen()", window)
        # Zoom/fullscreen never enter persistent ViewSettings.
        from graphium.application.view_settings import ViewSettings
        fields = set(ViewSettings.__dataclass_fields__)
        self.assertNotIn("zoom_percent", fields)
        self.assertNotIn("fullscreen", fields)

    def test_canonical_g06_contract_markers_are_frozen(self):
        contract = (ROOT / "docs/canonical/GRAPHIUM_PRODUCT_ARCHITECTURE_CONTRACT.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "docs/canonical/GRAPHIUM_ROADMAP.md").read_text(encoding="utf-8")
        mo = (ROOT / "docs/canonical/GRAPHIUM_MEMORIA_OPERATIVA.txt").read_text(encoding="utf-8")
        for marker in (
            "G06_CONTRACT=FROZEN",
            "G06_TOOLBAR=REJECT_V1",
            "G06_WORD_WRAP=GTK_WORD_CHAR",
            "G06_LINE_NUMBERS=GTK_TEXTVIEW_LEFT_BORDER_WINDOW",
            "G06_LINE_NUMBER_DRAW_SCOPE=VISIBLE_LOGICAL_LINES_ONLY",
            "G06_STATUS_FIELDS=LINE_COLUMN,ENCODING_EOL,SAVED_MODIFIED",
            "G06_FONT=PERSISTENT_FAMILY_SIZE_VIA_CSS_PROVIDER",
            "G06_ZOOM=TRANSIENT_RELATIVE_TO_BASE_FONT",
            "G06_SETTINGS_BACKGROUND_WRITE=FORBIDDEN",
        ):
            self.assertIn(marker, contract)
        self.assertIn("CLOSED / CERTIFIED / PUBLISHED", roadmap)
        self.assertIn("G06_LINE_NUMBERS=ADOPT", mo)
        self.assertIn("a9083daf22ab23cf6cd20841be643510e35d700d", roadmap)

    def test_user_help_tracks_view_scope_and_shortcuts(self):
        guide = (ROOT / "docs/user/GRAPHIUM_USER_GUIDE.txt").read_text(encoding="utf-8")
        keys = (ROOT / "docs/user/GRAPHIUM_KEYBOARD_SHORTCUTS.txt").read_text(encoding="utf-8")
        for marker in ("VIEW AND COMPACT STATUS", "Line Numbers", "WORD_CHAR", "Toolbar", "100%"):
            self.assertIn(marker, guide)
        for marker in ("Ctrl++", "Ctrl+-", "Ctrl+0", "F11"):
            self.assertIn(marker, keys)


if __name__ == "__main__":
    unittest.main()
