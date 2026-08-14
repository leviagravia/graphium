from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

# Import directly from the tool; it intentionally has no GTK dependency.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import g04_performance as perf  # noqa: E402


class G04PerformanceProtocolTests(unittest.TestCase):
    def test_parse_ready_line_accepts_one_complete_record(self):
        self.assertEqual(perf.parse_ready_line(b"READY 123 456"), (123, 456))

    def test_parse_ready_line_rejects_old_partial_or_key_value_schema(self):
        for line in (b"READY 123", b"pid=123", b"monotonic_ns=456", b""):
            with self.assertRaises((RuntimeError, ValueError)):
                perf.parse_ready_line(line)

    def test_inherited_pipe_waits_for_complete_newline_record(self):
        # Deterministic protocol test: model two kernel-pipe reads without relying on
        # scheduler timing or a sleeping subprocess. The first readable chunk is partial;
        # _read_ready_line must continue until the second chunk terminates the record.
        proc = SimpleNamespace(poll=lambda: None, returncode=None)
        with patch.object(perf.select, "select", side_effect=[([77], [], []), ([77], [], [])]), \
             patch.object(perf.os, "read", side_effect=[b"READY 999 ", b"123456\n"]):
            line = perf._read_ready_line(77, proc, timeout=2.0)
        self.assertEqual(line, b"READY 999 123456")

    def test_exact_benchmark_has_no_ready_file_race(self):
        text = (Path(__file__).resolve().parents[1] / "tools/g04_performance.py").read_text(encoding="utf-8")
        self.assertNotIn("exists()", text)
        self.assertNotIn("monotonic_ns=", text)
        self.assertIn("os.pipe()", text)
        self.assertIn("select.select", text)

    def test_exact_benchmark_isolates_xdg_and_rejects_impossible_timestamp(self):
        text = (Path(__file__).resolve().parents[1] / "tools/g04_performance.py").read_text(encoding="utf-8")
        self.assertIn('"--state-root"', text)
        self.assertIn('"XDG_CONFIG_HOME"', text)
        self.assertIn('if stamp < start:', text)
        self.assertIn('env["GDK_BACKEND"] = "x11"', text)

    def test_comparator_version_probe_cannot_open_gui_via_guessed_short_option(self):
        text = (Path(__file__).resolve().parents[1] / "tools/g04_comparator_proxy.py").read_text(encoding="utf-8")
        self.assertIn('[cmd[0], "--version"]', text)
        self.assertNotIn('["-v"]', text)
        self.assertIn('graphium_version_from_source', text)
        self.assertIn('if name == "Graphium"', text)
        self.assertIn('if proc.poll() is not None:', text)

    def test_comparators_are_process_isolated_for_exact_pid_oracle(self):
        text = (Path(__file__).resolve().parents[1] / "tools/g04_comparator_proxy.py").read_text(encoding="utf-8")
        self.assertIn('commands["Mousepad"].append("--disable-server")', text)
        self.assertIn('commands["FeatherPad"].append("--standalone")', text)
        self.assertIn('exact spawned-PID oracle requires process isolation', text)
        self.assertIn('pid_for_window(wid) == proc.pid', text)
        self.assertNotIn('accept_any_featherpad_pid', text)


if __name__ == "__main__":
    unittest.main()
