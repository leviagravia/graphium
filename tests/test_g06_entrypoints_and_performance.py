from __future__ import annotations

from pathlib import Path
import json
import subprocess
import tempfile
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class G06EntrypointAndPerformanceTests(unittest.TestCase):
    def test_g06_tools_self_root_before_graphium_import(self):
        for rel in (
            "tools/g06_shortcut_audit.py",
            "tools/g06_true_gtk_gate.py",
            "tools/g06_view_performance.py",
            "tools/g06_startup_regression.py",
        ):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("Path(__file__).resolve().parents[1]", text)
            self.assertLess(text.index("sys.path.insert"), text.index("from graphium"))
            self.assertNotIn('os.environ["PYTHONPATH"]', text)

    def test_g06_bootstrap_probes_run_from_arbitrary_cwd(self):
        for rel, marker in (
            ("tools/g06_shortcut_audit.py", "G06_SHORTCUT_BOOTSTRAP=PASS"),
            ("tools/g06_true_gtk_gate.py", "G06_TRUE_GTK_BOOTSTRAP=PASS"),
            ("tools/g06_view_performance.py", "G06_VIEW_PERFORMANCE_BOOTSTRAP=PASS"),
            ("tools/g06_startup_regression.py", "G06_STARTUP_REGRESSION_BOOTSTRAP=PASS"),
        ):
            with self.subTest(tool=rel):
                proc = subprocess.run(
                    [sys.executable, str(ROOT / rel), "--bootstrap-only"],
                    cwd="/",
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn(marker, proc.stdout)

    def test_true_gtk_gate_covers_view_contract_and_content_neutrality(self):
        text = (ROOT / "tools/g06_true_gtk_gate.py").read_text(encoding="utf-8")
        for marker in (
            "G06_TRUE_GTK_VIEW_ACTIONS=PASS",
            "G06_TRUE_GTK_SETTINGS_PERSISTENCE=PASS",
            "G06_TRUE_GTK_LINE_NUMBERS_NATIVE_GUTTER=PASS",
            "G06_TRUE_GTK_WORD_WRAP=PASS",
            "G06_TRUE_GTK_FONT_ZOOM_SPLIT=PASS",
            "G06_TRUE_GTK_COMPACT_STATUS=PASS",
            "G06_TRUE_GTK_VIEW_CONTENT_NEUTRAL=PASS",
            "G06_TRUE_GTK_LARGE_MULTILINE_VIEW=PASS",
            "G06_TRUE_GTK_TOOLBAR_ABSENT=PASS",
            "G06_TRUE_GTK_MODAL_OWNERSHIP=PASS",
            "G06_TRUE_GTK_LIFECYCLE_BOUNDARIES=PASS",
        ):
            self.assertIn(marker, text)


    def test_true_gtk_gate_owns_lifecycle_boundaries_before_fixture_open(self):
        text = (ROOT / "tools/g06_true_gtk_gate.py").read_text(encoding="utf-8")
        self.assertIn("UnexpectedModalTripwire", text)
        self.assertIn("unexpected modal dialog", text)
        self.assertIn("top.response(Gtk.ResponseType.CANCEL)", text)
        self.assertIn("assert_clean_lifecycle", text)
        self.assertIn('phase("CRLF_STATUS_CLEAN_BOUNDARY_PASS")', text)
        self.assertIn('undo.activate(None)', text)
        self.assertIn('open_clean(window, big, label="1 MiB multiline fixture", tripwire=tripwire)', text)
        self.assertIn('tripwire.arm("Font action")', text)
        # The only raw product open_path call belongs inside the fail-fast clean-open helper.
        self.assertEqual(text.count("window.open_path("), 1)
        # Unexpected dialogs may be cancelled only to unwind a nested loop; they must then fail.
        self.assertLess(text.index("top.response(Gtk.ResponseType.CANCEL)"), text.index("fail(detected)"))

    def test_view_performance_gate_owns_clean_lifecycle_boundaries(self):
        text = (ROOT / "tools/g06_view_performance.py").read_text(encoding="utf-8")
        self.assertIn("assert_clean_lifecycle", text)
        self.assertIn("open_clean(window, fixture_path", text)
        self.assertIn("G06_VIEW_PERFORMANCE_LIFECYCLE_BOUNDARIES=PASS", text)
        self.assertIn("shared read-only fixture bytes changed", text)
        for marker in (
            "INPUT_CONTAMINATION_EXIT_CODE = 3",
            "key-press-event",
            "button-press-event",
            "G06_VIEW_INPUT_CONTAMINATION=",
            "PRODUCT_VERDICT=NOT_REACHED",
            "G06_VIEW_PERFORMANCE_INVALID_DESKTOP_INPUT_CONTAMINATION",
            "G06_VIEW_PERFORMANCE_INPUT_CONTAMINATION_TRIPWIRE=PASS",
            '"text_logging": "NONE"',
        ):
            self.assertIn(marker, text)
        self.assertEqual(text.count("window.open_path("), 1)

    def test_view_performance_gate_covers_1m_10m_and_lightweight_budget(self):
        text = (ROOT / "tools/g06_view_performance.py").read_text(encoding="utf-8")
        for marker in (
            "MAX_LINE_NUMBERS_10M_P90_MS",
            "MAX_WRAP_1M_P90_MS",
            "MAX_WRAP_10M_P90_MS",
            "MAX_ZOOM_10M_P90_MS",
            "MAX_FONT_APPLY_10M_P90_MS",
            "MAX_STATUS_1000_UPDATES_MS",
            "MAX_RSS_MIB",
            "line-numbers-1m",
            "line-numbers-10m",
            "wrap-1m",
            "wrap-10m",
            "zoom-10m",
            "font-apply-10m",
            "status-1000-updates",
            "LIGHTWEIGHT_BUDGET_VIEW_GATE=PASS",
        ):
            self.assertIn(marker, text)

    def test_view_performance_oracle_is_single_transition_fresh_process(self):
        text = (ROOT / "tools/g06_view_performance.py").read_text(encoding="utf-8")
        for marker in (
            "PRIMING_PROCESSES = 1",
            "MEASURED_PROCESSES = 7",
            "WORKER_TIMEOUT_SECONDS = 30",
            "FRAME_DEADLINE_SECONDS = 15.0",
            "G06_VIEW_PERFORMANCE_ORACLE=SINGLE_TRANSITION_FRESH_PROCESS",
            "after-paint",
            "G06_VIEW_SCENARIO_BEGIN",
            "G06_VIEW_WORKER_BEGIN",
            "G06_VIEW_PERFORMANCE_FIRST_POST_TRANSITION_FRAME=PASS",
        ):
            self.assertIn(marker, text)
        self.assertNotIn("def benchmark_toggle", text)
        self.assertNotIn("def benchmark_zoom", text)
        # Parent imports remain GTK-free; worker-local imports are below run_worker().
        self.assertGreater(text.index('import gi'), text.index('def run_worker('))
        # The mature-toolkit boundary is version-coherent: Gdk and Gtk must both be
        # frozen to GTK3 before either GI namespace is imported.
        gdk_req = text.index('gi.require_version("Gdk", "3.0")')
        gtk_req = text.index('gi.require_version("Gtk", "3.0")', gdk_req)
        gi_import = text.index('from gi.repository import Gdk, Gtk', gtk_req)
        self.assertLess(gdk_req, gtk_req)
        self.assertLess(gtk_req, gi_import)

    def test_view_performance_headless_orchestrator_protocol_selftest(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "tools/g06_view_performance.py"), "--selftest-protocol"],
            cwd="/", text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(
            "G06_VIEW_PERFORMANCE_SELFTEST_PROTOCOL=PASS priming=1 measured=7 transitions_per_worker=1",
            proc.stdout,
        )

    def test_view_performance_headless_budget_is_fail_closed_and_binds_font(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "tools/g06_view_performance.py"), "--selftest-budget"],
            cwd="/", text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(
            "G06_VIEW_PERFORMANCE_SELFTEST_BUDGET=PASS font_budget_binding=PASS fail_closed=PASS",
            proc.stdout,
        )

    def test_startup_regression_gate_uses_certified_g04_self_baseline(self):
        text = (ROOT / "tools/g06_startup_regression.py").read_text(encoding="utf-8")
        for marker in (
            "G04_FIRST_EDITABLE_BASELINE_MS",
            "G04_FIRST_VISIBLE_GRAPHIUM_BASELINE_MS",
            "MAX_TIME_RATIO = 1.25",
            "MAX_TIME_ADDITIVE_MS = 75.0",
            "MAX_RSS_ADDITIVE_MIB = 20.0",
            "G06_STARTUP_REGRESSION_GATE=PASS",
            "G06_FIRST_EDITABLE_CROSS_PRODUCT_CLAIM=FORBIDDEN_UNTIL_G12",
        ):
            self.assertIn(marker, text)

    def test_startup_regression_tool_accepts_baseline_and_rejects_material_regression(self):
        editable_workloads = {
            "empty": {"median_ms": 227.383, "median_rss_mib": 54.36},
            "5KiB": {"median_ms": 231.208, "median_rss_mib": 54.49},
            "1MiB": {"median_ms": 626.719, "median_rss_mib": 58.87},
            "10MiB": {"median_ms": 4015.953, "median_rss_mib": 108.02},
        }
        graph_visible = {
            "empty": {"median_ms": 244.814},
            "5KiB": {"median_ms": 278.106},
            "1MiB": {"median_ms": 273.236},
            "10MiB": {"median_ms": 591.753},
        }
        apps = {name: {"workloads": dict(graph_visible)} for name in
                ("Graphium", "Leafpad", "L3afpad", "Mousepad", "FeatherPad")}
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            editable = td / "editable.json"
            visible = td / "visible.json"
            output = td / "out.json"
            editable.write_text(json.dumps({
                "metric": "FIRST_EDITABLE",
                "cross_product_comparable": False,
                "workloads": editable_workloads,
            }), encoding="utf-8")
            visible.write_text(json.dumps({
                "metric": "FIRST_VISIBLE",
                "cross_product_comparable": True,
                "applications": apps,
            }), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(ROOT / "tools/g06_startup_regression.py"),
                 "--first-editable", str(editable), "--first-visible", str(visible),
                 "--output", str(output)],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("G06_STARTUP_REGRESSION_GATE=PASS", proc.stdout)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(payload["pass"])

            bad = json.loads(editable.read_text(encoding="utf-8"))
            bad["workloads"]["empty"]["median_ms"] = 500.0
            editable.write_text(json.dumps(bad), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(ROOT / "tools/g06_startup_regression.py"),
                 "--first-editable", str(editable), "--first-visible", str(visible),
                 "--output", str(output)],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(proc.returncode, 2)
            self.assertIn("G06_STARTUP_REGRESSION_GATE=FAIL", proc.stdout)


if __name__ == "__main__":
    unittest.main()
