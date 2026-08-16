# Graphium — Product & Architecture Contract

Canonical document 1 of 3.
Initial freeze: 2026-08-13 — G00.
Status: **G00-G05 CLOSED / CERTIFIED / PUBLISHED; G06 OPEN / CONTRACT FROZEN / IMPLEMENTATION AUTHORIZED / DESKTOP CANDIDATE READY**.
Published G05 baseline: `a9083daf22ab23cf6cd20841be643510e35d700d` / tree `12d55249263e006cc68fa304f3c3cc2a9ef73acb`.

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
- For the current Gxx, the assistant performs source audit, falsification-oriented mature-source comparison, implementation, complete non-desktop tests, strict gates, source bundle and incremental MO update autonomously.
- Headless/domain logic is implemented and tested before GTK wiring where feasible; GTK adapters remain thin.
- The user is asked only for the final desktop validation after the candidate has passed the preceding automated gates. That validation uses an isolated Graphium copy, never Calamus or the installed user configuration.
- Graphium does not progress by numbered trial-and-error candidate attempts. A pre-product harness/oracle stop or product defect is localized and re-audited against relevant mature sources; the whole discovered failure/design class is repaired and fully revalidated before another final desktop validation is requested.
- Failures are classified before repair; harness/oracle failures are not silently converted into product failures.
- Git publication is a separate explicit operation on the user's machine. Only the user executes Git-mutating stage/commit/push commands on the T480.

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

Rebaseline: 2026-08-14 — G04 deep mature-source audit.

`PERFORMANCE_PERCEIVED_LATENCY_BUDGET=FROZEN`
`PERMANENT_COMPARATORS=Leafpad,L3afpad,Mousepad,FeatherPad`
`PRIMARY_TARGET_SEGMENT=QUICK_EDIT_SIMPLE_TEXT_EDITOR_USERS`
`SAFETY_MAY_NOT_BE_DISABLED_FOR_BENCHMARKS=YES`
`PERFORMANCE_HETEROGENEOUS_ORACLE_RATIOS=FORBIDDEN`
`PRODUCT_CATEGORY=LIGHTWEIGHT_TRUST_EDITOR`
`FEATURE_COUNT_IS_NOT_THE_COMPETITIVE_AXIS=YES`
`NORMAL_SAVE_IS_CONTENT_NEUTRAL=YES`
`FILE_MONITOR_IS_OBSERVATION_TRIGGER_NOT_TRUTH_AUTHORITY=YES`
`V1_TABS_SYNTAX_IDE_PLUGIN_PLATFORM=FORBIDDEN`
`SAFETY_AND_PERFORMANCE_MAY_NOT_WEAKEN_EACH_OTHER=YES`

### 12.1 Positioning

Graphium freezes **FAST + SIMPLE + SAFE + NATIVE GTK** and the product category **LIGHTWEIGHT TRUST EDITOR**. Leafpad/L3afpad are the immediacy/low-cognitive-load references; Mousepad is the primary operational-maturity comparator; FeatherPad is the permanent speed-plus-maturity comparator proving that greater feature density does not excuse poor launch latency. Graphium targets the quick-edit subset of Mousepad/FeatherPad users rather than their tab/session/syntax/column-editing power-user segment.

### 12.2 Comparator set and falsifiable receipts

Every desktop-capable checkpoint records the actually installed Leafpad, L3afpad, Mousepad and FeatherPad versions on the T480, together with Graphium version/tree, sample hashes, run count, metric definition and environment isolation. Missing comparators block the comparative receipt; they do not become a product failure.

### 12.3 Two metrics that must not be conflated

**FIRST_VISIBLE** is the common cross-product metric: process start -> first new X11 top-level mapped for the exact spawned process. The same external X11 oracle is used for Graphium, Leafpad, L3afpad, Mousepad and FeatherPad. Ratios may be calculated only within this common metric.

Comparator process-isolation is part of the oracle contract, not an implementation detail: Mousepad is launched with its no-server mode when supported, and FeatherPad is launched with `--standalone` because FeatherPad is single-instance by default. A comparator build that cannot provide the required isolated-process mode BLOCKS the comparative receipt; the oracle must not be weakened to accept a window owned by a different pre-existing PID.

**FIRST_EDITABLE** is the exact Graphium-internal metric: process start -> requested file Open (if any) completed -> window mapped -> Gtk.TextView focused -> one complete READY record emitted. G04 transports this record through an inherited pipe, not a filesystem ready flag. It is exact Graphium regression/admission evidence but is **not** numerically compared with comparator FIRST_VISIBLE values.

Direct source audit established why this distinction is mandatory: Leafpad and L3afpad show their window before completing command-line file Open, while Airpad follows a different ordering. Therefore `first mapped window` cannot be silently relabelled `first editable`.

G12 may make hard cross-product FIRST_EDITABLE claims only after a single common external oracle is implemented for all compared applications, e.g. an AT-SPI/XTest-style disposable first-input acceptance probe.

### 12.4 Workloads and statistics

Both applicable G04 metrics cover empty, 5 KiB, 1 MiB and 10 MiB UTF-8/LF files. Normal series use one uncounted priming run plus at least seven measured runs. Report median and p90; Graphium exact measurements also record RSS. Real user configuration must not be read/mutated for benchmarking.

### 12.5 G04 admission

Graphium exact FIRST_EDITABLE must satisfy:

- empty median <= 750 ms;
- 5 KiB median <= 900 ms;
- idle RSS <= 200 MiB.

The common FIRST_VISIBLE receipt also applies the existing quick-edit admission comparison against Mousepad:

- Graphium empty FIRST_VISIBLE <= 2.0x Mousepad or <= 750 ms;
- Graphium 5 KiB FIRST_VISIBLE <= 2.0x Mousepad or <= 900 ms;
- Graphium idle RSS <= 200 MiB.

Leafpad and L3afpad gaps are always reported. These thresholds are admission ceilings, not marketing claims.

### 12.6 Permanent regression budget

After G04, relative to the immediately preceding published Graphium desktop baseline, >10% median regression in empty/5 KiB, >15% in 1/10 MiB, or >15% idle-RSS growth blocks closure until explained and explicitly accepted. Noise is handled by rerunning complete series, never by cherry-picking.

### 12.7 Startup discipline

Subsystems not needed for the first editable document remain off the critical path where reasonable. Help content, Print/Preview/Page Setup, optional spellcheck and later nonessential services are lazy. Performance optimizations may never weaken G01-G03 safety, encoding/EOL neutrality, exact savepoint semantics or guarded writes.


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


## 14. G03 — Guarded Save / Save As

Freeze: 2026-08-14.

`G03_CONTRACT=FROZEN`
`G03_SCOPE=GUARDED_SAVE_SAVE_AS`
`G03_GTK_REQUIRED=NO`
`G03_SINGLE_PHYSICAL_WRITER=GuardedFileWriter`
`G03_DIRECT_WRITE_FALLBACK=FORBIDDEN`
`G03_HARDLINK_POLICY=FAIL_CLOSED`
`G03_SAVE_AS_REBIND_BEFORE_COMMIT=FORBIDDEN`
`G03_TARGET_USERS=Leafpad,L3afpad,Mousepad_quick_edit`

### 14.1 Target-user consequence

Graphium's quick-edit user must experience Save as an ordinary, immediate editor operation. The complexity below is **invisible safety**, not a new workflow. G03 adds no dialogs, monitor, conflict panel, backup manager or history UI. The future G04 chooser remains responsible for path selection and human overwrite consent; G03 owns only transactional persistence safety.

### 14.2 One physical writer authority

`graphium.infrastructure.guarded_file_writer.GuardedFileWriter` is the only Graphium v1 authority permitted to perform authoritative document namespace mutation. There is no direct/truncate fallback and no second atomic writer.

The guarded lane is:

1. capture one stable G02 editor state;
2. derive strict G01 serialization before filesystem mutation;
3. observe the exact target and topology;
4. create an exclusive unpredictable sibling stage in the target directory;
5. write all bytes and apply required metadata;
6. `fsync` the staged inode; sync failure is fatal before commit;
7. revalidate logical path, parent identity and target immediately before commit;
8. commit through the topology-appropriate namespace operation;
9. `fsync` the parent directory;
10. reload through the G01 stable loader and verify the committed fingerprint;
11. advance only the exact captured G02 editor-state identity.

Graphium does **not** claim a mathematically linearizable filesystem CAS against arbitrary non-cooperating writers. Existing-target replacement remains a guarded late-check followed by atomic namespace replacement.

### 14.3 Ordinary Save guard

Ordinary Save requires:

- a named active `DocumentSession`;
- the accepted G01 `DocumentFileState` installed by Open or a previous confirmed save;
- the exact current stable G02 editor-state ID.

Writer observation checks the accepted target against fresh physical evidence, including object identity where present, size, mtime/ctime, mode, owner/group, link count and SHA-256 content fingerprint. Same-size + same-mtime but different bytes must fail closed.

If the accepted baseline is absent, the target disappeared, identity/topology changed, or required metadata cannot enter the safe lane, ordinary Save fails before authoritative target mutation. It does not silently reacquire a new baseline and overwrite.

### 14.4 Serialization boundary

G01 remains the representation authority:

- accepted encoding is preserved;
- BOM policy is preserved;
- homogeneous EOL is preserved;
- mixed EOL requires explicit normalization consent from the future G04 user-facing boundary;
- new/unbound document default for Save As is UTF-8, no BOM, LF;
- encoding is strict and replacement-character fallback is forbidden;
- decoded/serialized NUL content remains outside Graphium's plain-text scope.

Serialization must complete before stage/target mutation.

### 14.5 Symlink and hardlink policy

For an active document opened through a stable symlink:

- the logical path remains the document binding;
- the physical/canonical regular-file target receives the atomic commit;
- the logical symlink itself is preserved;
- logical parent and symlink relation are late-revalidated before commit.

A dangling/cyclic/retargeted symlink fails closed.

An existing target with `st_nlink != 1` is outside the G03 guarded replacement lane and fails closed. Graphium does not silently break a hardlink group and does not fall back to in-place truncate/write.

### 14.6 Failure-atomic staging

Existing authoritative bytes remain untouched on every pre-commit failure, including:

- strict encoding failure;
- stage creation collision/substitution;
- short/injected write failure;
- stage `fsync` failure;
- metadata/xattr preservation failure;
- parent replacement/retarget;
- target mutation/deletion/replacement during staging;
- late stale-target mismatch.

Stage files are best-effort cleaned after failure.

### 14.7 Save As transaction

G03 does not create a GTK chooser. Future G04 owns destination selection and human overwrite consent.

After the destination is accepted, G04 supplies an immutable `SaveTargetObservation` to `DocumentSaveService.save_as()`.

Required identity semantics:

- target choice alone does not rebind `DocumentSession`;
- pre-commit failure leaves the previous logical binding and savepoint relation unchanged;
- Save As to the currently active physical object routes ordinary guarded Save semantics;
- an absent target uses a no-overwrite namespace commit (`link`-style lane) so an attacker/process creating the final name before commit is not overwritten;
- an existing accepted overwrite target is late-revalidated before atomic replacement;
- only after namespace commit does the session bind the new logical path and mark the captured editor-state ID saved.

### 14.8 Post-commit truthfulness

Once the namespace commit happened, Graphium must not throw a normal retry-shaped "nothing was saved" error.

Outcomes distinguish at least:

- `COMMITTED_CONFIRMED`;
- `COMMITTED_DURABILITY_UNCERTAIN` when parent-directory durability could not be confirmed;
- `COMMITTED_BASELINE_UNAVAILABLE` when a fresh stable post-save baseline cannot be reacquired/verified.

A post-commit baseline-unavailable result retains the logical document path but clears accepted `file_state`. The next ordinary Save therefore fails closed until a baseline is deliberately re-established by a later lifecycle boundary. No blind automatic second write is permitted.

### 14.9 G02 integration

The save transaction persists the captured stable editor state, not "whatever text exists when I/O finishes".

After a committed result, `DocumentSession.accept_committed_save()` marks exactly the captured `editor_state_id` saved. If editing advanced while I/O was in progress, the newer current state remains Modified.

Pre-commit failure never advances the savepoint.

### 14.10 G03/G04/G11 boundary

G03 remains GTK-free and adds no:

- `GtkFileChooser`;
- permanent `Gio.FileMonitor`;
- auto-reload;
- merge/diff conflict UI;
- deleted/renamed background state machine;
- Recent Files side effects;
- backup/local-history subsystem.

G04 owns chooser/consent and visible Save/Save As wiring. G11 owns observation-only live external-file monitoring. Both must call the existing G03/G02 authorities rather than create new file/session authorities.



## 15. G04 — Native Edit Integration Hardening / Thin GTK Shell / Core File Lifecycle

Rebuild freeze: 2026-08-14, after deep mature-source falsification audit.

`G04_CONTRACT=FROZEN`
`G04_NATIVE_HISTORY=DELTA_BASED`
`G04_NATIVE_EDIT_TIMER_AUTHORITY=FORBIDDEN`
`G04_FULL_BUFFER_CAPTURE_PER_NATIVE_EDIT=FORBIDDEN`
`G04_APPLICATION_TOPOLOGY=ONE_PROCESS_ONE_WINDOW_ONE_DOCUMENT`
`G04_APPLICATION_UNIQUENESS=NON_UNIQUE`
`G04_MULTI_FILE_CLI=ONE_PROCESS_PER_FILE`
`G04_GTK_EDITOR_WIDGET=Gtk.TextView`
`G04_GTK_SOURCEVIEW=FORBIDDEN`
`G04_TOOLBAR=ABSENT`
`G04_HELP=LAZY_OFFLINE`
`G04_PERFORMANCE_COMMON_METRIC=FIRST_VISIBLE`
`G04_PERFORMANCE_EXACT_INTERNAL_METRIC=FIRST_EDITABLE`
`G04_PERFORMANCE_READY_PROTOCOL=INHERITED_PIPE_ATOMIC_RECORD`
`G04_HETEROGENEOUS_READINESS_RATIO=FORBIDDEN`
`G04_TARGET_USERS=Leafpad,L3afpad,Mousepad_quick_edit,FeatherPad_quick_edit`
`G04_INTERACTIVE_LINE_BUDGET_CHARS=20000`
`G04_PATHOLOGICAL_LINE_POLICY=REFUSE_BEFORE_GTK_BUFFER_INSTALL`
`G04_PATHOLOGICAL_LINE_CONTENT_MUTATION=FORBIDDEN`

### 15.1 Explicit architecture review of the published G02 snapshot engine

G02 remains published historical authority for **editor-state identity and savepoint semantics**:

- positive monotonically increasing state IDs;
- state IDs never reused after Undo branching, pruning or rollback;
- Saved/Modified derived from current-state ID versus saved-state ID;
- late Save may mark only the exact persisted state saved;
- text equality alone is never the dirty-state oracle.

G04 is the explicit architecture review contemplated by G02 section 13.5. Direct source comparison against Leafpad, L3afpad, Airpad, Mousepad/GtkSourceView clients, gedit, GNOME Text Editor, NEdit and JOE showed that the active native editor should not retain a complete document snapshot per ordinary edit. Therefore:

- `TextHistory` remains available as published G02 headless/regression code;
- the active G04 GTK runtime composes `DeltaHistory` instead;
- the active native editor stores insertion/deletion payload plus offsets/view state, not the entire base document;
- document size itself is not a switch that disables ordinary Undo;
- a 1 MiB document with a one-character edit must retain normal Undo and store approximately that changed payload rather than another 1 MiB document copy.

This supersedes only G02's **active-runtime storage choice** and old 750,000-character native-Undo degradation assumption. It does not rewrite G02 history or invalidate its published tests/commit.

### 15.2 Native user-action and grouping authority

Wall-clock inactivity is not semantic evidence that an editing operation ended. The withdrawn pre-rebuild G04 design's fixed native-commit delay is forbidden.

The active GTK adapter records deltas from real `GtkTextBuffer` insertion/deletion signals and uses `begin-user-action` / `end-user-action` as the primary compound-action boundary. Across adjacent completed user actions, bounded structural coalescing may combine compatible contiguous single-character insertion/deletion runs. Whitespace class, operation kind/direction, non-contiguity, multi-character compound operations and the exact saved state are merge barriers.

Required consequences:

- Undo behavior does not change merely because the user typed faster/slower than a timeout;
- Save is a semantic merge barrier so Undo can land exactly on the saved state;
- programmatic edits outside a GTK user-action may create one explicit fallback group, but never by waiting for elapsed time;
- Undo/Redo replay is suppressed from re-recording itself;
- replay verifies expected deleted text and fails rather than silently applying a delta to an unexpected buffer state.

### 15.3 DocumentSession/live-buffer split

The mutable Gtk.TextBuffer is the live text surface but not a second savepoint authority. G04 allows `DocumentSession.current_editor_state_id` to advance without copying the full live text into the session on every native edit.

`DocumentSession.text_editor_state_id` records which editor-state identity the session's synchronized text represents. After an ordinary native edit, `text_is_current` may be false while Saved/Modified remains exact from state IDs.

Immediately before physical Save/Save As, `NativeEditorController.prepare_for_save()` must:

1. require no active native edit group;
2. verify delta-history current ID equals DocumentSession current ID;
3. capture the full GtkTextBuffer once;
4. synchronize that text to the exact current editor-state ID;
5. then call the existing G03 save service.

Merely asking whether New/Open/Quit should discard a Modified document must not capture/copy the whole buffer.

### 15.4 Process/window/document topology

Graphium v1 remains single-document. For the target quick-edit workflow, G04 freezes the stronger process topology:

**one invocation/process -> one Gtk.ApplicationWindow -> one active document.**

`Gtk.Application` uses `G_APPLICATION_NON_UNIQUE`. A second Graphium invocation must create its own process/window and must not forward an Open request into a pre-existing Graphium process. If one invocation receives several filenames, the first belongs to that process and remaining files are fanned out to separate Graphium processes, following the useful Airpad pattern.

File -> Open within one window may deliberately replace that window's current document after the normal Save/Discard/Cancel lifecycle. This is different from another OS/file-manager invocation hijacking an unrelated open document.

### 15.5 Thin visible shell

G04 exposes only the first credible classic quick-edit surface:

File:
- New
- Open…
- Save
- Save As…
- Quit

Edit:
- Undo
- Redo
- Cut
- Copy
- Paste
- Delete
- Select All

Help:
- User Guide
- Keyboard Shortcuts
- About

Help text is offline product material loaded only when requested. G04 has no toolbar. The optional toolbar question remains routed to G06 after direct source/target-user audit. GtkSourceView, tabs, syntax, sidebars and project/session UI remain outside G04.

### 15.6 File lifecycle and content neutrality

G04 may perform chooser/consent/UI orchestration but may not bypass G01-G03 authorities.

- Open loads/validates before replacing the current document.
- failed Open leaves current buffer/session/history intact.
- New/Open/Quit consult `DocumentSession.modified` and offer Save/Discard/Cancel.
- Save/Save As physically write only through `DocumentSaveService` -> `GuardedFileWriter`.
- Save As rebind remains commit-after-only.
- mixed EOL normalization requires explicit consent.
- no implicit trailing-space cleanup, final-newline insertion, encoding conversion, BOM conversion or line-ending normalization is permitted merely because Open/Save occurred.

### 15.7 Performance protocol

The old filesystem ready-file protocol is rejected because file existence was observable before a complete readiness record was guaranteed. G04 exact FIRST_EDITABLE uses an inherited pipe. The child emits one short newline-terminated `READY <pid> <monotonic_ns>` record with one `os.write()` after requested Open completion, window map and editor focus. The parent waits for a complete newline record and verifies the emitting PID.

Cross-product comparison uses the common external FIRST_VISIBLE oracle defined in section 12. FIRST_VISIBLE and FIRST_EDITABLE receipts are intentionally separate. A report must never infer that a competitor is editable merely because its window became visible.

### 15.8 Mature-source audit discipline / confirmation-bias countermeasure

For every Graphium design decision evaluated against mature software, evidence must state:

1. the Graphium assumption under test;
2. a mature source that contradicts or stresses that assumption;
3. the materially different model used by that source and why it works;
4. the Graphium decision that would change if the alternative evidence is stronger;
5. final ADOPT / ADAPT / REJECT / DEFER classification.

An audit that records only corroborating examples is incomplete. A pre-product harness/oracle stop triggers failure localization and re-audit of the whole failure class before another desktop candidate is issued; Graphium does not progress by numbered trial-and-error attempts.

### 15.9 Pathological logical-line / renderer-safety policy

The valid T480 manual product FAIL on the seven-editor candidate demonstrated that "1 MiB file" and "1 MiB single logical line" are not equivalent workloads. The failed fixture was one line of 1,048,576 characters. Delta Undo remained available, but navigating/rendering the line end could make the GtkTextView window unresponsive. Mature-source re-audit showed that long-line display is a distinct renderer problem: FeatherPad applies an explicit logical-line guard, NEdit bounds custom display work, and GNOME's own GtkTextView issue history documents severe long-line behavior.

G04 therefore freezes a **20,000 Unicode-character per logical line interactive-rendering budget** for the GtkTextView editor surface. This is a conservative Graphium product budget for the chosen renderer, not a claim that GTK has a universal 20,000-character hard limit. It may be changed only by later explicit renderer qualification.

Required semantics:

- G01 may still load/decode such input as valid plain text; renderability is a G04 interactive-surface concern.
- before `NativeEditorController.initialize_open()` installs loaded text into GtkTextBuffer, G04 scans logical-line width without splitting/rewriting the document; any line above the budget causes a typed refusal.
- failed renderability admission leaves current buffer, session, history and logical path unchanged.
- Graphium never truncates the line, inserts a marker, inserts line breaks, normalizes content or silently changes wrap mode to make the file fit.
- no read-only GtkTextView fallback is offered for the same pathological line, because the failure class is rendering/navigation itself; a future exact paged/streamed viewer is separate architecture.
- native insertion/paste is preflighted before GtkTextBuffer's default insertion handler; a deletion that would join line fragments above the budget is likewise stopped before default mutation.
- blocked edits do not advance editor-state identity or Undo history and surface an explicit warning.
- automated large-file qualification uses a realistic multiline 1 MiB document and actually moves/scrolls the cursor to the end before edit/Undo. Huge-line refusal is a separate automated guard test.

This policy preserves both sides of the product identity: **large ordinary text remains editable; pathological renderer input is refused without altering user bytes**.

### 15.10 Desktop closure gates

Before asking the user for final G04 desktop validation, the candidate must pass:

- all G00-G03 regressions;
- G04 delta-history/native-editor/lifecycle/performance-protocol tests;
- architecture/source strict gates;
- arbitrary-cwd bootstrap probes;
- True-GTK shell/Open/Save/savepoint/delta-history/realistic-multiline-1-MiB Undo gate;
- True-GTK pathological-line Open/paste refusal gate before GtkTextBuffer mutation;
- `NON_UNIQUE` one-process/one-window/one-document topology gate;
- active Linux Mint/Cinnamon shortcut collision audit;
- exact Graphium FIRST_EDITABLE admission receipt;
- common FIRST_VISIBLE Graphium/Leafpad/L3afpad/Mousepad/FeatherPad receipt, or a comparator-missing BLOCKED result rather than a false product FAIL.

Only after these automated desktop gates pass is human visual/lifecycle validation requested.


## 16. G05 — Search / Replace / Go to Line Trust Contract

Freeze: 2026-08-14, after audit of published G04 source plus L3afpad, FeatherPad, GTK 3 and GtkSourceView search models.

`G05_CONTRACT=FROZEN`
`G05_SEARCH_SCOPE=LITERAL_CURRENT_DOCUMENT_ONLY`
`G05_SEARCH_QUERY=SINGLE_LINE_NONEMPTY_UNICODE`
`G05_REPLACEMENT=SINGLE_LINE_UNICODE_MAY_BE_EMPTY`
`G05_MATCH_CASE=ADOPT`
`G05_WHOLE_WORD=DEFER`
`G05_REGEX=REJECT_V1`
`G05_FUZZY=REJECT_V1`
`G05_MULTI_FILE_SEARCH=REJECT_V1`
`G05_SEARCH_HISTORY=DEFER`
`G05_HIGHLIGHT_ALL=REJECT`
`G05_BACKGROUND_SEARCH=REJECT`
`G05_WRAP=AUTOMATIC_ONE_WRAP`
`G05_CURRENT_MATCH=NATIVE_SELECTION`
`G05_REPLACE_ALL_MATCH_SET=FROZEN_FROM_ORIGINAL_SOURCE`
`G05_REPLACE_ALL_UNDO_GROUPS=1`
`G05_REPLACE_ALL_RENDERABILITY=PREFLIGHT_FINAL_TEXT`
`G05_PROGRAMMATIC_REPLACE=DELTA_EXPECTED_DELETE_INVERSE_ROLLBACK`
`G05_GENERIC_RENDER_GUARD_BYPASS=FORBIDDEN`
`G05_LEGACY_FULL_SNAPSHOT_TRANSACTION=FORBIDDEN`
`G05_REPLACE_UNDO_PAYLOAD_MAX=DELTA_HISTORY_MAX_PAYLOAD`
`G05_CASEFOLD_WORKING_SET=LOGICAL_LINE_BOUNDED`
`G05_REPLACE_ALL_MATCH_CAP=50000`

### 16.1 Search authority and navigation

G05 adds a GTK-free current-document literal-search authority. Search text is Unicode `str`; offsets are editor character offsets and must map exactly back to the original buffer. Case-sensitive search is exact codepoint literal comparison. Case-insensitive search uses Unicode casefold semantics with explicit transformed-boundary-to-original-offset mapping so length-changing folds cannot produce partial-source-character matches. Because G05 queries are single-line and G04 already bounds interactive logical-line length, casefold working memory is line-bounded: Graphium folds/maps one logical line at a time instead of casefolding/caching the complete multi-megabyte document or allocating per-character document-wide offset tables.

Find Next starts after the current selection when a selection is active, otherwise at the insertion point. Find Previous starts before the current selection/insertion point. Each command may wrap exactly once. Search navigation changes only view/selection state: it does not allocate a DeltaHistory state ID, touch the savepoint, mark Modified or create Undo data.

The last accepted non-empty query and Match Case option are application command state so F3/Shift+F3 work after the search surface is hidden. No search history database or cross-document persistence is introduced.

### 16.2 Lightweight visible search surface

The top-level Search menu owns:
- Find… (`Ctrl+F`)
- Find Next (`F3`)
- Find Previous (`Shift+F3`)
- Replace… (`Ctrl+H`)
- Go to Line… (`Ctrl+G`)

Find/Replace use one lazily shown in-window `Gtk.SearchBar`. Find mode exposes one single-line query entry plus Match Case and navigation. Replace mode adds one single-line replacement entry and Replace / Replace All commands. Editing the fields alone does not scan/highlight the whole document. Escape closes the bar and returns focus to the editor. The current occurrence is represented by the native text selection, not a separate highlight-all subsystem.

Opening Find/Replace may prefill a non-empty single-line editor selection. A multiline selection is never copied into the one-line query field merely because it is selected.

### 16.3 Replace One

Replace One is a single activation, not an exact-selection availability trap:
1. if the current selection is the exact active match under the current query/options, use it;
2. otherwise acquire the next match using normal Find Next semantics;
3. replace exactly that source range;
4. if another match exists after the resulting caret, select it for the next activation.

The text mutation is one DeltaHistory group/state-ID advance and therefore one Undo step. If no match exists, nothing is mutated and no editor-state identity is allocated.

### 16.4 Replace All atomicity and non-cascading semantics

Replace All snapshots the current buffer text and current editor-state identity on explicit activation, determines all non-overlapping matches against that original source, and derives the complete final text before GTK mutation. Inserted replacement text is never searched again during the same activation.

Before mutation, the final text must pass the published G04 interactive renderability authority. G05 query/replacement fields are single-line, so a replacement cannot introduce/remove a logical-line boundary. The programmatic transaction may suppress ordinary GTK signal recording only after this full final-state preflight; it must not expose a generic or caller-controlled renderer-safety bypass.

Changed source ranges are applied in descending original offset order. Each deletion verifies the exact expected original text before mutation. The buffer adapter owns inverse rollback if any operation fails. NativeEditorController also checkpoints DeltaHistory and DocumentSession; history/session advance only after successful buffer application. If post-buffer authority commit fails, the exact inverse operation sequence restores the prior buffer before authority rollback. No full-document snapshot is stored in Undo history.

All changed ranges belong to one DeltaHistory group and produce exactly one new editor-state ID. Undo restores the exact original text/view and saved-state relation; Redo restores the replacement result. Zero effective changes produce no Undo group and no state-ID advance.

Before mutation, the total changed Undo payload for a programmatic replacement must fit `DeltaHistory.max_payload_chars`. A replacement exceeding that bound is refused explicitly before GTK mutation; Graphium does not silently make a successful Replace All non-undoable and does not allow one oversized group to defeat the published changed-payload memory bound. Independently, Replace All may freeze at most 50,000 source matches in one activation. The 50,001st match fails closed before final-text/replay-plan materialization. This is an explicit command-scale bound against Python object amplification, not a document-size limit and not a limit on Find Next/Previous, which never materialize the complete match set.

A replacement plan is tied to the exact source editor-state ID. A stale plan must be rejected rather than applied to a newer editor state.

### 16.5 Go to Line

Go to Line is 1-based, bounded to the current document line count, and only changes cursor/selection/view state. It does not alter document text, history or Saved/Modified state. No bookmark stack/navigation history is created in G05.

### 16.6 Lightweight Budget

G05 performs no startup search scan, idle scan, background worker, persistent index, full-document casefold cache or eager highlight-all computation. Whole Word, canonical-equivalence expansion, regex, fuzzy search and search history remain outside the frozen G05 MUST scope. Explicit command-time text capture is permitted and must be measured on realistic multiline 1 MiB and 10 MiB fixtures; if evidence shows unacceptable responsiveness, architecture must be re-audited rather than silently adding a background subsystem.

G05 cannot close without `LIGHTWEIGHT_BUDGET_GATE=PASS`.


## 17. G06 — View Menu Core / Compact Status / Lightweight Presentation

Freeze: 2026-08-15, after audit of published G05 source, target-user/mature-source comparison and the T480 NON-CANDIDATE native `Gtk.TextView` line-number probe.

`G06_CONTRACT=FROZEN`
`G06_IMPLEMENTATION_AUTHORIZED=YES`
`G06_VIEW_MENU=STATUS_BAR,LINE_NUMBERS,WORD_WRAP,FONT,ZOOM_IN,ZOOM_OUT,ZOOM_RESET,FULL_SCREEN`
`G06_APPEARANCE=DEFER_G10`
`G06_TOOLBAR=REJECT_V1`
`G06_WORD_WRAP=GTK_WORD_CHAR`
`G06_LINE_NUMBERS=GTK_TEXTVIEW_LEFT_BORDER_WINDOW`
`G06_LINE_NUMBER_DRAW_SCOPE=VISIBLE_LOGICAL_LINES_ONLY`
`G06_WRAPPED_CONTINUATION_NUMBERS=NO`
`G06_GTKSOURCEVIEW=FORBIDDEN`
`G06_LINE_NUMBER_BACKGROUND_INDEX=FORBIDDEN`
`G06_STATUS_FIELDS=LINE_COLUMN,ENCODING_EOL,SAVED_MODIFIED`
`G06_LIVE_WORD_CHAR_COUNT=DEFER_G07_STATISTICS`
`G06_FONT=PERSISTENT_FAMILY_SIZE_VIA_CSS_PROVIDER`
`G06_ZOOM=TRANSIENT_RELATIVE_TO_BASE_FONT`
`G06_ZOOM_RESET=100_PERCENT`
`G06_FULL_SCREEN=TRANSIENT`
`G06_PERSISTENT_DIRECT_VIEW_SETTINGS=WORD_WRAP,LINE_NUMBERS,STATUS_BAR,FONT`
`G06_SETTINGS_STORAGE=XDG_SMALL_ATOMIC_JSON`
`G06_SETTINGS_BACKGROUND_WRITE=FORBIDDEN`
`G06_LIGHTWEIGHT_BUDGET_GATE=REQUIRED`
`G06_STARTUP_REGRESSION_BASELINE=G04_CERTIFIED_T480`
`G06_STARTUP_TIME_REGRESSION_LIMIT=MAX_25_PERCENT_OR_75_MS`
`G06_STARTUP_RSS_REGRESSION_LIMIT=MAX_25_PERCENT_OR_20_MIB`
`G06_FIRST_EDITABLE_CROSS_PRODUCT_CLAIM=DEFER_G12_COMMON_EXTERNAL_ORACLE`

### 17.1 Single-surface View authority

G06 adds one top-level View menu. Status Bar, Line Numbers and Word Wrap are stateful direct commands whose current state is visible in the menu and persisted from that command surface. Font owns the persistent base family+size. These settings must not later be duplicated in Preferences merely to create a second route. Appearance remains reserved for G10. Toolbar is rejected for v1 rather than hidden behind a preference.

### 17.2 Native line-number gutter

Graphium remains a plain `Gtk.TextView` editor. Line numbers use the widget's native LEFT border window. Gutter width depends on the decimal digit width of the logical line count. Drawing begins from the logical line intersecting the current visible rectangle and advances only through logical lines intersecting that viewport. Wrapped display-line continuations receive no additional number. The gutter must never scan the document, maintain a background line index, create a second scrollable widget, mutate the buffer, allocate history state or require GtkSourceView.

The qualifying T480 NON-CANDIDATE probe on GTK 3.24.41 passed 1 MiB wrap-off, 1 MiB wrap-on and 10 MiB wrap-off. Maximum observed logical lines visited per draw was 40; buffer mutations were zero; manual alignment/scroll/wrap/resize/toggle checks passed. This validates the architecture, not a product candidate.

### 17.3 Compact status and representation projection

The status surface is deliberately cheap and event-driven. Cursor line/column comes from the current `GtkTextIter`; Saved/Modified comes from the published state-ID relation; encoding and EOL come from the accepted document representation metadata. Status refresh must not call whole-document text capture, word counting, character counting or background analytics. New documents project UTF-8/LF. Mixed EOL is shown as observed representation rather than silently normalized.

### 17.4 Font and Zoom separation

Font stores only base family+size. GTK presentation uses a view-local CSS provider; deprecated `Gtk.Widget.override_font` is forbidden. Zoom is a transient multiplier over that configured base font, bounded to a small product range and reset to 100%. Zoom does not change the persistent base font, document text, history, savepoint or representation.

### 17.5 Persistent settings boundary

Persistent direct View settings are a small GTK-free value object backed by one product-local XDG JSON file. Load is read-only and fail-soft. The file is created or replaced only after an explicit setting change, using same-directory temporary staging plus atomic replace. There is no watcher, background writer, settings database, synchronization service or session semantics. A persistence failure must not publish a new in-memory setting as though it were durable.

### 17.6 Lightweight Budget and closure

G06 rejects Toolbar v1 because it duplicates a small conventional menu/shortcut command set without sufficient quick-edit value. Live word/character counts remain deferred to on-demand Statistics. G06 must preserve the G04/G05 startup and comparator gates, measure integrated View responsiveness, and close only with `LIGHTWEIGHT_BUDGET_GATE=PASS`.


### 17.4 G06 automated GTK ownership contract

The retired G06 integrated NON-CANDIDATE checkpoint established a harness-ownership rule,
not a product exception. G06 product qualification MUST preserve the published synchronous
unsaved-change lifecycle and MUST NOT suppress its dialogs to simplify testing.

Frozen markers:

`G06_INTEGRATED_CHECKPOINT_LINE=RETIRED`
`G06_TRUE_GTK_EXPECTED_MODAL_COUNT=0`
`G06_TRUE_GTK_UNEXPECTED_MODAL=UNWIND_THEN_FAIL`
`G06_FIXTURE_OPEN_REQUIRES_EXACT_SAVED_STATE=YES`
`G06_EXPECTED_DIALOG_RESPONSE_OWNERSHIP=SCHEDULE_BEFORE_TRIGGER`
`G06_GLIB_SOURCE_OWNERSHIP=EXPLICIT_CLEANUP_REQUIRED`
`G06_OUTER_TIMEOUT_ROLE=LAST_RESORT_PROCESS_CONTAINMENT_ONLY`
`G06_QUALIFICATION_TOPOLOGY=FRESH_PROCESS_GATE_MATRIX`

For a G06 View semantic/performance scenario, replacing the active fixture is legal only
when `session.modified == False` and the current editor state identity equals the Saved
state identity. If a scenario intentionally tests a modal, its deterministic response must
be armed before the product call. G06 View semantics intentionally expects zero modals; an
unexpected visible `GtkDialog` may be responded to only to unwind a nested loop and MUST
then fail the gate. A generic dialog auto-canceller that lets the scenario continue is
forbidden.

The eventual G06 candidate runner orchestrates independent fresh-process gates. No new
R3 of the retired integrated checkpoint is permitted.

### 17.7 G06 View performance oracle rebaseline after Candidate C1

Candidate C1 passed the full functional G06 True-GTK View gate and stopped only in the
old monolithic View-performance lane. Static mature-source re-audit established that the
retired oracle repeatedly oscillated layout-affecting state in one 10 MiB TextView and
therefore measured cumulative re-layout stress rather than one interactive user request.
The old repeated-toggle/repeated-reset oracle is forbidden.

Frozen markers:

`G06_VIEW_PERFORMANCE_ORACLE=SINGLE_TRANSITION_FRESH_PROCESS`
`G06_VIEW_PERFORMANCE_PRIMING_PROCESSES=1`
`G06_VIEW_PERFORMANCE_MEASURED_PROCESSES=7`
`G06_VIEW_PERFORMANCE_TRANSITIONS_PER_WORKER=1`
`G06_VIEW_PERFORMANCE_FRAME_ORACLE=FIRST_POST_TRANSITION_AFTER_PAINT`
`G06_VIEW_PERFORMANCE_WORKER_TIMEOUT_SECONDS=30`
`G06_VIEW_PERFORMANCE_FRAME_DEADLINE_SECONDS=15`
`G06_VIEW_PERFORMANCE_FONT_APPLY_10M_P90_MAX_MS=500`
`G06_VIEW_PERFORMANCE_BUDGETS_WEAKENED=NO`

Each scenario owns one discarded fresh-process priming sample and seven measured fresh
processes, each with isolated HOME/XDG and exactly one View transition. Open/startup is
setup and remains outside the transition latency because G04 already owns startup/open
performance. The clock begins immediately before the View action and ends at the first
post-transition GTK frame-clock `after-paint`. A worker timeout names the exact scenario,
role and sample; the outer candidate-lane watchdog is last-resort containment only.

Measured scenarios are Line Numbers at 1/10 MiB, Word Wrap at 1/10 MiB, Zoom at 10 MiB,
Font Apply at 10 MiB, and 1000 Compact Status updates. Font Apply replaces only human
chooser input with deterministic Monospace 14; the real Graphium persistence -> base-font
-> CSS path remains measured. Existing budgets are retained and Font Apply adds a 500 ms
p90 ceiling. A budget miss is product-performance evidence; the oracle must not be relaxed
to manufacture a PASS.


## G06 desktop certification and publication closure payload — 2026-08-16

G06 Candidate C2 exact certified tree is `52d4f07c4757e85f6ebeec87398ec8ec3b6e30bb`. T480 certification completed with 266/266 non-desktop tests PASS, strict gates PASS, G04/G05/G06 True-GTK lanes PASS, redesigned single-transition fresh-process View performance PASS, Lightweight Budget PASS, topology and Cinnamon shortcut gates PASS, startup self-regression PASS, common FIRST_VISIBLE comparison PASS, and manual View validation 4/4 PASS.

The certified product scope is Status Bar, native Gtk.TextView visible-logical-line numbers, Word Wrap, persistent Font family+size, transient Zoom, transient Full Screen and Compact Status. Toolbar remains REJECT v1; Appearance remains DEFER G10; live document-wide counts remain DEFER G07 on-demand Statistics.

The two retired integrated NON-CANDIDATE checkpoints remain historical evidence only and MUST NOT be reused. C1's repeated-toggle performance oracle also remains retired. The accepted performance oracle is one priming process plus seven fresh measured processes per scenario, exactly one View transition per worker, action to first post-transition `after-paint`, fail-closed hard budgets.

This file belongs to the G06 publication payload. G06 is considered `CLOSED / CERTIFIED / PUBLISHED` only when `RUN_G06_FINALIZE_AND_PUBLISH.sh` completes with `FINAL_PHASE=G06_PUBLICATION_PASS` and verifies the real remote.
