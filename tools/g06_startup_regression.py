#!/usr/bin/env python3
"""G06 anti-bloat comparison against the certified G04 T480 startup baseline."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_root = str(ROOT)
if _root in sys.path:
    sys.path.remove(_root)
sys.path.insert(0, _root)

from graphium.product import WORK_ITEM


def _g06_or_later() -> bool:
    return WORK_ITEM.startswith("G") and WORK_ITEM[1:].isdigit() and int(WORK_ITEM[1:]) >= 6


G04_FIRST_EDITABLE_BASELINE_MS = {
    "empty": 227.383,
    "5KiB": 231.208,
    "1MiB": 626.719,
    "10MiB": 4015.953,
}
G04_FIRST_EDITABLE_BASELINE_RSS_MIB = {
    "empty": 54.36,
    "5KiB": 54.49,
    "1MiB": 58.87,
    "10MiB": 108.02,
}
G04_FIRST_VISIBLE_GRAPHIUM_BASELINE_MS = {
    "empty": 244.814,
    "5KiB": 278.106,
    "1MiB": 273.236,
    "10MiB": 591.753,
}

MAX_TIME_RATIO = 1.25
MAX_TIME_ADDITIVE_MS = 75.0
MAX_RSS_RATIO = 1.25
MAX_RSS_ADDITIVE_MIB = 20.0


def fail(message: str) -> None:
    raise SystemExit(f"G06_STARTUP_REGRESSION_FAIL: {message}")


def time_limit(baseline: float) -> float:
    return max(baseline * MAX_TIME_RATIO, baseline + MAX_TIME_ADDITIVE_MS)


def rss_limit(baseline: float) -> float:
    return max(baseline * MAX_RSS_RATIO, baseline + MAX_RSS_ADDITIVE_MIB)


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        fail(f"could not read {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"receipt is not an object: {path}")
    return value


def main() -> None:
    if "--bootstrap-only" in sys.argv:
        if not _g06_or_later():
            fail(f"wrong work item: {WORK_ITEM}")
        print(f"G06_STARTUP_REGRESSION_BOOTSTRAP=PASS root={ROOT}")
        return

    ap = argparse.ArgumentParser()
    ap.add_argument("--first-editable", type=Path, required=True)
    ap.add_argument("--first-visible", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    if not _g06_or_later():
        fail(f"wrong work item: {WORK_ITEM}")

    editable = load_json(args.first_editable)
    visible = load_json(args.first_visible)
    if editable.get("metric") != "FIRST_EDITABLE" or editable.get("cross_product_comparable") is not False:
        fail("FIRST_EDITABLE receipt protocol mismatch")
    if visible.get("metric") != "FIRST_VISIBLE" or visible.get("cross_product_comparable") is not True:
        fail("FIRST_VISIBLE receipt protocol mismatch")

    editable_workloads = editable.get("workloads")
    visible_apps = visible.get("applications")
    if not isinstance(editable_workloads, dict) or not isinstance(visible_apps, dict):
        fail("receipt workloads missing")
    # This is a Graphium anti-bloat *self* gate. Comparator completeness belongs to
    # the separate common FIRST_VISIBLE comparative receipt. A blocked external
    # comparator must not turn into a Graphium startup product failure.
    if "Graphium" not in visible_apps:
        fail("Graphium FIRST_VISIBLE result missing")
    graph_visible = visible_apps["Graphium"].get("workloads")
    if not isinstance(graph_visible, dict):
        fail("Graphium FIRST_VISIBLE workloads missing")

    checks: dict[str, dict] = {}
    passed = True
    for workload, baseline in G04_FIRST_EDITABLE_BASELINE_MS.items():
        current = float(editable_workloads[workload]["median_ms"])
        limit = time_limit(baseline)
        ok = current <= limit
        passed &= ok
        checks[f"first_editable_{workload}"] = {
            "baseline": baseline,
            "current": current,
            "limit": limit,
            "delta_percent": (current / baseline - 1.0) * 100.0,
            "pass": ok,
        }
        print(
            f"G06_STARTUP_REGRESSION FIRST_EDITABLE {workload} "
            f"baseline_ms={baseline:.3f} current_ms={current:.3f} "
            f"limit_ms={limit:.3f} pass={'YES' if ok else 'NO'}"
        )

        rss_baseline = G04_FIRST_EDITABLE_BASELINE_RSS_MIB[workload]
        rss_current = float(editable_workloads[workload]["median_rss_mib"])
        rss_max = rss_limit(rss_baseline)
        rss_ok = rss_current <= rss_max
        passed &= rss_ok
        checks[f"first_editable_rss_{workload}"] = {
            "baseline": rss_baseline,
            "current": rss_current,
            "limit": rss_max,
            "delta_percent": (rss_current / rss_baseline - 1.0) * 100.0,
            "pass": rss_ok,
        }

    for workload, baseline in G04_FIRST_VISIBLE_GRAPHIUM_BASELINE_MS.items():
        current = float(graph_visible[workload]["median_ms"])
        limit = time_limit(baseline)
        ok = current <= limit
        passed &= ok
        checks[f"first_visible_{workload}"] = {
            "baseline": baseline,
            "current": current,
            "limit": limit,
            "delta_percent": (current / baseline - 1.0) * 100.0,
            "pass": ok,
        }
        print(
            f"G06_STARTUP_REGRESSION FIRST_VISIBLE {workload} "
            f"baseline_ms={baseline:.3f} current_ms={current:.3f} "
            f"limit_ms={limit:.3f} pass={'YES' if ok else 'NO'}"
        )

    report = {
        "work_item": "G06",
        "baseline": "G04 certified T480 desktop validation 2026-08-14",
        "policy": {
            "time": "limit=max(baseline*1.25, baseline+75ms)",
            "rss": "limit=max(baseline*1.25, baseline+20MiB)",
            "purpose": "anti-bloat self-regression gate; not a cross-product FIRST_EDITABLE claim",
        },
        "checks": checks,
        "pass": passed,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if not passed:
        print("G06_STARTUP_REGRESSION_GATE=FAIL")
        raise SystemExit(2)
    print("G06_STARTUP_REGRESSION_GATE=PASS")
    print("G06_FIRST_EDITABLE_CROSS_PRODUCT_CLAIM=FORBIDDEN_UNTIL_G12")
    print("FINAL_PHASE=G06_STARTUP_REGRESSION_PASS")


if __name__ == "__main__":
    main()
