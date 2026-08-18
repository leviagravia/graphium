from __future__ import annotations
from pathlib import Path
import unittest

from graphium.application.commands import COMMANDS
from graphium.composition import describe_composition
from graphium.product import VERSION, WORK_ITEM, WORK_ITEM_DESCRIPTION

ROOT=Path(__file__).resolve().parents[1]


class G05ContractArchitectureTests(unittest.TestCase):
    def test_published_g05_identity_is_retained_as_regression_authority(self):
        roadmap=(ROOT/"docs/canonical/GRAPHIUM_ROADMAP.md").read_text(encoding="utf-8")
        self.assertIn("a9083daf22ab23cf6cd20841be643510e35d700d", roadmap)
        self.assertIn("12d55249263e006cc68fa304f3c3cc2a9ef73acb", roadmap)
        self.assertTrue(WORK_ITEM.startswith("G"))
        self.assertTrue(VERSION.startswith("0.0."))
        self.assertTrue(WORK_ITEM_DESCRIPTION)

    def test_search_commands_are_product_owned_and_exact(self):
        search=[(c.action,c.label,c.accelerator) for c in COMMANDS if c.menu=="Search"]
        self.assertEqual(search,[
            ("find","Find…","<Ctrl>F"),
            ("find-next","Find Next","F3"),
            ("find-previous","Find Previous","<Shift>F3"),
            ("replace","Replace…","<Ctrl>H"),
            ("go-to-line","Go to Line…","<Ctrl>G"),
        ])

    def test_search_authority_is_gtk_free_and_composed_once(self):
        search=(ROOT/"graphium/application/search.py").read_text(encoding="utf-8")
        domain=(ROOT/"graphium/domain/text_search.py").read_text(encoding="utf-8")
        composition=(ROOT/"graphium/composition.py").read_text(encoding="utf-8")
        self.assertNotIn("import gi",search); self.assertNotIn("import gi",domain)
        self.assertEqual(composition.count("SearchController()"),1)
        self.assertEqual(describe_composition().document_authority_count,1)

    def test_search_bar_is_lazy_and_background_search_absent(self):
        window=(ROOT/"graphium/adapters/gtk/window.py").read_text(encoding="utf-8")
        self.assertIn("self._search_bar: Gtk.SearchBar | None = None",window)
        self.assertIn("def _ensure_search_bar",window)
        self.assertIn("Gtk.SearchBar()",window)
        self.assertIn("set_show_close_button(True)",window)
        self.assertNotIn("handle_event(",window)
        for forbidden in ("threading", "Thread(", "timeout_add", "background_search", "search_index"):
            self.assertNotIn(forbidden,window)

    def test_replace_uses_prevalidated_delta_transaction_not_legacy_snapshot(self):
        search=(ROOT/"graphium/application/search.py").read_text(encoding="utf-8")
        native=(ROOT/"graphium/application/native_editor.py").read_text(encoding="utf-8")
        window=(ROOT/"graphium/adapters/gtk/window.py").read_text(encoding="utf-8")
        self.assertIn("ensure_interactive_text_renderable(final_text)",search)
        self.assertIn("apply_prevalidated_programmatic_group",native)
        self.assertIn("apply_prevalidated_programmatic_group",window)
        self.assertIn("bounded Undo payload",native)
        self.assertNotIn("EditorTransactionController",search+window)

    def test_replace_all_operations_are_original_match_frozen_and_descending(self):
        search=(ROOT/"graphium/application/search.py").read_text(encoding="utf-8")
        self.assertIn("for match in reversed(matches)",search)
        self.assertIn("matches = find_all(",search)
        self.assertIn("max_matches=MAX_REPLACE_ALL_MATCHES",search)
        self.assertIn("_build_final_text(source_text, matches",search)

    def test_g04_normal_edit_guards_remain_connected(self):
        window=(ROOT/"graphium/adapters/gtk/window.py").read_text(encoding="utf-8")
        self.assertIn('connect("insert-text", self._on_insert_text_guard)',window)
        self.assertIn('connect("delete-range", self._on_delete_range_guard)',window)
        self.assertNotIn("disable_render",window)
        self.assertNotIn("bypass_render",window)

    def test_canonical_g05_contract_and_lightweight_budget_are_frozen(self):
        contract=(ROOT/"docs/canonical/GRAPHIUM_PRODUCT_ARCHITECTURE_CONTRACT.md").read_text(encoding="utf-8")
        roadmap=(ROOT/"docs/canonical/GRAPHIUM_ROADMAP.md").read_text(encoding="utf-8")
        mo=(ROOT/"docs/canonical/GRAPHIUM_MEMORIA_OPERATIVA.txt").read_text(encoding="utf-8")
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
            self.assertIn(marker,contract)
        self.assertIn("CLOSED / CERTIFIED / PUBLISHED",roadmap)
        self.assertIn("G05_IMPLEMENTATION_AUTHORIZED=YES",mo)

    def test_user_help_tracks_search_scope_and_shortcuts(self):
        guide=(ROOT/"docs/user/GRAPHIUM_USER_GUIDE.txt").read_text(encoding="utf-8")
        keys=(ROOT/"docs/user/GRAPHIUM_KEYBOARD_SHORTCUTS.txt").read_text(encoding="utf-8")
        for marker in ("SEARCH AND REPLACE","Unicode casefold","Replace All","no startup scan"):
            self.assertIn(marker,guide)
        for marker in ("Ctrl+F", "F3", "Shift+F3", "Ctrl+H", "Ctrl+G"):
            self.assertIn(marker,keys)

    def test_evidence_source_and_mature_audits_exist(self):
        for rel in ("evidence/G05_SOURCE_AUDIT.txt","evidence/G05_MATURE_SOURCE_AUDIT.txt"):
            self.assertTrue((ROOT/rel).is_file(),rel)


if __name__=="__main__": unittest.main()
