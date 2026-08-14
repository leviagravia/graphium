"""Minimal Graphium G04 command catalog.

The first credible quick-edit shell exposes only essential editing/file commands plus
lazy offline Help. Later work items extend this same product-owned catalog; GTK is not the
command authority.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandSpec:
    action: str
    label: str
    accelerator: str | None = None
    menu: str = ""


COMMANDS = (
    CommandSpec("new", "New", "<Ctrl>N", "File"),
    CommandSpec("open", "Open…", "<Ctrl>O", "File"),
    CommandSpec("save", "Save", "<Ctrl>S", "File"),
    CommandSpec("save-as", "Save As…", "<Ctrl><Shift>S", "File"),
    CommandSpec("quit", "Quit", "<Ctrl>Q", "File"),
    CommandSpec("undo", "Undo", "<Ctrl>Z", "Edit"),
    CommandSpec("redo", "Redo", "<Ctrl><Shift>Z", "Edit"),
    CommandSpec("cut", "Cut", "<Ctrl>X", "Edit"),
    CommandSpec("copy", "Copy", "<Ctrl>C", "Edit"),
    CommandSpec("paste", "Paste", "<Ctrl>V", "Edit"),
    CommandSpec("delete", "Delete", "Delete", "Edit"),
    CommandSpec("select-all", "Select All", "<Ctrl>A", "Edit"),
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
