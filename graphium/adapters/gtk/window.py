"""Thin GTK3 single-document editor window through Graphium G05."""
from __future__ import annotations

import os
import time
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gio, GLib, GObject, Gtk

from graphium.application.commands import COMMANDS, command_availability
from graphium.domain.text_search import SearchInputError, SearchMatch
from graphium.composition import build_core
from graphium.domain.edit_history import ViewState
from graphium.application.renderability import (
    InteractiveRenderabilityError,
    ensure_insert_renderable,
    ensure_join_renderable,
)
from graphium.product import PRODUCT_NAME, VERSION
from .dialogs import GtkLifecycleUI, choose_line_number, show_about, show_text_document
from .editor_buffer import GtkTextBufferPort


class GraphiumWindow(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application) -> None:
        super().__init__(application=application)
        self.set_default_size(720, 520)
        self.set_role("graphium-editor")

        self._closing_accepted = False
        self._startup_open_pending = False
        self._mapped = False
        self._benchmark_ready_emitted = False
        self._implicit_delete_group = False
        self._renderability_notice_pending = False
        self._actions: dict[str, Gio.SimpleAction] = {}
        self._search_bar: Gtk.SearchBar | None = None
        self._search_query_entry: Gtk.Entry | None = None
        self._search_replace_entry: Gtk.Entry | None = None
        self._search_replace_row: Gtk.Widget | None = None
        self._search_match_case: Gtk.CheckButton | None = None
        self._search_status: Gtk.Label | None = None

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(box)

        self.text_view = Gtk.TextView()
        self.text_view.set_wrap_mode(Gtk.WrapMode.NONE)
        self.text_view.set_monospace(True)
        self.text_view.set_left_margin(6)
        self.text_view.set_right_margin(6)
        self.buffer = self.text_view.get_buffer()
        self.buffer_port = GtkTextBufferPort(self.buffer)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.add(self.text_view)
        box.pack_start(scroller, True, True, 0)

        ui = GtkLifecycleUI(self)
        self._ui = ui
        self.core = build_core(buffer=self.buffer_port, ui=ui)
        self.core.editor.initialize_new_text("", clean=True)

        self._install_actions()
        self._install_menu()
        self._connect_native_edit_signals()
        self.buffer.connect("notify::has-selection", self._on_selection_changed)
        self.connect("delete-event", self._on_delete_event)
        self.connect("map-event", self._on_mapped)
        self._refresh_projection()

    def _install_actions(self) -> None:
        callbacks = {
            "new": self._action_new,
            "open": self._action_open,
            "save": self._action_save,
            "save-as": self._action_save_as,
            "quit": self._action_quit,
            "undo": self._action_undo,
            "redo": self._action_redo,
            "cut": self._action_cut,
            "copy": self._action_copy,
            "paste": self._action_paste,
            "delete": self._action_delete,
            "select-all": self._action_select_all,
            "find": self._action_find,
            "find-next": self._action_find_next,
            "find-previous": self._action_find_previous,
            "replace": self._action_replace,
            "go-to-line": self._action_go_to_line,
            "user-guide": self._action_user_guide,
            "keyboard-shortcuts": self._action_keyboard_shortcuts,
            "about": self._action_about,
        }
        for spec in COMMANDS:
            action = Gio.SimpleAction.new(spec.action, None)
            action.connect("activate", callbacks[spec.action])
            self.add_action(action)
            self._actions[spec.action] = action

    def _install_menu(self) -> None:
        root = Gio.Menu()
        for menu_name in ("File", "Edit", "Search", "Help"):
            section = Gio.Menu()
            for spec in COMMANDS:
                if spec.menu == menu_name:
                    section.append(spec.label, f"win.{spec.action}")
            root.append_submenu(menu_name, section)
        menubar = Gtk.MenuBar.new_from_model(root)
        container = self.get_child()
        assert isinstance(container, Gtk.Box)
        container.pack_start(menubar, False, False, 0)
        container.reorder_child(menubar, 0)
        menubar.show_all()

    def _connect_native_edit_signals(self) -> None:
        # Real semantic boundaries come from GtkTextBuffer user actions and structural
        # insert/delete deltas. No wall-clock timer participates in Undo grouping.
        self.buffer.connect("begin-user-action", self._on_begin_user_action)
        # Pre-default guards run before GtkTextBuffer mutates. They prevent a normal
        # document from being edited into the same pathological huge-line state that
        # G04 rejects on Open. GTK documents that insertion/deletion occurs in the
        # default handler, after handlers connected with connect().
        self.buffer.connect("insert-text", self._on_insert_text_guard)
        self.buffer.connect_after("insert-text", self._on_insert_text_after)
        self.buffer.connect("delete-range", self._on_delete_range_guard)
        self.buffer.connect("delete-range", self._on_delete_range_before)
        self.buffer.connect_after("delete-range", self._on_delete_range_after)
        self.buffer.connect_after("end-user-action", self._on_end_user_action)

    def _editing_suppressed(self) -> bool:
        return self.core.editor.restoring or self.core.session.loading

    def _on_begin_user_action(self, _buffer) -> None:
        if self._editing_suppressed() or self.core.editor.native_group_active:
            return
        self.core.editor.begin_native_group(self.buffer_port.capture_view())

    def _queue_renderability_notice(self, message: str) -> None:
        if self._renderability_notice_pending:
            return
        self._renderability_notice_pending = True

        def show_notice() -> bool:
            self._renderability_notice_pending = False
            self._ui.show_warning("Edit blocked to keep Graphium responsive", message)
            return False

        GLib.idle_add(show_notice)

    def _on_insert_text_guard(self, buffer, location, text: str, _length: int) -> None:
        if self._editing_suppressed() or not text:
            return
        line_start = location.copy()
        line_start.set_line_offset(0)
        line_end = location.copy()
        line_end.forward_to_line_end()
        prefix = location.get_offset() - line_start.get_offset()
        suffix = line_end.get_offset() - location.get_offset()
        try:
            ensure_insert_renderable(
                prefix_chars=prefix,
                suffix_chars=suffix,
                inserted_text=text,
            )
        except InteractiveRenderabilityError as exc:
            GObject.signal_stop_emission_by_name(buffer, "insert-text")
            self._queue_renderability_notice(str(exc))

    def _on_delete_range_guard(self, buffer, start_iter, end_iter) -> None:
        if self._editing_suppressed() or start_iter.get_line() == end_iter.get_line():
            return
        end_line_end = end_iter.copy()
        end_line_end.forward_to_line_end()
        prefix = start_iter.get_line_offset()
        suffix = end_line_end.get_offset() - end_iter.get_offset()
        try:
            ensure_join_renderable(prefix_chars=prefix, suffix_chars=suffix)
        except InteractiveRenderabilityError as exc:
            GObject.signal_stop_emission_by_name(buffer, "delete-range")
            self._queue_renderability_notice(str(exc))

    def _begin_implicit_insert_group(self, start_offset: int) -> bool:
        if self.core.editor.native_group_active:
            return False
        # Fallback for programmatic GtkTextBuffer edits not wrapped in a user action.
        self.core.editor.begin_native_group(ViewState(start_offset, start_offset))
        return True

    def _on_insert_text_after(self, _buffer, location, text: str, _length: int) -> None:
        if self._editing_suppressed() or not text:
            return
        end = location.get_offset()
        start = end - len(text)
        implicit = self._begin_implicit_insert_group(start)
        self.core.editor.record_native_insert(start, text)
        if implicit:
            self.core.editor.end_native_group(self.buffer_port.capture_view())
            self._refresh_projection()

    def _on_delete_range_before(self, _buffer, start_iter, end_iter) -> None:
        if self._editing_suppressed():
            return
        start = start_iter.get_offset()
        end = end_iter.get_offset()
        if end <= start:
            return
        implicit = False
        if not self.core.editor.native_group_active:
            self.core.editor.begin_native_group(self.buffer_port.capture_view())
            implicit = True
        deleted = self.buffer_port.text_in_range(start, end)
        direction = self.buffer_port.delete_direction(start, end)
        self.core.editor.record_native_delete(start, deleted, direction=direction)
        self._implicit_delete_group = implicit

    def _on_delete_range_after(self, _buffer, _start_iter, _end_iter) -> None:
        if self._editing_suppressed():
            return
        if self._implicit_delete_group and self.core.editor.native_group_active:
            self._implicit_delete_group = False
            self.core.editor.end_native_group(self.buffer_port.capture_view())
            self._refresh_projection()

    def _on_end_user_action(self, _buffer) -> None:
        if self._editing_suppressed():
            return
        self._implicit_delete_group = False
        if self.core.editor.native_group_active:
            self.core.editor.end_native_group(self.buffer_port.capture_view())
        self._refresh_projection()

    def _on_selection_changed(self, _buffer, _pspec) -> None:
        self._refresh_projection()

    def _title(self) -> str:
        path = self.core.session.logical_path
        name = Path(path).name if path else "Untitled"
        state = "Modified" if self.core.session.modified else "Saved"
        return f"{name} ({state}) — {PRODUCT_NAME}"

    def _refresh_projection(self) -> None:
        self.set_title(self._title())
        session = self.core.session
        availability = command_availability(
            modified=session.modified,
            has_path=session.logical_path is not None,
            can_undo=self.core.editor.can_undo,
            can_redo=self.core.editor.can_redo,
            has_selection=self.buffer.get_has_selection(),
        )
        self._actions["save"].set_enabled(availability.save)
        self._actions["undo"].set_enabled(availability.undo)
        self._actions["redo"].set_enabled(availability.redo)
        self._actions["cut"].set_enabled(availability.cut)
        self._actions["copy"].set_enabled(availability.copy)
        self._actions["delete"].set_enabled(availability.delete)

    def _action_new(self, *_args) -> None:
        self.core.lifecycle.new_document()
        self._refresh_projection()
        self.text_view.grab_focus()

    def _action_open(self, *_args) -> None:
        self.core.lifecycle.open_document()
        self._refresh_projection()
        self.text_view.grab_focus()

    def open_path(self, path: str) -> bool:
        result = self.core.lifecycle.open_document(path)
        self._refresh_projection()
        self.text_view.grab_focus()
        return result.completed

    def _action_save(self, *_args) -> None:
        self.core.lifecycle.save()
        self._refresh_projection()

    def _action_save_as(self, *_args) -> None:
        self.core.lifecycle.save_as()
        self._refresh_projection()

    def _action_quit(self, *_args) -> None:
        self.close()

    def _action_undo(self, *_args) -> None:
        self.core.editor.undo()
        self._refresh_projection()

    def _action_redo(self, *_args) -> None:
        self.core.editor.redo()
        self._refresh_projection()

    def _action_cut(self, *_args) -> None:
        self.text_view.emit("cut-clipboard")

    def _action_copy(self, *_args) -> None:
        self.text_view.emit("copy-clipboard")

    def _action_paste(self, *_args) -> None:
        self.text_view.emit("paste-clipboard")

    def _action_delete(self, *_args) -> None:
        self.buffer.begin_user_action()
        try:
            self.buffer.delete_selection(True, True)
        finally:
            self.buffer.end_user_action()

    def _action_select_all(self, *_args) -> None:
        start, end = self.buffer.get_bounds()
        self.buffer.select_range(start, end)

    def _set_search_status(self, message: str) -> None:
        if self._search_status is not None:
            self._search_status.set_text(message)

    def _search_entry_key_press(self, _widget, event) -> bool:
        if event.keyval == Gdk.KEY_Escape:
            self._close_search_bar()
            return True
        return False

    def _ensure_search_bar(self) -> None:
        if self._search_bar is not None:
            return
        bar = Gtk.SearchBar()
        bar.set_show_close_button(True)
        grid = Gtk.Grid(column_spacing=8, row_spacing=5)
        grid.set_border_width(6)
        bar.add(grid)

        query_label = Gtk.Label(label="Find:")
        query_label.set_xalign(0.0)
        query = Gtk.SearchEntry()
        query.set_width_chars(24)
        previous = Gtk.Button(label="Previous")
        next_button = Gtk.Button(label="Next")
        match_case = Gtk.CheckButton(label="Match Case")
        status = Gtk.Label(label="")
        status.set_xalign(0.0)

        grid.attach(query_label, 0, 0, 1, 1)
        grid.attach(query, 1, 0, 1, 1)
        grid.attach(previous, 2, 0, 1, 1)
        grid.attach(next_button, 3, 0, 1, 1)
        grid.attach(match_case, 4, 0, 1, 1)
        grid.attach(status, 5, 0, 1, 1)

        replace_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        replace_label = Gtk.Label(label="Replace with:")
        replacement = Gtk.Entry()
        replacement.set_width_chars(24)
        replace_one = Gtk.Button(label="Replace")
        replace_all = Gtk.Button(label="Replace All")
        replace_row.pack_start(replace_label, False, False, 0)
        replace_row.pack_start(replacement, True, True, 0)
        replace_row.pack_start(replace_one, False, False, 0)
        replace_row.pack_start(replace_all, False, False, 0)
        grid.attach(replace_row, 0, 1, 6, 1)

        query.connect("activate", lambda *_args: self._perform_find_next())
        query.connect("key-press-event", self._search_entry_key_press)
        replacement.connect("activate", lambda *_args: self._perform_replace_one())
        replacement.connect("key-press-event", self._search_entry_key_press)
        previous.connect("clicked", lambda *_args: self._perform_find_previous())
        next_button.connect("clicked", lambda *_args: self._perform_find_next())
        replace_one.connect("clicked", lambda *_args: self._perform_replace_one())
        replace_all.connect("clicked", lambda *_args: self._perform_replace_all())
        match_case.connect("toggled", self._on_search_option_changed)
        query.connect("changed", self._on_query_entry_changed)
        replacement.connect("changed", self._on_replacement_entry_changed)
        bar.connect_entry(query)
        bar.connect("notify::search-mode-enabled", self._on_search_mode_changed)

        container = self.get_child()
        assert isinstance(container, Gtk.Box)
        container.pack_start(bar, False, False, 0)
        container.reorder_child(bar, 1)

        self._search_bar = bar
        self._search_query_entry = query
        self._search_replace_entry = replacement
        self._search_replace_row = replace_row
        self._search_match_case = match_case
        self._search_status = status
        bar.show_all()
        replace_row.hide()
        bar.set_search_mode(False)

    def _on_search_mode_changed(self, bar: Gtk.SearchBar, _param) -> None:
        if not bar.get_search_mode():
            self.text_view.grab_focus()

    def _on_query_entry_changed(self, entry: Gtk.Entry) -> None:
        query = entry.get_text()
        if not query:
            self.core.search.clear_query()
            self._set_search_status("")
            return
        try:
            self.core.search.configure(query=query)
            self._set_search_status("")
        except SearchInputError as exc:
            self._set_search_status(str(exc))

    def _on_replacement_entry_changed(self, entry: Gtk.Entry) -> None:
        try:
            self.core.search.configure(replacement=entry.get_text())
        except SearchInputError as exc:
            self._set_search_status(str(exc))

    def _on_search_option_changed(self, button: Gtk.CheckButton) -> None:
        self.core.search.configure(match_case=button.get_active())
        self._set_search_status("")

    def _sync_search_fields(self) -> bool:
        assert self._search_query_entry is not None
        assert self._search_replace_entry is not None
        assert self._search_match_case is not None
        query = self._search_query_entry.get_text()
        if not query:
            self.core.search.clear_query()
            self._set_search_status("Type text to find")
            self._search_query_entry.grab_focus()
            return False
        try:
            self.core.search.configure(
                query=query,
                replacement=self._search_replace_entry.get_text(),
                match_case=self._search_match_case.get_active(),
            )
        except SearchInputError as exc:
            self._set_search_status(str(exc))
            self._search_query_entry.grab_focus()
            return False
        return True

    def _selected_single_line_text(self) -> str | None:
        selected = self.buffer.get_selection_bounds()
        if not selected:
            return None
        start, end = selected
        text = self.buffer.get_text(start, end, True)
        if not text or "\n" in text or "\r" in text or len(text) > 4096:
            return None
        return text

    def _show_search_bar(self, *, replace_mode: bool) -> None:
        self._ensure_search_bar()
        assert self._search_bar is not None
        assert self._search_query_entry is not None
        assert self._search_replace_entry is not None
        assert self._search_replace_row is not None
        assert self._search_match_case is not None
        selected = self._selected_single_line_text()
        if selected is not None:
            self._search_query_entry.set_text(selected)
        elif self.core.search.has_query and self._search_query_entry.get_text() != self.core.search.query:
            self._search_query_entry.set_text(self.core.search.query)
        self._search_replace_entry.set_text(self.core.search.replacement)
        self._search_match_case.set_active(self.core.search.match_case)
        self._search_bar.set_search_mode(True)
        self._search_bar.show_all()
        self._search_replace_row.set_visible(replace_mode)
        self._set_search_status("")
        self._search_query_entry.grab_focus()
        self._search_query_entry.select_region(0, -1)

    def _close_search_bar(self) -> None:
        if self._search_bar is not None:
            self._search_bar.set_search_mode(False)
        self.text_view.grab_focus()

    def _search_snapshot(self) -> tuple[str, ViewState]:
        captured = self.buffer_port.capture_full()
        return captured.text, ViewState(captured.insert_offset, captured.selection_bound_offset)

    def _selection_offsets(self, view: ViewState | None = None) -> tuple[int, int]:
        if view is None:
            view = self.buffer_port.capture_view()
        return min(view.insert_offset, view.selection_bound_offset), max(
            view.insert_offset, view.selection_bound_offset
        )

    def _project_view(self, view: ViewState) -> None:
        insert = self.buffer.get_iter_at_offset(view.insert_offset)
        bound = self.buffer.get_iter_at_offset(view.selection_bound_offset)
        self.buffer.select_range(insert, bound)
        self.text_view.scroll_to_mark(self.buffer.get_insert(), 0.08, False, 0.0, 0.0)
        self._refresh_projection()

    def _project_match(self, match: SearchMatch) -> None:
        self._project_view(ViewState(match.end, match.start))

    def _perform_find_next(self) -> None:
        self._ensure_search_bar()
        if not self._sync_search_fields():
            return
        text, view = self._search_snapshot()
        start, end = self._selection_offsets(view)
        anchor = end if end > start else view.insert_offset
        result = self.core.search.find_next(text, anchor)
        if result.match is None:
            self._set_search_status("Not found")
            return
        self._project_match(result.match)
        self._set_search_status("Wrapped" if result.wrapped else "")

    def _perform_find_previous(self) -> None:
        self._ensure_search_bar()
        if not self._sync_search_fields():
            return
        text, view = self._search_snapshot()
        start, end = self._selection_offsets(view)
        anchor = start if end > start else view.insert_offset
        result = self.core.search.find_previous(text, anchor)
        if result.match is None:
            self._set_search_status("Not found")
            return
        self._project_match(result.match)
        self._set_search_status("Wrapped" if result.wrapped else "")

    def _apply_replacement_plan(self, plan) -> None:
        if plan.changed:
            self.core.editor.apply_prevalidated_programmatic_group(
                operations=plan.operations,
                expected_source_state_id=plan.source_state_id,
                final_text=plan.final_text,
                before_view=plan.before_view,
                target_view=plan.target_view,
            )
            self._refresh_projection()
        else:
            self._project_view(plan.target_view)
        self.text_view.scroll_to_mark(self.buffer.get_insert(), 0.08, False, 0.0, 0.0)

    def _perform_replace_one(self) -> None:
        self._ensure_search_bar()
        if not self._sync_search_fields():
            return
        text, view = self._search_snapshot()
        start, end = self._selection_offsets(view)
        try:
            plan = self.core.search.build_replace_one_plan(
                source_text=text,
                source_state_id=self.core.history.current_state_id,
                before_view=view,
                selection_start=start,
                selection_end=end,
            )
            if plan is None:
                self._set_search_status("Not found")
                return
            self._apply_replacement_plan(plan)
            self._set_search_status("Replaced" if plan.changed else "No text change")
        except Exception as exc:
            self._ui.show_warning("Replace was not applied", str(exc))

    def _perform_replace_all(self) -> None:
        self._ensure_search_bar()
        if not self._sync_search_fields():
            return
        text, view = self._search_snapshot()
        try:
            plan = self.core.search.build_replace_all_plan(
                source_text=text,
                source_state_id=self.core.history.current_state_id,
                before_view=view,
            )
            self._apply_replacement_plan(plan)
            if plan.changed_count == 0:
                self._set_search_status("No changes")
            elif plan.changed_count == 1:
                self._set_search_status("1 replacement")
            else:
                self._set_search_status(f"{plan.changed_count} replacements")
        except Exception as exc:
            self._ui.show_warning("Replace All was not applied", str(exc))

    def _action_find(self, *_args) -> None:
        self._show_search_bar(replace_mode=False)

    def _action_find_next(self, *_args) -> None:
        if not self.core.search.has_query:
            self._show_search_bar(replace_mode=False)
            return
        search_visible = self._search_bar is not None and self._search_bar.get_search_mode()
        self._ensure_search_bar()
        assert self._search_query_entry is not None
        if not self._search_query_entry.get_text():
            self._search_query_entry.set_text(self.core.search.query)
        self._perform_find_next()
        if not search_visible:
            self.text_view.grab_focus()

    def _action_find_previous(self, *_args) -> None:
        if not self.core.search.has_query:
            self._show_search_bar(replace_mode=False)
            return
        search_visible = self._search_bar is not None and self._search_bar.get_search_mode()
        self._ensure_search_bar()
        assert self._search_query_entry is not None
        if not self._search_query_entry.get_text():
            self._search_query_entry.set_text(self.core.search.query)
        self._perform_find_previous()
        if not search_visible:
            self.text_view.grab_focus()

    def _action_replace(self, *_args) -> None:
        self._show_search_bar(replace_mode=True)

    def _action_go_to_line(self, *_args) -> None:
        insert = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        chosen = choose_line_number(
            self,
            current_line=insert.get_line() + 1,
            max_line=self.buffer.get_line_count(),
        )
        if chosen is None:
            self.text_view.grab_focus()
            return
        target = self.buffer.get_iter_at_line(chosen - 1)
        self.buffer.place_cursor(target)
        self.text_view.scroll_to_iter(target, 0.08, False, 0.0, 0.0)
        self._refresh_projection()
        self.text_view.grab_focus()

    @staticmethod
    def _help_path(name: str) -> str:
        return str(Path(__file__).resolve().parents[3] / "docs" / "user" / name)

    def _action_user_guide(self, *_args) -> None:
        show_text_document(
            self,
            title="Graphium User Guide",
            path=self._help_path("GRAPHIUM_USER_GUIDE.txt"),
        )

    def _action_keyboard_shortcuts(self, *_args) -> None:
        show_text_document(
            self,
            title="Graphium Keyboard Shortcuts",
            path=self._help_path("GRAPHIUM_KEYBOARD_SHORTCUTS.txt"),
        )

    def _action_about(self, *_args) -> None:
        show_about(self, version=VERSION)

    def _on_delete_event(self, *_args) -> bool:
        if self._closing_accepted:
            return False
        result = self.core.lifecycle.request_close()
        if not result.completed:
            self._refresh_projection()
            return True
        self._closing_accepted = True
        return False

    def begin_startup_open(self) -> None:
        self._startup_open_pending = True

    def finish_startup_open(self) -> None:
        self._startup_open_pending = False
        self._schedule_benchmark_ready_if_ready()

    def _on_mapped(self, *_args) -> bool:
        self._mapped = True
        self._schedule_benchmark_ready_if_ready()
        return False

    def _schedule_benchmark_ready_if_ready(self) -> None:
        if self._mapped and not self._startup_open_pending and not self._benchmark_ready_emitted:
            GLib.idle_add(self._emit_benchmark_ready)

    def _emit_benchmark_ready(self) -> bool:
        if self._benchmark_ready_emitted or self._startup_open_pending or not self._mapped:
            return False
        self.text_view.grab_focus()
        self._benchmark_ready_emitted = True
        raw_fd = os.environ.get("GRAPHIUM_BENCHMARK_READY_FD")
        if raw_fd:
            try:
                fd = int(raw_fd)
                payload = f"READY {os.getpid()} {time.monotonic_ns()}\n".encode("ascii")
                os.write(fd, payload)  # one short PIPE_BUF-bounded atomic write
                os.close(fd)
            except (OSError, ValueError):
                pass
        return False
