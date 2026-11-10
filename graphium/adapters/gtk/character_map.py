"""Large, readable native GTK3 Character Map for Graphium."""
from __future__ import annotations

from collections.abc import Callable

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from graphium.application.character_map import (
    ALL_GROUP_KEY,
    CHARACTER_GROUPS,
    PAGE_SIZE,
    CharacterEntry,
    page_count,
    page_slice,
    search_entries,
)


class CharacterMapDialog(Gtk.Dialog):
    """Modeless Unicode picker whose only side effect is its explicit insert callback."""

    PARENT_SIZE_RATIO = 0.75
    FALLBACK_PARENT_WIDTH = 720
    FALLBACK_PARENT_HEIGHT = 520
    MIN_WIDTH = 480
    MIN_HEIGHT = 360
    GLYPH_CELL_SIZE = 76
    GLYPH_FONT_PT = 30
    PREVIEW_FONT_PT = 88

    def __init__(self, parent: Gtk.Window, *, on_insert: Callable[[str], None]) -> None:
        super().__init__(title="Character Map", transient_for=parent, modal=False)
        self.set_destroy_with_parent(True)
        self.set_resizable(True)
        target_width, target_height = self._initial_size_for_parent(parent)
        self.set_default_size(target_width, target_height)
        self.set_size_request(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.set_border_width(0)
        self.connect("destroy", self._on_destroy)

        self._on_insert = on_insert
        self._entries: tuple[CharacterEntry, ...] = ()
        self._page = 0
        self._selected: CharacterEntry | None = None
        self._refresh_source_id = 0

        self.add_button("Close", Gtk.ResponseType.CLOSE)
        self._insert_button = self.add_button("Insert", Gtk.ResponseType.APPLY)
        self._insert_button.set_sensitive(False)
        self.set_default_response(Gtk.ResponseType.APPLY)
        self.connect("response", self._on_response)

        self._css_provider = Gtk.CssProvider()
        css = (
            ".graphium-character-glyph { font-size: %dpt; padding: 6px; }\n"
            ".graphium-character-preview { font-size: %dpt; padding: 4px 18px; }\n"
            ".graphium-character-name { font-weight: bold; }\n"
        ) % (self.GLYPH_FONT_PT, self.PREVIEW_FONT_PT)
        self._css_provider.load_from_data(css.encode("utf-8"))

        content = self.get_content_area()
        content.set_spacing(10)
        content.set_border_width(12)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        content.pack_start(top, False, False, 0)

        group_label = Gtk.Label(label="Group:")
        group_label.set_xalign(0.0)
        top.pack_start(group_label, False, False, 0)
        self._group_combo = Gtk.ComboBoxText()
        self._group_combo.append(ALL_GROUP_KEY, "All")
        for group in CHARACTER_GROUPS:
            self._group_combo.append(group.key, group.label)
        self._group_combo.set_active_id("latin")
        self._group_combo.connect("changed", self._queue_refresh)
        top.pack_start(self._group_combo, False, False, 0)

        self._search = Gtk.SearchEntry()
        self._search.set_placeholder_text("Search character, Unicode name, or U+03A9")
        self._search.set_hexpand(True)
        self._search.connect("search-changed", self._queue_refresh)
        top.pack_start(self._search, True, True, 0)

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        content.pack_start(body, True, True, 0)

        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        body.pack_start(left, True, True, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.set_shadow_type(Gtk.ShadowType.IN)
        left.pack_start(scroller, True, True, 0)

        self._flow = Gtk.FlowBox()
        self._flow.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._flow.set_activate_on_single_click(False)
        self._flow.set_column_spacing(6)
        self._flow.set_row_spacing(6)
        self._flow.set_homogeneous(True)
        self._flow.set_min_children_per_line(2)
        self._flow.set_max_children_per_line(16)
        self._flow.connect("selected-children-changed", self._on_selection_changed)
        self._flow.connect("child-activated", self._on_child_activated)
        scroller.add(self._flow)

        pager = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        left.pack_start(pager, False, False, 0)
        self._previous_button = Gtk.Button(label="Previous")
        self._previous_button.connect("clicked", self._on_previous)
        pager.pack_start(self._previous_button, False, False, 0)
        self._page_label = Gtk.Label()
        self._page_label.set_xalign(0.5)
        pager.pack_start(self._page_label, True, True, 0)
        self._next_button = Gtk.Button(label="Next")
        self._next_button.connect("clicked", self._on_next)
        pager.pack_end(self._next_button, False, False, 0)

        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        details.set_size_request(200, -1)
        body.pack_start(details, False, False, 0)

        preview_frame = Gtk.Frame(label="Selected character")
        details.pack_start(preview_frame, False, False, 0)
        self._preview = Gtk.Label(label="—")
        self._preview.set_size_request(180, 130)
        self._apply_css_class(self._preview, "graphium-character-preview")
        preview_frame.add(self._preview)

        self._name = Gtk.Label(label="Select a character")
        self._name.set_line_wrap(True)
        self._name.set_xalign(0.0)
        self._name.set_selectable(True)
        self._apply_css_class(self._name, "graphium-character-name")
        details.pack_start(self._name, False, False, 0)

        self._code = Gtk.Label(label="")
        self._code.set_xalign(0.0)
        self._code.set_selectable(True)
        details.pack_start(self._code, False, False, 0)

        self._category = Gtk.Label(label="")
        self._category.set_xalign(0.0)
        details.pack_start(self._category, False, False, 0)

        hint = Gtk.Label(label="Double-click a character, or select it and choose Insert.")
        hint.set_line_wrap(True)
        hint.set_xalign(0.0)
        details.pack_end(hint, False, False, 0)

        self._refresh_results()
        self.show_all()
        self._search.grab_focus()


    @classmethod
    def _initial_size_for_parent(cls, parent: Gtk.Window) -> tuple[int, int]:
        """Return a readable dialog target at roughly three quarters of the editor."""
        try:
            parent_width, parent_height = parent.get_size()
        except Exception:
            parent_width, parent_height = cls.FALLBACK_PARENT_WIDTH, cls.FALLBACK_PARENT_HEIGHT
        if parent_width <= 1:
            parent_width = cls.FALLBACK_PARENT_WIDTH
        if parent_height <= 1:
            parent_height = cls.FALLBACK_PARENT_HEIGHT
        return (
            max(cls.MIN_WIDTH, int(round(parent_width * cls.PARENT_SIZE_RATIO))),
            max(cls.MIN_HEIGHT, int(round(parent_height * cls.PARENT_SIZE_RATIO))),
        )

    def _on_destroy(self, *_args) -> None:
        source_id = int(self._refresh_source_id)
        self._refresh_source_id = 0
        if source_id:
            try:
                GLib.source_remove(source_id)
            except Exception:
                pass

    def _apply_css_class(self, widget: Gtk.Widget, class_name: str) -> None:
        context = widget.get_style_context()
        context.add_class(class_name)
        context.add_provider(self._css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _queue_refresh(self, *_args) -> None:
        if self._refresh_source_id:
            GLib.source_remove(self._refresh_source_id)
        self._refresh_source_id = GLib.timeout_add(90, self._refresh_results)

    def _refresh_results(self) -> bool:
        self._refresh_source_id = 0
        group_key = self._group_combo.get_active_id() or "latin"
        self._entries = search_entries(group_key, self._search.get_text())
        self._page = 0
        self._render_page()
        return False

    def _clear_flow(self) -> None:
        for child in self._flow.get_children():
            self._flow.remove(child)

    def _render_page(self) -> None:
        self._clear_flow()
        self._selected = None
        self._update_details()
        visible = page_slice(self._entries, self._page, PAGE_SIZE)
        for entry in visible:
            child = Gtk.FlowBoxChild()
            child._graphium_character_entry = entry  # product-local projection metadata
            label = Gtk.Label(label=entry.display_text)
            label.set_size_request(self.GLYPH_CELL_SIZE, self.GLYPH_CELL_SIZE)
            label.set_tooltip_text(f"{entry.code_label}  {entry.name}")
            self._apply_css_class(label, "graphium-character-glyph")
            child.add(label)
            self._flow.add(child)
        self._flow.show_all()

        pages = page_count(len(self._entries), PAGE_SIZE)
        if self._page >= pages:
            self._page = pages - 1
        self._previous_button.set_sensitive(self._page > 0)
        self._next_button.set_sensitive(self._page + 1 < pages)
        if self._entries:
            first = self._page * PAGE_SIZE + 1
            last = min(len(self._entries), first + PAGE_SIZE - 1)
            self._page_label.set_text(f"{first}–{last} of {len(self._entries)}  •  Page {self._page + 1} of {pages}")
        else:
            self._page_label.set_text("No matching characters")

    def _selected_entry_from_flow(self) -> CharacterEntry | None:
        selected = self._flow.get_selected_children()
        if not selected:
            return None
        return getattr(selected[0], "_graphium_character_entry", None)

    def _on_selection_changed(self, _flow) -> None:
        self._selected = self._selected_entry_from_flow()
        self._update_details()

    def _on_child_activated(self, _flow, child) -> None:
        entry = getattr(child, "_graphium_character_entry", None)
        if entry is not None:
            self._selected = entry
            self._update_details()
            self._insert_selected()

    def _update_details(self) -> None:
        entry = self._selected
        self._insert_button.set_sensitive(entry is not None)
        if entry is None:
            self._preview.set_text("—")
            self._name.set_text("Select a character")
            self._code.set_text("")
            self._category.set_text("")
            return
        self._preview.set_text(entry.display_text)
        self._name.set_text(entry.name)
        self._code.set_text(entry.code_label)
        self._category.set_text(f"Unicode category: {entry.category}")

    def _insert_selected(self) -> None:
        if self._selected is None:
            return
        self._on_insert(self._selected.char)

    def _on_previous(self, _button) -> None:
        if self._page <= 0:
            return
        self._page -= 1
        self._render_page()

    def _on_next(self, _button) -> None:
        if self._page + 1 >= page_count(len(self._entries), PAGE_SIZE):
            return
        self._page += 1
        self._render_page()

    def _on_response(self, dialog, response_id) -> None:
        if response_id == Gtk.ResponseType.APPLY:
            self._insert_selected()
            return
        dialog.destroy()
