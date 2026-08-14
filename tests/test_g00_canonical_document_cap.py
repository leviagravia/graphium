from __future__ import annotations

from pathlib import Path
import unittest

from graphium.architecture import CANONICAL_DOCUMENTS, MAX_CANONICAL_DOCUMENTS

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "docs" / "canonical"


class CanonicalDocumentCapTests(unittest.TestCase):
    def test_cap_is_three(self):
        self.assertEqual(MAX_CANONICAL_DOCUMENTS, 3)

    def test_exactly_the_three_designated_canonical_documents_exist(self):
        actual = tuple(sorted(p.name for p in CANON.iterdir() if p.is_file()))
        expected = tuple(sorted(CANONICAL_DOCUMENTS))
        self.assertEqual(actual, expected)
        self.assertLessEqual(len(actual), MAX_CANONICAL_DOCUMENTS)


if __name__ == "__main__":
    unittest.main()
