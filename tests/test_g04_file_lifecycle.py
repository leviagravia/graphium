from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from graphium.application.document_save_service import DocumentSaveService
from graphium.application.document_session import DocumentSession
from graphium.application.file_lifecycle import FileLifecycleController, UnsavedDecision
from graphium.application.native_editor import NativeEditorController
from graphium.domain.edit_history import DeltaHistory, EditKind, ReplayPlan, ViewState
from graphium.domain.history import HistoryState
from graphium.infrastructure.document_loader import load_document
from graphium.infrastructure.guarded_file_writer import GuardedFileWriter


class FakeBuffer:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.insert = len(text)
        self.bound = len(text)
        self.full_captures = 0

    def capture_full(self) -> HistoryState:
        self.full_captures += 1
        return HistoryState(self.text, self.insert, self.bound)

    def restore_full(self, state: HistoryState) -> None:
        self.text = state.text
        self.insert = state.insert_offset
        self.bound = state.selection_bound_offset

    def capture_view(self) -> ViewState:
        return ViewState(self.insert, self.bound)

    def apply_replay(self, plan: ReplayPlan) -> None:
        for operation in plan.operations:
            if operation.kind is EditKind.INSERT:
                self.text = self.text[:operation.offset] + operation.text + self.text[operation.offset:]
            else:
                end = operation.offset + len(operation.text)
                if self.text[operation.offset:end] != operation.text:
                    raise RuntimeError("replay mismatch")
                self.text = self.text[:operation.offset] + self.text[end:]
        self.insert = plan.target_view.insert_offset
        self.bound = plan.target_view.selection_bound_offset

    def user_insert(self, editor: NativeEditorController, offset: int, text: str) -> None:
        editor.begin_native_group(self.capture_view())
        self.text = self.text[:offset] + text + self.text[offset:]
        self.insert = self.bound = offset + len(text)
        editor.record_native_insert(offset, text)
        editor.end_native_group(self.capture_view())


class FakeUI:
    def __init__(self) -> None:
        self.open_path: str | None = None
        self.save_path: str | None = None
        self.unsaved = UnsavedDecision.CANCEL
        self.overwrite = False
        self.mixed = False
        self.errors: list[tuple[str, str]] = []
        self.warnings: list[tuple[str, str]] = []
        self.unsaved_prompts: list[str] = []
        self.overwrite_prompts: list[str] = []

    def choose_open_path(self): return self.open_path
    def choose_save_path(self, _current): return self.save_path
    def confirm_unsaved_changes(self, action_label):
        self.unsaved_prompts.append(action_label)
        return self.unsaved
    def confirm_overwrite(self, path):
        self.overwrite_prompts.append(path)
        return self.overwrite
    def confirm_mixed_eol_normalization(self): return self.mixed
    def show_error(self, title, message): self.errors.append((title, message))
    def show_warning(self, title, message): self.warnings.append((title, message))


class G04FileLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.buffer = FakeBuffer()
        self.session = DocumentSession()
        self.history = DeltaHistory()
        self.editor = NativeEditorController(
            session=self.session,
            history=self.history,
            buffer=self.buffer,
        )
        self.editor.initialize_new_text("", clean=True)
        self.writer = GuardedFileWriter()
        self.save_service = DocumentSaveService(session=self.session, writer=self.writer)
        self.ui = FakeUI()
        self.lifecycle = FileLifecycleController(
            session=self.session,
            editor=self.editor,
            save_service=self.save_service,
            loader=load_document,
            ui=self.ui,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def edit(self, text: str) -> None:
        old = self.buffer.text
        self.assertTrue(text.startswith(old), "test helper supports append edits")
        self.buffer.user_insert(self.editor, len(old), text[len(old):])

    def test_unsaved_prompt_does_not_copy_full_buffer(self):
        self.edit("draft")
        self.buffer.full_captures = 0
        self.ui.unsaved = UnsavedDecision.CANCEL
        result = self.lifecycle.new_document()
        self.assertFalse(result.completed)
        self.assertEqual(self.buffer.full_captures, 0)

    def test_new_document_cancel_preserves_modified_document(self):
        self.edit("draft")
        before = self.session.snapshot()
        self.ui.unsaved = UnsavedDecision.CANCEL
        result = self.lifecycle.new_document()
        self.assertFalse(result.completed)
        self.assertTrue(result.cancelled)
        self.assertEqual(self.session.snapshot(), before)
        self.assertEqual(self.buffer.text, "draft")

    def test_new_document_discard_replaces_and_is_clean(self):
        self.edit("draft")
        self.ui.unsaved = UnsavedDecision.DISCARD
        result = self.lifecycle.new_document()
        self.assertTrue(result.completed)
        self.assertEqual(self.buffer.text, "")
        self.assertIsNone(self.session.logical_path)
        self.assertFalse(self.session.modified)
        self.assertFalse(self.editor.can_undo)

    def test_failed_open_preserves_current_document(self):
        self.edit("keep me")
        self.ui.unsaved = UnsavedDecision.DISCARD
        before = self.session.snapshot()
        result = self.lifecycle.open_document(str(self.root / "missing.txt"))
        self.assertFalse(result.completed)
        self.assertEqual(self.session.snapshot(), before)
        self.assertEqual(self.buffer.text, "keep me")
        self.assertTrue(self.ui.errors)

    def test_open_loads_before_replacing_and_is_clean(self):
        source = self.root / "source.txt"
        source.write_bytes(b"hello\r\nworld\r\n")
        result = self.lifecycle.open_document(str(source))
        self.assertTrue(result.completed)
        self.assertEqual(self.buffer.text, "hello\nworld\n")
        self.assertEqual(self.session.logical_path, str(source))
        self.assertFalse(self.session.modified)
        self.assertFalse(self.editor.can_undo)


    def test_pathological_huge_line_open_is_rejected_before_buffer_install(self):
        from graphium.application.renderability import MAX_INTERACTIVE_LINE_CHARS

        self.edit("keep current")
        self.ui.unsaved = UnsavedDecision.DISCARD
        before_session = self.session.snapshot()
        before_history = self.history.checkpoint()
        source = self.root / "huge-line.txt"
        source.write_text("x" * (MAX_INTERACTIVE_LINE_CHARS + 1), encoding="utf-8")

        result = self.lifecycle.open_document(str(source))

        self.assertFalse(result.completed)
        self.assertEqual(self.buffer.text, "keep current")
        self.assertEqual(self.session.snapshot(), before_session)
        after_history = self.history.checkpoint()
        self.assertEqual(after_history, before_history)
        self.assertTrue(self.ui.errors)
        self.assertIn("line too long", self.ui.errors[-1][0].lower())

    def test_huge_line_open_does_not_truncate_or_mutate_source_bytes(self):
        from graphium.application.renderability import MAX_INTERACTIVE_LINE_CHARS

        source = self.root / "huge-line.txt"
        raw = ("x" * (MAX_INTERACTIVE_LINE_CHARS + 1)).encode("utf-8")
        source.write_bytes(raw)
        result = self.lifecycle.open_document(str(source))
        self.assertFalse(result.completed)
        self.assertEqual(source.read_bytes(), raw)

    def test_save_untitled_syncs_once_then_save_as_rebinds_after_commit(self):
        self.edit("hello")
        target = self.root / "new.txt"
        self.ui.save_path = str(target)
        self.buffer.full_captures = 0
        result = self.lifecycle.save()
        self.assertTrue(result.completed)
        self.assertEqual(self.buffer.full_captures, 1)
        self.assertEqual(target.read_bytes(), b"hello")
        self.assertEqual(self.session.logical_path, str(target))
        self.assertFalse(self.session.modified)

    def test_save_as_existing_requires_explicit_overwrite_consent(self):
        self.edit("new bytes")
        target = self.root / "existing.txt"
        target.write_bytes(b"old bytes")
        self.ui.save_path = str(target)
        result = self.lifecycle.save_as()
        self.assertFalse(result.completed)
        self.assertTrue(result.cancelled)
        self.assertEqual(target.read_bytes(), b"old bytes")
        self.assertIsNone(self.session.logical_path)

    def test_save_as_existing_rebinds_only_after_successful_commit(self):
        self.edit("new bytes")
        target = self.root / "existing.txt"
        target.write_bytes(b"old bytes")
        self.ui.save_path = str(target)
        self.ui.overwrite = True
        result = self.lifecycle.save_as()
        self.assertTrue(result.completed)
        self.assertEqual(target.read_bytes(), b"new bytes")
        self.assertEqual(self.session.logical_path, str(target))
        self.assertFalse(self.session.modified)

    def test_mixed_eol_save_requires_explicit_normalization_consent(self):
        source = self.root / "mixed.txt"
        source.write_bytes(b"a\r\nb\nc\r")
        self.assertTrue(self.lifecycle.open_document(str(source)).completed)
        self.buffer.user_insert(self.editor, len(self.buffer.text), "d")
        self.ui.mixed = False
        denied = self.lifecycle.save()
        self.assertFalse(denied.completed)
        self.assertTrue(denied.cancelled)
        self.assertTrue(self.session.modified)
        self.ui.mixed = True
        accepted = self.lifecycle.save()
        self.assertTrue(accepted.completed)
        self.assertFalse(self.session.modified)

    def test_stale_external_mutation_blocks_ordinary_save(self):
        source = self.root / "doc.txt"
        source.write_bytes(b"one")
        self.assertTrue(self.lifecycle.open_document(str(source)).completed)
        self.buffer.user_insert(self.editor, len(self.buffer.text), " mine")
        source.write_bytes(b"theirs")
        result = self.lifecycle.save()
        self.assertFalse(result.completed)
        self.assertEqual(source.read_bytes(), b"theirs")
        self.assertTrue(self.session.modified)
        self.assertTrue(self.ui.errors)

    def test_close_save_cancelled_keeps_window_open_semantics(self):
        self.edit("draft")
        self.ui.unsaved = UnsavedDecision.SAVE
        self.ui.save_path = None
        result = self.lifecycle.request_close()
        self.assertFalse(result.completed)
        self.assertTrue(result.cancelled)
        self.assertTrue(self.session.modified)

    def test_close_discard_completes_without_mutating_document(self):
        self.edit("draft")
        self.ui.unsaved = UnsavedDecision.DISCARD
        result = self.lifecycle.request_close()
        self.assertTrue(result.completed)
        self.assertEqual(self.buffer.text, "draft")


if __name__ == "__main__":
    unittest.main()
