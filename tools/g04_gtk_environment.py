#!/usr/bin/env python3
"""Report the GTK3 runtime version without relying on non-existent convenience APIs."""
from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


def main() -> None:
    version = (Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version())
    print("GTK_VERSION=" + ".".join(str(part) for part in version))


if __name__ == "__main__":
    main()
