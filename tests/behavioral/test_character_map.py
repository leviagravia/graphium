from __future__ import annotations

import unittest

from graphium.application.character_map import (
    ALL_GROUP_KEY,
    CHARACTER_GROUPS,
    PAGE_SIZE,
    iter_entries,
    page_count,
    page_slice,
    search_entries,
)
from graphium.application.commands import COMMANDS, accelerator_map


class CharacterMapModelTests(unittest.TestCase):
    def test_command_is_one_native_edit_command_without_accelerator(self):
        matches = [c for c in COMMANDS if c.action == "character-map"]
        self.assertEqual(len(matches), 1)
        command = matches[0]
        self.assertEqual((command.label, command.menu, command.accelerator), ("Character Map…", "Edit", None))
        self.assertNotIn("character-map", accelerator_map())

    def test_groups_are_bounded_unique_and_include_requested_core_scripts(self):
        keys = [group.key for group in CHARACTER_GROUPS]
        self.assertEqual(len(keys), len(set(keys)))
        for key in ("latin", "greek", "diacritics", "cyrillic", "hebrew", "arabic", "punctuation", "currency", "arrows", "mathematics", "symbols"):
            self.assertIn(key, keys)
        for group in CHARACTER_GROUPS:
            self.assertTrue(group.ranges)
            for start, end in group.ranges:
                self.assertLessEqual(0, start)
                self.assertLessEqual(start, end)
                self.assertLessEqual(end, 0x10FFFF)

    def test_greek_search_supports_name_literal_and_uplus(self):
        by_name = search_entries("greek", "capital omega")
        self.assertTrue(any(e.char == "Ω" for e in by_name))
        self.assertEqual([e.char for e in search_entries("greek", "Ω")], ["Ω"])
        self.assertEqual([e.char for e in search_entries("greek", "U+03A9")], ["Ω"])
        self.assertEqual([e.char for e in search_entries("greek", "0x03a9")], ["Ω"])

    def test_unicode_name_search_is_token_based_not_order_dependent_substring_only(self):
        matches = search_entries("currency", "euro sign")
        self.assertIn("€", [entry.char for entry in matches])
        matches_reordered = search_entries("currency", "sign euro")
        self.assertEqual(
            [entry.codepoint for entry in matches],
            [entry.codepoint for entry in matches_reordered],
        )


    def test_combining_marks_use_dotted_circle_only_for_display(self):
        entries = search_entries("diacritics", "U+0301")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].char, "\u0301")
        self.assertEqual(entries[0].display_text, "◌\u0301")

    def test_all_group_deduplicates_overlapping_ranges(self):
        entries = tuple(iter_entries(ALL_GROUP_KEY))
        codepoints = [entry.codepoint for entry in entries]
        self.assertEqual(len(codepoints), len(set(codepoints)))
        self.assertIn(ord("A"), codepoints)
        self.assertIn(ord("Ω"), codepoints)
        self.assertIn(ord("→"), codepoints)

    def test_unassigned_controls_and_whitespace_are_not_cells(self):
        latin = tuple(iter_entries("latin"))
        chars = {entry.char for entry in latin}
        self.assertNotIn("\n", chars)
        self.assertNotIn(" ", chars)
        self.assertIn("A", chars)
        self.assertIn("é", chars)

    def test_pagination_is_bounded_and_stable(self):
        entries = search_entries("symbols", "")
        self.assertEqual(PAGE_SIZE, 96)
        self.assertGreater(len(entries), PAGE_SIZE)
        first = page_slice(entries, 0)
        second = page_slice(entries, 1)
        self.assertLessEqual(len(first), PAGE_SIZE)
        self.assertLessEqual(len(second), PAGE_SIZE)
        self.assertFalse({e.codepoint for e in first} & {e.codepoint for e in second})
        self.assertEqual(page_count(0), 1)
        self.assertEqual(page_count(PAGE_SIZE), 1)
        self.assertEqual(page_count(PAGE_SIZE + 1), 2)

    def test_unknown_group_fails_closed(self):
        with self.assertRaises(ValueError):
            tuple(iter_entries("not-a-group"))


if __name__ == "__main__":
    unittest.main()
