#!/usr/bin/env python3
"""True-GTK real-window product gate for Graphium G07."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) in sys.path: sys.path.remove(str(ROOT))
sys.path.insert(0,str(ROOT))

from graphium.product import WORK_ITEM

def _g07_or_later():
    return WORK_ITEM.startswith('G') and WORK_ITEM[1:].isdigit() and int(WORK_ITEM[1:])>=7

if '--bootstrap-only' in sys.argv:
    if not _g07_or_later(): raise SystemExit(f'G07_TRUE_GTK_BOOTSTRAP=FAIL work_item={WORK_ITEM}')
    print(f'G07_TRUE_GTK_BOOTSTRAP=PASS root={ROOT}'); raise SystemExit(0)

import gi
gi.require_version('Gtk','3.0')
from gi.repository import GLib, Gtk

import graphium.adapters.gtk.window as window_module
from graphium.adapters.gtk.application import GraphiumApplication


def fail(msg): raise SystemExit(f'G07_TRUE_GTK_FAIL: {msg}')

def drain(seconds=0.0):
    deadline=time.monotonic()+seconds
    while True:
        while Gtk.events_pending(): Gtk.main_iteration_do(False)
        if time.monotonic()>=deadline: return
        time.sleep(0.005)

def text_of(buffer):
    a,b=buffer.get_bounds(); return buffer.get_text(a,b,True)

def user_insert(buffer,text):
    buffer.begin_user_action()
    try: buffer.insert(buffer.get_end_iter(),text)
    finally: buffer.end_user_action()
    drain(0.02)

def descendants(widget):
    yield widget
    if isinstance(widget,Gtk.Container):
        for child in widget.get_children(): yield from descendants(child)

def schedule_unsaved_cancel():
    def poll():
        for top in Gtk.Window.list_toplevels():
            if isinstance(top,Gtk.MessageDialog) and top.get_visible():
                top.response(Gtk.ResponseType.CANCEL); return False
        return True
    GLib.timeout_add(10,poll)

def schedule_dialog_check(title, check_response=None):
    capture={}
    def close_poll():
        for top in Gtk.Window.list_toplevels():
            if isinstance(top,Gtk.Dialog) and top.get_title()==title and top.get_visible():
                labels=[w.get_text() for w in descendants(top) if isinstance(w,Gtk.Label)]
                capture['text']=' | '.join(labels)
                top.response(Gtk.ResponseType.CLOSE); return False
        return True
    def first_poll():
        for top in Gtk.Window.list_toplevels():
            if isinstance(top,Gtk.Dialog) and top.get_title()==title and top.get_visible():
                if check_response is not None:
                    top.response(check_response)
                    GLib.timeout_add(25,close_poll)
                else:
                    GLib.timeout_add(10,close_poll)
                return False
        return True
    GLib.timeout_add(10,first_poll)
    return capture


def main():
    if not _g07_or_later(): fail(f'wrong work item {WORK_ITEM}')
    with tempfile.TemporaryDirectory(prefix='graphium-g07-true-gtk-') as td_raw:
        td=Path(td_raw)
        for key,name in [('HOME','home'),('XDG_CONFIG_HOME','config'),('XDG_CACHE_HOME','cache'),('XDG_DATA_HOME','data'),('XDG_STATE_HOME','state')]:
            os.environ[key]=str(td/name); Path(os.environ[key]).mkdir(parents=True,exist_ok=True)
        app=GraphiumApplication()
        if not app.register(None): fail('Gtk.Application registration failed')
        app.activate(); drain(0.08); window=app.window
        if window is None: fail('application did not create window')
        for name in ('open-recent','clear-recent','save-copy','save-version-copy','properties','statistics'):
            if window.lookup_action(name) is None: fail(f'missing G07 action {name}')
        if any(isinstance(w,Gtk.Toolbar) for w in descendants(window)): fail('Toolbar appeared')

        # Recent: real lifecycle Open and real unsaved Save/Discard/Cancel boundary.
        a=td/'a.txt'; b=td/'b.txt'; a.write_text('alpha\n',encoding='utf-8'); b.write_text('beta\n',encoding='utf-8')
        if not window.open_path(str(a)): fail('initial Open failed')
        if window.core.recent_files.paths[0] != os.path.abspath(str(a)): fail('Open did not touch Recent')
        if not window.open_path(str(b)): fail('second Open failed')
        recent_before=window.core.recent_files.paths
        user_insert(window.buffer,'MOD')
        schedule_unsaved_cancel()
        window.lookup_action('open-recent').activate(GLib.Variant.new_string(str(a))); drain(0.05)
        if window.core.session.logical_path != os.path.abspath(str(b)) or not window.core.session.modified:
            fail('Recent Open bypassed real modified-document cancel boundary')
        if window.core.recent_files.paths != recent_before: fail('cancelled Recent Open changed history')
        window.lookup_action('undo').activate(None); drain(0.02)
        if window.core.session.modified: fail('could not restore clean boundary after Recent scenario')

        # Save a Copy: exact live text, non-binding, no savepoint/history/recent movement.
        user_insert(window.buffer,'X')
        copy_path=td/'beta-copy.txt'
        before_path=window.core.session.logical_path; before_file_state=window.core.session.file_state
        before_current=window.core.session.current_editor_state_id; before_saved=window.core.session.saved_editor_state_id
        before_history=window.core.history.checkpoint(); before_recent=window.core.recent_files.paths
        original_choose=window_module.choose_copy_path
        try:
            window_module.choose_copy_path=lambda *_a,**_k: str(copy_path)
            window.lookup_action('save-copy').activate(None); drain(0.03)
        finally:
            window_module.choose_copy_path=original_choose
        if copy_path.read_text(encoding='utf-8') != text_of(window.buffer): fail('Save a Copy bytes differ from live buffer')
        if window.core.session.logical_path!=before_path or window.core.session.file_state!=before_file_state: fail('Save a Copy rebound active document')
        if window.core.session.current_editor_state_id!=before_current or window.core.session.saved_editor_state_id!=before_saved: fail('Save a Copy moved state/savepoint')
        if window.core.history.checkpoint()!=before_history: fail('Save a Copy mutated Undo/Redo history')
        if window.core.recent_files.paths!=before_recent: fail('Save a Copy touched Recent')

        # Version copy: deterministic v0001, same non-binding invariants.
        expected=td/'b_v0001.txt'
        window.lookup_action('save-version-copy').activate(None); drain(0.03)
        if not expected.exists() or expected.read_text(encoding='utf-8')!=text_of(window.buffer): fail('Version Copy target/content mismatch')
        if window.core.session.logical_path!=before_path or window.core.session.saved_editor_state_id!=before_saved: fail('Version Copy changed binding/savepoint')
        if window.core.recent_files.paths!=before_recent: fail('Version Copy touched Recent')
        window.lookup_action('undo').activate(None); drain(0.02)
        if window.core.session.modified: fail('copy scenario Undo did not restore clean state')

        # Properties: same-size/same-mtime content mutation is detected by strong hash without accepting baseline.
        prop=td/'properties.txt'; prop.write_bytes(b'abcd'); window.open_path(str(prop)); accepted=window.core.session.snapshot(); mtime=prop.stat().st_mtime_ns
        prop.write_bytes(b'wxyz'); os.utime(prop,ns=(mtime,mtime))
        capture=schedule_dialog_check('Properties',1001)
        window.lookup_action('properties').activate(None); drain(0.03)
        if 'Content changed on disk' not in capture.get('text',''): fail(f'Properties Check Now missed content change: {capture}')
        if window.core.session.snapshot()!=accepted: fail('Properties Check Now mutated accepted session baseline')

        # Reopen current bytes, then replace inode with identical bytes; must classify replacement.
        if not window.open_path(str(prop)): fail('Properties rebaseline Open failed')
        accepted=window.core.session.snapshot(); repl=td/'replacement.tmp'; repl.write_bytes(prop.read_bytes()); os.replace(repl,prop)
        capture=schedule_dialog_check('Properties',1001)
        window.lookup_action('properties').activate(None); drain(0.03)
        if 'replaced or the logical path was retargeted' not in capture.get('text',''): fail(f'Properties missed inode replacement: {capture}')
        if window.core.session.snapshot()!=accepted: fail('replacement Check Now mutated baseline')

        # Statistics: actual G07 dialog, explicit activation only, exact document+selection projection.
        window.core.editor.initialize_new_text('one two\nthree',clean=True); window._refresh_projection()
        start=window.buffer.get_iter_at_offset(4); end=window.buffer.get_iter_at_offset(7); window.buffer.select_range(end,start)
        before_state=window.core.session.snapshot(); before_history=window.core.history.checkpoint()
        capture=schedule_dialog_check('Statistics')
        window.lookup_action('statistics').activate(None); drain(0.03)
        labels=capture.get('text','')
        for marker in ('Document','Selection','Lines','Words','Characters','13'):
            if marker not in labels: fail(f'Statistics dialog missing {marker!r}: {labels}')
        if window.core.session.snapshot()!=before_state or window.core.history.checkpoint()!=before_history: fail('Statistics mutated document/session/history')

        # Realistic 1 MiB explicit Statistics activation remains bounded; dialog is auto-closed only after visible.
        line='Graphium G07 realistic multiline quick-edit sample 0123456789\n'; bigtext=(line*((1024*1024//len(line))+2))[:1024*1024]
        window.core.editor.initialize_new_text(bigtext,clean=True); window._refresh_projection(); capture=schedule_dialog_check('Statistics')
        t0=time.monotonic(); window.lookup_action('statistics').activate(None); elapsed=time.monotonic()-t0
        if elapsed>2.0: fail(f'1MiB Statistics activation exceeded 2s: {elapsed:.3f}s')
        if not capture.get('text'): fail('1MiB Statistics dialog never became visible')

        window.destroy(); drain(0.02); app.quit()
    print('G07_TRUE_GTK_RECENT=PASS')
    print('G07_TRUE_GTK_COPY=PASS')
    print('G07_TRUE_GTK_VERSION_COPY=PASS')
    print('G07_TRUE_GTK_PROPERTIES=PASS')
    print('G07_TRUE_GTK_STATISTICS=PASS')
    print('G07_TRUE_GTK_MODAL_LIFECYCLE=PASS')
    print('G07_TRUE_GTK_1M_RESPONSIVENESS=PASS')
    print('FINAL_PHASE=G07_TRUE_GTK_GATE_PASS')

if __name__=='__main__': main()
