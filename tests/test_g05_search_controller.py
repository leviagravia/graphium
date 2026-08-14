from __future__ import annotations
import unittest
from unittest.mock import patch

from graphium.application.renderability import InteractiveRenderabilityError, MAX_INTERACTIVE_LINE_CHARS
from graphium.application.search import MAX_REPLACE_ALL_MATCHES, SearchController
from graphium.domain.edit_history import EditKind, ViewState
from graphium.domain.text_search import SearchScaleError


class G05SearchControllerTests(unittest.TestCase):
    def test_config_is_small_and_single_line(self):
        c=SearchController(); c.configure(query="Alpha", replacement="beta", match_case=True)
        self.assertEqual(c.query,"Alpha"); self.assertEqual(c.replacement,"beta"); self.assertTrue(c.match_case)

    def test_replace_all_freezes_original_matches_and_does_not_cascade(self):
        c=SearchController(); c.configure(query="a", replacement="aa", match_case=True)
        plan=c.build_replace_all_plan(source_text="a a", source_state_id=7, before_view=ViewState(3,3))
        self.assertEqual(plan.final_text,"aa aa")
        self.assertEqual(plan.changed_count,2)
        self.assertEqual([(o.kind,o.offset,o.text) for o in plan.operations], [
            (EditKind.DELETE,2,"a"),(EditKind.INSERT,2,"aa"),
            (EditKind.DELETE,0,"a"),(EditKind.INSERT,0,"aa"),
        ])

    def test_replace_all_casefold_preserves_exact_original_ranges(self):
        c=SearchController(); c.configure(query="STRASSE", replacement="X", match_case=False)
        plan=c.build_replace_all_plan(source_text="Straße STRASSE", source_state_id=3, before_view=ViewState(14,14))
        self.assertEqual(plan.final_text,"X X")
        self.assertEqual(plan.changed_count,2)
        self.assertEqual(plan.target_view,ViewState(3,3))

    def test_replace_all_zero_effective_changes_is_noop(self):
        c=SearchController(); c.configure(query="x", replacement="x", match_case=True)
        plan=c.build_replace_all_plan(source_text="x x", source_state_id=2, before_view=ViewState(1,1))
        self.assertFalse(plan.changed); self.assertEqual(plan.operations,()); self.assertEqual(plan.final_text,"x x")

    def test_replace_all_empty_replacement(self):
        c=SearchController(); c.configure(query="xx", replacement="", match_case=True)
        plan=c.build_replace_all_plan(source_text="axx bxx", source_state_id=2, before_view=ViewState(7,7))
        self.assertEqual(plan.final_text,"a b"); self.assertEqual(plan.changed_count,2)
        self.assertTrue(all(o.kind is EditKind.DELETE for o in plan.operations))

    def test_replace_all_preflights_pathological_final_line(self):
        source="x"*(MAX_INTERACTIVE_LINE_CHARS-1)
        c=SearchController(); c.configure(query="x", replacement="xx", match_case=True)
        with self.assertRaises(InteractiveRenderabilityError):
            c.build_replace_all_plan(source_text=source, source_state_id=1, before_view=ViewState())

    def test_replace_one_acquires_next_when_selection_is_not_match(self):
        c=SearchController(); c.configure(query="one", replacement="X", match_case=True)
        plan=c.build_replace_one_plan(
            source_text="zero one two one", source_state_id=5, before_view=ViewState(0,0),
            selection_start=0, selection_end=0,
        )
        self.assertEqual(plan.final_text,"zero X two one")
        self.assertEqual(plan.changed_count,1)
        # Next occurrence is selected after replacement.
        self.assertNotEqual(plan.target_view.insert_offset, plan.target_view.selection_bound_offset)

    def test_replace_one_exact_selection_is_fast_path(self):
        c=SearchController(); c.configure(query="one", replacement="1", match_case=True)
        plan=c.build_replace_one_plan(
            source_text="one two", source_state_id=4, before_view=ViewState(3,0),
            selection_start=0, selection_end=3,
        )
        self.assertEqual(plan.final_text,"1 two")
        self.assertEqual(plan.operations[0].offset,0)

    def test_replace_one_no_match_returns_none(self):
        c=SearchController(); c.configure(query="z", replacement="x")
        self.assertIsNone(c.build_replace_one_plan(
            source_text="abc", source_state_id=1, before_view=ViewState(), selection_start=0, selection_end=0
        ))

    def test_replace_all_match_count_is_bounded_before_plan_materialization(self):
        c=SearchController(); c.configure(query="a", replacement="b", match_case=True)
        source="a "*(MAX_REPLACE_ALL_MATCHES+1)
        with self.assertRaises(SearchScaleError):
            c.build_replace_all_plan(source_text=source, source_state_id=1, before_view=ViewState())

    def test_replace_all_default_undo_payload_is_preflighted_before_final_text(self):
        c=SearchController(); c.configure(query="a", replacement="BBBB", match_case=True)
        with patch("graphium.application.search.DEFAULT_MAX_HISTORY_PAYLOAD_CHARS", 4):
            with self.assertRaises(SearchScaleError):
                c.build_replace_all_plan(source_text="a\na", source_state_id=1, before_view=ViewState())

    def test_case_sensitive_identical_replace_all_is_zero_cost_noop_even_when_dense(self):
        c=SearchController(); c.configure(query="a", replacement="a", match_case=True)
        source="a"*(MAX_REPLACE_ALL_MATCHES+100)
        plan=c.build_replace_all_plan(source_text=source, source_state_id=1, before_view=ViewState(5,5))
        self.assertFalse(plan.changed); self.assertEqual(plan.operations,()); self.assertEqual(plan.target_view,ViewState(5,5))


if __name__ == "__main__": unittest.main()
