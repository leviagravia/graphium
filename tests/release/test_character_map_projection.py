from __future__ import annotations

import ast
import unittest

from tests.release._common import ROOT


class CharacterMapProjectionTests(unittest.TestCase):
    def test_character_map_is_large_readable_and_modeless(self):
        source = (ROOT / "graphium/adapters/gtk/character_map.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertIn("PARENT_SIZE_RATIO = 0.75", source)
        self.assertIn("MIN_WIDTH = 480", source)
        self.assertIn("MIN_HEIGHT = 360", source)
        self.assertIn("target_width, target_height = self._initial_size_for_parent(parent)", source)
        self.assertIn("parent_width * cls.PARENT_SIZE_RATIO", source)
        self.assertIn("parent_height * cls.PARENT_SIZE_RATIO", source)
        self.assertIn("GLYPH_CELL_SIZE = 76", source)
        self.assertIn("GLYPH_FONT_PT = 30", source)
        self.assertIn("PREVIEW_FONT_PT = 88", source)
        self.assertIn('modal=False', source)
        self.assertIn('set_resizable(True)', source)
        self.assertIn('set_activate_on_single_click(False)', source)
        self.assertIn('child-activated', source)
        self.assertIn('self.connect("destroy", self._on_destroy)', source)
        self.assertIn('GLib.source_remove(source_id)', source)
        self.assertIn('self._css_provider.load_from_data(css.encode("utf-8"))', source)
        self.assertNotIn(') % (self.GLYPH_FONT_PT, self.PREVIEW_FONT_PT)\n        .encode("utf-8")', source)
        self.assertIsInstance(tree, ast.Module)

    def test_character_map_has_no_network_subprocess_filesystem_or_new_dependency_boundary(self):
        source = (ROOT / "graphium/adapters/gtk/character_map.py").read_text(encoding="utf-8")
        model = (ROOT / "graphium/application/character_map.py").read_text(encoding="utf-8")
        joined = source + "\n" + model
        for forbidden in (
            "subprocess", "requests", "httpx", "aiohttp", "socket", "pathlib", "open(",
            "GuardedFileWriter", "DocumentSave", "GtkSource", "gucharmap", "libgucharmap",
        ):
            self.assertNotIn(forbidden, joined)
        self.assertIn("import unicodedata", model)

    def test_unicode_catalog_is_bounded_not_full_scalar_sweep(self):
        source = (ROOT / "graphium/application/character_map.py").read_text(encoding="utf-8")
        self.assertNotIn("range(0x110000", source)
        self.assertNotIn("range(0, 0x110000", source)
        self.assertIn("PAGE_SIZE = 96", source)
        self.assertIn("CHARACTER_GROUPS", source)

    def test_window_wires_single_dialog_and_native_buffer_user_action(self):
        source = (ROOT / "graphium/adapters/gtk/window.py").read_text(encoding="utf-8")
        for required in (
            '"character-map": self._action_character_map',
            "def _action_character_map",
            "CharacterMapDialog(self, on_insert=self._insert_character_from_map)",
            "self.buffer.begin_user_action()",
            "self.buffer.insert_at_cursor(char)",
            "ensure_insert_renderable",
        ):
            self.assertIn(required, source)
        self.assertNotIn("CharacterMapWriter", source)

    def test_user_guide_documents_readability_and_insert_semantics(self):
        guide = (ROOT / "docs/user/GRAPHIUM_USER_GUIDE.txt").read_text(encoding="utf-8")
        self.assertIn("Edit -> Character Map…", guide)
        self.assertIn("glyph cells stay large", guide)
        self.assertIn("Unicode name", guide)
        self.assertIn("U+03A9", guide)
        self.assertIn("normal Undo step", guide)


if __name__ == "__main__":
    unittest.main()
