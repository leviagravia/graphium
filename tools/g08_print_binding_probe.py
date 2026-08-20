#!/usr/bin/env python3
"""T480 NON-CANDIDATE PyGObject/GTK3 print-binding probe for Graphium G08.

This is a boundary probe, not a product candidate.  It exercises the exact Gtk3/Pango
bindings used by the G08 implementation, including a native Page Setup cancel and a
noninteractive GtkPrintOperation EXPORT path.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) in sys.path:
    sys.path.remove(str(ROOT))
sys.path.insert(0, str(ROOT))

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import GLib, Gtk, Pango, PangoCairo

from graphium.adapters.gtk.printing import (
    PrintSnapshot,
    _PageSetupStore,
    _PrintJob,
    _page_setup_signature,
)
from graphium.product import WORK_ITEM


def fail(message: str) -> None:
    raise SystemExit(f"G08_PRINT_BINDING_PROBE=FAIL detail={message}")


def phase(name: str) -> None:
    print(f"G08_PRINT_BINDING_PHASE={name}", flush=True)


def drain(seconds: float = 0.0) -> None:
    deadline = time.monotonic() + seconds
    while True:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        if time.monotonic() >= deadline:
            return
        time.sleep(0.005)


def schedule_page_setup_cancel() -> dict[str, object]:
    state: dict[str, object] = {"seen": False, "deadline": time.monotonic() + 3.0}

    def poll() -> bool:
        for top in Gtk.Window.list_toplevels():
            if top.get_visible() and isinstance(top, Gtk.Dialog):
                title = top.get_title() or ""
                if "Page" in title or "Setup" in title:
                    state["seen"] = True
                    top.response(Gtk.ResponseType.CANCEL)
                    return False
        if time.monotonic() >= float(state["deadline"]):
            state["timed_out"] = True
            for top in Gtk.Window.list_toplevels():
                if top.get_visible() and isinstance(top, Gtk.Dialog):
                    try:
                        top.response(Gtk.ResponseType.CANCEL)
                    except Exception:
                        top.destroy()
            return False
        return True

    GLib.timeout_add(15, poll)
    return state


def main() -> None:
    if not (WORK_ITEM.startswith("G") and int(WORK_ITEM[1:]) >= 8):
        fail(f"wrong work item {WORK_ITEM}")

    phase("NAMESPACE")
    if Gtk.get_major_version() != 3:
        fail(f"GTK major is {Gtk.get_major_version()}, expected 3")
    if not callable(getattr(Gtk, "print_run_page_setup_dialog", None)):
        fail("Gtk.print_run_page_setup_dialog missing")
    for obj, method in (
        (Gtk.PageSetup, "new_from_file"),
        (Gtk.PageSetup(), "copy"),
        (Gtk.PageSetup(), "to_file"),
        (Gtk.PrintSettings(), "copy"),
        (Gtk.PrintOperation(), "run"),
        (Gtk.PrintOperation(), "set_allow_async"),
    ):
        if not callable(getattr(obj, method, None)):
            fail(f"binding missing: {type(obj).__name__}.{method}")
    print(f"G08_GTK_VERSION={Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}")

    with tempfile.TemporaryDirectory(prefix="graphium-g08-print-binding-") as td_raw:
        td = Path(td_raw)
        for key, name in (
            ("HOME", "home"),
            ("XDG_CONFIG_HOME", "config"),
            ("XDG_CACHE_HOME", "cache"),
            ("XDG_DATA_HOME", "data"),
            ("XDG_STATE_HOME", "state"),
        ):
            os.environ[key] = str(td / name)
            Path(os.environ[key]).mkdir(parents=True, exist_ok=True)

        phase("PAGE_SETUP_SERIALIZATION")
        store_path = td / "config" / "graphium" / "page-setup.ini"
        store = _PageSetupStore(store_path)
        setup = Gtk.PageSetup()
        setup.set_top_margin(17.0, Gtk.Unit.MM)
        setup.set_bottom_margin(19.0, Gtk.Unit.MM)
        store.save(setup)
        if not store_path.is_file():
            fail("Page Setup store did not create regular file")
        if stat.S_IMODE(store_path.stat().st_mode) != 0o600:
            fail(f"Page Setup mode is {oct(stat.S_IMODE(store_path.stat().st_mode))}, expected 0o600")
        loaded = store.load()
        if _page_setup_signature(loaded) != _page_setup_signature(setup):
            fail("Gtk.PageSetup file roundtrip changed setup semantics")

        phase("NATIVE_PAGE_SETUP_CANCEL")
        parent = Gtk.Window(title="Graphium G08 Binding Probe")
        parent.show_all()
        drain(0.03)
        before = loaded.copy()
        state = schedule_page_setup_cancel()
        returned = Gtk.print_run_page_setup_dialog(parent, before, Gtk.PrintSettings())
        drain(0.03)
        if state.get("timed_out"):
            fail("native Page Setup dialog could not be auto-cancelled")
        if not state.get("seen"):
            fail("native Page Setup dialog was not observed")
        if returned is None:
            fail("Page Setup cancel returned None")
        if _page_setup_signature(returned) != _page_setup_signature(before):
            fail("Page Setup cancel changed semantic setup")

        phase("PRINT_OPERATION_EXPORT")
        pdf = td / "probe.pdf"
        operation = Gtk.PrintOperation()
        operation.set_unit(Gtk.Unit.POINTS)
        operation.set_default_page_setup(loaded.copy())
        operation.set_print_settings(Gtk.PrintSettings().copy())
        operation.set_allow_async(False)
        operation.set_export_filename(str(pdf))
        snapshot = PrintSnapshot(
            text="Alpha βeta\ncombining: e\u0301\n\tTabbed\n" * 250,
            title="binding-probe.txt",
            font_family="Monospace",
            font_size_points=11.0,
        )
        job = _PrintJob(snapshot)
        observed = {"begin": 0, "paginate": 0, "draw": 0, "end": 0, "line": False}

        def begin(op, context):
            observed["begin"] += 1
            job.begin_print(op, context)
            if job.chunks or job.pages:
                fail("begin-print performed document pagination eagerly")

        def paginate(op, context):
            observed["paginate"] += 1
            finished = job.paginate(op, context)
            if job.chunks and not observed["line"]:
                layout = job.chunks[0].layout
                if layout.get_line_count() < 1:
                    fail("Pango chunk layout unavailable in paginate")
                line = layout.get_line_readonly(0)
                if line is None:
                    fail("Pango get_line_readonly returned None")
                _ink, logical = line.get_extents()
                if logical.height <= 0:
                    fail("Pango visual line logical height is non-positive")
                observed["line"] = True
            return finished

        def draw(op, context, page_nr):
            observed["draw"] += 1
            # Exercise exact Cairo/PangoCairo rendering used by production.
            probe_layout = context.create_pango_layout()
            probe_layout.set_text("probe", -1)
            PangoCairo.show_layout(context.get_cairo_context(), probe_layout)
            job.draw_page(op, context, page_nr)

        def end(op, context):
            observed["end"] += 1
            job.end_print(op, context)

        operation.connect("begin-print", begin)
        operation.connect("paginate", paginate)
        operation.connect("draw-page", draw)
        operation.connect("end-print", end)
        try:
            result = operation.run(Gtk.PrintOperationAction.EXPORT, parent)
        except Exception as exc:
            fail(f"GtkPrintOperation EXPORT raised {type(exc).__name__}: {exc}")
        if result == Gtk.PrintOperationResult.ERROR:
            fail("GtkPrintOperation EXPORT returned ERROR")
        if not pdf.is_file() or pdf.stat().st_size <= 0:
            fail("GtkPrintOperation EXPORT did not produce a non-empty PDF")
        if (
            observed["begin"] != 1
            or observed["paginate"] < 1
            or observed["draw"] < 1
            or observed["end"] != 1
            or not observed["line"]
        ):
            fail(f"unexpected print callback lifecycle {observed}")
        if operation.get_print_settings() is None:
            fail("GtkPrintOperation.get_print_settings returned None")
        copied_settings = operation.get_print_settings().copy()
        if copied_settings is None:
            fail("GtkPrintSettings.copy returned None")

        parent.destroy()
        drain(0.02)

    phase("PASS")
    print("G08_PRINT_BINDING_PROBE=PASS")
    print("CANDIDATE_ATTEMPT_CONSUMED=NO")
    print("GIT_MUTATION=NO")
    print("FINAL_PHASE=G08_PRINT_BINDING_NONCANDIDATE_PASS")


if __name__ == "__main__":
    main()
