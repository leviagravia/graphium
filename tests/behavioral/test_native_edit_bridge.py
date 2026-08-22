from __future__ import annotations
import unittest
from graphium.application.document_session import DocumentSession
from graphium.application.native_editor import NativeEditorController
from graphium.domain.edit_history import DeleteDirection, DeltaHistory, EditKind, ReplayPlan, ViewState
from graphium.domain.history import HistoryState

class FakeBuffer:

    def __init__(self, text=''):
        self.text = text
        self.insert = len(text)
        self.bound = len(text)
        self.full_captures = 0
        self.fail_restore_text = None

    def capture_full(self):
        self.full_captures += 1
        return HistoryState(self.text, self.insert, self.bound)

    def restore_full(self, state):
        if state.text == self.fail_restore_text:
            raise RuntimeError('injected restore failure')
        self.text = state.text
        self.insert = state.insert_offset
        self.bound = state.selection_bound_offset

    def capture_view(self):
        return ViewState(self.insert, self.bound)

    def apply_replay(self, plan: ReplayPlan):
        for op in plan.operations:
            if op.kind is EditKind.INSERT:
                self.text = self.text[:op.offset] + op.text + self.text[op.offset:]
            else:
                actual = self.text[op.offset:op.offset + len(op.text)]
                if actual != op.text:
                    raise RuntimeError('replay mismatch')
                self.text = self.text[:op.offset] + self.text[op.offset + len(op.text):]
        self.insert = plan.target_view.insert_offset
        self.bound = plan.target_view.selection_bound_offset

    def user_insert(self, controller, offset, text):
        controller.begin_native_group(ViewState(self.insert, self.bound))
        self.text = self.text[:offset] + text + self.text[offset:]
        self.insert = self.bound = offset + len(text)
        controller.record_native_insert(offset, text)
        return controller.end_native_group(self.capture_view())

    def user_delete(self, controller, offset, length, direction=DeleteDirection.RANGE):
        controller.begin_native_group(ViewState(self.insert, self.bound))
        deleted = self.text[offset:offset + length]
        self.text = self.text[:offset] + self.text[offset + length:]
        self.insert = self.bound = offset
        controller.record_native_delete(offset, deleted, direction=direction)
        return controller.end_native_group(self.capture_view())

def make(text=''):
    session = DocumentSession()
    hist = DeltaHistory()
    buf = FakeBuffer(text)
    editor = NativeEditorController(session=session, history=hist, buffer=buf)
    editor.initialize_new_text(text, clean=True)
    return (session, hist, buf, editor)

class NativeEditorTests(unittest.TestCase):

    def test_native_edit_advances_identity_without_full_buffer_capture(self):
        s, h, b, e = make('abc')
        b.full_captures = 0
        old = s.current_editor_state_id
        b.user_insert(e, 3, 'x')
        self.assertEqual(b.full_captures, 0)
        self.assertNotEqual(s.current_editor_state_id, old)
        self.assertTrue(s.modified)
        self.assertFalse(s.text_is_current)
        self.assertEqual(s.text, 'abc')

    def test_prepare_for_save_captures_once_and_synchronizes_exact_state(self):
        s, h, b, e = make('abc')
        b.user_insert(e, 3, 'x')
        b.full_captures = 0
        sid = e.prepare_for_save()
        self.assertEqual(b.full_captures, 1)
        self.assertEqual(s.text, 'abcx')
        self.assertTrue(s.text_is_current)
        self.assertEqual(s.text_editor_state_id, sid)

    def test_save_undo_redo_savepoint_semantics(self):
        s, h, b, e = make('A')
        b.user_insert(e, 1, 'B')
        saved = e.prepare_for_save()
        s.accept_saved_state(saved)
        self.assertFalse(s.modified)
        e.undo()
        self.assertEqual(b.text, 'A')
        self.assertTrue(s.modified)
        e.redo()
        self.assertEqual(b.text, 'AB')
        self.assertFalse(s.modified)

    def test_undo_redo_do_not_capture_full_document(self):
        s, h, b, e = make('abc')
        b.user_insert(e, 3, 'x')
        b.full_captures = 0
        e.undo()
        e.redo()
        self.assertEqual(b.full_captures, 0)

    def test_branch_after_undo_same_text_is_distinct_identity(self):
        s, h, b, e = make('A')
        first = b.user_insert(e, 1, 'B')
        e.prepare_for_save()
        s.accept_saved_state(first)
        e.undo()
        self.assertEqual(b.text, 'A')
        branch = b.user_insert(e, 1, 'B')
        self.assertGreater(branch, first)
        self.assertEqual(b.text, 'AB')
        self.assertTrue(s.modified)

    def test_large_document_keeps_normal_undo_with_delta_payload(self):
        big = 'x' * (1024 * 1024)
        s, h, b, e = make(big)
        b.full_captures = 0
        b.user_insert(e, len(big), 'Y')
        self.assertTrue(e.can_undo)
        self.assertEqual(h.stored_payload_chars, 1)
        self.assertEqual(b.full_captures, 0)
        e.undo()
        self.assertEqual(len(b.text), len(big))
        self.assertEqual(b.full_captures, 0)

    def test_new_resets_undo_but_never_reuses_state_ids(self):
        s, h, b, e = make('a')
        edited = b.user_insert(e, 1, 'b')
        new = e.initialize_new_text('', clean=True)
        self.assertGreater(new.state_id, edited)
        self.assertFalse(e.can_undo)
        self.assertFalse(s.modified)

    def test_failed_new_restore_rolls_authorities_and_buffer_back(self):
        s, h, b, e = make('keep')
        before_s = s.snapshot()
        before_h = h.checkpoint()
        before = b.text
        b.fail_restore_text = 'boom'
        with self.assertRaises(RuntimeError):
            e.initialize_new_text('boom')
        self.assertEqual(b.text, before)
        self.assertEqual(s.snapshot(), before_s)
        self.assertEqual(h.undo_stack, list(before_h.undo_stack))
        self.assertEqual(h.redo_stack, list(before_h.redo_stack))

    def test_multidelta_replacement_undo_is_exact(self):
        s, h, b, e = make('abcd')
        e.begin_native_group(ViewState(1, 3))
        deleted = b.text[1:3]
        b.text = 'ad'
        b.insert = b.bound = 1
        e.record_native_delete(1, deleted, direction=DeleteDirection.RANGE)
        b.text = 'aXYd'
        b.insert = b.bound = 3
        e.record_native_insert(1, 'XY')
        e.end_native_group(b.capture_view())
        e.undo()
        self.assertEqual(b.text, 'abcd')
        e.redo()
        self.assertEqual(b.text, 'aXYd')

    def test_unicode_native_delta_undo_redo_is_exact(self):
        s, h, b, e = make('αβ')
        b.user_insert(e, 2, '🙂')
        self.assertEqual(b.text, 'αβ🙂')
        e.undo()
        self.assertEqual(b.text, 'αβ')
        e.redo()
        self.assertEqual(b.text, 'αβ🙂')
if __name__ == '__main__':
    unittest.main()
