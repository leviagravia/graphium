from __future__ import annotations

import ast
from pathlib import Path
import unittest

from graphium.application.commands import COMMANDS, accelerator_map
from graphium.composition import describe_composition
from graphium.product import VERSION, WORK_ITEM, WORK_ITEM_DESCRIPTION

ROOT = Path(__file__).resolve().parents[1]


def imported_modules(rel: str) -> set[str]:
    tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


class G07ContractArchitectureTests(unittest.TestCase):
    def test_runtime_identity_is_g07(self):
        self.assertEqual(WORK_ITEM, "G07")
        self.assertEqual(VERSION, "0.0.8-g07")
        self.assertEqual(WORK_ITEM_DESCRIPTION, "Recent / Save Copy / Version Copy / Properties / Statistics")

    def test_command_surface_is_exact_and_document_only_statistics(self):
        file_actions = [c.action for c in COMMANDS if c.menu == "File"]
        self.assertEqual(file_actions, [
            "new", "open", "open-recent", "save", "save-as", "save-copy",
            "save-version-copy", "properties", "quit",
        ])
        self.assertEqual([(c.action, c.label) for c in COMMANDS if c.menu == "Document"], [
            ("statistics", "Statistics…"),
        ])
        self.assertEqual([c.action for c in COMMANDS if c.menu == "Recent"], ["clear-recent"])
        for action in ("open-recent", "clear-recent", "save-copy", "save-version-copy", "properties", "statistics"):
            self.assertNotIn(action, accelerator_map())

    def test_g07_application_and_infrastructure_authorities_are_gtk_free(self):
        rels = (
            "graphium/application/recent_files.py",
            "graphium/application/document_copy.py",
            "graphium/application/document_properties.py",
            "graphium/application/text_statistics.py",
            "graphium/domain/document_observation.py",
            "graphium/infrastructure/document_observer.py",
            "graphium/infrastructure/recent_files_store.py",
        )
        for rel in rels:
            imports = imported_modules(rel)
            self.assertFalse(any(name == "gi" or name.startswith("gi.") for name in imports), rel)

    def test_shared_strong_observer_is_loader_and_properties_authority(self):
        loader = (ROOT / "graphium/infrastructure/document_loader.py").read_text(encoding="utf-8")
        observer = (ROOT / "graphium/infrastructure/document_observer.py").read_text(encoding="utf-8")
        composition = (ROOT / "graphium/composition.py").read_text(encoding="utf-8")
        self.assertIn("observe_document(path, capture_bytes=True", loader)
        for marker in ("hashlib.sha256", "os.fstat", "os.stat(logical)", "os.path.realpath", "stat.S_ISREG"):
            self.assertIn(marker, observer)
        self.assertIn("DocumentPropertiesController(session=session, observer=observe_document)", composition)

    def test_one_document_and_one_physical_writer_authority_remain(self):
        descriptor = describe_composition()
        self.assertEqual(descriptor.document_authority_count, 1)
        self.assertEqual(descriptor.physical_writer_authority_count, 1)
        composition = (ROOT / "graphium/composition.py").read_text(encoding="utf-8")
        self.assertEqual(composition.count("GuardedFileWriter()"), 1)
        self.assertIn("DocumentCopyService(session=session, writer=writer)", composition)
        self.assertIn("DocumentSaveService(session=session, writer=writer)", composition)

    def test_recent_store_is_lazy_bounded_versioned_and_product_local(self):
        application = (ROOT / "graphium/application/recent_files.py").read_text(encoding="utf-8")
        store = (ROOT / "graphium/infrastructure/recent_files_store.py").read_text(encoding="utf-8")
        composition = (ROOT / "graphium/composition.py").read_text(encoding="utf-8")
        self.assertIn("MAX_RECENT_FILES = 10", application)
        self.assertIn("if self._loaded:", application)
        self.assertIn('resolve_xdg_paths().state / "recent-files.json"', composition)
        self.assertIn('{"version": 1, "paths": list(values)}', store)
        self.assertIn("0o600", store)
        self.assertIn("os.replace", store)
        self.assertNotIn("os.fsync", store)
        for forbidden in ("sqlite", "GtkRecent", "xbel", "cursor_position", "encoding_profile"):
            self.assertNotIn(forbidden, application + store)

    def test_no_session_manager_monitor_or_background_statistics(self):
        sources = "\n".join(
            (ROOT / rel).read_text(encoding="utf-8")
            for rel in (
                "graphium/application/recent_files.py",
                "graphium/application/document_copy.py",
                "graphium/application/document_properties.py",
                "graphium/application/text_statistics.py",
                "graphium/infrastructure/document_observer.py",
            )
        )
        for forbidden in ("threading", "Thread(", "concurrent.futures", "Gio.FileMonitor", "sqlite3", "SessionManager"):
            self.assertNotIn(forbidden, sources)
        stats = (ROOT / "graphium/application/text_statistics.py").read_text(encoding="utf-8")
        for forbidden in ("timeout_add", "cache", "worker", "signal"):
            self.assertNotIn(forbidden, stats.lower())

    def test_canonical_contract_help_and_evidence_are_synchronized(self):
        contract = (ROOT / "docs/canonical/GRAPHIUM_PRODUCT_ARCHITECTURE_CONTRACT.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "docs/canonical/GRAPHIUM_ROADMAP.md").read_text(encoding="utf-8")
        guide = (ROOT / "docs/user/GRAPHIUM_USER_GUIDE.txt").read_text(encoding="utf-8")
        shortcuts = (ROOT / "docs/user/GRAPHIUM_KEYBOARD_SHORTCUTS.txt").read_text(encoding="utf-8")
        for marker in (
            "G07_CONTRACT=FROZEN", "G07_RECENT_CAP=10", "G07_COPY_BINDING_CHANGE=FORBIDDEN",
            "G07_CHECK_NOW_ACCEPT_BASELINE=FORBIDDEN", "G07_STATISTICS=EXPLICIT_ON_DEMAND_ONLY",
            "G07_DOCUMENT_AUTHORITY_COUNT=1", "G07_PHYSICAL_WRITER_AUTHORITY_COUNT=1",
        ):
            self.assertIn(marker, contract)
        self.assertIn("IMPLEMENTATION R1 BUILT", roadmap)
        for marker in ("Open Recent", "Save a Copy", "Save Version Copy", "Properties", "DOCUMENT STATISTICS"):
            self.assertIn(marker, guide)
        self.assertIn("G07 commands without dedicated accelerators", shortcuts)
        for rel in (
            "evidence/G07_SOURCE_AUDIT.txt", "evidence/G07_MATURE_SOURCE_AUDIT.txt",
            "evidence/G07_LIGHTWEIGHT_BUDGET_AND_CONTRACT_FREEZE.txt", "evidence/G07_FEATHERPAD_SOURCE_RECEIPT.txt",
            "evidence/G07_COMPARATOR_FAILURE_MATURE_SOURCE_REAUDIT_20260817.txt",
            "evidence/G07_R1_INPUT_CONTAMINATION_MATURE_SOURCE_REAUDIT_20260818.txt",
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_canonical_document_cap_remains_three(self):
        docs = [p for p in (ROOT / "docs/canonical").iterdir() if p.is_file()]
        self.assertEqual(len(docs), 3)


if __name__ == "__main__":
    unittest.main()
