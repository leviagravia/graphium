"""GTK3 application root for Graphium through G08.

Graphium is deliberately NON_UNIQUE: one invocation/process owns one window and one active
document, matching the quick-edit mental model of Leafpad/L3afpad and Airpad. Multiple
command-line files are split into separate Graphium processes rather than tabs/windows in
one server instance.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gio, Gtk

from graphium.application.commands import COMMANDS
from graphium.product import DESKTOP_APPLICATION_ID
from .window import GraphiumWindow


class GraphiumApplication(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=DESKTOP_APPLICATION_ID,
            flags=Gio.ApplicationFlags.HANDLES_OPEN | Gio.ApplicationFlags.NON_UNIQUE,
        )
        self.window: GraphiumWindow | None = None

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        for spec in COMMANDS:
            if spec.accelerator:
                self.set_accels_for_action(f"win.{spec.action}", [spec.accelerator])

    def _ensure_window(self) -> GraphiumWindow:
        if self.window is None:
            self.window = GraphiumWindow(self)
            self.window.connect("destroy", self._on_window_destroyed)
        return self.window

    def _on_window_destroyed(self, *_args) -> None:
        self.window = None

    def do_activate(self) -> None:
        window = self._ensure_window()
        window.show_all()
        window.present()

    @staticmethod
    def _spawn_additional_files(files) -> None:
        launcher = Path(sys.argv[0]).resolve()
        for gfile in files:
            path = gfile.get_path()
            if not path:
                continue
            subprocess.Popen(
                [str(launcher), path],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )

    def do_open(self, files, _n_files, _hint) -> None:
        window = self._ensure_window()
        first_path = files[0].get_path() if files else None
        if first_path:
            window.begin_startup_open()
        window.show_all()
        window.present()
        if first_path:
            try:
                window.open_path(first_path)
            finally:
                window.finish_startup_open()
        if len(files) > 1:
            self._spawn_additional_files(files[1:])
