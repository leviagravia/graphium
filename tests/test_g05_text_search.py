from __future__ import annotations
import unittest

from graphium.domain.text_search import (
    SearchInputError,
    SearchScaleError,
    find_all,
    find_next,
    find_previous,
    is_exact_match,
    validate_query,
    validate_replacement,
)


class G05TextSearchTests(unittest.TestCase):
    def test_single_line_contract(self):
        self.assertEqual(validate_query("needle"), "needle")
        self.assertEqual(validate_replacement(""), "")
        with self.assertRaises(SearchInputError): validate_query("")
        with self.assertRaises(SearchInputError): validate_query("a\nb")
        with self.assertRaises(SearchInputError): validate_replacement("a\rb")

    def test_case_sensitive_literal_non_overlapping(self):
        self.assertEqual(
            [(m.start, m.end) for m in find_all("aaaa", "aa", match_case=True)],
            [(0, 2), (2, 4)],
        )
        self.assertEqual(find_all("Ab aB", "ab", match_case=True), ())

    def test_unicode_casefold_maps_back_to_exact_source_offsets(self):
        matches = find_all("Straße STRASSE", "strasse", match_case=False)
        self.assertEqual([(m.start, m.end) for m in matches], [(0, 6), (7, 14)])
        self.assertTrue(is_exact_match("Straße", "STRASSE", 0, 6, match_case=False))

    def test_casefold_does_not_match_inside_one_source_character_expansion(self):
        self.assertEqual(find_all("ß", "s", match_case=False), ())
        self.assertEqual([(m.start, m.end) for m in find_all("ß", "ss", match_case=False)], [(0, 1)])

    def test_unicode_multibyte_offsets_are_character_offsets(self):
        text = "α🙂βeta βETA"
        matches = find_all(text, "βeta", match_case=False)
        self.assertEqual([(m.start, m.end) for m in matches], [(2, 6), (7, 11)])

    def test_forward_and_backward_wrap_once(self):
        text = "one two one"
        self.assertEqual((find_next(text, "one", 4, match_case=True).match.start), 8)
        wrapped = find_next(text, "one", len(text), match_case=True)
        self.assertTrue(wrapped.wrapped); self.assertEqual(wrapped.match.start, 0)
        self.assertEqual(find_previous(text, "one", 8, match_case=True).match.start, 0)
        wrapped = find_previous(text, "one", 0, match_case=True)
        self.assertTrue(wrapped.wrapped); self.assertEqual(wrapped.match.start, 8)

    def test_no_match_does_not_claim_wrap(self):
        result = find_next("abc", "z", 0)
        self.assertIsNone(result.match); self.assertFalse(result.wrapped)

    def test_navigation_does_not_inherit_replace_all_nonoverlap_grid(self):
        # Cursor navigation starts at the actual cursor boundary. Replace All separately
        # freezes a non-overlapping source match set.
        m=find_next("aaaa", "aa", 1, match_case=True).match
        self.assertEqual((m.start, m.end), (1, 3))

    def test_unicode_casefold_is_line_bounded_and_does_not_cross_newline(self):
        text = "Straße\nSTRASSE\nneedle"
        first = find_next(text, "strasse", 0, match_case=False)
        self.assertEqual((first.match.start, first.match.end), (0, 6))
        second = find_next(text, "strasse", first.match.end, match_case=False)
        self.assertEqual((second.match.start, second.match.end), (7, 14))
        self.assertEqual(find_all("s\ns", "ss", match_case=False), ())

    def test_find_all_match_cap_fails_closed_before_unbounded_materialization(self):
        with self.assertRaises(SearchScaleError):
            find_all("a a a", "a", match_case=True, max_matches=2)
        self.assertEqual(
            [(m.start, m.end) for m in find_all("a a", "a", match_case=True, max_matches=2)],
            [(0, 1), (2, 3)],
        )

    def test_exact_match_checks_only_selected_source_range(self):
        self.assertTrue(is_exact_match("Straße elsewhere", "STRASSE", 0, 6, match_case=False))
        self.assertFalse(is_exact_match("ß", "s", 0, 1, match_case=False))
        self.assertFalse(is_exact_match("a\nb", "ab", 0, 3, match_case=False))


if __name__ == "__main__": unittest.main()
