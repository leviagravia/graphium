<p align="center">
  <img src="assets/graphium.svg" width="128" height="128" alt="Graphium logo">
</p>

<h1 align="center">Graphium</h1>

<p align="center">
  <strong>Fast · Simple · Safe · Native GTK</strong>
</p>

<p align="center">
  A lightweight plain-text editor for Linux with unusually strict file-safety semantics.
</p>

Graphium is a native **GTK 3 / Gtk.TextView** editor for quick single-file work.

It deliberately keeps the classic lightweight-editor model — **one process, one window, one active document** — while adding careful file handling, exact Saved/Modified state, representation preservation, recovery, printing, spell checking and the everyday conveniences expected from a mature desktop editor.

Graphium has no projects, plugin platform, cloud service, hidden document database, syntax-highlighting subsystem or multi-document tab model.

## Why Graphium?

### Lightweight by design

Graphium is continuously benchmarked against **Leafpad, L3afpad, Mousepad and FeatherPad**.

Certified comparative runs place Graphium in the **same practical lightweight performance class** as these editors: startup and working-set results are broadly comparable for ordinary quick-edit use, although different editors lead in different workloads.

Graphium is not designed to win every microbenchmark. Its goal is to remain lightweight while providing stronger guarantees around the file being edited.

### Where Graphium goes further

**Compared with Leafpad and L3afpad**, Graphium keeps a similarly direct single-document workflow but provides a substantially broader trust and desktop-completeness layer: guarded saving, external-file monitoring, recovery, explicit encoding and line-ending control, printing, spell checking, appearance controls and richer file-state information.

**Compared with Mousepad**, Graphium deliberately keeps a smaller architectural surface: no server-style document sharing, no tabs, no syntax/language subsystem and no plugin platform. At the same time, its Save model explicitly separates editor state from filesystem state and treats external notifications only as triggers for fresh observation.

**Compared with FeatherPad**, Graphium is intentionally narrower. FeatherPad is stronger for users who need tabs, sessions, syntax highlighting or power-editor features; Graphium instead focuses on a single-document GTK workflow with a smaller conceptual surface and stricter file-preservation rules.

Graphium's clearest advantage is therefore not feature count alone. It is the combination of:

- **lightweight quick-edit behavior**;
- **guarded file writes and destination revalidation**;
- **content-neutral Open and Save**;
- **explicit preservation of encoding, BOM and line endings**;
- **external-change detection without silent reload/adoption**;
- **exact Saved/Modified semantics across Undo and Redo**;
- **crash recovery without turning the editor into a session manager**;
- enough mature desktop features to avoid feeling intentionally incomplete.

## File safety

Graphium treats the state of the file on disk separately from the text visible in the editor.

Saving uses same-directory staging and revalidates the destination before replacement. If another process replaces or changes the file unexpectedly, Graphium fails closed instead of silently overwriting the new filesystem object.

External filesystem notifications are not accepted as authoritative state. They trigger a fresh observation of the file, and unexpected changes are reported to the user.

Graphium does **not** silently normalize a file merely because it was opened and saved. Encoding, BOM, line endings, whitespace and final-newline representation are preserved unless the user explicitly requests a conversion or transformation.

## Features

### Files and safety

- New, Open, Open Recent, Save and Save As
- **Save a Copy**
- **Save Version Copy**
- guarded saving with destination revalidation
- external-file change detection
- explicit **Reload from Disk**
- crash recovery
- UTF-8, UTF-16 and UTF-32
- LF, CRLF and CR line endings
- explicit handling of mixed line endings

### Editing

- Undo / Redo
- Cut / Copy / Paste / Delete / Select All
- Find / Replace
- Go to Line
- Duplicate Line / Selection
- Move Lines Up / Down
- Uppercase / Lowercase
- Trim Trailing Spaces

### View and document controls

- Line Numbers
- Word Wrap
- Font and Zoom
- compact status information
- System / Light / Dark appearance
- direct **Tab Width**
- direct **Insert Spaces Instead of Tabs**
- document statistics
- explicit encoding and line-ending conversion

### Desktop integration

- Hunspell spell checking with selection among installed dictionaries
- GTK Page Setup
- Print Preview
- Print
- offline User Guide
- offline Keyboard Shortcuts
- native Linux desktop entry and application icon

## Editing model

Graphium is intentionally single-document.

To edit several files at the same time, open several Graphium windows. Each invocation owns its own process, window and active document.

Search is literal and limited to the current document. Graphium intentionally does not provide project search, regular expressions, syntax highlighting, tabs or plugins.

## Installation

### Debian / Ubuntu / Linux Mint

Download the current `.deb` from the repository's **Releases** page and install it with:

```bash
sudo apt install ./graphium_<version>_all.deb
```

### Run from source

Requirements:

- Linux
- Python 3
- PyGObject
- GTK 3
- Hunspell (optional, for spell checking)

```bash
git clone https://github.com/leviagravia/graphium.git
cd graphium
./bin/graphium
```

### Install for the current user

```bash
./bin/graphium-install
```

The default installation prefix is `~/.local`.

## Keyboard shortcuts

| Action | Shortcut |
|---|---|
| New | `Ctrl+N` |
| Open | `Ctrl+O` |
| Save | `Ctrl+S` |
| Save As | `Ctrl+Shift+S` |
| Reload from Disk | `F5` |
| Undo | `Ctrl+Z` |
| Redo | `Ctrl+Shift+Z` |
| Find | `Ctrl+F` |
| Find Next | `F3` |
| Find Previous | `Shift+F3` |
| Replace | `Ctrl+H` |
| Go to Line | `Ctrl+G` |
| Uppercase | `Ctrl+U` |
| Lowercase | `Ctrl+Shift+L` |
| Print | `Ctrl+P` |
| Full Screen | `F11` |
| Move Lines Up | `Alt+Up` |
| Move Lines Down | `Alt+Down` |
| Quit | `Ctrl+Q` |

See [`docs/user/GRAPHIUM_KEYBOARD_SHORTCUTS.txt`](docs/user/GRAPHIUM_KEYBOARD_SHORTCUTS.txt) for the complete list.

## Deliberate non-goals

Graphium is not trying to be a smaller IDE.

It deliberately does **not** provide:

- tabs inside one window;
- project/workspace management;
- syntax highlighting;
- language modes;
- column editing;
- plugin marketplace;
- integrated file browser;
- cloud services.

Users who depend on those workflows may be better served by Mousepad, FeatherPad, Kate or a code-oriented editor.

Graphium instead focuses on the quick-edit user who values a conventional interface, low cognitive load and strong trust in Save and file-state behavior.

## Documentation

- [`User Guide`](docs/user/GRAPHIUM_USER_GUIDE.txt)
- [`Keyboard Shortcuts`](docs/user/GRAPHIUM_KEYBOARD_SHORTCUTS.txt)

Both are also available offline from Graphium's **Help** menu.

## About the name

*Graphium* is Latin for a **writing stylus**, the instrument traditionally used to write on wax tablets: a simple tool made for writing.

## License

Graphium is free software released under the **GNU General Public License v3.0 or later (GPL-3.0-or-later)**.

See [`LICENSE`](LICENSE) for the complete license terms.

## Author

**leviagravia**  
`leviagravia@zohomail.eu`

---

**Graphium** — a lightweight native GTK editor built around a simple idea: the text editor should never make you distrust your file.
