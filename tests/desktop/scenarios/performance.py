from __future__ import annotations
import argparse,sys,time
from tests.desktop.harness.runtime import load_gtk3
from tests.desktop.harness.runtime import drain, text_of
from tests.desktop.harness.fixtures import realistic_text
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',required=True); ap.add_argument('--manual',action='store_true'); ns=ap.parse_args(); sys.path.insert(0,ns.repo)
    Gdk,GLib,Gtk=load_gtk3(); from graphium.adapters.gtk.application import GraphiumApplication
    app=GraphiumApplication();
    if not app.register(None):return 1
    app.activate(); drain(Gtk); w=app.window; text=realistic_text(); w.core.editor.initialize_new_text(text,clean=True); w._refresh_projection(); b=w.buffer; a,z=b.get_bounds(); b.select_range(a,z)
    t=time.monotonic(); w.lookup_action('uppercase').activate(None); drain(Gtk); elapsed=time.monotonic()-t
    if elapsed>3.0 or not w.core.session.modified:return 1
    w.lookup_action('undo').activate(None); drain(Gtk)
    if text_of(w.text_view)!=text or w.core.session.modified:return 1
    w.destroy(); drain(Gtk); return 0
if __name__=='__main__': raise SystemExit(main())
