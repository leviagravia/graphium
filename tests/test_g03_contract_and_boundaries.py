from __future__ import annotations

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


class G03ContractAndBoundaryTests(unittest.TestCase):
    def test_published_g03_release_identity_is_retained_as_regression_evidence(self):
        roadmap = (ROOT / "docs/canonical/GRAPHIUM_ROADMAP.md").read_text(encoding="utf-8")
        self.assertIn("e7045e0ce1c79da71c9968bdfa052df25a5378b7", roadmap)
        self.assertIn("42fe5340e1181199db86ed69cfa93b4735e45666", roadmap)
        self.assertTrue((ROOT / "graphium/infrastructure/guarded_file_writer.py").is_file())
        self.assertTrue((ROOT / "graphium/application/document_save_service.py").is_file())

    def test_canonical_document_cap_remains_exactly_three(self):
        docs = [p for p in (ROOT / "docs/canonical").iterdir() if p.is_file()]
        self.assertEqual(len(docs), 3)

    def test_g03_modules_are_gtk_free(self):
        for rel in (
            "graphium/domain/document_save.py",
            "graphium/application/document_save_service.py",
            "graphium/infrastructure/guarded_file_writer.py",
        ):
            names = imports(ROOT / rel)
            self.assertFalse(any(name == "gi" or name.startswith("gi.") for name in names), rel)

    def test_single_physical_document_writer_authority_owns_document_namespace_mutation(self):
        # G03 freezes exactly one writer for user DOCUMENT targets. Later work items add
        # narrowly scoped XDG product-configuration stores; treating those config namespaces
        # as document writers would conflate product configuration with document I/O.
        allowed_non_document_stores = (
            "graphium/infrastructure/view_settings_store.py",
            "graphium/infrastructure/recent_files_store.py",
            "graphium/adapters/gtk/printing.py",
        )
        offenders = []
        for path in (ROOT / "graphium").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            rel = path.relative_to(ROOT).as_posix()
            if rel not in (
                "graphium/infrastructure/guarded_file_writer.py",
                *allowed_non_document_stores,
            ):
                for marker in ("os.replace(", "os.link(", "Path.write_bytes(", ".write_bytes("):
                    if marker in text:
                        offenders.append((rel, marker))
        self.assertEqual(offenders, [])
        for store in allowed_non_document_stores:
            config = (ROOT / store).read_text(encoding="utf-8")
            for forbidden in ("DocumentSave", "GuardedFileWriter", "load_document", "logical_target_path"):
                self.assertNotIn(forbidden, config)

    def test_published_g03_modules_remain_free_of_g04_ui_and_g11_monitoring(self):
        runtime = "\n".join(
            (ROOT / rel).read_text(encoding="utf-8")
            for rel in (
                "graphium/domain/document_save.py",
                "graphium/application/document_save_service.py",
                "graphium/infrastructure/guarded_file_writer.py",
            )
        )
        for marker in ("Gtk.FileChooser", "GtkFileChooser", "Gio.FileMonitor", "FileMonitor"):
            self.assertNotIn(marker, runtime)

    def test_architecture_contract_records_g03_fail_closed_save_invariants(self):
        text = (ROOT / "docs/canonical/GRAPHIUM_PRODUCT_ARCHITECTURE_CONTRACT.md").read_text(
            encoding="utf-8"
        )
        for marker in (
            "G03_CONTRACT=FROZEN",
            "G03_SCOPE=GUARDED_SAVE_SAVE_AS",
            "G03_GTK_REQUIRED=NO",
            "G03_SINGLE_PHYSICAL_WRITER=GuardedFileWriter",
            "G03_DIRECT_WRITE_FALLBACK=FORBIDDEN",
            "G03_HARDLINK_POLICY=FAIL_CLOSED",
            "G03_SAVE_AS_REBIND_BEFORE_COMMIT=FORBIDDEN",
            "G03_TARGET_USERS=Leafpad,L3afpad,Mousepad_quick_edit",
        ):
            self.assertIn(marker, text)

    def test_mature_audit_and_dead_code_receipts_exist(self):
        self.assertTrue((ROOT / "evidence/G03_MATURE_SOURCE_AUDIT.txt").is_file())
        self.assertTrue((ROOT / "evidence/G03_DEAD_CODE_AUDIT.txt").is_file())

    def test_mo_records_published_g02_and_g03_entries(self):
        text = (ROOT / "docs/canonical/GRAPHIUM_MEMORIA_OPERATIVA.txt").read_text(encoding="utf-8")
        self.assertIn("b91af48a5688772ceffc7eac202c68e1815d7a36", text)
        self.assertIn("ENTRY G03-001", text)
        self.assertIn("ENTRY G03-004", text)


if __name__ == "__main__":
    unittest.main()
