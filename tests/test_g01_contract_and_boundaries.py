from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "docs" / "canonical"


class G01ContractAndBoundaryTests(unittest.TestCase):
    def test_published_g01_runtime_modules_remain_present_as_regression_authority(self):
        for rel in (
            "graphium/domain/document_identity.py",
            "graphium/domain/document_serialization.py",
            "graphium/infrastructure/document_loader.py",
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_g01_modules_are_gtk_free(self):
        rels = (
            "graphium/domain/document_identity.py",
            "graphium/domain/document_serialization.py",
            "graphium/infrastructure/document_loader.py",
        )
        for rel in rels:
            source = (ROOT / rel).read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            self.assertFalse(any(name == "gi" or name.startswith("gi.") for name in imports), rel)

    def test_g01_does_not_smuggle_future_session_or_save_authorities(self):
        source = "\n".join(
            (ROOT / rel).read_text(encoding="utf-8")
            for rel in (
                "graphium/domain/document_identity.py",
                "graphium/domain/document_serialization.py",
                "graphium/infrastructure/document_loader.py",
            )
        )
        for forbidden in (
            "DocumentSession",
            "GuardedFileWriter",
            "Gtk.",
            "Gio.FileMonitor",
        ):
            self.assertNotIn(forbidden, source)

    def test_canonical_contract_records_g01_codec_eol_and_scope(self):
        architecture = (CANON / "GRAPHIUM_PRODUCT_ARCHITECTURE_CONTRACT.md").read_text(encoding="utf-8")
        for marker in (
            "G01_CONTRACT=FROZEN",
            "no BOM means strict UTF-8",
            "UTF-16 LE/BE",
            "UTF-32 LE/BE",
            "LF-normalized",
            "regular local files",
            "extension-neutral",
            "G02",
            "G03",
        ):
            self.assertIn(marker, architecture)

    def test_canonical_document_cap_stays_exactly_three(self):
        actual = sorted(p.name for p in CANON.iterdir() if p.is_file())
        self.assertEqual(
            actual,
            sorted(
                [
                    "GRAPHIUM_MEMORIA_OPERATIVA.txt",
                    "GRAPHIUM_PRODUCT_ARCHITECTURE_CONTRACT.md",
                    "GRAPHIUM_ROADMAP.md",
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
