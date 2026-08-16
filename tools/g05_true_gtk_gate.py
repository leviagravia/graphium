#!/usr/bin/env python3
"""True-GTK automated product gate for Graphium G05 Search/Replace/Go to Line."""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_root = str(ROOT)
if _root in sys.path:
    sys.path.remove(_root)
sys.path.insert(0, _root)

from graphium.product import WORK_ITEM


def _g05_or_later() -> bool:
    return WORK_ITEM.startswith("G") and WORK_ITEM[1:].isdigit() and int(WORK_ITEM[1:]) >= 5

if "--bootstrap-only" in sys.argv:
    if not _g05_or_later():
        raise SystemExit(f"G05_TRUE_GTK_BOOTSTRAP=FAIL work_item={WORK_ITEM}")
    print(f"G05_TRUE_GTK_BOOTSTRAP=PASS root={ROOT}")
    raise SystemExit(0)

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, Gtk

from graphium.adapters.gtk.application import GraphiumApplication
from graphium.application.renderability import MAX_INTERACTIVE_LINE_CHARS


def fail(message: str) -> None:
    raise SystemExit(f"G05_TRUE_GTK_FAIL: {message}")


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
    start, end = buffer.get_bounds()
    return buffer.get_text(start, end, True)


def selection_offsets(buffer: Gtk.TextBuffer) -> tuple[int, int] | None:
    bounds = buffer.get_selection_bounds()
    if not bounds:
        return None
    a, b = bounds
    return (min(a.get_offset(), b.get_offset()), max(a.get_offset(), b.get_offset()))


def close_message_dialog() -> bool:
    for top in Gtk.Window.list_toplevels():
        if isinstance(top, Gtk.MessageDialog):
            top.response(Gtk.ResponseType.CLOSE)
            return False
    return True


def accept_go_to_line(line: int) -> bool:
    for top in Gtk.Window.list_toplevels():
        if isinstance(top, Gtk.Dialog) and top.get_title() == "Go to Line":
            for widget in descendants(top):
                if isinstance(widget, Gtk.SpinButton):
                    widget.set_value(line)
                    top.response(Gtk.ResponseType.ACCEPT)
                    return False
    return True


def establish(window, text: str) -> int:
    window.core.editor.initialize_new_text(text, clean=True)
    window._refresh_projection()
    drain(0.01)
    return window.core.history.current_state_id


def set_search(window, query: str, replacement: str = "", *, match_case: bool = False) -> None:
    window._ensure_search_bar()
    window._search_query_entry.set_text(query)
    window._search_replace_entry.set_text(replacement)
    window._search_match_case.set_active(match_case)
    drain(0.01)


def main() -> None:
    if not _g05_or_later():
        fail(f"wrong work item: {WORK_ITEM}")
    app = GraphiumApplication()
    if not (app.get_flags() & Gio.ApplicationFlags.NON_UNIQUE):
        fail("GraphiumApplication lost NON_UNIQUE topology")
    if not app.register(None):
        fail("Gtk.Application registration failed")
    app.activate(); drain(0.05)
    window = app.window
    if window is None:
        fail("application did not create window")
    if window._search_bar is not None:
        fail("SearchBar was created eagerly at startup")
    if any(isinstance(widget, Gtk.Toolbar) for widget in descendants(window)):
        fail("toolbar unexpectedly present")
    for action in ("find", "find-next", "find-previous", "replace", "go-to-line"):
        if window.lookup_action(action) is None:
            fail(f"Search action missing: {action}")

    # Find action must lazily create and show the single search surface.
    window.lookup_action("find").activate(None); drain(0.02)
    if window._search_bar is None or not window._search_bar.get_search_mode():
        fail("Find did not lazily show Gtk.SearchBar")

    source = "Straße alpha STRASSE\nline two\nneedle end\n"
    saved_state = establish(window, source)
    set_search(window, "strasse", match_case=False)
    window._perform_find_next(); drain(0.01)
    if selection_offsets(window.buffer) != (0, 6):
        fail(f"Unicode casefold first match wrong: {selection_offsets(window.buffer)}")
    if window.core.history.current_state_id != saved_state or window.core.session.modified:
        fail("Find navigation changed state identity/Saved relation")
    window._perform_find_next(); drain(0.01)
    if selection_offsets(window.buffer) != (13, 20):
        fail(f"Unicode casefold second match wrong: {selection_offsets(window.buffer)}")
    window._perform_find_next(); drain(0.01)
    if selection_offsets(window.buffer) != (0, 6):
        fail("Find Next did not wrap once to first match")

    # Replace One must acquire the next match, mutate one state, and be exactly undoable.
    saved_state = establish(window, source)
    set_search(window, "alpha", "BETA", match_case=True)
    window._perform_replace_one(); drain(0.01)
    replaced = "Straße BETA STRASSE\nline two\nneedle end\n"
    if text_of(window.buffer) != replaced:
        fail("Replace One result mismatch")
    if window.core.history.current_state_id == saved_state or not window.core.session.modified:
        fail("Replace One did not advance to Modified state")
    if len(window.core.history.undo_stack) != 1:
        fail("Replace One was not one Undo group")
    window.lookup_action("undo").activate(None); drain(0.01)
    if text_of(window.buffer) != source or window.core.session.modified:
        fail("Replace One Undo did not restore exact Saved source")
    window.lookup_action("redo").activate(None); drain(0.01)
    if text_of(window.buffer) != replaced or not window.core.session.modified:
        fail("Replace One Redo did not restore replacement")

    # Replace All = one state/group and non-cascading frozen original match set.
    source_all = "a a a\nline a\n"
    saved_state = establish(window, source_all)
    set_search(window, "a", "aa", match_case=True)
    window._perform_replace_all(); drain(0.01)
    expected_all = "aa aa aa\nline aa\n"
    if text_of(window.buffer) != expected_all:
        fail(f"Replace All result mismatch: {text_of(window.buffer)!r}")
    if len(window.core.history.undo_stack) != 1:
        fail("Replace All did not create exactly one Undo group")
    if window.core.history.current_state_id == saved_state or not window.core.session.modified:
        fail("Replace All did not advance one Modified state")
    window.lookup_action("undo").activate(None); drain(0.01)
    if text_of(window.buffer) != source_all or window.core.session.modified:
        fail("Replace All Undo did not restore exact Saved source")
    window.lookup_action("redo").activate(None); drain(0.01)
    if text_of(window.buffer) != expected_all:
        fail("Replace All Redo mismatch")

    # Proven no-op must allocate neither state nor Undo.
    saved_state = establish(window, "x x\n")
    set_search(window, "x", "x", match_case=True)
    window._perform_replace_all(); drain(0.01)
    if window.core.history.current_state_id != saved_state or window.core.history.undo_stack:
        fail("zero-change Replace All allocated history/state")
    if window.core.session.modified:
        fail("zero-change Replace All changed Saved relation")

    # Renderer safety remains authoritative for programmatic replacement.
    near_limit = "x" * (MAX_INTERACTIVE_LINE_CHARS - 1)
    saved_state = establish(window, near_limit)
    set_search(window, "x", "xx", match_case=True)
    GLib.timeout_add(20, close_message_dialog)
    window._perform_replace_all(); drain(0.03)
    if text_of(window.buffer) != near_limit or window.core.history.current_state_id != saved_state:
        fail("renderer-rejected Replace All mutated buffer/state")

    # Go to Line is view-only.
    saved_state = establish(window, "one\ntwo\nthree\n")
    GLib.timeout_add(20, accept_go_to_line, 3)
    window.lookup_action("go-to-line").activate(None); drain(0.02)
    insert = window.buffer.get_iter_at_mark(window.buffer.get_insert())
    if insert.get_line() != 2:
        fail(f"Go to Line selected wrong line: {insert.get_line()+1}")
    if window.core.history.current_state_id != saved_state or window.core.session.modified:
        fail("Go to Line changed document state")

    # Realistic 1 MiB explicit command path, including GtkTextBuffer capture/projection.
    line = "Graphium realistic search line alpha beta gamma 0123456789\n"
    marker = "SearchNeedle\n"
    body_size = 1024 * 1024 - len(marker)
    large = (line * (body_size // len(line) + 2))[:body_size] + marker
    saved_state = establish(window, large)
    set_search(window, "searchneedle", "DONE", match_case=False)
    started = time.monotonic()
    window._perform_find_next(); drain(0.01)
    find_elapsed = time.monotonic() - started
    if find_elapsed > 3.0:
        fail(f"1 MiB Find Next responsiveness >3s: {find_elapsed:.3f}s")
    expected_start = len(large) - len(marker)
    if selection_offsets(window.buffer) != (expected_start, expected_start + len("SearchNeedle")):
        fail("1 MiB Find Next selected wrong source range")
    if window.core.history.current_state_id != saved_state:
        fail("1 MiB Find changed state identity")
    started = time.monotonic()
    window._perform_replace_one(); drain(0.01)
    replace_elapsed = time.monotonic() - started
    if replace_elapsed > 3.0:
        fail(f"1 MiB Replace One responsiveness >3s: {replace_elapsed:.3f}s")
    if not window.core.session.modified or len(window.core.history.undo_stack) != 1:
        fail("1 MiB Replace One history/state wrong")
    window.lookup_action("undo").activate(None); drain(0.02)
    if text_of(window.buffer) != large or window.core.session.modified:
        fail("1 MiB Replace One Undo mismatch")

    window.destroy(); drain(0.02); app.quit()
    print("G05_TRUE_GTK_SEARCHBAR_LAZY=PASS")
    print("G05_TRUE_GTK_UNICODE_FIND_WRAP=PASS")
    print("G05_TRUE_GTK_FIND_STATE_NEUTRAL=PASS")
    print("G05_TRUE_GTK_REPLACE_ONE_UNDO=PASS")
    print("G05_TRUE_GTK_REPLACE_ALL_ONE_UNDO=PASS")
    print("G05_TRUE_GTK_ZERO_CHANGE_NOOP=PASS")
    print("G05_TRUE_GTK_RENDERABILITY_PREFLIGHT=PASS")
    print("G05_TRUE_GTK_GO_TO_LINE=PASS")
    print(f"G05_TRUE_GTK_1M_FIND_MS={find_elapsed*1000:.3f}")
    print(f"G05_TRUE_GTK_1M_REPLACE_MS={replace_elapsed*1000:.3f}")
    print("G05_TRUE_GTK_LARGE_MULTILINE_SEARCH=PASS")
    print("G05_TRUE_GTK_TOOLBAR_ABSENT=PASS")
    print("FINAL_PHASE=G05_TRUE_GTK_GATE_PASS")


if __name__ == "__main__":
    main()
