from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "docs" / "canonical"


class CanonicalContractMarkerTests(unittest.TestCase):
    def read(self, name):
        return (CANON / name).read_text(encoding="utf-8")

    def test_architecture_contract_freezes_technology_and_boundaries(self):
        text = self.read("GRAPHIUM_PRODUCT_ARCHITECTURE_CONTRACT.md")
        for marker in (
            "GTK 3",
            "Gtk.TextView",
            "single-document",
            "one physical writer authority",
            "graphium.adapters.gtk",
            "MAXIMUM CANONICAL DOCUMENTS: 3",
        ):
            self.assertIn(marker, text)

    def test_roadmap_starts_with_g00_and_has_v1_closure(self):
        text = self.read("GRAPHIUM_ROADMAP.md")
        self.assertIn("G00 — Architecture Bootstrap", text)
        self.assertIn("G12 — V1 Product Closure", text)

    def test_mo_records_g00_authorization(self):
        text = self.read("GRAPHIUM_MEMORIA_OPERATIVA.txt")
        self.assertIn("G00 AUTHORIZED", text)
        self.assertIn("CANONICAL_DOCUMENT_CAP=3", text)


if __name__ == "__main__":
    unittest.main()
