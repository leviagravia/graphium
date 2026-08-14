from __future__ import annotations

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "graphium"


def python_sources():
    return sorted(PACKAGE.rglob("*.py"))


def imports_in(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append(node.module)
    return found


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_graphium_runtime_has_no_calamus_imports(self):
        offenders = []
        for path in python_sources():
            for imported in imports_in(path):
                if imported == "calamus" or imported.startswith("calamus.") or imported.startswith("calamus_"):
                    offenders.append((path.relative_to(ROOT).as_posix(), imported))
        self.assertEqual(offenders, [])

    def test_gi_is_allowed_only_below_gtk_adapter_boundary(self):
        offenders = []
        for path in python_sources():
            rel = path.relative_to(ROOT).as_posix()
            for imported in imports_in(path):
                if imported == "gi" or imported.startswith("gi."):
                    if not rel.startswith("graphium/adapters/gtk/"):
                        offenders.append((rel, imported))
        self.assertEqual(offenders, [])

    def test_domain_does_not_import_outer_layers(self):
        forbidden = ("graphium.application", "graphium.adapters", "graphium.infrastructure", "graphium.composition")
        offenders = []
        for path in sorted((PACKAGE / "domain").rglob("*.py")):
            for imported in imports_in(path):
                if imported.startswith(forbidden):
                    offenders.append((path.relative_to(ROOT).as_posix(), imported))
        self.assertEqual(offenders, [])

    def test_application_does_not_import_adapters(self):
        offenders = []
        for path in sorted((PACKAGE / "application").rglob("*.py")):
            for imported in imports_in(path):
                if imported.startswith("graphium.adapters"):
                    offenders.append((path.relative_to(ROOT).as_posix(), imported))
        self.assertEqual(offenders, [])

    def test_forbidden_product_clusters_are_not_bootstrapped(self):
        forbidden = {
            "research", "bibliography", "citations", "source_notes", "workspace",
            "document_overview", "navigator", "scratchpad", "clips", "tags", "pandoc",
        }
        dirs = {p.name for p in PACKAGE.iterdir() if p.is_dir()}
        self.assertTrue(forbidden.isdisjoint(dirs))


if __name__ == "__main__":
    unittest.main()
