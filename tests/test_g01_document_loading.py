from __future__ import annotations

import codecs
import hashlib
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from graphium.domain.document_identity import (
    BomKind,
    FileObjectIdentity,
    LineEnding,
    UnsupportedDocumentContentError,
    UnsupportedDocumentEncodingError,
    UnsupportedDocumentTypeError,
    UnstableDocumentLoadError,
)
from graphium.infrastructure.document_loader import load_document, normalize_logical_path


class G01DocumentLoadingTests(unittest.TestCase):
    def write_bytes(self, directory: str, name: str, data: bytes) -> str:
        path = Path(directory) / name
        path.write_bytes(data)
        return str(path)

    def test_utf8_lf_metadata_and_fingerprint_are_exact(self):
        with tempfile.TemporaryDirectory() as td:
            raw = b"alpha\nbeta\n"
            path = self.write_bytes(td, "doc.txt", raw)
            result = load_document(path)
            self.assertEqual(result.text, "alpha\nbeta\n")
            self.assertEqual(result.file_state.load.encoding, "utf-8")
            self.assertEqual(result.file_state.load.bom, BomKind.NONE)
            self.assertEqual(result.file_state.load.eol.dominant, LineEnding.LF)
            self.assertFalse(result.file_state.load.eol.mixed)
            self.assertTrue(result.file_state.load.eol.final_newline)
            self.assertEqual(result.file_state.content_fingerprint.algorithm, "sha256")
            self.assertEqual(
                result.file_state.content_fingerprint.hex_digest,
                hashlib.sha256(raw).hexdigest(),
            )
            self.assertEqual(result.file_state.disk.size, len(raw))

    def test_utf8_bom_is_stripped_but_recorded(self):
        with tempfile.TemporaryDirectory() as td:
            path = self.write_bytes(td, "bom.txt", codecs.BOM_UTF8 + b"Body\n")
            result = load_document(path)
            self.assertEqual(result.text, "Body\n")
            self.assertEqual(result.file_state.load.bom, BomKind.UTF8)
            self.assertNotIn("\ufeff", result.text)

    def test_utf16_and_utf32_bom_families_decode_explicitly(self):
        cases = (
            (codecs.BOM_UTF16_LE + "A\r\nB".encode("utf-16-le"), "utf-16-le", BomKind.UTF16_LE),
            (codecs.BOM_UTF16_BE + "A\rB".encode("utf-16-be"), "utf-16-be", BomKind.UTF16_BE),
            (codecs.BOM_UTF32_LE + "A\nB".encode("utf-32-le"), "utf-32-le", BomKind.UTF32_LE),
            (codecs.BOM_UTF32_BE + "A\nB".encode("utf-32-be"), "utf-32-be", BomKind.UTF32_BE),
        )
        with tempfile.TemporaryDirectory() as td:
            for index, (raw, encoding, bom) in enumerate(cases):
                with self.subTest(encoding=encoding):
                    path = self.write_bytes(td, f"doc-{index}.txt", raw)
                    result = load_document(path)
                    self.assertEqual(result.file_state.load.encoding, encoding)
                    self.assertEqual(result.file_state.load.bom, bom)
                    self.assertEqual(result.text, "A\nB")

    def test_crlf_cr_and_mixed_eol_are_recorded_before_normalization(self):
        cases = (
            (b"a\r\nb\r\n", LineEnding.CRLF, False, (0, 2, 0), True),
            (b"a\rb\r", LineEnding.CR, False, (0, 0, 2), True),
            (b"a\r\nb\nc\r", LineEnding.CRLF, True, (1, 1, 1), True),
        )
        with tempfile.TemporaryDirectory() as td:
            for index, (raw, dominant, mixed, counts, final) in enumerate(cases):
                result = load_document(self.write_bytes(td, f"eol-{index}.txt", raw))
                eol = result.file_state.load.eol
                self.assertEqual(eol.dominant, dominant)
                self.assertEqual(eol.mixed, mixed)
                self.assertEqual((eol.lf_count, eol.crlf_count, eol.cr_count), counts)
                self.assertEqual(eol.final_newline, final)
                self.assertNotIn("\r", result.text)

    def test_mixed_eol_tie_uses_first_occurrence(self):
        with tempfile.TemporaryDirectory() as td:
            result = load_document(self.write_bytes(td, "mixed.txt", b"a\nb\r\nc"))
            self.assertEqual(result.file_state.load.eol.dominant, LineEnding.LF)
            self.assertTrue(result.file_state.load.eol.mixed)
            self.assertFalse(result.file_state.load.eol.final_newline)

    def test_invalid_utf8_fails_without_locale_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            path = self.write_bytes(td, "legacy.txt", b"caf\xe9")
            with self.assertRaises(UnsupportedDocumentEncodingError):
                load_document(path)

    def test_nul_content_is_typed_unsupported_text(self):
        with tempfile.TemporaryDirectory() as td:
            path = self.write_bytes(td, "nul.bin", b"a\x00b")
            with self.assertRaises(UnsupportedDocumentContentError):
                load_document(path)

    def test_directory_is_rejected_as_document_visit(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(UnsupportedDocumentTypeError):
                load_document(td)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO required")
    def test_fifo_is_rejected_without_waiting_for_writer(self):
        with tempfile.TemporaryDirectory() as td:
            path = str(Path(td) / "pipe")
            os.mkfifo(path)
            with self.assertRaises(UnsupportedDocumentTypeError):
                load_document(path)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support required")
    def test_symlink_preserves_logical_path_and_resolves_physical_identity(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "target.txt"
            target.write_text("Body\n", encoding="utf-8", newline="")
            link = Path(td) / "alias.txt"
            link.symlink_to(target.name)
            result = load_document(str(link))
            binding = result.file_state.binding
            self.assertEqual(binding.logical_path, os.path.abspath(str(link)))
            self.assertEqual(binding.canonical_path, os.path.realpath(str(link)))
            st = target.stat()
            self.assertEqual(
                (binding.object_id.device, binding.object_id.inode),
                (st.st_dev, st.st_ino),
            )

    def test_read_only_is_mode_observation_not_path_identity(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "readonly.txt"
            path.write_text("Body", encoding="utf-8")
            path.chmod(0o444)
            result = load_document(str(path))
            self.assertTrue(result.file_state.disk.read_only)
            self.assertTrue(stat.S_ISREG(result.file_state.disk.mode))

    def test_path_replacement_during_read_retries_and_binds_current_named_object(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "document.txt"
            retired = Path(td) / "retired.txt"
            path.write_bytes(b"old bytes\n")
            real_fstat = os.fstat
            calls = 0

            def replacing_fstat(fd):
                nonlocal calls
                calls += 1
                result = real_fstat(fd)
                if calls == 1:
                    path.rename(retired)
                    path.write_bytes(b"new bytes\n")
                return result

            with patch(
                "graphium.infrastructure.document_loader.os.fstat",
                side_effect=replacing_fstat,
            ):
                result = load_document(str(path), retries=1)

            self.assertEqual(result.text, "new bytes\n")
            current = path.stat()
            self.assertEqual(
                result.file_state.binding.object_id,
                FileObjectIdentity(device=current.st_dev, inode=current.st_ino),
            )
            self.assertEqual(
                result.file_state.content_fingerprint.hex_digest,
                hashlib.sha256(b"new bytes\n").hexdigest(),
            )

    def test_unstable_read_retries_once_then_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "unstable.txt"
            path.write_text("Body", encoding="utf-8")
            real = os.stat(path)
            changed = type(
                "Stat",
                (),
                {
                    "st_dev": real.st_dev,
                    "st_ino": real.st_ino,
                    "st_size": real.st_size,
                    "st_mtime_ns": real.st_mtime_ns + 1,
                    "st_mode": real.st_mode,
                },
            )()
            with patch(
                "graphium.infrastructure.document_loader.os.fstat",
                side_effect=[real, changed, real, changed],
            ):
                with self.assertRaises(UnstableDocumentLoadError):
                    load_document(str(path), retries=1)

    def test_logical_path_normalization_is_general_purpose_and_extension_neutral(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "README"
            path.write_text("plain text", encoding="utf-8")
            self.assertEqual(load_document(str(path)).text, "plain text")
            self.assertEqual(normalize_logical_path(str(path)), os.path.abspath(str(path)))

    def test_large_file_flag_uses_explicit_threshold_without_changing_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "large.txt"
            path.write_bytes(b"12345")
            self.assertTrue(load_document(str(path), large_file_threshold=5).large_file)
            self.assertFalse(load_document(str(path), large_file_threshold=6).large_file)


if __name__ == "__main__":
    unittest.main()
