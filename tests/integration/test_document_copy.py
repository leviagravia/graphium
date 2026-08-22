from __future__ import annotations
import codecs
from pathlib import Path
import tempfile
import unittest
from graphium.application.document_copy import CopyBindingError, DocumentCopyService
from graphium.application.document_session import DocumentSession
from graphium.domain.document_save import StaleSaveTargetError
from graphium.domain.document_serialization import MixedLineEndingConfirmationRequired
from graphium.domain.history import TextHistory
from graphium.infrastructure.document_loader import load_document
from graphium.infrastructure.guarded_file_writer import GuardedFileWriter

def open_session(path: Path):
    history = TextHistory()
    session = DocumentSession()
    loaded = load_document(str(path))
    state = history.reset(loaded.text)
    session.establish_open(loaded, state)
    return (history, session)

def edit(history, session, text):
    history.commit(text)
    session.commit_history_state(history.current)

class DocumentCopyTests(unittest.TestCase):

    def test_modified_copy_preserves_exact_session_binding_savepoint_and_history(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / 'source.txt'
            dst = root / 'copy.txt'
            src.write_text('A\n', encoding='utf-8')
            h, s = open_session(src)
            edit(h, s, 'AB\n')
            service = DocumentCopyService(session=s, writer=GuardedFileWriter())
            before = s.snapshot()
            hcp = h.checkpoint()
            obs = service.observe_target(str(dst))
            service.copy_to(obs)
            self.assertEqual(dst.read_text(encoding='utf-8'), 'AB\n')
            self.assertEqual(s.snapshot(), before)
            self.assertEqual(h.checkpoint(), hcp)
            self.assertTrue(s.modified)

    def test_copy_preserves_utf16_bom_and_crlf_profile(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / 'source.txt'
            dst = root / 'copy.txt'
            src.write_bytes(codecs.BOM_UTF16_LE + 'A\r\n'.encode('utf-16-le'))
            h, s = open_session(src)
            edit(h, s, 'AB\n')
            service = DocumentCopyService(session=s, writer=GuardedFileWriter())
            service.copy_to(service.observe_target(str(dst)))
            raw = dst.read_bytes()
            self.assertTrue(raw.startswith(codecs.BOM_UTF16_LE))
            self.assertEqual(load_document(str(dst)).text, 'AB\n')

    def test_mixed_eol_requires_explicit_consent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / 'mixed.txt'
            dst = root / 'copy.txt'
            src.write_bytes(b'A\r\nB\nC\r\n')
            h, s = open_session(src)
            edit(h, s, 'A\nB2\nC\n')
            service = DocumentCopyService(session=s, writer=GuardedFileWriter())
            obs = service.observe_target(str(dst))
            with self.assertRaises(MixedLineEndingConfirmationRequired):
                service.copy_to(obs)
            self.assertFalse(dst.exists())
            service.copy_to(obs, allow_mixed_eol_normalization=True)
            self.assertTrue(dst.exists())

    def test_active_logical_and_symlink_alias_targets_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / 'source.txt'
            alias = root / 'alias.txt'
            src.write_text('A', encoding='utf-8')
            alias.symlink_to(src)
            h, s = open_session(src)
            service = DocumentCopyService(session=s, writer=GuardedFileWriter())
            with self.assertRaises(CopyBindingError):
                service.observe_target(str(src))
            with self.assertRaises(CopyBindingError):
                service.observe_target(str(alias))

    def test_version_copy_uses_max_plus_one_width_and_ignores_unrelated(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / 'report.md'
            src.write_text('A', encoding='utf-8')
            for name in ('report_v0001.md', 'report_v0003.md', 'report_v10002.md', 'other_v99999.md', 'report_v12.md'):
                (root / name).write_text('x', encoding='utf-8')
            h, s = open_session(src)
            service = DocumentCopyService(session=s, writer=GuardedFileWriter())
            plan = service.plan_named_version_copy()
            self.assertEqual(plan.number, 10003)
            self.assertTrue(plan.logical_target_path.endswith('report_v10003.md'))
            obs = service.observe_planned_version_target(plan)
            service.copy_to(obs)
            self.assertEqual(Path(plan.logical_target_path).read_text(), 'A')

    def test_version_dotfile_and_no_suffix(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name, expected in (('.notes', '.notes_v0001'), ('README', 'README_v0001')):
                src = root / name
                src.write_text('A', encoding='utf-8')
                h, s = open_session(src)
                service = DocumentCopyService(session=s, writer=GuardedFileWriter())
                self.assertTrue(service.plan_named_version_copy().logical_target_path.endswith(expected))

    def test_version_target_race_fails_closed_not_renumbered(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / 'doc.txt'
            src.write_text('A', encoding='utf-8')
            h, s = open_session(src)
            service = DocumentCopyService(session=s, writer=GuardedFileWriter())
            plan = service.plan_named_version_copy()
            Path(plan.logical_target_path).write_text('racer', encoding='utf-8')
            with self.assertRaises(StaleSaveTargetError):
                service.observe_planned_version_target(plan)
if __name__ == '__main__':
    unittest.main()
