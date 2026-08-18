#!/usr/bin/env python3
"""True-GTK G06 gate for lightweight View/status integration."""
from __future__ import annotations

import os
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


def _g06_or_later() -> bool:
    return WORK_ITEM.startswith("G") and WORK_ITEM[1:].isdigit() and int(WORK_ITEM[1:]) >= 6

if "--bootstrap-only" in sys.argv:
    if not _g06_or_later():
        raise SystemExit(f"G06_TRUE_GTK_BOOTSTRAP=FAIL work_item={WORK_ITEM}")
    print(f"G06_TRUE_GTK_BOOTSTRAP=PASS root={ROOT}")
    raise SystemExit(0)

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

import graphium.adapters.gtk.window as window_module
from graphium.adapters.gtk.application import GraphiumApplication
from graphium.infrastructure.view_settings_store import JsonViewSettingsStore
from graphium.paths import resolve_xdg_paths


def fail(message: str) -> None:
    raise SystemExit(f"G06_TRUE_GTK_FAIL: {message}")


def drain(seconds: float = 0.0) -> None:
    deadline = time.monotonic() + seconds
    while True:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        if time.monotonic() >= deadline:
            return
        time.sleep(0.005)


def descendants(widget):
    yield widget
    if isinstance(widget, Gtk.Container):
        for child in widget.get_children():
            yield from descendants(child)


def action_bool(window, name: str) -> bool:
    action = window.lookup_action(name)
    if action is None or action.get_state() is None:
        fail(f"stateful action missing: {name}")
    return action.get_state().get_boolean()


def text_of(buffer: Gtk.TextBuffer) -> str:
    a, b = buffer.get_bounds()
    return buffer.get_text(a, b, True)


def user_insert(buffer: Gtk.TextBuffer, text: str) -> None:
    buffer.begin_user_action()
    try:
        buffer.insert(buffer.get_end_iter(), text)
    finally:
        buffer.end_user_action()
    drain(0.01)


def phase(name: str) -> None:
    print(f"G06_TRUE_GTK_PHASE={name}", flush=True)




class UnexpectedModalTripwire:
    """Fail-closed escape hatch for calls that must remain non-modal in this gate.

    The tripwire is armed *before* a potentially modal-capable product call.  If an
    unexpected Gtk.Dialog enters a nested gtk_dialog_run() loop, the GLib source still
    runs inside that nested loop, records the dialog, responds CANCEL only to unwind it,
    and forces the scenario to FAIL after control returns.  It never turns a dialog into
    a successful test path.
    """

    def __init__(self) -> None:
        self._source_id: int | None = None
        self._label = ""
        self._detected: str | None = None

    def _poll(self) -> bool:
        for top in Gtk.Window.list_toplevels():
            if isinstance(top, Gtk.Dialog) and top.get_visible():
                title = top.get_title() or top.__class__.__name__
                self._detected = f"{self._label}: unexpected modal dialog {title!r}"
                try:
                    top.response(Gtk.ResponseType.CANCEL)
                except Exception:
                    top.destroy()
                self._source_id = None
                return False
        return True

    def arm(self, label: str) -> None:
        if self._source_id is not None:
            fail(f"modal tripwire already armed for {self._label}")
        self._label = label
        self._detected = None
        self._source_id = GLib.timeout_add(20, self._poll)

    def finish(self) -> None:
        if self._source_id is not None:
            GLib.source_remove(self._source_id)
            self._source_id = None
        detected = self._detected
        self._detected = None
        if detected is not None:
            fail(detected)

    def cancel(self) -> None:
        if self._source_id is not None:
            GLib.source_remove(self._source_id)
            self._source_id = None
        self._detected = None


def assert_clean_lifecycle(window, *, label: str) -> None:
    if window.core.session.modified:
        fail(f"{label}: lifecycle boundary is Modified")
    if window.core.history.current_state_id != window.core.session.saved_editor_state_id:
        fail(f"{label}: current state is not the exact Saved state")

def open_clean(window, path: Path, *, label: str, tripwire: UnexpectedModalTripwire) -> None:
    """Open a fixture only from an explicitly clean, non-modal lifecycle boundary."""
    assert_clean_lifecycle(window, label=f"{label} pre-open")
    tripwire.arm(label)
    try:
        completed = window.open_path(str(path))
    finally:
        tripwire.finish()
    if not completed:
        fail(f"{label}: Open failed without an expected dialog path")
    drain(0.03)
    assert_clean_lifecycle(window, label=f"{label} post-open")


def main() -> None:
    if not _g06_or_later():
        fail(f"wrong work item: {WORK_ITEM}")

    with tempfile.TemporaryDirectory(prefix="graphium-g06-true-gtk-") as td:
        td = Path(td)
        os.environ["HOME"] = str(td / "home")
        os.environ["XDG_CONFIG_HOME"] = str(td / "config")
        os.environ["XDG_CACHE_HOME"] = str(td / "cache")
        os.environ["XDG_DATA_HOME"] = str(td / "data")
        os.environ["XDG_STATE_HOME"] = str(td / "state")
        for key in ("HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
            Path(os.environ[key]).mkdir(parents=True, exist_ok=True)

        app = GraphiumApplication()
        if not app.register(None):
            fail("Gtk.Application registration failed")
        app.activate(); drain(0.08)
        window = app.window
        if window is None:
            fail("application did not create a window")
        tripwire = UnexpectedModalTripwire()
        if any(isinstance(w, Gtk.Toolbar) for w in descendants(window)):
            fail("Toolbar appeared despite G06 REJECT v1")

        for name in (
            "status-bar", "line-numbers", "word-wrap", "font",
            "zoom-in", "zoom-out", "zoom-reset", "full-screen",
        ):
            if window.lookup_action(name) is None:
                fail(f"View action missing: {name}")

        if not action_bool(window, "status-bar"):
            fail("default Status Bar state is not ON")
        if action_bool(window, "line-numbers") or action_bool(window, "word-wrap"):
            fail("default uncluttered line-number/wrap state changed")
        if window.text_view.zoom_percent != 100:
            fail("initial zoom is not 100%")

        before_text = text_of(window.buffer)
        before_state = window.core.history.current_state_id
        before_saved = window.core.session.saved_editor_state_id

        window.lookup_action("line-numbers").activate(None); drain(0.05)
        if not action_bool(window, "line-numbers"):
            fail("Line Numbers action did not become active")
        if window.text_view.get_border_window_size(Gtk.TextWindowType.LEFT) <= 0:
            fail("Line Numbers did not create native LEFT border window")

        window.lookup_action("word-wrap").activate(None); drain(0.03)
        if window.text_view.get_wrap_mode() != Gtk.WrapMode.WORD_CHAR:
            fail("Word Wrap did not use WORD_CHAR")

        window.lookup_action("status-bar").activate(None); drain(0.02)
        if window._status_bar.get_visible():
            fail("Status Bar did not hide")
        window.lookup_action("status-bar").activate(None); drain(0.02)
        if not window._status_bar.get_visible():
            fail("Status Bar did not show")

        original_choose_font = window_module.choose_font
        try:
            window_module.choose_font = lambda *_args, **_kwargs: ("DejaVu Sans Mono", 13.0)
            tripwire.arm("Font action")
            try:
                window.lookup_action("font").activate(None); drain(0.03)
            finally:
                tripwire.finish()
        finally:
            window_module.choose_font = original_choose_font
        if window.text_view.base_font != ("DejaVu Sans Mono", 13.0):
            fail(f"Font action did not project persistent base font: {window.text_view.base_font}")

        window.lookup_action("zoom-in").activate(None); drain(0.02)
        if window.text_view.zoom_percent != 110:
            fail("Zoom In did not reach 110%")
        window.lookup_action("zoom-reset").activate(None); drain(0.02)
        if window.text_view.zoom_percent != 100:
            fail("Reset Zoom did not return to 100%")

        if text_of(window.buffer) != before_text:
            fail("View commands mutated document text")
        if window.core.history.current_state_id != before_state:
            fail("View commands advanced editor history state")
        if window.core.session.saved_editor_state_id != before_saved:
            fail("View commands changed savepoint relation")

        config_path = resolve_xdg_paths().config / "view.json"
        persisted = JsonViewSettingsStore(config_path).load()
        if not (persisted.line_numbers and persisted.word_wrap and persisted.status_bar):
            fail(f"direct View settings did not persist: {persisted}")
        if persisted.font_family != "DejaVu Sans Mono" or persisted.font_size_points != 13.0:
            fail(f"Font setting did not persist: {persisted}")
        if "zoom" in config_path.read_text(encoding="utf-8").lower():
            fail("transient Zoom leaked into persistent config")

        phase("CRLF_STATUS_BEGIN")
        crlf = td / "crlf.txt"
        crlf.write_bytes(b"one\r\ntwo\r\n")
        open_clean(window, crlf, label="CRLF fixture", tripwire=tripwire)
        if window._status_document.get_text() != "UTF-8 · CRLF · Saved":
            fail(f"representation status mismatch: {window._status_document.get_text()!r}")
        target = window.buffer.get_iter_at_line_offset(1, 1)
        window.buffer.place_cursor(target); drain(0.02)
        if window._status_position.get_text() != "Ln 2, Col 2":
            fail(f"cursor status mismatch: {window._status_position.get_text()!r}")
        user_insert(window.buffer, "X")
        if not window._status_document.get_text().endswith("Modified"):
            fail("status did not project Modified after native edit")

        # Close the status-projection scenario at the same Saved lifecycle boundary at
        # which it started.  Opening the next fixture while Modified would correctly
        # invoke the real unsaved-changes dialog, which this View gate does not own.
        undo = window.lookup_action("undo")
        if undo is None or not undo.get_enabled():
            fail("status scenario could not restore clean state: Undo unavailable")
        undo.activate(None); drain(0.02)
        assert_clean_lifecycle(window, label="CRLF status scenario after Undo")
        if window._status_document.get_text() != "UTF-8 · CRLF · Saved":
            fail(f"status did not return to Saved after Undo: {window._status_document.get_text()!r}")
        if text_of(window.buffer) != "one\ntwo\n":
            fail("status scenario Undo did not restore exact CRLF editor text")
        phase("CRLF_STATUS_CLEAN_BOUNDARY_PASS")

        phase("LARGE_MULTILINE_BEGIN")
        big = td / "one-mib-multiline.txt"
        line = "Graphium G06 integrated line-number regression 0123456789 abcdefghijklmnopqrstuvwxyz\n"
        text = (line * ((1024 * 1024 // len(line)) + 2))[: 1024 * 1024]
        big.write_text(text, encoding="utf-8")
        open_clean(window, big, label="1 MiB multiline fixture", tripwire=tripwire)
        drain(0.05)
        end = window.buffer.get_end_iter()
        window.buffer.place_cursor(end)
        window.text_view.scroll_to_mark(window.buffer.get_insert(), 0.0, False, 0.0, 0.0)
        t0 = time.monotonic()
        drain(0.12)
        if time.monotonic() - t0 > 1.0:
            fail("large-file View scroll exceeded bounded responsiveness window")
        if window.text_view.get_border_window_size(Gtk.TextWindowType.LEFT) <= 0:
            fail("line-number gutter disappeared on large multiline document")
        phase("LARGE_MULTILINE_PASS")
        assert_clean_lifecycle(window, label="G06 True-GTK final boundary")

        tripwire.cancel()
        window.destroy(); drain(0.02); app.quit()

    print("G06_TRUE_GTK_VIEW_ACTIONS=PASS")
    print("G06_TRUE_GTK_SETTINGS_PERSISTENCE=PASS")
    print("G06_TRUE_GTK_LINE_NUMBERS_NATIVE_GUTTER=PASS")
    print("G06_TRUE_GTK_WORD_WRAP=PASS")
    print("G06_TRUE_GTK_FONT_ZOOM_SPLIT=PASS")
    print("G06_TRUE_GTK_COMPACT_STATUS=PASS")
    print("G06_TRUE_GTK_VIEW_CONTENT_NEUTRAL=PASS")
    print("G06_TRUE_GTK_LARGE_MULTILINE_VIEW=PASS")
    print("G06_TRUE_GTK_TOOLBAR_ABSENT=PASS")
    print("G06_TRUE_GTK_MODAL_OWNERSHIP=PASS")
    print("G06_TRUE_GTK_LIFECYCLE_BOUNDARIES=PASS")
    print("FINAL_PHASE=G06_TRUE_GTK_GATE_PASS")


if __name__ == "__main__":
    main()
