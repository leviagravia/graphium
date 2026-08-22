from __future__ import annotations
import argparse,sys
from tests.desktop.harness.runtime import load_gtk3
from tests.desktop.harness.runtime import drain
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',required=True); ap.add_argument('--manual',action='store_true'); ns=ap.parse_args(); sys.path.insert(0,ns.repo)
    Gdk,GLib,Gtk=load_gtk3(); from gi.repository import Gio
    if Gtk.get_major_version()!=3: return 1
    from graphium.adapters.gtk.application import GraphiumApplication
    app=GraphiumApplication()
    if not (app.get_flags() & Gio.ApplicationFlags.NON_UNIQUE): return 1
    if not app.register(None): return 1
    app.activate(); drain(Gtk); w=app.window
    if w is None or not isinstance(w,Gtk.ApplicationWindow): return 1
    if len([x for x in Gtk.Window.list_toplevels() if isinstance(x,Gtk.ApplicationWindow)])<1:return 1
    w.destroy(); drain(Gtk); return 0
if __name__=='__main__': raise SystemExit(main())
