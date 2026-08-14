from __future__ import annotations
import unittest

from graphium.domain.edit_history import (
    DeleteDirection,
    DeltaHistory,
    EditKind,
    ViewState,
)


class G04DeltaHistoryTests(unittest.TestCase):
    def test_contiguous_word_typing_coalesces_without_timer(self):
        h = DeltaHistory(); s1 = h.reset()
        for i, ch in enumerate("abc"):
            h.begin_group(ViewState(i, i)); h.record_insert(i, ch)
            sid = h.end_group(ViewState(i + 1, i + 1), saved_state_id=s1)
        self.assertEqual(len(h.undo_stack), 1)
        self.assertEqual(h.undo_stack[0].deltas[0].text, "abc")
        self.assertEqual(h.current_state_id, sid)

    def test_whitespace_is_a_structural_boundary(self):
        h = DeltaHistory(); h.reset()
        for i, ch in enumerate("a b"):
            h.begin_group(ViewState(i, i)); h.record_insert(i, ch)
            h.end_group(ViewState(i + 1, i + 1))
        self.assertEqual([g.deltas[0].text for g in h.undo_stack], ["a", " ", "b"])

    def test_savepoint_boundary_prevents_later_merge_across_saved_state(self):
        h = DeltaHistory(); h.reset()
        h.begin_group(ViewState()); h.record_insert(0, "a"); saved = h.end_group(ViewState(1, 1))
        h.begin_group(ViewState(1, 1)); h.record_insert(1, "b"); h.end_group(ViewState(2, 2), saved_state_id=saved)
        self.assertEqual(len(h.undo_stack), 2)
        self.assertEqual(h.undo_stack[0].after_state_id, saved)

    def test_backward_delete_coalesces_by_position(self):
        h = DeltaHistory(); h.reset()
        h.begin_group(ViewState(3, 3)); h.record_delete(2, "c", direction=DeleteDirection.BACKWARD); h.end_group(ViewState(2, 2))
        h.begin_group(ViewState(2, 2)); h.record_delete(1, "b", direction=DeleteDirection.BACKWARD); h.end_group(ViewState(1, 1))
        d = h.undo_stack[-1].deltas[0]
        self.assertEqual((d.offset, d.text, d.delete_direction), (1, "bc", DeleteDirection.BACKWARD))

    def test_forward_delete_coalesces_at_same_offset(self):
        h = DeltaHistory(); h.reset()
        h.begin_group(ViewState(0, 0)); h.record_delete(0, "a", direction=DeleteDirection.FORWARD); h.end_group(ViewState(0, 0))
        h.begin_group(ViewState(0, 0)); h.record_delete(0, "b", direction=DeleteDirection.FORWARD); h.end_group(ViewState(0, 0))
        d = h.undo_stack[-1].deltas[0]
        self.assertEqual((d.offset, d.text), (0, "ab"))

    def test_undo_redo_replay_and_saved_identity_are_exact(self):
        h = DeltaHistory(); initial = h.reset()
        h.begin_group(ViewState()); h.record_insert(0, "A"); saved = h.end_group(ViewState(1, 1))
        undo = h.undo(); self.assertIsNotNone(undo)
        self.assertEqual(undo.target_state_id, initial)
        self.assertEqual(undo.operations[0].kind, EditKind.DELETE)
        redo = h.redo(); self.assertIsNotNone(redo)
        self.assertEqual(redo.target_state_id, saved)
        self.assertEqual(redo.operations[0].kind, EditKind.INSERT)

    def test_branch_after_undo_never_reuses_state_ids(self):
        h = DeltaHistory(); h.reset()
        h.begin_group(ViewState()); h.record_insert(0, "a"); a = h.end_group(ViewState(1, 1))
        h.begin_group(ViewState(1, 1)); h.record_insert(1, "b"); b = h.end_group(ViewState(2, 2))
        h.undo()
        h.begin_group(ViewState(1, 1)); h.record_insert(1, "x"); x = h.end_group(ViewState(2, 2))
        self.assertGreater(x, b); self.assertGreater(b, a)
        self.assertFalse(h.can_redo)

    def test_large_document_size_is_not_a_history_disable_switch(self):
        h = DeltaHistory(); h.reset()
        # Base document size is intentionally not stored in the journal. One edit costs
        # one changed character regardless of whether the document is 1 KiB or 10 MiB.
        h.begin_group(ViewState(10_000_000, 10_000_000))
        h.record_insert(10_000_000, "X")
        h.end_group(ViewState(10_000_001, 10_000_001))
        self.assertTrue(h.can_undo)
        self.assertEqual(h.stored_payload_chars, 1)

    def test_multidelta_replace_is_one_undo_group(self):
        h = DeltaHistory(); h.reset()
        h.begin_group(ViewState(1, 3))
        h.record_delete(1, "bc", direction=DeleteDirection.RANGE)
        h.record_insert(1, "XY")
        h.end_group(ViewState(3, 3))
        self.assertEqual(len(h.undo_stack), 1)
        plan = h.undo()
        self.assertEqual([(o.kind, o.offset, o.text) for o in plan.operations], [
            (EditKind.DELETE, 1, "XY"),
            (EditKind.INSERT, 1, "bc"),
        ])

    def test_checkpoint_rollback_does_not_reuse_speculative_id(self):
        h = DeltaHistory(); h.reset(); cp = h.checkpoint()
        h.begin_group(ViewState()); h.record_insert(0, "a"); speculative = h.end_group(ViewState(1, 1))
        h.restore_checkpoint(cp)
        h.begin_group(ViewState()); h.record_insert(0, "b"); later = h.end_group(ViewState(1, 1))
        self.assertGreater(later, speculative)

    def test_newline_and_space_do_not_merge_into_one_typing_group(self):
        h=DeltaHistory(); h.reset()
        h.begin_group(ViewState(0,0)); h.record_insert(0," "); h.end_group(ViewState(1,1))
        h.begin_group(ViewState(1,1)); h.record_insert(1,"\n"); h.end_group(ViewState(2,2))
        self.assertEqual(len(h.undo_stack),2)

    def test_unicode_payload_is_counted_in_text_characters(self):
        h=DeltaHistory(); h.reset()
        h.begin_group(ViewState(0,0)); h.record_insert(0,"é🙂"); h.end_group(ViewState(2,2))
        self.assertEqual(h.stored_payload_chars,2)
        plan=h.undo(); self.assertIsNotNone(plan)
        self.assertEqual(plan.operations[0].text,"é🙂")


if __name__ == "__main__": unittest.main()
