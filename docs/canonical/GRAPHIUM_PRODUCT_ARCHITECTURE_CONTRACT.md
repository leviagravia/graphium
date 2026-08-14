# Graphium — Product & Architecture Contract

Canonical document 1 of 3.
Initial freeze: 2026-08-13 — G00.
Status: **G00-G01 CLOSED / CERTIFIED / PUBLISHED; G02 OPEN / CONTRACT FROZEN / HEADLESS VALIDATED / FINALIZATION READY**.
Published G01 baseline: `bf7878c3cdc5cf895b0ffba86b854860c34936a4` / tree `2334e0c71f01a1b0a30bcb9298911c7c0cafe042`.

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

## 11. G01 — Document Identity / Load / Serialize Foundation

Freeze: 2026-08-14.

`G01_CONTRACT=FROZEN`
`G01_SCOPE=DOCUMENT_IDENTITY_LOAD_SERIALIZE_FOUNDATION`
`G01_GTK_REQUIRED=NO`
`G01_SECOND_DOCUMENT_AUTHORITY=FORBIDDEN`
`G01_PHYSICAL_WRITER_IMPLEMENTATION=DEFERRED_TO_G03`

### 11.1 Ownership and layer placement

G01 introduces no document session and no physical writer. It freezes only immutable
accepted-load values, stable local-file loading, and pure byte serialization policy.

- `graphium.domain.document_identity` owns immutable identity/load metadata values and typed load failures.
- `graphium.domain.document_serialization` owns pure representation profiles and byte serialization.
- `graphium.infrastructure.document_loader` owns local filesystem observation/read operations and returns domain values.
- no G01 module may import `gi`/GTK;
- G01 does not instantiate a second active-document authority.

The future G02 `DocumentSession` will own one accepted `DocumentFileState`. G01 merely defines the value that G02 may accept atomically. The future G03 guarded writer will be the one physical writer authority and will consume G01 serialization rather than creating a second codec/EOL model.

### 11.2 File visit contract

Graphium G01 visits **regular local files** only. The visit rule is extension-neutral: Graphium does not require `.txt`, `.md` or another filename suffix in order to recognize a document.

The stable loader:

1. preserves an absolute normalized logical path without replacing it by `realpath`;
2. opens bytes and requires a regular-file target;
3. observes descriptor identity before and after the read;
4. rejects torn/unstable reads after one retry by default;
5. preserves canonical path and `(device, inode)` separately from the logical path;
6. records exact accepted raw-byte SHA-256 as equivalence evidence, never as filesystem identity;
7. records size, mtime-ns, mode and read-only mode observation;
8. derives encoding/BOM/EOL metadata before newline normalization;
9. returns editor text LF-normalized;
10. rejects decoded NUL content as outside Graphium's plain-text scope.

FIFO/socket/device visiting and remote URI semantics are outside G01.

### 11.3 Codec policy

- BOM-aware UTF-8, UTF-16 LE/BE and UTF-32 LE/BE are supported.
- **no BOM means strict UTF-8**.
- no locale fallback and no heuristic legacy-encoding guessing are allowed.
- the BOM is removed from editor text and retained as metadata.
- invalid bytes fail with a typed encoding error.

A future explicit “Open with Encoding…” may add a user-selected decode path, but must not silently weaken the G01 default loader.

### 11.4 EOL and internal text policy

G01 records LF, CRLF and CR counts, dominant style, mixedness and final-newline state from decoded source text. Dominant style is the most frequent style; ties use first occurrence. A file with no separator records `LineEnding.NONE`.

Graphium's in-memory editor representation is **LF-normalized**. Serialization converts only at the byte boundary:

- an accepted source retains its encoding, BOM and dominant EOL profile;
- a source with no separator uses LF if later editing introduces newlines;
- a new unbound document defaults to UTF-8, no BOM, LF;
- mixed-EOL normalization requires explicit consent before serialization can proceed;
- serialization is strict and may not replace unrepresentable characters.

G01 serialization performs no filesystem mutation.

### 11.5 Hard anti-scope

G01 MUST NOT implement:

- G02 history, editor transaction, savepoint/dirty state or `DocumentSession`;
- G03 guarded/atomic Save or Save As;
- G04 GTK shell, Open chooser or buffer wiring;
- live external-file monitoring;
- Recent Files, copy/version commands, Properties UI;
- encoding heuristics, autosave, remote files, tabs or a document registry.

### 11.6 Provenance

G01 is a selective adaptation of the Calamus W116 published `calamus_document_identity.py`, `calamus_document_loader.py` and `calamus_document_serializer.py` semantics. Runtime imports from Calamus remain forbidden. Exact source hashes and adaptation decisions live in non-canonical G01 provenance evidence and are summarized in the MO.


## 12. Performance & Perceived Latency Budget

Freeze: 2026-08-14.

`PERFORMANCE_PERCEIVED_LATENCY_BUDGET=FROZEN`
`PERMANENT_COMPARATORS=Leafpad,L3afpad,Mousepad`
`PRIMARY_TARGET_SEGMENT=QUICK_EDIT_SIMPLE_TEXT_EDITOR_USERS`
`SAFETY_MAY_NOT_BE_DISABLED_FOR_BENCHMARKS=YES`

### 12.1 Product-positioning consequence

Web/user research reviewed in G01 confirms that the core Leafpad/L3afpad audience values immediate startup, a small UI, low cognitive load and basic text-file work; the quick-edit segment of Mousepad values the same qualities while tolerating a somewhat richer editor. Graphium therefore freezes the product principle:

**FAST + SIMPLE + SAFE + NATIVE GTK**

The differentiator is not feature count. Graphium must preserve Leafpad/L3afpad-like immediacy while adding stronger file safety, transparent encoding/EOL state, persistent essential preferences, mature print/preview/page setup, a compact useful status bar, and identity-preserving copy/version operations.

Syntax highlighting, tabs, IDE facilities and feature-platform behavior are not admitted merely to compete with Mousepad's richer use cases. Graphium targets Mousepad's quick-edit users, not its mini-code-editor segment.

### 12.2 Permanent comparator set

Performance claims and regression checks must be measured on the same T480 against installed versions of:

- Leafpad;
- L3afpad;
- Mousepad.

Each benchmark receipt records application version, package/source identity where available, Linux/GTK/Python versions, power mode, sample-file hashes and measurement method. Comparator versions may change over time; the currently installed versions are the reference for that measurement and must be recorded rather than assumed.

### 12.3 Mandatory workloads and metrics

At minimum, the benchmark harness must cover:

1. empty-window/process start to first editable state;
2. open a 5 KiB UTF-8/LF plain-text file to editable state;
3. open a 1 MiB UTF-8/LF plain-text file to editable state;
4. open a 10 MiB UTF-8/LF plain-text file to editable state;
5. idle resident memory after first editable state;
6. resident memory after the 1 MiB workload.

Primary metrics:

- median wall-clock time to first editable state;
- p90 time to first editable state;
- median open-to-editable latency;
- idle RSS MiB;
- RSS MiB after the 1 MiB open workload.

Normal benchmark series use at least 7 measured runs after one uncounted priming run. Session-first/cold observations are reported separately because filesystem/page-cache state cannot be made perfectly comparable without intrusive system-wide cache manipulation. Graphium benchmarking must not require root or mutate the user's real configuration.

### 12.4 G04 admission ceilings and G12 competitive targets

The first real GTK shell at G04 establishes the initial Graphium performance baseline. G04 may not close as a credible quick editor if, on the T480:

- warm empty time-to-editable exceeds both **2.0x Mousepad** and **750 ms median**; or
- warm 5 KiB open-to-editable exceeds both **2.0x Mousepad** and **900 ms median**; or
- idle RSS exceeds **200 MiB**.

These are admission ceilings, not aspirational targets. Missing one requires optimization or an explicit user-authorized contract rebaseline before feature expansion.

For G12 v1 closure, the target is stronger:

- warm empty and 5 KiB median latency: target <= **1.5x Mousepad**;
- 1 MiB and 10 MiB open median latency: target <= **1.75x Mousepad**;
- idle RSS: target <= **150 MiB** and <= **2.5x Mousepad** where both conditions are meaningful;
- Leafpad and L3afpad gaps are always reported even when they are not the hard gate, because they represent the most latency-sensitive target audience.

Graphium may not market itself or document itself as "fast" if the G12 competitive target is materially missed without an explicit documented rebaseline.

### 12.5 Permanent regression budget

After G04, every later desktop-capable published Gxx records the same core benchmark set. Relative to the immediately preceding published Graphium baseline:

- >10% median regression in empty or 5 KiB startup/open latency is a closure blocker until explained and accepted;
- >15% median regression in 1 MiB/10 MiB open latency is a closure blocker until explained and accepted;
- >15% idle-RSS growth is a closure blocker unless caused by an explicitly authorized, measurable v1 requirement.

Noise must be handled by rerunning the complete series, not by selecting favorable individual runs.

### 12.6 Startup discipline

Features not needed to make the first document editable must not be eagerly initialized on the startup critical path. In particular, Print/Preview/Page Setup, Help, optional spellcheck and other dormant subsystems should be lazy where technically reasonable. Recent-file maintenance or live-monitor setup must not delay the editor becoming usable unless required for correctness.

Performance optimizations may never weaken G01-G03 document safety, savepoint semantics, encoding/EOL correctness or guarded-write guarantees. Safety is a product invariant, not a benchmark toggle.


## 13. G02 — History / Editor Transaction / Savepoint Session

Freeze: 2026-08-14.

`G02_CONTRACT=FROZEN`
`G02_SCOPE=HISTORY_TRANSACTION_SAVEPOINT_SESSION`
`G02_GTK_REQUIRED=NO`
`G02_DIRTY_AUTHORITY=EDITOR_STATE_ID_RELATION`
`G02_PHYSICAL_WRITER=FORBIDDEN`
`G02_TARGET_USERS=Leafpad,L3afpad,Mousepad_quick_edit`

### 13.1 Target-user consequence

G02 serves Leafpad/L3afpad/Mousepad-style quick-edit users by making Undo/Redo and Saved/Modified behavior trustworthy **without adding visible workflow complexity**. History sophistication is an internal safety/maturity mechanism, not a reason to add timelines, persistent undo, history panels or session machinery to the UI.

The user-facing mental model remains simple:

- type -> Modified;
- save -> Saved;
- Undo/Redo may naturally return to the exact saved state;
- opening or creating a document does not create fake undo steps.

### 13.2 Stable editor-state identity

Every committed text state owned by `TextHistory` receives a positive monotonically increasing `state_id`. State identities are **never reused** during one history lifetime, including after pruning or after a new branch discards redo history.

Caret/selection-only refreshes preserve the current text-state identity. The current insertion position and selection-bound position remain part of the restorable history snapshot, including selection direction, but they do not make a clean text state dirty by themselves.

A new branch after Undo receives a fresh identity even when its text happens to equal text that existed on the discarded branch. Therefore text equality or content digest equality may never be used as the Saved/Modified authority.

### 13.3 Savepoint-aware DocumentSession

The one active `DocumentSession` owns:

- current LF-normalized text;
- at most one accepted G01 `DocumentFileState`;
- `current_editor_state_id`;
- `saved_editor_state_id`.

`modified` is derived only from the relation:

```text
current_editor_state_id == saved_editor_state_id != None  -> Saved
otherwise                                                   -> Modified
```

Pending native text that has not yet been committed to history has no stable current state ID and is therefore Modified. If a native edit nets back to the already committed current text before the group is committed, the existing stable identity may be reconciled immediately.

A **late save** completion may mark only the exact editor-state identity whose bytes were actually accepted by the future G03 writer. If the current editor has already advanced to a newer state, accepting the older saved identity must leave the document Modified.

External-file changed/deleted/replaced state is not the dirty-state authority and remains a separate concern for G11.

### 13.4 Transaction grouping and rollback

`EditorTransactionController` is GTK-free. It coordinates a buffer port, `TextHistory`, and `DocumentSession`.

Required semantics:

- one logical programmatic edit becomes at most one committed Undo step;
- nested programmatic transactions are rejected;
- failed programmatic actions restore visible buffer, history and session exactly;
- Undo/Redo restoration includes text, insertion offset and selection-bound offset;
- a failed Undo/Redo buffer restore must roll history/session/buffer back to the pre-operation checkpoint;
- New/Open replacement is not an ordinary edit and resets history rather than becoming Undoable document content;
- actual Gtk.TextBuffer `begin-user-action` / `end-user-action` signal wiring and native debounce timing are deferred to G04, where the GTK adapter must call this headless authority rather than duplicate it.

### 13.5 Bounded history / large-document policy

Graphium uses bounded full-text snapshots in G02 because they are simple, predictable and appropriate to the quick-edit target. Default policy:

- 100 history steps;
- 750,000 characters maximum per snapshot for Undo history;
- 2,500,000 characters approximate aggregate snapshot budget.

When a document exceeds the per-snapshot threshold, Graphium keeps a current stable state identity but disables multi-snapshot Undo for that document state instead of multiplying large copies in memory. Saving remains possible. G04/G12 performance evidence may tighten this policy but may not substitute a more complex engine without explicit architecture review.

### 13.6 G02/G03/G04 boundary

G02 performs **no physical write** and imports no GTK/Gio. `accept_saved_state()` is only a state-transition hook for G03: it may be called after G03 has successfully written and accepted the corresponding state.

G03 owns the guarded physical writer and Save/Save As orchestration.
G04 owns the Gtk.TextBuffer adapter, native user-action events, debounce/timing policy and visual Saved/Modified projection.

G02 must not pre-implement either layer.
