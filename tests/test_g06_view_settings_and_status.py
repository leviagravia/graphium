from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from graphium.application.view_settings import ViewSettings, ViewSettingsController
from graphium.application.view_status import project_compact_status
from graphium.domain.document_identity import (
    BomKind,
    ContentFingerprint,
    DiskObservation,
    DocumentFileBinding,
    DocumentFileState,
    DocumentLoadMetadata,
    FileObjectIdentity,
    LineEnding,
    LineEndingProfile,
)
from graphium.infrastructure.view_settings_store import JsonViewSettingsStore


class MemoryStore:
    def __init__(self, value=None, *, fail_save=False):
        self.value = value or ViewSettings()
        self.fail_save = fail_save
        self.saves = 0

    def load(self):
        return self.value

    def save(self, settings):
        self.saves += 1
        if self.fail_save:
            raise OSError("synthetic config failure")
        self.value = settings


def file_state(*, encoding="utf-8", bom=BomKind.NONE, eol=LineEnding.LF, mixed=False):
    return DocumentFileState(
        binding=DocumentFileBinding(
            logical_path="/tmp/example.txt",
            canonical_path="/tmp/example.txt",
            object_id=FileObjectIdentity(1, 2),
        ),
        load=DocumentLoadMetadata(
            encoding=encoding,
            bom=bom,
            eol=LineEndingProfile(
                dominant=eol,
                mixed=mixed,
                final_newline=True,
                lf_count=2 if eol is LineEnding.LF else 0,
                crlf_count=2 if eol is LineEnding.CRLF else 0,
                cr_count=2 if eol is LineEnding.CR else 0,
            ),
        ),
        disk=DiskObservation(size=10, mtime_ns=1, mode=0o100644, read_only=False),
        content_fingerprint=ContentFingerprint("sha256", "0" * 64),
    )


class G06ViewSettingsTests(unittest.TestCase):
    def test_defaults_are_small_and_preserve_uncluttered_g05_view(self):
        got = ViewSettings()
        self.assertFalse(got.word_wrap)
        self.assertFalse(got.line_numbers)
        self.assertTrue(got.status_bar)
        self.assertEqual(got.font_family, "Monospace")
        self.assertEqual(got.font_size_points, 11.0)

    def test_validation_rejects_bad_font_without_hidden_coercion(self):
        with self.assertRaises(ValueError):
            ViewSettings(font_family="")
        with self.assertRaises(ValueError):
            ViewSettings(font_size_points=2)
        with self.assertRaises(ValueError):
            ViewSettings(font_size_points=100)

    def test_controller_publishes_setting_only_after_persistence_succeeds(self):
        store = MemoryStore(fail_save=True)
        controller = ViewSettingsController(store)
        before = controller.current
        with self.assertRaises(OSError):
            controller.update(word_wrap=True)
        self.assertEqual(controller.current, before)
        self.assertEqual(store.saves, 1)

    def test_json_store_roundtrip_is_atomic_and_has_no_temp_residue(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "graphium" / "view.json"
            store = JsonViewSettingsStore(path)
            expected = ViewSettings(
                word_wrap=True,
                line_numbers=True,
                status_bar=False,
                font_family="DejaVu Sans Mono",
                font_size_points=13.5,
            )
            store.save(expected)
            self.assertEqual(store.load(), expected)
            self.assertEqual(oct(path.stat().st_mode & 0o777), "0o600")
            self.assertFalse(list(path.parent.glob(".view-settings-*.tmp")))
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(set(payload), {
                "word_wrap", "line_numbers", "status_bar", "font_family", "font_size_points"
            })

    def test_missing_or_corrupt_config_falls_back_without_creating_file(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "view.json"
            store = JsonViewSettingsStore(path)
            self.assertEqual(store.load(), ViewSettings())
            self.assertFalse(path.exists())
            path.write_text("not-json", encoding="utf-8")
            self.assertEqual(store.load(), ViewSettings())


class G06CompactStatusTests(unittest.TestCase):
    def test_new_document_projects_utf8_lf_saved(self):
        got = project_compact_status(line=1, column=1, file_state=None, modified=False)
        self.assertEqual(got.position_text, "Ln 1, Col 1")
        self.assertEqual(got.document_text, "UTF-8 · LF · Saved")

    def test_loaded_representation_and_modified_relation_are_projected(self):
        got = project_compact_status(
            line=12,
            column=7,
            file_state=file_state(encoding="utf-16-le", bom=BomKind.UTF16_LE, eol=LineEnding.CRLF),
            modified=True,
        )
        self.assertEqual(got.position_text, "Ln 12, Col 7")
        self.assertEqual(got.document_text, "UTF-16 LE · CRLF · Modified")

    def test_utf8_bom_and_mixed_eol_are_observation_not_conversion(self):
        got = project_compact_status(
            line=2,
            column=3,
            file_state=file_state(encoding="utf-8", bom=BomKind.UTF8, eol=LineEnding.LF, mixed=True),
            modified=False,
        )
        self.assertEqual(got.document_text, "UTF-8 BOM · Mixed EOL (LF) · Saved")

    def test_position_is_strictly_one_based(self):
        with self.assertRaises(ValueError):
            project_compact_status(line=0, column=1, file_state=None, modified=False)


if __name__ == "__main__":
    unittest.main()
