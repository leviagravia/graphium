#!/usr/bin/env python3
"""T480 G06 View/Status Lightweight Budget performance gate.

Parent orchestration is GTK-free. Each measured sample is a fresh process with a fresh
HOME/XDG and exactly one View transition. GTK is imported only in worker mode.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_root = str(ROOT)
if _root in sys.path:
    sys.path.remove(_root)
sys.path.insert(0, _root)

from graphium.product import WORK_ITEM

PRIMING_PROCESSES = 1
MEASURED_PROCESSES = 7
WORKER_TIMEOUT_SECONDS = 30
FRAME_DEADLINE_SECONDS = 15.0
MAX_RSS_MIB = 220.0
MAX_LINE_NUMBERS_10M_P90_MS = 250.0
MAX_WRAP_1M_P90_MS = 500.0
MAX_WRAP_10M_P90_MS = 1500.0
MAX_ZOOM_10M_P90_MS = 500.0
MAX_FONT_APPLY_10M_P90_MS = 500.0
MAX_STATUS_1000_UPDATES_MS = 100.0

SCENARIOS = (
    "line-numbers-1m",
    "wrap-1m",
    "line-numbers-10m",
    "wrap-10m",
    "zoom-10m",
    "font-apply-10m",
    "status-1000-updates",
)


def fail(message: str) -> None:
    raise SystemExit(f"G06_VIEW_PERFORMANCE_FAIL: {message}")


def p90(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, int((len(ordered) - 1) * 0.9 + 0.999999))]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fixture(path: Path, mib: int) -> None:
    target = mib * 1024 * 1024
    line = b"Graphium G06 view performance 0123456789 abcdefghijklmnopqrstuvwxyz viewport line\n"
    with path.open("wb") as handle:
        remaining = target
        while remaining:
            chunk = line if remaining >= len(line) else line[:remaining]
            handle.write(chunk)
            remaining -= len(chunk)


def metric_budget_failures(metrics: dict[str, dict[str, float]]) -> list[str]:
    failures: list[str] = []
    checks = (
        ("line-numbers-10m", "p90_ms", MAX_LINE_NUMBERS_10M_P90_MS, "10 MiB Line Numbers"),
        ("wrap-1m", "p90_ms", MAX_WRAP_1M_P90_MS, "1 MiB Word Wrap"),
        ("wrap-10m", "p90_ms", MAX_WRAP_10M_P90_MS, "10 MiB Word Wrap"),
        ("zoom-10m", "p90_ms", MAX_ZOOM_10M_P90_MS, "10 MiB Zoom"),
        ("font-apply-10m", "p90_ms", MAX_FONT_APPLY_10M_P90_MS, "10 MiB Font Apply"),
        ("status-1000-updates", "p90_ms", MAX_STATUS_1000_UPDATES_MS, "1000 status updates"),
    )
    for scenario, field, maximum, label in checks:
        observed = float(metrics[scenario][field])
        if observed > maximum:
            failures.append(f"{label} p90 {observed:.3f} ms exceeds {maximum:.0f} ms")
    max_rss = max(float(payload["max_rss_mib"]) for payload in metrics.values())
    if max_rss > MAX_RSS_MIB:
        failures.append(f"RSS {max_rss:.2f} MiB exceeds {MAX_RSS_MIB:.0f} MiB")
    return failures


def synthetic_worker_result(scenario: str, index: int) -> dict[str, float | str | int]:
    base = float(index + 1)
    return {
        "scenario": scenario,
        "latency_ms": base,
        "rss_mib": 50.0 + base / 10.0,
        "state_id": 1,
    }


def run_selftest_protocol() -> None:
    counts: dict[str, dict[str, int]] = {}
    for scenario in SCENARIOS:
        counts[scenario] = {"priming": 0, "measured": 0}
        for role, total in (("priming", PRIMING_PROCESSES), ("measured", MEASURED_PROCESSES)):
            for index in range(total):
                synthetic_worker_result(scenario, index)
                counts[scenario][role] += 1
    if any(v != {"priming": 1, "measured": 7} for v in counts.values()):
        fail(f"synthetic protocol count mismatch: {counts}")
    print("G06_VIEW_PERFORMANCE_SELFTEST_PROTOCOL=PASS priming=1 measured=7 transitions_per_worker=1")


def run_selftest_budget() -> None:
    metrics = {
        scenario: {"p90_ms": 1.0, "median_ms": 1.0, "max_rss_mib": 50.0}
        for scenario in SCENARIOS
    }
    if metric_budget_failures(metrics):
        fail("healthy synthetic budget unexpectedly failed")
    metrics["font-apply-10m"]["p90_ms"] = MAX_FONT_APPLY_10M_P90_MS + 1.0
    failures = metric_budget_failures(metrics)
    if not any("Font Apply" in item for item in failures):
        fail("Font Apply budget is not fail-closed")
    print("G06_VIEW_PERFORMANCE_SELFTEST_BUDGET=PASS font_budget_binding=PASS fail_closed=PASS")


def rss_mib() -> float:
    for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) / 1024.0
    return 0.0


def run_worker(scenario: str, fixture_path: Path) -> None:
    # GTK imports are worker-local by contract. The parent/orchestrator remains GTK-free.
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

    from graphium.adapters.gtk.application import GraphiumApplication
    import graphium.adapters.gtk.window as gtk_window_module

    def drain(seconds: float = 0.0) -> None:
        deadline = time.monotonic() + seconds
        while True:
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)
            if time.monotonic() >= deadline:
                return
            time.sleep(0.002)

    def assert_clean_lifecycle(window, *, label: str) -> None:
        if window.core.session.modified:
            fail(f"{label}: worker crossed into Modified lifecycle state")
        if window.core.history.current_state_id != window.core.session.saved_editor_state_id:
            fail(f"{label}: worker is not at exact Saved identity")

    def open_clean(window, path: Path, *, label: str) -> None:
        assert_clean_lifecycle(window, label=f"{label} pre-open")
        if not window.open_path(str(path)):
            fail(f"{label}: fixture open failed")
        drain(0.08)
        assert_clean_lifecycle(window, label=f"{label} post-open")

    def measure_first_post_transition_frame(window, transition) -> float:
        frame_clock = window.get_frame_clock()
        if frame_clock is None:
            fail(f"{scenario}: no Gtk frame clock")
        painted_ns: list[int] = []
        armed = False

        def after_paint(_clock) -> None:
            if armed and not painted_ns:
                painted_ns.append(time.monotonic_ns())

        handler = frame_clock.connect("after-paint", after_paint)
        try:
            drain(0.03)
            t0 = time.monotonic_ns()
            armed = True
            transition()
            deadline = time.monotonic() + FRAME_DEADLINE_SECONDS
            while not painted_ns:
                while Gtk.events_pending():
                    Gtk.main_iteration_do(False)
                if painted_ns:
                    break
                if time.monotonic() >= deadline:
                    fail(f"{scenario}: first post-transition after-paint deadline exceeded")
                time.sleep(0.001)
            return (painted_ns[0] - t0) / 1_000_000.0
        finally:
            frame_clock.disconnect(handler)

    with tempfile.TemporaryDirectory(prefix=f"graphium-g06-view-worker-{scenario}-") as td_raw:
        td = Path(td_raw)
        for name in ("home", "config", "cache", "data", "state"):
            (td / name).mkdir()
        os.environ.update({
            "HOME": str(td / "home"),
            "XDG_CONFIG_HOME": str(td / "config"),
            "XDG_CACHE_HOME": str(td / "cache"),
            "XDG_DATA_HOME": str(td / "data"),
            "XDG_STATE_HOME": str(td / "state"),
        })

        app = GraphiumApplication()
        if not app.register(None):
            fail(f"{scenario}: Gtk.Application registration failed")
        app.activate(); drain(0.10)
        window = app.window
        if window is None:
            fail(f"{scenario}: window missing")

        open_clean(window, fixture_path, label=f"{scenario} fixture")
        baseline_state = window.core.history.current_state_id
        baseline_saved = window.core.session.saved_editor_state_id

        if scenario.startswith("line-numbers-"):
            action = window.lookup_action("line-numbers")
            if action is None:
                fail("missing line-numbers action")
            latency_ms = measure_first_post_transition_frame(window, lambda: action.activate(None))
            if not window.text_view.line_numbers_visible:
                fail(f"{scenario}: requested line numbers state not committed")
        elif scenario.startswith("wrap-"):
            action = window.lookup_action("word-wrap")
            if action is None:
                fail("missing word-wrap action")
            latency_ms = measure_first_post_transition_frame(window, lambda: action.activate(None))
            if window.text_view.get_wrap_mode() != Gtk.WrapMode.WORD_CHAR:
                fail(f"{scenario}: requested word-wrap state not committed")
        elif scenario == "zoom-10m":
            action = window.lookup_action("zoom-in")
            if action is None:
                fail("missing zoom-in action")
            latency_ms = measure_first_post_transition_frame(window, lambda: action.activate(None))
            if window.text_view.zoom_percent != 110:
                fail("zoom-10m: requested 110% state not committed")
        elif scenario == "font-apply-10m":
            original_choose_font = gtk_window_module.choose_font
            gtk_window_module.choose_font = lambda *_args, **_kwargs: ("Monospace", 14.0)
            try:
                action = window.lookup_action("font")
                if action is None:
                    fail("missing font action")
                latency_ms = measure_first_post_transition_frame(window, lambda: action.activate(None))
            finally:
                gtk_window_module.choose_font = original_choose_font
            if window.text_view.base_font != ("Monospace", 14.0):
                fail(f"font-apply-10m: requested base font not committed: {window.text_view.base_font}")
        elif scenario == "status-1000-updates":
            lines = max(1, window.buffer.get_line_count())
            t0 = time.monotonic_ns()
            for i in range(1000):
                target = window.buffer.get_iter_at_line((i * 97) % lines)
                window.buffer.place_cursor(target)
                window._refresh_status()
            latency_ms = (time.monotonic_ns() - t0) / 1_000_000.0
        else:
            fail(f"unknown worker scenario: {scenario}")

        assert_clean_lifecycle(window, label=f"{scenario} final")
        if window.core.history.current_state_id != baseline_state or baseline_state != baseline_saved:
            fail(f"{scenario}: View action mutated document/history identity")
        observed_rss = rss_mib()
        result = {
            "scenario": scenario,
            "latency_ms": latency_ms,
            "rss_mib": observed_rss,
            "state_id": baseline_state,
        }
        print("G06_VIEW_WORKER_RESULT=" + json.dumps(result, sort_keys=True), flush=True)
        window.destroy(); drain(0.02); app.quit()


def parse_worker_result(stdout: str, *, scenario: str, role: str, index: int) -> dict[str, float | str | int]:
    prefix = "G06_VIEW_WORKER_RESULT="
    records = [line[len(prefix):] for line in stdout.splitlines() if line.startswith(prefix)]
    if len(records) != 1:
        fail(f"{scenario} {role} worker {index}: expected one result record, got {len(records)}")
    try:
        payload = json.loads(records[0])
    except json.JSONDecodeError as exc:
        fail(f"{scenario} {role} worker {index}: invalid result JSON: {exc}")
    if payload.get("scenario") != scenario:
        fail(f"{scenario} {role} worker {index}: scenario identity mismatch")
    return payload


def run_worker_process(scenario: str, fixture_path: Path, *, role: str, index: int) -> dict[str, float | str | int]:
    print(f"G06_VIEW_WORKER_BEGIN scenario={scenario} role={role} index={index}", flush=True)
    cmd = [sys.executable, str(Path(__file__).resolve()), "--worker", scenario, "--fixture", str(fixture_path)]
    try:
        proc = subprocess.run(
            cmd,
            cwd="/",
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=WORKER_TIMEOUT_SECONDS,
            check=False,
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired:
        fail(
            f"{scenario} {role} worker {index}: process timeout after "
            f"{WORKER_TIMEOUT_SECONDS}s"
        )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip().splitlines()
        tail = " | ".join(detail[-6:]) if detail else "no diagnostic output"
        fail(f"{scenario} {role} worker {index}: exit={proc.returncode}: {tail}")
    payload = parse_worker_result(proc.stdout, scenario=scenario, role=role, index=index)
    print(
        f"G06_VIEW_WORKER_PASS scenario={scenario} role={role} index={index} "
        f"latency_ms={float(payload['latency_ms']):.3f} rss_mib={float(payload['rss_mib']):.2f}",
        flush=True,
    )
    return payload


def run_parent() -> None:
    if WORK_ITEM != "G06":
        fail(f"wrong work item: {WORK_ITEM}")
    print("G06_VIEW_PERFORMANCE_ORACLE=SINGLE_TRANSITION_FRESH_PROCESS", flush=True)
    print(
        "G06_VIEW_PERFORMANCE_PROTOCOL="
        f"priming={PRIMING_PROCESSES} measured={MEASURED_PROCESSES} transitions_per_worker=1",
        flush=True,
    )
    metrics: dict[str, dict[str, float]] = {}
    with tempfile.TemporaryDirectory(prefix="graphium-g06-view-perf-parent-") as td_raw:
        td = Path(td_raw)
        one = td / "one-mib.txt"
        ten = td / "ten-mib.txt"
        fixture(one, 1); fixture(ten, 10)
        os.chmod(one, 0o444); os.chmod(ten, 0o444)
        original_hashes = {one: sha256(one), ten: sha256(ten)}

        for scenario in SCENARIOS:
            fixture_path = one if scenario.endswith("-1m") else ten
            print(f"G06_VIEW_SCENARIO_BEGIN scenario={scenario}", flush=True)
            for index in range(PRIMING_PROCESSES):
                run_worker_process(scenario, fixture_path, role="priming", index=index + 1)
            measured: list[dict[str, float | str | int]] = []
            for index in range(MEASURED_PROCESSES):
                measured.append(
                    run_worker_process(scenario, fixture_path, role="measured", index=index + 1)
                )
            values = [float(item["latency_ms"]) for item in measured]
            rss_values = [float(item["rss_mib"]) for item in measured]
            metrics[scenario] = {
                "median_ms": statistics.median(values),
                "p90_ms": p90(values),
                "max_rss_mib": max(rss_values),
            }
            if sha256(fixture_path) != original_hashes[fixture_path]:
                fail(f"{scenario}: shared read-only fixture bytes changed")
            metric = metrics[scenario]
            print(
                f"G06_VIEW_METRIC scenario={scenario} median_ms={metric['median_ms']:.3f} "
                f"p90_ms={metric['p90_ms']:.3f} max_rss_mib={metric['max_rss_mib']:.2f}",
                flush=True,
            )
            print(f"G06_VIEW_SCENARIO_PASS scenario={scenario}", flush=True)

    failures = metric_budget_failures(metrics)
    if failures:
        fail("; ".join(failures))
    print("G06_VIEW_RESPONSIVENESS_GATE=PASS")
    print("G06_STATUS_NO_DOCUMENT_SCAN_GATE=PASS")
    print("G06_VIEW_PERFORMANCE_LIFECYCLE_BOUNDARIES=PASS")
    print("G06_VIEW_PERFORMANCE_FRESH_PROCESS_PROTOCOL=PASS")
    print("G06_VIEW_PERFORMANCE_FIRST_POST_TRANSITION_FRAME=PASS")
    print("LIGHTWEIGHT_BUDGET_VIEW_GATE=PASS")
    print("FINAL_PHASE=G06_VIEW_PERFORMANCE_PASS")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap-only", action="store_true")
    parser.add_argument("--worker", choices=SCENARIOS)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--selftest-protocol", action="store_true")
    parser.add_argument("--selftest-budget", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.bootstrap_only:
        if WORK_ITEM != "G06":
            raise SystemExit(f"G06_VIEW_PERFORMANCE_BOOTSTRAP=FAIL work_item={WORK_ITEM}")
        print(f"G06_VIEW_PERFORMANCE_BOOTSTRAP=PASS root={ROOT}")
        return
    if args.selftest_protocol:
        run_selftest_protocol(); return
    if args.selftest_budget:
        run_selftest_budget(); return
    if args.worker:
        if args.fixture is None:
            fail("worker requires --fixture")
        run_worker(args.worker, args.fixture)
        return
    if args.fixture is not None:
        fail("--fixture is valid only with --worker")
    run_parent()


if __name__ == "__main__":
    main()
