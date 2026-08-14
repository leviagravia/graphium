from __future__ import annotations

import unittest

from graphium.domain.history import HistoryState, TextHistory


class G02HistoryTests(unittest.TestCase):
    def test_state_ids_are_positive_monotonic_and_never_reused_after_branch(self):
        history = TextHistory()
        a = history.reset(HistoryState("A", 1, 1))
        history.commit(HistoryState("AB", 2, 2))
        ab = history.current
        self.assertIsNotNone(ab)
        self.assertGreater(ab.state_id, a.state_id)

        target = history.undo(ab)
        self.assertEqual(target.state_id, a.state_id)
        old_redo_id = history.redo_stack[-1].state_id

        history.commit(HistoryState("AX", 2, 2))
        branched = history.current
        self.assertGreater(branched.state_id, old_redo_id)
        self.assertEqual(history.redo_stack, [])

    def test_same_text_on_new_branch_has_distinct_identity(self):
        history = TextHistory()
        a = history.reset("A")
        history.commit("AB")
        saved_ab = history.current
        history.undo(saved_ab)
        history.commit("AB")
        branched_ab = history.current
        self.assertEqual(branched_ab.text, saved_ab.text)
        self.assertNotEqual(branched_ab.state_id, saved_ab.state_id)
        self.assertNotEqual(branched_ab.state_id, a.state_id)

    def test_caret_and_selection_refresh_preserve_text_state_identity_and_direction(self):
        history = TextHistory()
        initial = history.reset(HistoryState("abcdef", 2, 5))
        self.assertTrue(history.replace_current_view_state(HistoryState("abcdef", 5, 1)))
        current = history.current
        self.assertEqual(current.state_id, initial.state_id)
        self.assertEqual((current.insert_offset, current.selection_bound_offset), (5, 1))
        self.assertTrue(current.has_selection)
        self.assertFalse(history.can_undo)

    def test_commit_same_text_is_view_refresh_not_undo_step(self):
        history = TextHistory()
        initial = history.reset(HistoryState("abc", 0, 0))
        self.assertFalse(history.commit(HistoryState("abc", 3, 3)))
        self.assertEqual(history.current.state_id, initial.state_id)
        self.assertEqual(len(history.undo_stack), 1)

    def test_pruning_does_not_reuse_state_ids(self):
        history = TextHistory(max_steps=2, max_snapshot_chars=100, max_total_chars=100)
        first = history.reset("0")
        ids = [first.state_id]
        for value in ("1", "2", "3", "4"):
            history.commit(value)
            ids.append(history.current.state_id)
        self.assertEqual(ids, sorted(set(ids)))
        self.assertGreater(history.current.state_id, first.state_id)
        self.assertLessEqual(len(history.undo_stack), 3)

    def test_large_document_disables_snapshot_undo_but_advances_identity(self):
        history = TextHistory(max_snapshot_chars=4, max_total_chars=20)
        first = history.reset("12345")
        self.assertIsNotNone(history.disabled_reason)
        self.assertFalse(history.can_undo)
        self.assertTrue(history.commit("123456"))
        second = history.current
        self.assertGreater(second.state_id, first.state_id)
        self.assertEqual(len(history.undo_stack), 1)
        self.assertFalse(history.can_undo)

    def test_checkpoint_restore_is_exact(self):
        history = TextHistory()
        history.reset(HistoryState("A", 1, 0))
        history.commit(HistoryState("AB", 2, 1))
        checkpoint = history.checkpoint()
        history.commit("ABC")
        history.undo(history.current)
        allocated_next = history.checkpoint().next_state_id
        history.restore_checkpoint(checkpoint)
        restored = history.checkpoint()
        self.assertEqual(restored.undo_stack, checkpoint.undo_stack)
        self.assertEqual(restored.redo_stack, checkpoint.redo_stack)
        self.assertEqual(restored.disabled_reason, checkpoint.disabled_reason)
        self.assertEqual(restored.next_state_id, allocated_next)
        self.assertGreaterEqual(restored.next_state_id, checkpoint.next_state_id)

    def test_checkpoint_restore_does_not_reuse_speculatively_allocated_ids(self):
        history = TextHistory()
        first = history.reset("A")
        checkpoint = history.checkpoint()
        history.commit("AB")
        speculative_id = history.current.state_id
        history.restore_checkpoint(checkpoint)
        self.assertEqual(history.current.state_id, first.state_id)
        history.commit("AX")
        self.assertGreater(history.current.state_id, speculative_id)

    def test_offsets_are_clamped(self):
        state = HistoryState("abc", insert_offset=99, selection_bound_offset=-3)
        self.assertEqual(state.insert_offset, 3)
        self.assertEqual(state.selection_bound_offset, 0)


if __name__ == "__main__":
    unittest.main()
