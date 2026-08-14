from __future__ import annotations

import unittest

from graphium.composition import describe_composition
from graphium.product import (
    DESKTOP_APPLICATION_ID,
    EXECUTABLE_NAME,
    PACKAGE_NAME,
    PRODUCT_NAME,
    VERSION,
    WORK_ITEM,
)


class ProductIdentityTests(unittest.TestCase):
    def test_graphium_identity_is_independent(self):
        self.assertEqual(PRODUCT_NAME, "Graphium")
        self.assertEqual(PACKAGE_NAME, "graphium")
        self.assertEqual(EXECUTABLE_NAME, "graphium")
        self.assertTrue(WORK_ITEM.startswith("G"))
        self.assertTrue(VERSION.startswith("0.0."))

    def test_desktop_application_id_was_deferred_in_g00_and_is_frozen_by_g04(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        contract = (root / "docs/canonical/GRAPHIUM_PRODUCT_ARCHITECTURE_CONTRACT.md").read_text(encoding="utf-8")
        self.assertIn("desktop application ID is **DEFERRED in G00**", contract)
        self.assertEqual(DESKTOP_APPLICATION_ID, "io.github.leviagravia.Graphium")

    def test_single_document_and_writer_authorities_are_frozen(self):
        descriptor = describe_composition()
        self.assertEqual(descriptor.document_authority_count, 1)
        self.assertEqual(descriptor.physical_writer_authority_count, 1)
        self.assertEqual(descriptor.gtk_adapter_boundary, "graphium.adapters.gtk")


if __name__ == "__main__":
    unittest.main()
