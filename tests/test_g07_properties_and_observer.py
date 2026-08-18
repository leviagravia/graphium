from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from graphium.application.document_properties import CheckNowStatus, DocumentPropertiesController
from graphium.application.document_session import DocumentSession
from graphium.domain.history import TextHistory
from graphium.infrastructure.document_loader import load_document
from graphium.infrastructure.document_observer import observe_document


def opened(path: Path):
    history=TextHistory(); session=DocumentSession(); result=load_document(str(path)); session.establish_open(result,history.reset(result.text)); return session


class G07PropertiesObserverTests(unittest.TestCase):
    def test_unchanged_and_check_now_never_mutates_session(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"doc.txt"; path.write_bytes(b"abcd") ; session=opened(path); controller=DocumentPropertiesController(session=session,observer=observe_document)
            before=session.snapshot(); self.assertEqual(controller.check_now().status,CheckNowStatus.UNCHANGED); self.assertEqual(session.snapshot(),before)

    def test_same_size_same_mtime_different_bytes_is_content_changed(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"doc.txt"; path.write_bytes(b"abcd"); session=opened(path); controller=DocumentPropertiesController(session=session,observer=observe_document); mtime=path.stat().st_mtime_ns
            path.write_bytes(b"wxyz"); os.utime(path,ns=(mtime,mtime))
            self.assertEqual(controller.check_now().status,CheckNowStatus.CONTENT_CHANGED)

    def test_metadata_only_change_is_classified(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"doc.txt"; path.write_bytes(b"abcd"); session=opened(path); controller=DocumentPropertiesController(session=session,observer=observe_document)
            os.chmod(path,0o444)
            self.assertEqual(controller.check_now().status,CheckNowStatus.METADATA_CHANGED)

    def test_inode_replacement_with_identical_bytes_is_replaced(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); path=root/"doc.txt"; path.write_bytes(b"abcd"); session=opened(path); controller=DocumentPropertiesController(session=session,observer=observe_document)
            repl=root/"replacement"; repl.write_bytes(b"abcd"); os.replace(repl,path)
            self.assertEqual(controller.check_now().status,CheckNowStatus.REPLACED_OR_RETARGETED)

    def test_symlink_retarget_is_replaced(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); a=root/"a"; b=root/"b"; link=root/"logical.txt"; a.write_bytes(b"same"); b.write_bytes(b"same"); link.symlink_to(a)
            session=opened(link); controller=DocumentPropertiesController(session=session,observer=observe_document); link.unlink(); link.symlink_to(b)
            self.assertEqual(controller.check_now().status,CheckNowStatus.REPLACED_OR_RETARGETED)

    def test_deletion_is_missing(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"doc.txt"; path.write_bytes(b"a"); session=opened(path); controller=DocumentPropertiesController(session=session,observer=observe_document); path.unlink()
            self.assertEqual(controller.check_now().status,CheckNowStatus.MISSING)

    def test_observer_reports_readonly_and_hardlink_instead_of_rejecting(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); path=root/"doc.txt"; alias=root/"alias.txt"; path.write_bytes(b"a"); os.link(path,alias); os.chmod(path,0o444)
            obs=observe_document(str(path)); self.assertTrue(obs.disk.read_only); self.assertEqual(obs.disk.nlink,2)

    def test_untitled_properties_have_default_representation_and_disabled_disk_facts(self):
        session=DocumentSession(); history=TextHistory(); session.establish_new(history.reset(""),clean=True); controller=DocumentPropertiesController(session=session,observer=observe_document); props=controller.snapshot()
        self.assertIsNone(props.logical_path); self.assertEqual(props.encoding,"utf-8"); self.assertEqual(props.eol.value,"lf"); self.assertFalse(props.modified)

if __name__=='__main__': unittest.main()
