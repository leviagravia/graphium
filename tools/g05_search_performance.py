#!/usr/bin/env python3
"""G05 explicit-command search/replace performance qualification.

This is deliberately separate from G04 startup FIRST_EDITABLE/FIRST_VISIBLE. G05 has no
background index: explicit search commands must remain responsive on realistic multiline
1 MiB and 10 MiB documents while keeping memory bounded. Each workload runs in a fresh
child process so ru_maxrss is attributable to that workload rather than accumulated tests.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import resource
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
_root = str(ROOT)
if _root in sys.path:
    sys.path.remove(_root)
sys.path.insert(0, _root)

from graphium.application.search import MAX_REPLACE_ALL_MATCHES, SearchController
from graphium.domain.edit_history import ViewState
from graphium.domain.text_search import SearchScaleError, find_next
from graphium.product import WORK_ITEM


def _g05_or_later() -> bool:
    return WORK_ITEM.startswith("G") and WORK_ITEM[1:].isdigit() and int(WORK_ITEM[1:]) >= 5

MIB = 1024 * 1024

GATES_MS = {
    "find-cs-1m": 1000.0,
    "find-ci-1m": 1500.0,
    "find-ci-expansion-1m": 1500.0,
    "find-cs-10m": 1500.0,
    "find-ci-10m": 3500.0,
    "find-ci-expansion-10m": 3500.0,
    "replace-all-1m": 3000.0,
    "replace-all-10m": 9000.0,
    "replace-cap-refusal": 2000.0,
}
MAX_WORKER_RSS_MIB = 260.0


def fail(message: str) -> None:
    raise SystemExit(f"G05_SEARCH_PERFORMANCE_FAIL: {message}")


def _realistic_find_fixture(size: int, *, expansion: bool) -> str:
    line = "Graphium alpha beta gamma delta 0123456789 plain text search regression line.\n"
    marker = "SearchNeedle\n"
    body_size = max(0, size - len(marker))
    body = (line * (body_size // len(line) + 2))[:body_size]
    if expansion and body:
        # Keep line lengths unchanged and safely below the published G04 line budget.
        midpoint = len(body) // 2
        line_start = body.rfind("\n", 0, midpoint) + 1
        replace_at = min(line_start + 10, max(0, len(body) - 1))
        body = body[:replace_at] + "ß" + body[replace_at + 1 :]
    return body + marker


def _replace_fixture(size: int) -> str:
    prefix = "Graphium replace regression needle "
    padding = "x" * (500 - len(prefix))
    line = prefix + padding + "\n"
    return (line * (size // len(line) + 2))[:size]


def _rss_mib() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux ru_maxrss is KiB.
    return float(value) / 1024.0


def _timed(callable_, repeats: int) -> tuple[list[float], object]:
    samples: list[float] = []
    result = None
    for _ in range(repeats):
        started = time.perf_counter_ns()
        result = callable_()
        samples.append((time.perf_counter_ns() - started) / 1_000_000.0)
    return samples, result


def worker(name: str) -> dict[str, object]:
    if name.startswith("find-"):
        size = 10 * MIB if name.endswith("10m") else MIB
        case_sensitive = "-cs-" in name
        expansion = "-expansion-" in name
        text = _realistic_find_fixture(size, expansion=expansion)
        query = "SearchNeedle" if case_sensitive else "searchneedle"
        samples, result = _timed(
            lambda: find_next(text, query, 0, match_case=case_sensitive, wrap=False),
            5,
        )
        expected = len(text) - len("SearchNeedle\n")
        if result.match is None or result.match.start != expected or result.wrapped:
            fail(f"{name} returned wrong match: {result}")
        detail = {"match_start": result.match.start}
    elif name.startswith("replace-all-"):
        size = 10 * MIB if name.endswith("10m") else MIB
        text = _replace_fixture(size)
        controller = SearchController()
        controller.configure(query="needle", replacement="REPLACED", match_case=True)
        before = ViewState(len(text), len(text))
        samples, result = _timed(
            lambda: controller.build_replace_all_plan(
                source_text=text,
                source_state_id=1,
                before_view=before,
            ),
            3,
        )
        if not result.changed or result.changed_count <= 0:
            fail(f"{name} produced no replacement plan")
        if result.changed_count > MAX_REPLACE_ALL_MATCHES:
            fail(f"{name} exceeded match authority: {result.changed_count}")
        if "needle" in result.final_text:
            fail(f"{name} left source query in result")
        detail = {
            "changed_count": result.changed_count,
            "operations": len(result.operations),
            "payload_chars": result.payload_chars,
        }
    elif name == "replace-cap-refusal":
        text = "a " * (MAX_REPLACE_ALL_MATCHES + 1)
        controller = SearchController()
        controller.configure(query="a", replacement="b", match_case=True)

        def refused():
            try:
                controller.build_replace_all_plan(
                    source_text=text,
                    source_state_id=1,
                    before_view=ViewState(),
                )
            except SearchScaleError:
                return "REFUSED"
            fail("dense Replace All was not refused")

        samples, result = _timed(refused, 3)
        if result != "REFUSED":
            fail("dense Replace All refusal result mismatch")
        detail = {"match_cap": MAX_REPLACE_ALL_MATCHES}
    else:
        fail(f"unknown worker workload: {name}")

    ordered = sorted(samples)
    p90_index = min(len(ordered) - 1, int((len(ordered) - 1) * 0.9 + 0.999999))
    return {
        "workload": name,
        "samples_ms": [round(value, 3) for value in samples],
        "median_ms": round(statistics.median(samples), 3),
        "p90_ms": round(ordered[p90_index], 3),
        "max_rss_mib": round(_rss_mib(), 2),
        **detail,
    }


def run_parent(output: Path | None) -> None:
    if not _g05_or_later():
        fail(f"wrong work item: {WORK_ITEM}")
    workloads = list(GATES_MS)
    results: list[dict[str, object]] = []
    for name in workloads:
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--worker", name],
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=dict(os.environ),
        )
        if proc.returncode != 0:
            fail(f"worker {name} rc={proc.returncode}: {proc.stderr.strip() or proc.stdout.strip()}")
        try:
            result = json.loads(proc.stdout.strip().splitlines()[-1])
        except Exception as exc:
            fail(f"worker {name} returned invalid JSON: {exc}: {proc.stdout!r}")
        gate = GATES_MS[name]
        result["gate_median_ms"] = gate
        result["gate_rss_mib"] = MAX_WORKER_RSS_MIB
        if float(result["median_ms"]) > gate:
            fail(f"{name} median {result['median_ms']} ms > {gate} ms")
        if float(result["max_rss_mib"]) > MAX_WORKER_RSS_MIB:
            fail(f"{name} RSS {result['max_rss_mib']} MiB > {MAX_WORKER_RSS_MIB} MiB")
        results.append(result)
        print(
            f"G05_SEARCH_PERF {name} median_ms={result['median_ms']} "
            f"p90_ms={result['p90_ms']} rss_mib={result['max_rss_mib']}"
        )

    receipt = {
        "schema": "graphium-g05-search-performance-v1",
        "work_item": WORK_ITEM,
        "metric": "EXPLICIT_COMMAND_LATENCY",
        "background_index": False,
        "max_replace_all_matches": MAX_REPLACE_ALL_MATCHES,
        "worker_rss_gate_mib": MAX_WORKER_RSS_MIB,
        "results": results,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"G05_SEARCH_PERFORMANCE_RECEIPT={output}")
    print("G05_SEARCH_PERFORMANCE=PASS")
    print("LIGHTWEIGHT_BUDGET_SEARCH_GATE=PASS")
    print("FINAL_PHASE=G05_SEARCH_PERFORMANCE_PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", choices=list(GATES_MS))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--bootstrap-only", action="store_true")
    args = parser.parse_args()
    if args.bootstrap_only:
        if not _g05_or_later():
            fail(f"bootstrap wrong work item: {WORK_ITEM}")
        print(f"G05_SEARCH_PERFORMANCE_BOOTSTRAP=PASS root={ROOT}")
        return
    if args.worker:
        print(json.dumps(worker(args.worker), sort_keys=True))
        return
    run_parent(args.output)


if __name__ == "__main__":
    main()
