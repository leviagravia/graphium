from __future__ import annotations

import ast
from pathlib import Path
import unittest

from graphium.product import VERSION, WORK_ITEM, WORK_ITEM_DESCRIPTION

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "docs" / "canonical"


class G02ContractAndBoundaryTests(unittest.TestCase):
    def test_runtime_identity_is_g02(self):
        self.assertEqual(WORK_ITEM, "G02")
        self.assertEqual(WORK_ITEM_DESCRIPTION, "History / Editor Transaction / Savepoint Session")
        self.assertTrue(VERSION.endswith("-g02"))

    def test_g02_modules_are_gtk_and_io_free(self):
        rels = (
            "graphium/domain/history.py",
            "graphium/application/document_session.py",
            "graphium/application/editor_transaction.py",
        )
        forbidden_import_roots = {"gi", "os", "pathlib", "tempfile", "shutil", "subprocess"}
        for rel in rels:
            source = (ROOT / rel).read_text(encoding="utf-8")
            tree = ast.parse(source)
            imported = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.append(node.module)
            roots = {name.split(".", 1)[0] for name in imported}
            self.assertFalse(roots & forbidden_import_roots, (rel, sorted(roots & forbidden_import_roots)))
            for marker in ("GuardedFileWriter", "os.replace", "Gtk.", "Gio."):
                self.assertNotIn(marker, source, rel)

    def test_history_domain_does_not_import_application_or_infrastructure(self):
        source = (ROOT / "graphium/domain/history.py").read_text(encoding="utf-8")
        self.assertNotIn("graphium.application", source)
        self.assertNotIn("graphium.infrastructure", source)
        self.assertNotIn("graphium.adapters", source)

    def test_canonical_contract_records_g02_state_identity_and_anti_scope(self):
        architecture = (CANON / "GRAPHIUM_PRODUCT_ARCHITECTURE_CONTRACT.md").read_text(encoding="utf-8")
        for marker in (
            "G02_CONTRACT=FROZEN",
            "G02_SCOPE=HISTORY_TRANSACTION_SAVEPOINT_SESSION",
            "G02_GTK_REQUIRED=NO",
            "G02_DIRTY_AUTHORITY=EDITOR_STATE_ID_RELATION",
            "G02_PHYSICAL_WRITER=FORBIDDEN",
            "Leafpad",
            "L3afpad",
            "Mousepad",
            "never reused",
            "late save",
        ):
            self.assertIn(marker, architecture)

    def test_canonical_document_cap_remains_three(self):
        actual = sorted(p.name for p in CANON.iterdir() if p.is_file())
        self.assertEqual(actual, sorted([
            "GRAPHIUM_MEMORIA_OPERATIVA.txt",
            "GRAPHIUM_PRODUCT_ARCHITECTURE_CONTRACT.md",
            "GRAPHIUM_ROADMAP.md",
        ]))

    def test_obsolete_current_work_item_verifiers_are_removed(self):
        self.assertFalse((ROOT / "VERIFY_G00.py").exists())
        self.assertFalse((ROOT / "VERIFY_G01.py").exists())
        self.assertFalse((ROOT / "bin" / "graphium-g00-selftest").exists())


if __name__ == "__main__":
    unittest.main()
