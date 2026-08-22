from __future__ import annotations
import os
import pathlib
import subprocess
import tempfile
from contextlib import contextmanager


def load_gtk3():
    import gi
    gi.require_version('Gdk', '3.0')
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gdk, GLib, Gtk
    return Gdk, GLib, Gtk


def drain(Gtk, limit=200):
    n = 0
    while Gtk.events_pending() and n < limit:
        Gtk.main_iteration_do(False)
        n += 1


def descendants(widget):
    out = []
    if hasattr(widget, 'get_children'):
        for child in widget.get_children():
            out.append(child)
            out.extend(descendants(child))
    return out


def text_of(view):
    buffer = view.get_buffer()
    start, end = buffer.get_bounds()
    return buffer.get_text(start, end, True)


@contextmanager
def isolated_env(prefix='graphium-desktop-'):
    with tempfile.TemporaryDirectory(prefix=prefix) as td:
        root = pathlib.Path(td)
        env = os.environ.copy()
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        for key, sub in [('HOME', 'home'), ('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'), ('XDG_CACHE_HOME', 'cache'), ('XDG_STATE_HOME', 'state')]:
            path = root / sub
            path.mkdir()
            env[key] = str(path)
        yield root, env


def run_owned(cmd, *, cwd, env, timeout=20):
    try:
        return subprocess.run(cmd, cwd=cwd, env=env, timeout=timeout, text=True, capture_output=True)
    except subprocess.TimeoutExpired:
        return None
