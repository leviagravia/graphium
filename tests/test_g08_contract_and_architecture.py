from __future__ import annotations

import ast
from pathlib import Path
import unittest

from graphium.adapters.gtk.print_pagination import (
    IncrementalVisualPage,
    IncrementalVisualPaginator,
    VisualLinePage,
    VisualLineSpan,
    logical_line_chunk_end,
    paginate_visual_line_heights,
)
from graphium.application.commands import COMMANDS, accelerator_map
from graphium.product import VERSION, WORK_ITEM, WORK_ITEM_DESCRIPTION

ROOT = Path(__file__).resolve().parents[1]


class G08ContractArchitectureTests(unittest.TestCase):
    def test_runtime_identity_is_g08(self):
        self.assertEqual(WORK_ITEM, "G08")
        self.assertEqual(VERSION, "0.0.9-g08")
        self.assertEqual(WORK_ITEM_DESCRIPTION, "Page Setup / Print Preview / Print / Startup Isolation")

    def test_file_command_surface_and_accelerators_are_exact(self):
        file_commands = [(c.action, c.label, c.accelerator) for c in COMMANDS if c.menu == "File"]
        self.assertEqual(file_commands, [
            ("new", "New", "<Ctrl>N"),
            ("open", "Open…", "<Ctrl>O"),
            ("open-recent", "Open Recent", None),
            ("save", "Save", "<Ctrl>S"),
            ("save-as", "Save As…", "<Ctrl><Shift>S"),
            ("save-copy", "Save a Copy…", None),
            ("save-version-copy", "Save Version Copy…", None),
            ("properties", "Properties…", None),
            ("page-setup", "Page Setup…", None),
            ("print-preview", "Print Preview", "<Ctrl><Shift>P"),
            ("print", "Print…", "<Ctrl>P"),
            ("quit", "Quit", "<Ctrl>Q"),
        ])
        self.assertEqual(accelerator_map()["print"], "<Ctrl>P")
        self.assertEqual(accelerator_map()["print-preview"], "<Ctrl><Shift>P")
        self.assertNotIn("page-setup", accelerator_map())

    def test_print_adapter_is_strictly_lazy_from_window_module(self):
        window_path = ROOT / "graphium/adapters/gtk/window.py"
        tree = ast.parse(window_path.read_text(encoding="utf-8"))
        top_imports: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                top_imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                top_imports.add(node.module)
        self.assertFalse(any("printing" in name for name in top_imports))
        text = window_path.read_text(encoding="utf-8")
        self.assertIn("self._print_controller = None", text)
        self.assertIn("from .printing import GraphiumPrintController", text)
        self.assertIn("def _ensure_print_controller", text)
        self.assertIn("def _capture_print_snapshot", text)

    def test_printing_owns_no_background_custom_preview_or_sourceview(self):
        text = (ROOT / "graphium/adapters/gtk/printing.py").read_text(encoding="utf-8")
        for forbidden in (
            "GtkSourceView", "GtkSourcePrintCompositor", "threading", "Thread(",
            "concurrent.futures", "timeout_add", "idle_add",
            'connect("preview"', "custom preview",
        ):
            self.assertNotIn(forbidden, text)
        self.assertIn("Gtk.PrintOperation()", text)
        self.assertIn("Gtk.PrintOperationAction.PREVIEW", text)
        self.assertIn("Gtk.PrintOperationAction.PRINT_DIALOG", text)
        self.assertIn("PangoCairo.show_layout_line", text)
        self.assertIn("layout.set_wrap(Pango.WrapMode.WORD_CHAR)", text)

    def test_native_async_done_lifecycle_is_single_inflight_and_fail_closed(self):
        text = (ROOT / "graphium/adapters/gtk/printing.py").read_text(encoding="utf-8")
        for marker in (
            "operation.set_allow_async(True)",
            'operation.connect("done", self._on_done)',
            "Gtk.PrintOperationResult.IN_PROGRESS",
            "self._active_operation = operation",
            "if operation is not self._active_operation",
            "def _reject_if_busy",
            "Printing is already in progress",
            "self._active_job = job",
            "self._active_operation = None",
        ):
            self.assertIn(marker, text)
        self.assertNotIn("operation.set_allow_async(False)", text)

    def test_render_cleanup_is_exact_once_across_end_print_and_done(self):
        text = (ROOT / "graphium/adapters/gtk/printing.py").read_text(encoding="utf-8")
        for marker in (
            '"_render_released"',
            "def render_released(self) -> bool",
            "if self._render_released:",
            "self._render_released = True",
            "if job is not None and not job.render_released:",
        ):
            self.assertIn(marker, text)
        self.assertNotIn("Idempotent even if GTK already emitted end-print", text)

    def test_page_setup_store_is_product_local_atomic_0600_and_load_fail_soft(self):
        text = (ROOT / "graphium/adapters/gtk/printing.py").read_text(encoding="utf-8")
        for marker in (
            'resolve_xdg_paths().config / "page-setup.ini"',
            "os.lstat(self.path)",
            "stat.S_ISREG", "Gtk.PageSetup.new_from_file", "Gtk.PageSetup()",
            "tempfile.mkstemp", "0o600", "setup.to_file(temp_name)",
            "os.fsync", "os.replace(temp_name, self.path)",
        ):
            self.assertIn(marker, text)
        # Loading is only reached from lazy controller construction, never Graphium composition.
        composition = (ROOT / "graphium/composition.py").read_text(encoding="utf-8")
        self.assertNotIn("page-setup.ini", composition)
        self.assertNotIn("GraphiumPrintController", composition)

    def test_snapshot_uses_live_text_logical_basename_and_persistent_base_font(self):
        window = (ROOT / "graphium/adapters/gtk/window.py").read_text(encoding="utf-8")
        capture = window[window.index("    def _capture_print_snapshot"):window.index("    def _action_page_setup")]
        self.assertIn("self.buffer_port.capture_full()", capture)
        self.assertIn("self.core.session.logical_path", capture)
        self.assertIn('else "Untitled"', capture)
        self.assertIn("self.text_view.base_font", capture)
        self.assertNotIn("zoom_percent", capture)
        self.assertNotIn("line_numbers", capture)
        self.assertNotIn("word_wrap", capture)

    def test_visual_line_pagination_never_splits_a_measured_line(self):
        self.assertEqual(
            paginate_visual_line_heights([10, 10, 10, 10], usable_height=25),
            (VisualLinePage(0, 2), VisualLinePage(2, 4)),
        )
        self.assertEqual(
            paginate_visual_line_heights([40, 5, 5], usable_height=25),
            (VisualLinePage(0, 1), VisualLinePage(1, 3)),
        )
        with self.assertRaises(ValueError):
            paginate_visual_line_heights([10, 0], usable_height=25)

    def test_incremental_visual_paginator_preserves_chunk_spans_and_page_boundaries(self):
        paginator = IncrementalVisualPaginator(usable_height=25)
        paginator.add_chunk(0, [10, 10, 10])
        paginator.add_chunk(1, [5, 20, 5])
        self.assertEqual(
            paginator.finish(),
            (
                IncrementalVisualPage((VisualLineSpan(0, 0, 2),)),
                IncrementalVisualPage((
                    VisualLineSpan(0, 2, 3),
                    VisualLineSpan(1, 0, 1),
                )),
                IncrementalVisualPage((VisualLineSpan(1, 1, 3),)),
            ),
        )
        self.assertTrue(paginator.finished)
        with self.assertRaises(RuntimeError):
            paginator.add_chunk(2, [1])

    def test_logical_line_chunking_is_bounded_and_never_splits_source_lines(self):
        text = "aa\nbbbb\ncc\n"
        first = logical_line_chunk_end(text, 0, target_chars=5, max_logical_lines=8)
        self.assertEqual(text[:first], "aa\n")
        second = logical_line_chunk_end(text, first, target_chars=5, max_logical_lines=8)
        self.assertEqual(text[first:second], "bbbb\n")
        self.assertEqual(
            logical_line_chunk_end("x" * 20, 0, target_chars=4, max_logical_lines=1),
            20,
        )
        with self.assertRaises(ValueError):
            logical_line_chunk_end(text, -1, target_chars=5, max_logical_lines=8)

    def test_print_job_paginates_incrementally_from_pango_visual_line_geometry(self):
        text = (ROOT / "graphium/adapters/gtk/printing.py").read_text(encoding="utf-8")
        for marker in (
            'operation.connect("paginate", job.paginate)',
            "def paginate(self, operation, context)",
            "_PAGINATION_CHUNK_TARGET_CHARS = 16 * 1024",
            "_PAGINATION_CHUNK_MAX_LOGICAL_LINES = 64",
            "layout.get_line_count()", "layout.get_line_readonly(index)",
            "line.get_extents()", "logical.height", "IncrementalVisualPaginator",
            "operation.set_n_pages(max(1, len(self.pages)))",
        ):
            self.assertIn(marker, text)
        begin = text[text.index("    def begin_print"):text.index("    def _next_text_chunk")]
        self.assertNotIn("create_pango_layout", begin)
        self.assertNotIn("set_text", begin)
        for forbidden in ("splitlines()", "characters_per_page", "get_visible_rect()"):
            self.assertNotIn(forbidden, text)

    def test_binding_probe_exercises_exact_gtk3_page_setup_and_export_path(self):
        probe = (ROOT / "tools/g08_print_binding_probe.py").read_text(encoding="utf-8")
        for marker in (
            'gi.require_version("Gtk", "3.0")', "Gtk.get_major_version()",
            "Gtk.print_run_page_setup_dialog", "_PageSetupStore", "Gtk.PrintOperation()",
            "Gtk.PrintOperationAction.EXPORT", "PangoCairo.show_layout",
            "G08_PRINT_BINDING_PROBE=PASS", "CANDIDATE_ATTEMPT_CONSUMED=NO",
        ):
            self.assertIn(marker, probe)

    def test_executable_entrypoint_mode_topology_is_preserved(self):
        expected = [
            ROOT / "VERIFY_GRAPHIUM.py",
            ROOT / "bin/graphium",
            ROOT / "bin/graphium-selftest",
            *sorted((ROOT / "tools").glob("g*.py")),
        ]
        for path in expected:
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertEqual(path.stat().st_mode & 0o777, 0o755)

    def test_canonical_document_cap_remains_three(self):
        self.assertEqual(len([p for p in (ROOT / "docs/canonical").iterdir() if p.is_file()]), 3)


if __name__ == "__main__":
    unittest.main()
