#!/usr/bin/env python3
"""G09 fail-closed GTK-free 1 MiB planner performance gate."""
from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) in sys.path:
    sys.path.remove(str(ROOT))
sys.path.insert(0, str(ROOT))

from graphium.application.text_transform import build_transformation_plan
from graphium.domain.edit_history import ViewState

LIMIT_MS = 1000.0
SAMPLES = 5
SIZE = 1024 * 1024


def fixture(*, uppercase: bool = False, trailing: bool = False) -> str:
    if trailing:
        line = "Graphium realistic trailing sample alpha beta 0123456789   \n"
    elif uppercase:
        line = "GRAPHIUM REALISTIC MULTILINE SAMPLE ALPHA BETA 0123456789\n"
    else:
        line = "graphium realistic multiline sample alpha beta 0123456789\n"
    return (line * (SIZE // len(line) + 2))[:SIZE]


def median_ms(action: str, text: str, view: ViewState) -> float:
    values: list[float] = []
    for _ in range(SAMPLES):
        started = time.perf_counter()
        plan = build_transformation_plan(
            action,
            source_text=text,
            source_state_id=1,
            before_view=view,
        )
        elapsed = (time.perf_counter() - started) * 1000.0
        if action not in ("move-lines-up", "move-lines-down") and not plan.changed:
            raise SystemExit(f"G09_PERFORMANCE_FAIL: {action} unexpectedly no-op")
        values.append(elapsed)
    return statistics.median(values)


def main() -> None:
    lower = fixture()
    upper = fixture(uppercase=True)
    trailing = fixture(trailing=True)
    middle = len(lower) // 2
    line_start = lower.rfind("\n", 0, middle) + 1
    results = {
        "uppercase": median_ms("uppercase", lower, ViewState(len(lower), 0)),
        "lowercase": median_ms("lowercase", upper, ViewState(len(upper), 0)),
        "duplicate-line-selection": median_ms(
            "duplicate-line-selection", lower, ViewState(line_start + 7, line_start + 7)
        ),
        "move-lines-up": median_ms("move-lines-up", lower, ViewState(line_start + 7, line_start + 7)),
        "move-lines-down": median_ms("move-lines-down", lower, ViewState(line_start + 7, line_start + 7)),
        "trim-trailing-spaces": median_ms("trim-trailing-spaces", trailing, ViewState(0, 0)),
    }
    failed = False
    for action, value in results.items():
        print(f"G09_PLANNER_PERF action={action} median_ms={value:.3f} limit_ms={LIMIT_MS:.0f}")
        if value > LIMIT_MS:
            failed = True
    if failed:
        raise SystemExit("G09_PLANNER_PERFORMANCE=FAIL")
    print("G09_PLANNER_PERFORMANCE=PASS")
    print("FINAL_PHASE=G09_HEADLESS_PLANNER_PERFORMANCE_PASS")


if __name__ == "__main__":
    main()
