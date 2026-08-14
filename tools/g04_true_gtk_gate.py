#!/usr/bin/env python3
"""True-GTK automated gate for rebuilt Graphium G04."""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_root = str(ROOT)
if _root in sys.path:
    sys.path.remove(_root)
sys.path.insert(0, _root)

if "--bootstrap-only" in sys.argv:
    # This probe certifies only deterministic Graphium package discovery.  GTK availability
    # is a separate desktop-environment precondition checked by the real True-GTK gate.
    from graphium.product import WORK_ITEM
    if not WORK_ITEM.startswith("G"):
        raise SystemExit(f"G04_TRUE_GTK_BOOTSTRAP=FAIL work_item={WORK_ITEM}")
    print(f"G04_TRUE_GTK_BOOTSTRAP=PASS root={ROOT} current_work_item={WORK_ITEM}")
    raise SystemExit(0)

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, Gtk

from graphium.adapters.gtk.application import GraphiumApplication
from graphium.application.renderability import MAX_INTERACTIVE_LINE_CHARS


def fail(message: str) -> None:
    raise SystemExit(f"TRUE_GTK_FAIL: {message}")


def drain(seconds: float = 0.0) -> None:
    deadline = time.monotonic() + seconds
    while True:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        if time.monotonic() >= deadline:
            break
        time.sleep(0.005)


def descendants(widget):
    yield widget
    if isinstance(widget, Gtk.Container):
        for child in widget.get_children():
            yield from descendants(child)


def text_of(buffer: Gtk.TextBuffer) -> str:
    a, b = buffer.get_bounds()
    return buffer.get_text(a, b, True)


def user_insert(buffer: Gtk.TextBuffer, text: str) -> None:
    buffer.begin_user_action()
    try:
        end = buffer.get_end_iter()
        buffer.insert(end, text)
    finally:
        buffer.end_user_action()
    drain(0.01)



def close_message_dialog() -> bool:
    for top in Gtk.Window.list_toplevels():
        if isinstance(top, Gtk.MessageDialog):
            top.response(Gtk.ResponseType.CLOSE)
            return False
    return True


def main() -> None:
    app = GraphiumApplication()
    if not (app.get_flags() & Gio.ApplicationFlags.NON_UNIQUE):
        fail("GraphiumApplication is not NON_UNIQUE")
    if not app.register(None):
        fail("Gtk.Application registration failed")
    app.activate()
    drain(0.05)
    window = app.window
    if window is None:
        fail("application did not create window")
    if not isinstance(window.text_view, Gtk.TextView):
        fail("editor is not Gtk.TextView")
    if any(isinstance(w, Gtk.Toolbar) for w in descendants(window)):
        fail("G04 unexpectedly contains Gtk.Toolbar")
    if window.get_title() != "Untitled (Saved) — Graphium":
        fail(f"unexpected initial title: {window.get_title()!r}")
    for action in ("user-guide", "keyboard-shortcuts", "about"):
        if window.lookup_action(action) is None:
            fail(f"Help action missing: {action}")

    with tempfile.TemporaryDirectory(prefix="graphium-g04-true-gtk-") as td:
        td = Path(td)
        path = td / "crlf.txt"
        path.write_bytes(b"one\r\n")
        if not window.open_path(str(path)):
            fail("open_path failed")
        drain(0.01)
        if text_of(window.buffer) != "one\n":
            fail("CRLF open did not normalize only in editor representation")
        if window.get_title() != "crlf.txt (Saved) — Graphium":
            fail(f"open title mismatch: {window.get_title()!r}")

        # No wall-clock grouping authority: explicit GTK user-action completion is enough.
        user_insert(window.buffer, "X")
        if window.get_title() != "crlf.txt (Modified) — Graphium":
            fail("completed GTK user action did not immediately project Modified")

        save_action = window.lookup_action("save")
        if save_action is None or not save_action.get_enabled():
            fail("Save action unavailable after edit")
        save_action.activate(None)
        drain(0.02)
        if path.read_bytes() != b"one\r\nX":
            fail(f"Save did not preserve CRLF bytes: {path.read_bytes()!r}")
        if window.get_title() != "crlf.txt (Saved) — Graphium":
            fail("successful physical Save did not project Saved")

        undo = window.lookup_action("undo")
        redo = window.lookup_action("redo")
        if undo is None or redo is None:
            fail("Undo/Redo actions missing")
        undo.activate(None); drain(0.01)
        if text_of(window.buffer) != "one\n":
            fail("Undo did not restore previous text")
        if window.get_title() != "crlf.txt (Modified) — Graphium":
            fail("Undo away from saved state must be Modified")
        if not redo.get_enabled():
            fail("Redo disabled in stable Modified state")
        redo.activate(None); drain(0.01)
        if text_of(window.buffer) != "one\nX":
            fail("Redo did not restore saved text")
        if window.get_title() != "crlf.txt (Saved) — Graphium":
            fail("Redo to exact saved state must be Saved")

        # Realistic large-file regression: document size and pathological single-line width
        # are different concerns. Exercise a 1 MiB multiline file, move the visible cursor to
        # the real end, then edit/Undo. This reproduces the interactive viewport path that the
        # withdrawn gate previously missed without manufacturing a million-character line.
        big = td / "one-mib-multiline.txt"
        sample_line = "Graphium large-file editing regression 0123456789 abcdefghijklmnopqrstuvwxyz\n"
        big_text = (sample_line * ((1024 * 1024 // len(sample_line)) + 2))[: 1024 * 1024]
        big.write_text(big_text, encoding="utf-8")
        if not window.open_path(str(big)):
            fail("1 MiB multiline Open failed")
        end = window.buffer.get_end_iter()
        window.buffer.place_cursor(end)
        window.text_view.scroll_to_mark(window.buffer.get_insert(), 0.0, False, 0.0, 0.0)
        drain(0.10)
        before_len = window.buffer.get_char_count()
        user_insert(window.buffer, "Z")
        if not window.lookup_action("undo").get_enabled():
            fail("Undo unavailable after 1 MiB multiline document edit")
        if window.core.history.stored_payload_chars != 1:
            fail(f"large-file one-char edit stored {window.core.history.stored_payload_chars} chars of undo payload")
        window.lookup_action("undo").activate(None); drain(0.05)
        if window.buffer.get_char_count() != before_len:
            fail("large-file Undo did not restore original size")

        # Pathological-line Open must fail before GtkTextBuffer installation. The currently
        # open normal document remains exact; Graphium never truncates or inserts line breaks.
        huge = td / "huge-line.txt"
        huge.write_text("h" * (MAX_INTERACTIVE_LINE_CHARS + 1), encoding="utf-8")
        before_text = text_of(window.buffer)
        before_path = window.core.session.logical_path
        GLib.timeout_add(20, close_message_dialog)
        if window.open_path(str(huge)):
            fail("pathological huge-line Open was unexpectedly admitted")
        drain(0.02)
        if text_of(window.buffer) != before_text or window.core.session.logical_path != before_path:
            fail("rejected huge-line Open changed active document")

        # The same budget must prevent a safe document from being pasted into a pathological
        # line. GtkTextBuffer insertion is stopped before its default mutation handler runs.
        before_len = window.buffer.get_char_count()
        GLib.timeout_add(20, close_message_dialog)
        user_insert(window.buffer, "z" * (MAX_INTERACTIVE_LINE_CHARS + 1))
        drain(0.02)
        if window.buffer.get_char_count() != before_len:
            fail("pathological insertion guard mutated GtkTextBuffer")

    window.destroy()
    drain(0.02)
    app.quit()
    print("TRUE_GTK_NON_UNIQUE=PASS")
    print("TRUE_GTK_SHELL=PASS")
    print("TRUE_GTK_TEXTVIEW=PASS")
    print("TRUE_GTK_OPEN_SAVE_CRLF=PASS")
    print("TRUE_GTK_NATIVE_DELTA_UNDO=PASS")
    print("TRUE_GTK_SAVEPOINT_UNDO_REDO=PASS")
    print("TRUE_GTK_LARGE_MULTILINE_UNDO=PASS")
    print("TRUE_GTK_PATHOLOGICAL_LINE_GUARD=PASS")
    print("TRUE_GTK_HELP_ACTIONS=PASS")
    print("TRUE_GTK_TOOLBAR_ABSENT=PASS")
    print("FINAL_PHASE=G04_TRUE_GTK_GATE_PASS")


if __name__ == "__main__":
    main()
