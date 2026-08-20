"""Graphium product-owned command catalog through G08.

The catalog is the single command authority shared by menus, accelerators and Help.
Boolean direct View settings are stateful actions; their persistence remains owned by
G06 view-settings authority, not by GTK widgets.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandSpec:
    action: str
    label: str
    accelerator: str | None = None
    menu: str = ""
    stateful: bool = False


COMMANDS = (
    CommandSpec("new", "New", "<Ctrl>N", "File"),
    CommandSpec("open", "Open…", "<Ctrl>O", "File"),
    CommandSpec("open-recent", "Open Recent", None, "File"),
    CommandSpec("clear-recent", "Clear Recent", None, "Recent"),
    CommandSpec("save", "Save", "<Ctrl>S", "File"),
    CommandSpec("save-as", "Save As…", "<Ctrl><Shift>S", "File"),
    CommandSpec("save-copy", "Save a Copy…", None, "File"),
    CommandSpec("save-version-copy", "Save Version Copy…", None, "File"),
    CommandSpec("properties", "Properties…", None, "File"),
    CommandSpec("page-setup", "Page Setup…", None, "File"),
    CommandSpec("print-preview", "Print Preview", "<Ctrl><Shift>P", "File"),
    CommandSpec("print", "Print…", "<Ctrl>P", "File"),
    CommandSpec("quit", "Quit", "<Ctrl>Q", "File"),
    CommandSpec("undo", "Undo", "<Ctrl>Z", "Edit"),
    CommandSpec("redo", "Redo", "<Ctrl><Shift>Z", "Edit"),
    CommandSpec("cut", "Cut", "<Ctrl>X", "Edit"),
    CommandSpec("copy", "Copy", "<Ctrl>C", "Edit"),
    CommandSpec("paste", "Paste", "<Ctrl>V", "Edit"),
    CommandSpec("delete", "Delete", "Delete", "Edit"),
    CommandSpec("select-all", "Select All", "<Ctrl>A", "Edit"),
    CommandSpec("find", "Find…", "<Ctrl>F", "Search"),
    CommandSpec("find-next", "Find Next", "F3", "Search"),
    CommandSpec("find-previous", "Find Previous", "<Shift>F3", "Search"),
    CommandSpec("replace", "Replace…", "<Ctrl>H", "Search"),
    CommandSpec("go-to-line", "Go to Line…", "<Ctrl>G", "Search"),
    CommandSpec("status-bar", "Status Bar", None, "View", True),
    CommandSpec("line-numbers", "Line Numbers", None, "View", True),
    CommandSpec("word-wrap", "Word Wrap", None, "View", True),
    CommandSpec("font", "Font…", None, "View"),
    CommandSpec("zoom-in", "Zoom In", "<Ctrl>plus", "View"),
    CommandSpec("zoom-out", "Zoom Out", "<Ctrl>minus", "View"),
    CommandSpec("zoom-reset", "Reset Zoom", "<Ctrl>0", "View"),
    CommandSpec("full-screen", "Full Screen", "F11", "View", True),
    CommandSpec("statistics", "Statistics…", None, "Document"),
    CommandSpec("user-guide", "User Guide", None, "Help"),
    CommandSpec("keyboard-shortcuts", "Keyboard Shortcuts", None, "Help"),
    CommandSpec("about", "About", None, "Help"),
)

FORBIDDEN_ACCELERATORS = ("<Ctrl><Alt>L",)


def accelerator_map() -> dict[str, str]:
    return {item.action: item.accelerator for item in COMMANDS if item.accelerator}


@dataclass(frozen=True)
class CommandAvailability:
    save: bool
    undo: bool
    redo: bool
    cut: bool
    copy: bool
    delete: bool


def command_availability(
    *,
    modified: bool,
    has_path: bool,
    can_undo: bool,
    can_redo: bool,
    has_selection: bool,
) -> CommandAvailability:
    return CommandAvailability(
        save=modified or not has_path,
        undo=can_undo,
        redo=can_redo,
        cut=has_selection,
        copy=has_selection,
        delete=has_selection,
    )
