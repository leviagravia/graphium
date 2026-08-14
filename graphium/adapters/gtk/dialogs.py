"""Small GTK dialog/chooser adapter for the G04 lifecycle UI port."""
from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from graphium.application.file_lifecycle import UnsavedDecision


class GtkLifecycleUI:
    __slots__ = ("parent",)

    def __init__(self, parent: Gtk.Window) -> None:
        self.parent = parent

    def choose_open_path(self) -> str | None:
        dialog = Gtk.FileChooserNative.new(
            "Open File", self.parent, Gtk.FileChooserAction.OPEN, "Open", "Cancel"
        )
        try:
            response = dialog.run()
            return dialog.get_filename() if response == Gtk.ResponseType.ACCEPT else None
        finally:
            dialog.destroy()

    def choose_save_path(self, current_path: str | None) -> str | None:
        dialog = Gtk.FileChooserNative.new(
            "Save File", self.parent, Gtk.FileChooserAction.SAVE, "Save", "Cancel"
        )
        dialog.set_do_overwrite_confirmation(False)
        if current_path:
            dialog.set_filename(current_path)
        else:
            dialog.set_current_name("Untitled.txt")
        try:
            response = dialog.run()
            return dialog.get_filename() if response == Gtk.ResponseType.ACCEPT else None
        finally:
            dialog.destroy()

    def confirm_unsaved_changes(self, action_label: str) -> UnsavedDecision:
        dialog = Gtk.MessageDialog(
            transient_for=self.parent,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text="Save changes before continuing?",
        )
        dialog.format_secondary_text(
            f"The document has unsaved changes. Save them before you {action_label}?"
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Discard Changes", Gtk.ResponseType.REJECT)
        dialog.add_button("Save", Gtk.ResponseType.ACCEPT)
        dialog.set_default_response(Gtk.ResponseType.ACCEPT)
        try:
            response = dialog.run()
        finally:
            dialog.destroy()
        if response == Gtk.ResponseType.ACCEPT:
            return UnsavedDecision.SAVE
        if response == Gtk.ResponseType.REJECT:
            return UnsavedDecision.DISCARD
        return UnsavedDecision.CANCEL

    def confirm_overwrite(self, path: str) -> bool:
        dialog = Gtk.MessageDialog(
            transient_for=self.parent,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text="Replace existing file?",
        )
        dialog.format_secondary_text(
            f"A file already exists at:\n{path}\n\nGraphium will replace it only if it is still the same file at commit time."
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Replace", Gtk.ResponseType.ACCEPT)
        try:
            return dialog.run() == Gtk.ResponseType.ACCEPT
        finally:
            dialog.destroy()

    def confirm_mixed_eol_normalization(self) -> bool:
        dialog = Gtk.MessageDialog(
            transient_for=self.parent,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text="Normalize mixed line endings?",
        )
        dialog.format_secondary_text(
            "This file contains mixed line endings. Saving will normalize them to the dominant style."
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Save and Normalize", Gtk.ResponseType.ACCEPT)
        try:
            return dialog.run() == Gtk.ResponseType.ACCEPT
        finally:
            dialog.destroy()

    def _message(self, message_type, title: str, message: str) -> None:
        dialog = Gtk.MessageDialog(
            transient_for=self.parent,
            modal=True,
            message_type=message_type,
            buttons=Gtk.ButtonsType.CLOSE,
            text=title,
        )
        dialog.format_secondary_text(message)
        try:
            dialog.run()
        finally:
            dialog.destroy()

    def show_error(self, title: str, message: str) -> None:
        self._message(Gtk.MessageType.ERROR, title, message)

    def show_warning(self, title: str, message: str) -> None:
        self._message(Gtk.MessageType.WARNING, title, message)


def show_text_document(parent: Gtk.Window, *, title: str, path: str) -> None:
    """Show a UTF-8 offline help document, loading it only on explicit user request."""
    from pathlib import Path

    try:
        text = Path(path).read_text(encoding="utf-8")
    except Exception as exc:
        GtkLifecycleUI(parent).show_error("Could not open Help", str(exc))
        return
    dialog = Gtk.Dialog(title=title, transient_for=parent, modal=True)
    dialog.add_button("Close", Gtk.ResponseType.CLOSE)
    dialog.set_default_size(720, 560)
    area = dialog.get_content_area()
    scroller = Gtk.ScrolledWindow()
    scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    view = Gtk.TextView()
    view.set_editable(False)
    view.set_cursor_visible(False)
    view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    view.set_left_margin(12)
    view.set_right_margin(12)
    view.set_top_margin(10)
    view.set_bottom_margin(10)
    view.get_buffer().set_text(text)
    scroller.add(view)
    area.pack_start(scroller, True, True, 0)
    dialog.show_all()
    try:
        dialog.run()
    finally:
        dialog.destroy()


def show_about(parent: Gtk.Window, *, version: str) -> None:
    dialog = Gtk.AboutDialog(transient_for=parent, modal=True)
    dialog.set_program_name("Graphium")
    dialog.set_version(version)
    dialog.set_comments("Fast, simple and safety-focused plain-text editor for Linux.")
    dialog.set_website("https://github.com/leviagravia/graphium")
    dialog.set_website_label("Graphium repository")
    try:
        dialog.run()
    finally:
        dialog.destroy()
