from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from graphium.application.document_save_service import DocumentSaveService
from graphium.application.document_session import DocumentSession
from graphium.application.file_lifecycle import FileLifecycleController, UnsavedDecision
from graphium.application.native_editor import NativeEditorController
from graphium.application.recent_files import RecentFilesController
from graphium.domain.edit_history import DeltaHistory
from graphium.infrastructure.document_loader import load_document
from graphium.infrastructure.guarded_file_writer import GuardedFileWriter
from tests.test_g04_file_lifecycle import FakeBuffer, FakeUI


class RecordingRecentStore:
    def __init__(self, *, fail_save: bool = False) -> None:
        self.value: tuple[str, ...] = ()
        self.fail_save = fail_save
        self.save_calls: list[tuple[str, ...]] = []

    def load(self) -> tuple[str, ...]:
        return self.value

    def save(self, paths: tuple[str, ...]) -> None:
        self.save_calls.append(tuple(paths))
        if self.fail_save:
            raise OSError("simulated recent persistence failure")
        self.value = tuple(paths)


class G07LifecycleRecentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.buffer = FakeBuffer()
        self.session = DocumentSession()
        self.history = DeltaHistory()
        self.editor = NativeEditorController(session=self.session, history=self.history, buffer=self.buffer)
        self.editor.initialize_new_text("", clean=True)
        self.ui = FakeUI()
        self.store = RecordingRecentStore()
        self.recent = RecentFilesController(self.store)
        self.lifecycle = FileLifecycleController(
            session=self.session,
            editor=self.editor,
            save_service=DocumentSaveService(session=self.session, writer=GuardedFileWriter()),
            loader=load_document,
            ui=self.ui,
            recent_files=self.recent,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def edit_append(self, extra: str) -> None:
        self.buffer.user_insert(self.editor, len(self.buffer.text), extra)

    def test_successful_open_touches_only_after_install(self):
        source = self.root / "open.txt"
        source.write_text("hello\n", encoding="utf-8")
        self.assertTrue(self.lifecycle.open_document(str(source)).completed)
        self.assertEqual(self.recent.paths, (str(source.resolve()),))
        self.assertEqual(len(self.store.save_calls), 1)

    def test_failed_or_cancelled_open_does_not_touch(self):
        self.assertFalse(self.lifecycle.open_document(str(self.root / "missing.txt")).completed)
        self.assertEqual(self.store.save_calls, [])
        self.edit_append("draft")
        self.ui.unsaved = UnsavedDecision.CANCEL
        target = self.root / "target.txt"
        target.write_text("target", encoding="utf-8")
        self.assertTrue(self.lifecycle.open_document(str(target)).cancelled)
        self.assertEqual(self.store.save_calls, [])

    def test_first_save_touches_recent_but_ordinary_save_does_not(self):
        self.edit_append("one")
        target = self.root / "saved.txt"
        self.ui.save_path = str(target)
        self.assertTrue(self.lifecycle.save().completed)
        self.assertEqual(self.recent.paths, (str(target.resolve()),))
        calls = len(self.store.save_calls)
        self.edit_append(" two")
        self.assertTrue(self.lifecycle.save().completed)
        self.assertEqual(len(self.store.save_calls), calls)

    def test_binding_changing_save_as_touches_new_path(self):
        first = self.root / "first.txt"
        first.write_text("a", encoding="utf-8")
        self.assertTrue(self.lifecycle.open_document(str(first)).completed)
        second = self.root / "second.txt"
        self.ui.save_path = str(second)
        self.assertTrue(self.lifecycle.save_as().completed)
        self.assertEqual(self.recent.paths[0], str(second.resolve()))
        self.assertEqual(self.recent.paths[1], str(first.resolve()))

    def test_recent_persistence_failure_cannot_rollback_successful_open(self):
        store = RecordingRecentStore(fail_save=True)
        recent = RecentFilesController(store)
        lifecycle = FileLifecycleController(
            session=self.session,
            editor=self.editor,
            save_service=DocumentSaveService(session=self.session, writer=GuardedFileWriter()),
            loader=load_document,
            ui=self.ui,
            recent_files=recent,
        )
        source = self.root / "open.txt"
        source.write_text("accepted\n", encoding="utf-8")
        result = lifecycle.open_document(str(source))
        self.assertTrue(result.completed)
        self.assertEqual(self.session.logical_path, str(source.resolve()))
        self.assertEqual(self.buffer.text, "accepted\n")
        self.assertTrue(self.ui.warnings)
        self.assertEqual(recent.paths, ())


if __name__ == "__main__":
    unittest.main()
