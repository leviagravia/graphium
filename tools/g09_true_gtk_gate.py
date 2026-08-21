#!/usr/bin/env python3
"""True-GTK real-window hostile gate for Graphium G09 explicit text transformations."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) in sys.path:
    sys.path.remove(str(ROOT))
sys.path.insert(0, str(ROOT))

from graphium.product import WORK_ITEM

if "--bootstrap-only" in sys.argv:
    if WORK_ITEM != "G09":
        raise SystemExit(f"G09_TRUE_GTK_BOOTSTRAP=FAIL work_item={WORK_ITEM}")
    print(f"G09_TRUE_GTK_BOOTSTRAP=PASS root={ROOT}")
    raise SystemExit(0)

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from graphium.adapters.gtk.application import GraphiumApplication
from graphium.domain.edit_history import ViewState

LIMIT_SECONDS = 3.0
SIZE = 1024 * 1024


def fail(message: str) -> None:
    raise SystemExit(f"G09_TRUE_GTK_FAIL: {message}")


def drain(seconds: float = 0.0) -> None:
    deadline = time.monotonic() + seconds
    while True:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        if time.monotonic() >= deadline:
            return
        time.sleep(0.003)


def text_of(buffer) -> str:
    start, end = buffer.get_bounds()
    return buffer.get_text(start, end, True)


def view_of(window) -> ViewState:
    return window.buffer_port.capture_view()


def establish(window, text: str, view: ViewState) -> int:
    window.core.editor.initialize_new_text(text, clean=True)
    insert = window.buffer.get_iter_at_offset(view.insert_offset)
    bound = window.buffer.get_iter_at_offset(view.selection_bound_offset)
    window.buffer.select_range(insert, bound)
    window._refresh_projection()
    drain(0.01)
    return window.core.history.current_state_id


def activate(window, action: str) -> None:
    obj = window.lookup_action(action)
    if obj is None:
        fail(f"missing action {action}")
    obj.activate(None)
    drain(0.01)


def prove_one_undo_redo(window, source: str, expected: str, before: ViewState, target: ViewState, action: str) -> None:
    saved = establish(window, source, before)
    activate(window, action)
    if text_of(window.buffer) != expected:
        fail(f"{action} text mismatch: {text_of(window.buffer)!r}")
    if view_of(window) != target:
        fail(f"{action} view mismatch: {view_of(window)} != {target}")
    if not window.core.session.modified or len(window.core.history.undo_stack) != 1:
        fail(f"{action} did not create exactly one modified Undo group")
    activate(window, "undo")
    if text_of(window.buffer) != source or view_of(window) != before:
        fail(f"{action} Undo did not restore exact source/view")
    if window.core.session.modified:
        fail(f"{action} Undo did not restore Saved")
    activate(window, "redo")
    if text_of(window.buffer) != expected or view_of(window) != target:
        fail(f"{action} Redo mismatch")
    if not window.core.session.modified or window.core.history.current_state_id == saved:
        fail(f"{action} Redo did not restore transformed state")


def realistic(*, upper: bool = False, trailing: bool = False) -> str:
    if trailing:
        line = "Graphium realistic trailing sample alpha beta 0123456789   \n"
    elif upper:
        line = "GRAPHIUM REALISTIC MULTILINE SAMPLE ALPHA BETA 0123456789\n"
    else:
        line = "graphium realistic multiline sample alpha beta 0123456789\n"
    return (line * (SIZE // len(line) + 2))[:SIZE]


def timed_action(window, action: str, text: str, view: ViewState) -> float:
    establish(window, text, view)
    started = time.monotonic()
    activate(window, action)
    elapsed = time.monotonic() - started
    if elapsed > LIMIT_SECONDS:
        fail(f"1 MiB {action} responsiveness >{LIMIT_SECONDS:.1f}s: {elapsed:.3f}s")
    return elapsed


def main() -> None:
    if WORK_ITEM != "G09":
        fail(f"wrong work item {WORK_ITEM}")
    with tempfile.TemporaryDirectory(prefix="graphium-g09-true-gtk-") as td_raw:
        td = Path(td_raw)
        for key, name in (
            ("HOME", "home"), ("XDG_CONFIG_HOME", "config"), ("XDG_CACHE_HOME", "cache"),
            ("XDG_DATA_HOME", "data"), ("XDG_STATE_HOME", "state"),
        ):
            os.environ[key] = str(td / name)
            Path(os.environ[key]).mkdir(parents=True, exist_ok=True)

        app = GraphiumApplication()
        if not app.register(None):
            fail("Gtk.Application registration failed")
        app.activate(); drain(0.08)
        window = app.window
        if window is None:
            fail("application did not create window")

        for action in (
            "uppercase", "lowercase", "duplicate-line-selection",
            "move-lines-up", "move-lines-down", "trim-trailing-spaces",
        ):
            if window.lookup_action(action) is None:
                fail(f"missing G09 action {action}")

        # Case Unicode + reversed direction, exact one Undo/Redo.
        prove_one_undo_redo(
            window, "a straße z", "a STRASSE z", ViewState(8, 2), ViewState(9, 2), "uppercase"
        )
        prove_one_undo_redo(
            window, "İX", "i\u0307X", ViewState(0, 1), ViewState(0, 2), "lowercase"
        )
        prove_one_undo_redo(
            window, "abcde", "abcdbcde", ViewState(4, 1), ViewState(7, 4),
            "duplicate-line-selection",
        )
        prove_one_undo_redo(
            window, "a\nb\nc", "a\nc\nb", ViewState(2, 2), ViewState(4, 4), "move-lines-down"
        )
        prove_one_undo_redo(
            window, "a\nb", "b\na", ViewState(2, 2), ViewState(0, 0), "move-lines-up"
        )
        prove_one_undo_redo(
            window, "a  \n b\t\n c\u00a0 \n", "a\n b\n c\u00a0\n",
            ViewState(0, 0), ViewState(0, 0), "trim-trailing-spaces",
        )

        # Exact no-op state/history/view neutrality.
        before_id = establish(window, "ABC", ViewState(3, 0))
        before_history = window.core.history.checkpoint()
        before_view = view_of(window)
        activate(window, "uppercase")
        if window.core.history.current_state_id != before_id or window.core.history.checkpoint() != before_history:
            fail("uppercase semantic no-op changed history/state identity")
        if view_of(window) != before_view or window.core.session.modified:
            fail("uppercase semantic no-op changed view/dirty state")
        establish(window, "a\nb\n", ViewState(4, 4))
        before_id = window.core.history.current_state_id
        activate(window, "move-lines-up")
        if window.core.history.current_state_id != before_id or window.core.session.modified:
            fail("terminal sentinel Move Up was not an exact no-op")

        # No-selection case actions are disabled in normal UI projection.
        establish(window, "abc", ViewState(1, 1))
        if window.lookup_action("uppercase").get_enabled() or window.lookup_action("lowercase").get_enabled():
            fail("case actions enabled without selection")

        lower = realistic()
        upper = realistic(upper=True)
        trailing = realistic(trailing=True)
        middle = len(lower) // 2
        line_start = lower.rfind("\n", 0, middle) + 1
        scenarios = (
            ("uppercase", lower, ViewState(len(lower), 0)),
            ("lowercase", upper, ViewState(len(upper), 0)),
            ("duplicate-line-selection", lower, ViewState(line_start + 7, line_start + 7)),
            ("move-lines-up", lower, ViewState(line_start + 7, line_start + 7)),
            ("move-lines-down", lower, ViewState(line_start + 7, line_start + 7)),
            ("trim-trailing-spaces", trailing, ViewState(0, 0)),
        )
        for action, text, view in scenarios:
            elapsed = timed_action(window, action, text, view)
            print(f"G09_TRUE_GTK_1M action={action} elapsed_s={elapsed:.3f} limit_s={LIMIT_SECONDS:.1f}")

        window.destroy(); drain(0.02); app.quit()

    print("G09_TRUE_GTK_UNICODE=PASS")
    print("G09_TRUE_GTK_SELECTION_DIRECTION=PASS")
    print("G09_TRUE_GTK_MOVE_FINAL_EOL=PASS")
    print("G09_TRUE_GTK_TRIM_SCOPE=PASS")
    print("G09_TRUE_GTK_UNDO_REDO=PASS")
    print("G09_TRUE_GTK_NOOP_IDENTITY=PASS")
    print("G09_TRUE_GTK_1M_RESPONSIVENESS=PASS")
    print("FINAL_PHASE=G09_TRUE_GTK_GATE_PASS")


if __name__ == "__main__":
    main()
