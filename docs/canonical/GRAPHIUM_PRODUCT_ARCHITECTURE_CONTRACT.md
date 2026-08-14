# Graphium — Product & Architecture Contract

Canonical document 1 of 3.
Initial freeze: 2026-08-13 — G00.
Status: **G00 FROZEN / HEADLESS VERIFIED / INITIAL REPOSITORY BASELINE AUTHORIZED**.
Repository-baseline authorization: 2026-08-14.

## 1. Product identity

Graphium is a native Linux desktop text editor derived by selective, provenance-recorded extraction from the published Calamus W116 baseline. Graphium is an **independent product**, not a Calamus edition and not a feature-flag profile of the Calamus source tree.

Graphium v1 is:

- GTK native;
- **single-document**;
- general-purpose plain-text editing first;
- filesystem-first: the edited file is the source of truth;
- local/offline;
- deliberately small in UI surface but strong in file safety.

Graphium v1 is not a knowledge base, academic editor, IDE, project manager or multi-document session host.

## 2. Technology freeze

G00 selects:

- implementation language: **Python 3**;
- desktop toolkit: **PyGObject + GTK 3**;
- editor widget baseline: **Gtk.TextView** inside Gtk.ScrolledWindow;
- typography/printing: Pango + PangoCairo where required;
- filesystem implementation baseline: Python standard library, with Gio allowed only behind an adapter when a desktop-native facility such as live file monitoring requires it;
- tests: Python `unittest` plus source/static boundary gates;
- data encoding inside the program: Unicode Python strings, with file encoding/BOM/EOL represented explicitly by the document-safety domain;
- no GtkSourceView dependency is required by v1.

Rationale: this maximizes reuse of the W116 safety/editor/print work, keeps deployment compatible with the Calamus technology family, and avoids adding a dependency merely to obtain features Graphium can already provide itself.

## 3. Layer boundary

Target package layout:

```text
graphium/
  domain/          # pure product/domain rules; no gi
  application/     # use cases, ports, controllers; no gi
  adapters/
    gtk/           # only location permitted to import gi/GTK directly
  infrastructure/  # pure filesystem/settings implementations where possible; no GTK
  composition.py   # GTK-free composition descriptor/root policy
```

The direct `gi` / GTK dependency boundary is **`graphium.adapters.gtk`**.

Rules:

1. `domain` must not import application, adapters, infrastructure or composition.
2. `application` may import domain but must not import adapters.
3. `infrastructure` must not own product state or document identity.
4. GTK adapters implement ports and translate toolkit events; they do not own business semantics.
5. Composition is explicit. No service locator, global application state bag or plugin registry.
6. Runtime Graphium source must not import Calamus modules. Reuse is one-time extraction with provenance, then Graphium evolves independently.

## 4. Authority model

Graphium v1 has exactly **one active document authority**.

The document session owns the accepted binding and saved-state identity. UI widgets are projections/adapters, not a second document model.

Graphium v1 has exactly **one physical writer authority** for normal persisted document writes. Save, Save As and copy/version operations must converge on the appropriate guarded writer contract rather than inventing parallel write paths.

A future live file monitor is observation-only. It may report changed/deleted/replaced states but may not become a second file identity, automatic reload authority or automatic overwrite authority.

## 5. XDG isolation

Graphium owns independent XDG locations:

```text
$XDG_CONFIG_HOME/graphium   (fallback ~/.config/graphium)
$XDG_DATA_HOME/graphium     (fallback ~/.local/share/graphium)
$XDG_CACHE_HOME/graphium    (fallback ~/.cache/graphium)
$XDG_STATE_HOME/graphium    (fallback ~/.local/state/graphium)
```

Graphium must never read or mutate Calamus configuration merely because source logic originated there.

The desktop application ID is **DEFERRED in G00** until repository/packaging identity is explicitly frozen. It must not be guessed.

## 6. W116 extraction policy

ADOPT selective extraction from the certified Calamus W116 commit `33331672f5ba8fcc6a7e1ede9ab849638579f0c7`, tree `db11fee424273c0a383145c132b645c15581b30a`.

High-value source families reserved for later work items:

- document identity / loader / serializer;
- document save / guarded writer;
- document session / savepoint state;
- Save a Copy / Save Version Copy;
- history / editor transaction;
- search model;
- selected navigation and text-transform primitives;
- line numbers, typography, view preferences;
- print runtime.

REJECT:

- copying `bin/calamus`;
- copying Calamus application composition wholesale;
- a shared `calamus-core` runtime library;
- conditional editions or feature flags inside Calamus;
- runtime imports from Graphium back into Calamus.

Each imported component must receive Graphium naming, Graphium tests and explicit provenance.

## 7. V1 functional boundary

MUST families:

- New / Open / Recent;
- Save / Save As / Save a Copy / Save Version Copy;
- Properties;
- Page Setup / Print Preview / Print;
- Undo / Redo and clipboard basics;
- Find / Replace / Find Next / Find Previous;
- Go to Line;
- Word Wrap / Line Numbers / Font / Zoom / Status Bar;
- selected basic text transformations;
- persistent essential preferences and System/Light/Dark appearance;
- explicit Saved/Modified state;
- encoding/BOM/EOL visibility;
- save-time and live external-file safety;
- User Guide / Keyboard Shortcuts / About.

SHOULD:

- drag-and-drop file open;
- window geometry restore;
- EOL/encoding conversion if bounded;
- offline spellcheck after core v1 if it remains low-risk.

OUT OF V1:

- tabs or multiple documents in one window;
- split editor;
- projects/workspaces and file-browser panels;
- Markdown preview or outline/navigator;
- Research, Bibliography, References, Source Notes;
- Scratchpad, Clips, Tags, backlinks or knowledge graph;
- rich text/WYSIWYG;
- plugin system, macros, terminal, Git, LSP, debugger;
- cloud, collaboration, embedded browser or AI;
- autosave/recovery until separately designed and audited.

## 8. Canonical-document policy

**MAXIMUM CANONICAL DOCUMENTS: 3.** This is a permanent Graphium project constraint.

The complete canonical set is:

1. `GRAPHIUM_PRODUCT_ARCHITECTURE_CONTRACT.md` — product, technology, architecture and frozen boundaries.
2. `GRAPHIUM_ROADMAP.md` — serial Gxx work-item routing and current status.
3. `GRAPHIUM_MEMORIA_OPERATIVA.txt` — append-only operational history, evidence summary and decisions.

No Gxx may create a fourth canonical document. A work item updates one or more of these three instead.

Test logs, SHA manifests, provenance maps, release receipts, generated inventories, desktop-run logs and the end-user User Guide are **non-canonical evidence/product material**. They may support a decision but cannot override these three authorities.

## 9. Method

- Gxx work items are serial.
- A later Gxx does not begin as implementation until the preceding item reaches its required closure state.
- Headless/domain logic is implemented and tested before GTK wiring where feasible.
- GTK adapters remain thin.
- A desktop attempt, when a work item reaches that stage, must test an isolated Graphium candidate, not Calamus and not an installed user configuration.
- Failures are classified before repair; harness/oracle failures are not silently converted into product failures.
- Git publication is a separate explicit operation on the user's machine; generated bootstrap artifacts here do not mutate a canonical repository.

## 10. G00 closure conditions

G00 may close without a desktop run because it implements no product feature and no GTK shell. It must instead prove:

- Graphium identity is independent from Calamus;
- XDG paths are independent;
- package boundaries exist;
- core source has no Calamus runtime imports;
- GTK import boundary is mechanically enforced;
- the canonical-document cap is mechanically enforced;
- the roadmap and MO identify G00 and the next work item.
