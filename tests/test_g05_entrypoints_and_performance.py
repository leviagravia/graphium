from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class G05EntrypointAndPerformanceTests(unittest.TestCase):
    def test_g05_tools_self_root_before_graphium_import(self):
        for rel in (
            "tools/g05_search_performance.py",
            "tools/g05_true_gtk_gate.py",
            "tools/g05_shortcut_audit.py",
        ):
            text=(ROOT/rel).read_text(encoding="utf-8")
            self.assertIn("Path(__file__).resolve().parents[1]", text)
            self.assertLess(text.index("sys.path.insert"), text.index("from graphium"))
            self.assertNotIn('os.environ["PYTHONPATH"]', text)

    def test_g05_bootstrap_probes_run_from_arbitrary_cwd(self):
        for rel, marker in (
            ("tools/g05_search_performance.py", "G05_SEARCH_PERFORMANCE_BOOTSTRAP=PASS"),
            ("tools/g05_true_gtk_gate.py", "G05_TRUE_GTK_BOOTSTRAP=PASS"),
            ("tools/g05_shortcut_audit.py", "G05_SHORTCUT_BOOTSTRAP=PASS"),
        ):
            with self.subTest(tool=rel):
                proc=subprocess.run(
                    [sys.executable, str(ROOT/rel), "--bootstrap-only"],
                    cwd="/", text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    check=False,
                )
                self.assertEqual(proc.returncode,0,proc.stderr)
                self.assertIn(marker,proc.stdout)

    def test_search_performance_gate_covers_1m_10m_unicode_replace_and_scale_refusal(self):
        text=(ROOT/"tools/g05_search_performance.py").read_text(encoding="utf-8")
        for marker in (
            '"find-cs-1m"', '"find-ci-1m"', '"find-ci-expansion-1m"',
            '"find-cs-10m"', '"find-ci-10m"', '"find-ci-expansion-10m"',
            '"replace-all-1m"', '"replace-all-10m"', '"replace-cap-refusal"',
            "MAX_REPLACE_ALL_MATCHES", "MAX_WORKER_RSS_MIB",
            "LIGHTWEIGHT_BUDGET_SEARCH_GATE=PASS",
        ):
            self.assertIn(marker,text)

    def test_true_gtk_gate_covers_search_contract_and_large_multiline_path(self):
        text=(ROOT/"tools/g05_true_gtk_gate.py").read_text(encoding="utf-8")
        for marker in (
            "G05_TRUE_GTK_SEARCHBAR_LAZY=PASS",
            "G05_TRUE_GTK_UNICODE_FIND_WRAP=PASS",
            "G05_TRUE_GTK_REPLACE_ONE_UNDO=PASS",
            "G05_TRUE_GTK_REPLACE_ALL_ONE_UNDO=PASS",
            "G05_TRUE_GTK_RENDERABILITY_PREFLIGHT=PASS",
            "G05_TRUE_GTK_GO_TO_LINE=PASS",
            "G05_TRUE_GTK_LARGE_MULTILINE_SEARCH=PASS",
            "1024 * 1024",
        ):
            self.assertIn(marker,text)


if __name__ == "__main__":
    unittest.main()
