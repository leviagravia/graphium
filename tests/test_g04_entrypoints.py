from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class G04EntrypointTests(unittest.TestCase):
    def test_product_launcher_self_roots_before_graphium_import(self):
        text = (ROOT / "bin/graphium").read_text(encoding="utf-8")
        self.assertLess(text.index("sys.path.insert"), text.index("from graphium"))
        self.assertIn("Path(__file__).resolve().parents[1]", text)

    def test_executable_graphium_importing_tools_self_root(self):
        for rel in ("tools/g04_shortcut_audit.py", "tools/g04_true_gtk_gate.py"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("Path(__file__).resolve().parents[1]", text)
            self.assertLess(text.index("sys.path.insert"), text.index("from graphium"))

    def test_bootstrap_probes_run_from_arbitrary_cwd(self):
        with self.subTest(tool="shortcut"):
            p = subprocess.run(
                [sys.executable, str(ROOT / "tools/g04_shortcut_audit.py"), "--bootstrap-only"],
                cwd="/",
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("G04_SHORTCUT_BOOTSTRAP=PASS", p.stdout)
        with self.subTest(tool="true-gtk"):
            p = subprocess.run(
                [sys.executable, str(ROOT / "tools/g04_true_gtk_gate.py"), "--bootstrap-only"],
                cwd="/",
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("G04_TRUE_GTK_BOOTSTRAP=PASS", p.stdout)

    def test_no_global_pythonpath_workaround_in_desktop_tools(self):
        for path in [ROOT / "bin/graphium", *sorted((ROOT / "tools").glob("g04_*.py"))]:
            self.assertNotIn('os.environ["PYTHONPATH"]', path.read_text(encoding="utf-8"))

    def test_gtk_environment_probe_uses_real_gtk3_version_accessors(self):
        text = (ROOT / "tools/g04_gtk_environment.py").read_text(encoding="utf-8")
        self.assertNotIn("Gtk.get_version", text)
        self.assertIn("Gtk.get_major_version()", text)
        self.assertIn("Gtk.get_minor_version()", text)
        self.assertIn("Gtk.get_micro_version()", text)


if __name__ == "__main__":
    unittest.main()
