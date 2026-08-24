from __future__ import annotations
import importlib
import sys
import types
import unittest
from unittest.mock import patch
from graphium.application.document_session import DocumentSession, DocumentSessionPhase
from graphium.domain.document_identity import BomKind, ContentFingerprint, DiskObservation, DocumentFileBinding, DocumentFileState, DocumentLoadMetadata, DocumentLoadResult, FileObjectIdentity, LineEnding, LineEndingProfile
from graphium.domain.history import TextHistory

def file_state(path: str='/tmp/example.txt') -> DocumentFileState:
    return DocumentFileState(binding=DocumentFileBinding(path, path, FileObjectIdentity(1, 2)), load=DocumentLoadMetadata('utf-8', BomKind.NONE, LineEndingProfile(LineEnding.LF, False, True, lf_count=1)), disk=DiskObservation(2, 10, 33188, False), content_fingerprint=ContentFingerprint('sha256', '00' * 32))

class DocumentSessionTests(unittest.TestCase):

    def setUp(self):
        self.history = TextHistory()
        self.session = DocumentSession()

    def test_new_blank_can_be_clean_and_template_new_can_be_dirty(self):
        blank = self.history.reset('')
        self.session.establish_new(blank, clean=True)
        self.assertFalse(self.session.modified)
        self.assertIsNone(self.session.file_state)
        template = self.history.reset('template')
        self.session.establish_new(template, clean=False)
        self.assertTrue(self.session.modified)
        self.assertEqual(self.session.text, 'template')

    def test_open_is_clean_and_retains_loaded_file_state(self):
        fs = file_state()
        result = DocumentLoadResult('A\n', fs, False)
        state = self.history.reset(result.text)
        self.session.establish_open(result, state)
        self.assertFalse(self.session.modified)
        self.assertEqual(self.session.file_state, fs)
        self.assertEqual(self.session.file_path, '/tmp/example.txt')

    def test_modified_is_state_identity_relation_not_text_digest(self):
        a = self.history.reset('A')
        self.session.establish_new(a, clean=True)
        self.history.commit('AB')
        saved = self.history.current
        self.session.commit_history_state(saved)
        self.session.accept_saved_state(saved.state_id)
        self.history.undo(saved)
        self.session.commit_history_state(self.history.current)
        self.history.commit('AB')
        branched = self.history.current
        self.session.commit_history_state(branched)
        self.assertEqual(self.session.text, 'AB')
        self.assertNotEqual(branched.state_id, saved.state_id)
        self.assertTrue(self.session.modified)

    def test_pending_native_text_is_dirty_until_reconciled_to_stable_state(self):
        saved = self.history.reset('A')
        self.session.establish_new(saved, clean=True)
        self.assertTrue(self.session.observe_uncommitted_text('AB'))
        self.assertTrue(self.session.modified)
        self.assertIsNone(self.session.current_editor_state_id)
        self.assertTrue(self.session.observe_uncommitted_text('A'))
        self.assertTrue(self.session.reconcile_with_history(saved))
        self.assertFalse(self.session.modified)

    def test_late_save_of_older_state_does_not_clean_newer_current_state(self):
        a = self.history.reset('A')
        self.session.establish_new(a, clean=True)
        self.history.commit('AB')
        ab = self.history.current
        self.session.commit_history_state(ab)
        self.history.commit('ABC')
        abc = self.history.current
        self.session.commit_history_state(abc)
        self.session.accept_saved_state(ab.state_id)
        self.assertEqual(self.session.saved_editor_state_id, ab.state_id)
        self.assertEqual(self.session.current_editor_state_id, abc.state_id)
        self.assertTrue(self.session.modified)

    def test_accept_current_saved_state_can_update_file_baseline_without_writing(self):
        a = self.history.reset('A')
        self.session.establish_new(a, clean=False)
        fs = file_state()
        self.session.accept_saved_state(a.state_id, file_state=fs)
        self.assertFalse(self.session.modified)
        self.assertEqual(self.session.file_state, fs)

    def test_replacement_phase_suppresses_uncommitted_observation(self):
        a = self.history.reset('A')
        self.session.establish_new(a, clean=True)
        with self.session.replacement(DocumentSessionPhase.OPENING):
            self.assertTrue(self.session.loading)
            self.assertFalse(self.session.observe_uncommitted_text('spurious'))
        self.assertFalse(self.session.loading)
        self.assertEqual(self.session.text, 'A')
        self.assertFalse(self.session.modified)

    def test_checkpoint_restore_is_exact(self):
        a = self.history.reset('A')
        self.session.establish_new(a, clean=True)
        snapshot = self.session.snapshot()
        self.session.observe_uncommitted_text('AB')
        self.session.invalidate_saved_relation()
        self.session.restore_checkpoint(snapshot)
        self.assertEqual(self.session.snapshot(), snapshot)

class ExternalMonitorStateMachineTests(unittest.TestCase):
    def test_pending_delivery_semantics_are_scheduler_independent(self):
        gi = types.ModuleType("gi"); gi.require_version = lambda *_args: None
        repository = types.ModuleType("gi.repository")
        names = "CHANGED DELETED CREATED ATTRIBUTE_CHANGED MOVED RENAMED MOVED_IN MOVED_OUT CHANGES_DONE_HINT".split()
        repository.Gio = type("Gio", (), {"FileMonitorEvent": type("FileMonitorEvent", (), dict(zip(names, range(len(names)))))})
        class FakeGLib:
            @staticmethod
            def timeout_add(*_args): raise AssertionError("pending work scheduled a second worker")
            @staticmethod
            def source_remove(_source_id): return True
        repository.GLib = FakeGLib
        with patch.dict(sys.modules, {"gi": gi, "gi.repository": repository}):
            sys.modules.pop("graphium.adapters.gtk.external_monitor", None)
            module = importlib.import_module("graphium.adapters.gtk.external_monitor")
        accepted = file_state(); history = TextHistory(); session = DocumentSession()
        session.establish_open(DocumentLoadResult("A\n", accepted, False), history.reset("A\n"))
        delivered, followups = [], []
        monitor = module.StrongExternalFileMonitor(session=session, on_result=delivered.append, observer=lambda *_a, **_k: None)
        generation = monitor._generation; ticket = module._ObservationTicket(generation, accepted.binding.logical_path, accepted)
        first = module.CheckNowResult(module.CheckNowStatus.UNCHANGED); latest = module.CheckNowResult(module.CheckNowStatus.CONTENT_CHANGED)
        monitor._inflight_generation = generation; monitor._schedule_observation(generation, immediate=False)
        self.assertEqual(monitor._pending_generation, generation)
        with patch.object(module.StrongExternalFileMonitor, "_schedule_observation", autospec=True,
                          side_effect=lambda _self, gen, *, immediate: followups.append((gen, immediate))):
            monitor._deliver_result(ticket, first)
        self.assertEqual((delivered, followups, monitor._pending_generation, monitor._inflight_generation), ([], [(generation, False)], None, None))
        monitor._inflight_generation = generation; monitor._deliver_result(ticket, latest)
        self.assertEqual(delivered, [latest])
        monitor._generation += 1; monitor._inflight_generation = generation; monitor._deliver_result(ticket, first)
        self.assertEqual(delivered, [latest])

if __name__ == '__main__':
    unittest.main()
