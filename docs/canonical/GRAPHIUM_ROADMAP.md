# Graphium — Canonical Roadmap

Canonical document 2 of 3.
Initial freeze: 2026-08-13 — G00.
Rebaseline: 2026-08-14 — seven-editor competitive synthesis + FeatherPad audit + G04 native-edit/performance redesign + Menu Architecture R3.

## Product direction

Graphium is the **lightweight trust editor**: a **FAST + SIMPLE + SAFE + NATIVE GTK** single-document plain-text editor for Linux. It targets Leafpad/L3afpad-style quick-edit users and the quick-edit subset of Mousepad/FeatherPad users: people who want a file to open immediately, a calm conventional editor surface, a small number of useful persistent conveniences, and unusually strong assurance that Save will not silently alter, convert or overwrite the wrong file.

Permanent primary comparator set: **Leafpad / L3afpad / Mousepad / FeatherPad**.
Supporting mature-source oracles are selected per work item and may include Airpad, Janus, Parchment, gedit, GNOME Text Editor, NEdit, JOE, Lite XL, Calamus published baselines and other directly audited mature sources.

Competitive rules:

1. Leafpad/L3afpad are the reference for immediacy and low cognitive load, not for physical save safety.
2. Mousepad is the primary operational-maturity comparator for lifecycle, monitoring, printing and ordinary desktop completeness.
3. FeatherPad is the permanent speed-plus-maturity comparator: its feature density is evidence that richer internals do not excuse poor launch latency. Graphium targets FeatherPad users who value speed and plain-text maturity but do not depend on tabs, sessions, syntax or column editing.
4. Parchment is the scope-discipline reference, while its implicit Open/Save normalization remains a negative persistence oracle.
5. Graphium must prefer invisible maturity over visible feature count. Feature count is not the competitive axis.
6. Open and Save are content-neutral unless the user explicitly requests a transformation.
7. Safety and performance may never be weakened to improve one another.
8. A mature-source audit must actively search for evidence that contradicts Graphium's proposed design; confirmation-only comparison is invalid methodology.

Minimum convenience floor for v1:

- persistent Word Wrap, font, line numbers, compact status visibility and useful window geometry;
- tab width and spaces/tabs policy where relevant;
- System/Light/Dark appearance without a theme platform;
- trustworthy Find/Replace, Recent Files, printing, conventional shortcuts and useful offline Help;
- status information with line/column, Saved/Modified, encoding and EOL, plus word/character counts when cheap enough not to violate performance budgets.

Deliberate non-goals remain: tabs inside one window, syntax highlighting, projects/workspaces, IDE facilities, plugins, cloud, collaboration, embedded browser, AI and feature-platform expansion.

## Menu Architecture R3 — frozen product surface

Graphium v1 uses exactly six top-level menus: **File · Edit · Search · View · Document · Help**. The six-menu count is not itself considered bloat; bloat is defined instead as duplicated state/configuration surfaces, workflow-irrelevant diagnostics, or feature families that move Graphium toward multi-document/code-editor/platform scope.

Semantic ownership is frozen:

- **File** — persistence and document/file lifecycle;
- **Edit** — local text editing plus preferences that have no clearer direct command;
- **Search** — content search and navigation;
- **View** — how the active text is presented;
- **Document** — observed representation/state facts and explicit representation conversion;
- **Help** — user understanding, shortcuts and compact support information.

Target command surface at v1 closure:

- **File** — New, Open…, Open Recent, Save, Save As…, Save a Copy…, Save Version Copy…, Reload from Disk, Properties…, Page Setup…, Print Preview, Print…, Quit. `Close` is not a separate v1 command because one-process/one-window/one-document gives New and Quit the two distinct lifecycle outcomes already needed.
- **Edit** — Undo, Redo, Cut, Copy, Paste, Delete, Select All, Preferences…. `Paste as Plain Text` is unnecessary because Graphium is itself a plain-text editor.
- **Search** — Find…, Find Next, Find Previous, Replace…, Go to Line…. Next/Previous are first-class command-authority actions. Regex/fuzzy/multi-file search remain outside the v1 MUST scope.
- **View** — Status Bar, Line Numbers, Word Wrap, Font…, Zoom In/Out/Reset, Appearance (System/Light/Dark), Full Screen. Toolbar remains **DEFERRED to the G06 mature-source audit** and is not pre-authorized by the menu architecture.
- **Document** — Encoding, Line Endings, Statistics…. Encoding/EOL submenus must show current representation as an observation and label conversion as an explicit user action; normal Save is never conversion. Tab width/spaces-tabs do not belong here because they are editor behavior, not document representation.
- **Help** — Graphium Help, Keyboard Shortcuts, About Graphium. System Information is folded into About rather than promoted to a separate menu command.

Persistent settings follow a **single-surface rule**: when a setting has a clear direct command (`Word Wrap`, `Line Numbers`, `Status Bar`, `Appearance`, `Font`, and a toolbar toggle if later adopted), that command changes and persists the setting. Preferences does not duplicate it. Initial Preferences ownership is limited to tab width, tabs/spaces behavior and future settings that lack a clearer direct command. Safety invariants are never user-disableable preferences.

`Properties…` is the compact home for file/document facts (location, size/observation, encoding/BOM/EOL, Saved/Modified, writable state, useful symlink/hard-link information). The capability proposed as `Check File on Disk` is retained, but routed as a **Check Now** action inside Properties and as G11 automatic monitoring, not as a permanent primary Document-menu item.

Compact status v1 MUST information is line/column + encoding/EOL + Saved/Modified. Live word/character counts are optional only after cheapness proof; full counts remain available on demand through `Statistics…`.

There is no v1 top-level `Tools`, `Window`, `Format`, `Language`, `Session` or `Plugins` menu.

## Cross-cutting performance method

G04 replaces the earlier heterogeneous benchmark idea with two explicitly different metrics:

- **FIRST_VISIBLE** — common external oracle used identically for Graphium, Leafpad, L3afpad, Mousepad and FeatherPad: process start to first new X11 top-level mapped for the exact spawned PID. Cross-product ratios are valid only for this common metric.
  Comparator launches must be process-isolated when an editor is single-instance/server-capable: Mousepad no-server mode and FeatherPad `--standalone`; never relax exact-PID ownership to accommodate forwarding.
- **FIRST_EDITABLE** — exact Graphium-internal oracle: process start to requested Open completion + mapped window + focused Gtk.TextView, signalled through an inherited pipe with one complete READY record. This is an exact Graphium regression/admission metric, not a comparator ratio.

G12 may make hard cross-product FIRST_EDITABLE claims only after establishing one common external oracle for all compared products (for example an AT-SPI/XTest-style disposable-input measurement). It is forbidden to compare unlike readiness events as if they were the same metric.

Normal benchmark series use one uncounted priming run followed by at least seven measured runs, reporting median and p90. Real user XDG/configuration is never mutated.

Performance checkpoints:

- **G04** — first GTK shell, FIRST_VISIBLE comparator baseline, exact Graphium FIRST_EDITABLE baseline;
- **G06** — view/status checkpoint;
- **G08** — printing startup-isolation checkpoint;
- **G10** — preferences/appearance checkpoint;
- **G11** — live-monitor startup/idle checkpoint;
- **G12** — final competitive qualification with common readiness oracle.

## Serial roadmap

### G00 — Architecture Bootstrap / Technology & Boundary Contract
Status: **CLOSED / CERTIFIED / PUBLISHED**

Published commit: `1e9db0eed37d0c860c36c1e07c0dc77bbf59ff95`
Certified tree: `2023683019894366729e3ddc5f3652dbe9d5d0c2`

Freeze Graphium identity, Python/PyGObject/GTK3 technology, Gtk.TextView baseline, package boundaries, XDG isolation, one-document/one-writer authority rules, W116 selective-extraction policy and three-document canonical cap.

### G01 — Document Identity / Load / Serialize Foundation
Status: **CLOSED / CERTIFIED / PUBLISHED**

Published commit: `bf7878c3cdc5cf895b0ffba86b854860c34936a4`
Certified tree: `2334e0c71f01a1b0a30bcb9298911c7c0cafe042`

Strong local-file identity, stable loads, strict encoding/BOM/EOL representation and content-neutral serialization foundation.

### G02 — History / Editor Transaction / Savepoint Session
Status: **CLOSED / CERTIFIED / PUBLISHED**

Published commit: `b91af48a5688772ceffc7eac202c68e1815d7a36`
Certified tree: `3e5b24263d4086a3eccf4897b038b8992703db79`

Publishes the permanent savepoint principle: Saved/Modified is a relation between positive monotonic editor-state IDs, not text equality and not a sticky GtkTextBuffer flag. G02's full-snapshot `TextHistory` remains historical/headless regression material; G04 performs the explicitly authorized architecture review and does not use that storage engine as the active GTK native-edit history.

### G03 — Guarded Save / Save As Foundation
Status: **CLOSED / CERTIFIED / PUBLISHED**

Published commit: `e7045e0ce1c79da71c9968bdfa052df25a5378b7`
Certified tree: `42fe5340e1181199db86ed69cfa93b4735e45666`

Single physical `GuardedFileWriter`, strict pre-mutation serialization, same-directory staging, full-write/fsync semantics, late target revalidation, race-safe Save As, symlink-preserving logical identity, hardlink fail-closed policy and bind-after-commit semantics. No direct-write fallback.

### G04 — Native Edit Integration Hardening + Thin GTK Shell + File Lifecycle + Scientific Performance Baseline
Status: **DESKTOP CERTIFIED / PUBLICATION READY / NOT YET PUBLISHED**

Desktop certification on the T480 completed on 2026-08-14 against validated product tree `9138a273c2363ef2d43adf64470b3273d49c8eae`: 196/196 non-desktop tests PASS, strict gates PASS, True-GTK bounded-responsiveness PASS, NON_UNIQUE topology PASS, active Cinnamon shortcut audit PASS, exact FIRST_EDITABLE admission PASS, common FIRST_VISIBLE comparison PASS against Leafpad/L3afpad/Mousepad/FeatherPad, and human desktop validation 4/4 PASS. The candidate is publication-ready; G05 remains blocked until G04 publication PASS.

G04 is rebuilt rather than patched after two withdrawn pre-publication candidate transports exposed defects in the harness and, more importantly, weaknesses in the earlier architecture assumptions.

Mandatory G04 outcomes:

1. **Native delta history**
   - insertion/deletion deltas, not full-document snapshots per keystroke;
   - GtkTextBuffer `begin-user-action` / `end-user-action` plus structural continuity as grouping evidence;
   - no wall-clock timeout as semantic Undo authority;
   - preserve G02 monotonic state-ID/savepoint semantics;
   - Undo/Redo remains available on a realistic 1 MiB multiline document after a small edit;
   - changed-payload memory is bounded independently of base document size;
   - document byte size and pathological logical-line width are tested separately.

2. **Quick-edit process topology**
   - one invocation/process owns one window and one active document;
   - `G_APPLICATION_NON_UNIQUE`;
   - a second invocation must not hijack/replace the first process's document;
   - several command-line files fan out to separate Graphium processes/windows.

3. **Thin classic GTK3 shell**
   - Gtk.ApplicationWindow + Gtk.TextView + Gtk.ScrolledWindow;
   - File: New/Open/Save/Save As/Quit;
   - Edit: Undo/Redo/Cut/Copy/Paste/Delete/Select All;
   - Help: User Guide/Keyboard Shortcuts/About, loaded lazily;
   - no GtkSourceView, toolbar, tabs, syntax or project UI.

4. **Core file lifecycle**
   - failed Open preserves current document;
   - New/Open/Quit use Save/Discard/Cancel only when Modified;
   - merely deciding whether to discard must not copy the whole buffer;
   - Save synchronizes exact current buffer text once at the physical-save boundary;
   - all physical writes continue through G03.

5. **Renderer safety / pathological logical-line contract**
   - initial GtkTextView interactive budget: 20,000 Unicode characters per logical line;
   - a file over the budget is refused before GtkTextBuffer installation, leaving the current document exact;
   - no truncation, marker substitution, automatic wrapping or inserted line breaks;
   - insertion/paste and newline-deleting joins cannot create an over-budget line;
   - the budget is a Graphium safety policy, not a claimed universal GTK hard limit;
   - future paged/streamed exact viewing is deferred and cannot be simulated with the same GtkTextView.

6. **Scientific performance baseline**
   - Graphium exact FIRST_EDITABLE via atomic inherited-pipe handshake;
   - common FIRST_VISIBLE oracle for Graphium/Leafpad/L3afpad/Mousepad/FeatherPad;
   - no ready-file existence race;
   - no cross-product ratio based on heterogeneous readiness definitions.

7. **Desktop closure**
   - full non-desktop suite and strict gates first;
   - True-GTK native-edit/savepoint/realistic-multiline-large-file gate;
   - separate automated huge-line Open/paste refusal gate;
   - NON_UNIQUE topology gate;
   - active Linux Mint/Cinnamon accelerator collision audit;
   - exact and comparator performance receipts;
   - one final human desktop validation only after all automated gates pass.

### G05 — Search Menu Core / Find / Replace / Go to Line + Trustworthiness Gate
Status: PENDING

Establish the top-level **Search** command authority with Find…, Find Next, Find Previous, Replace… and Go to Line…. Next/Previous are true commands shared by menu/shortcuts/Help rather than UI-private buttons. Find/Replace stays deliberately small: case/whole-word behavior only when justified by mature-source audit; regex, fuzzy and multi-file search are non-MUST. Replace is trust infrastructure: tests must cover ASCII, UTF-8 multibyte text before/inside matches, empty/short/long replacements, selection boundaries, realistic large multiline documents, pathological-line guard interaction and Replace All as one logical Undo transaction.
### G06 — View Menu Core / Compact Status + Toolbar Decision + Performance Checkpoint
Status: PENDING

Implement the direct **View** surface: Word Wrap, Line Numbers, Status Bar, Font family+size, Zoom In/Out/Reset, Full Screen and the view-side command authority needed later for System/Light/Dark. Compact status MUST show line/column + Saved/Modified + encoding/EOL. Word/character counts are not mandatory live status fields; include them only if an incremental/cheap implementation is proven not to create eager whole-document work, otherwise keep counts on demand in G07 Statistics. Direct View settings are persistent and must not later be duplicated in Preferences.

Evaluate, by falsification-oriented mature-source and target-user audit, whether a small optional `View -> Toolbar` serves the product without bloat. Toolbar remains DEFERRED until that audit; if adopted, default-off is the leading hypothesis, visibility is persistent, command set is deliberately small and command availability remains owned by the common command authority. Repeat performance checkpoint against the permanent four-comparator set.
### G07 — Recent / Save Copy / Version Copy / Properties / Statistics
Status: PENDING

Complete the high-value **File/Document** conveniences without adding session/workspace state: Open Recent, Save a Copy, Save Version Copy, Graphium-specific Properties and on-demand Statistics. Recent is file history only, not session restoration. Properties is the compact visible surface for logical path/location, size and accepted disk observation, encoding/BOM/EOL, Saved/Modified, writable state and appropriate symlink/hard-link facts. It also owns an explicit **Check Now** disk-state action backed by strong observation; no separate permanent `Document -> Check File on Disk` command is required. Statistics provides document/selection counts on demand so G06 need not perform eager global analytics.
### G08 — Page Setup / Print Preview / Print + Startup-Isolation Checkpoint
Status: PENDING

Complete the **File** printing group with Page Setup…, Print Preview and Print…. Printing is desktop-complete but lazily initialized; dormant print code may not materially tax quick-edit startup. Page Setup is a Graphium authority rather than a fixed inherited pagination constant. Repeat startup-isolation/performance evidence.
### G09 — Explicit Text Transformations Only / No Format-Menu Expansion
Status: PENDING

Uppercase, Lowercase, Title Case, Duplicate Line/Selection, Move Lines, Trim Trailing Spaces, Remove Extra Spaces, Join Lines and Reflow Paragraph remain eligible only as explicit user actions after their own mature-source/scope review. They must not create implicit Open/Save cleanup, and they do **not** justify a permanent top-level `Format` menu. Parchment-style implicit cleanup during Open/Save remains a permanent negative oracle.
### G10 — Persistent Essential Preferences / Appearance / Desktop Polish + Performance Checkpoint
Status: PENDING

Implement persistence without a preference-platform layer. **Single-surface rule:** a setting with a direct command is changed and remembered there and is not duplicated in Preferences. Therefore Word Wrap, Line Numbers, Status Bar, Font, Appearance and any adopted Toolbar visibility persist from their direct View commands. Preferences initially owns only settings without a clearer direct command, especially tab width and tabs/spaces behavior, plus useful window geometry where appropriate. System/Light/Dark is the complete appearance set; no theme engine or arbitrary color platform. Safety invariants (guarded Save, strong identity/external-mutation protection) are not disableable preferences. Consider DnD Open. Repeat performance checkpoint.
### G11 — Reload + Strong Live External-File Safety + Slow-Filesystem Gate
Status: PENDING

Complete the external-file workflow behind ordinary **File -> Reload from Disk**, Properties -> Check Now and automatic monitoring. Filesystem monitor events are **interrupts, not truth**: event -> debounce/coalescing -> fresh strong G01-grade observation -> material classification -> UI decision. Never use a timer alone as proof that an event is self-generated or external. Reload must protect Modified text and distinguish changed content from physical replacement/deletion where the evidence permits. Mousepad is the positive operational comparator; FeatherPad is a contrast oracle for mtime-oriented external-change handling and persistence paths. Freeze the hostile scenario: open accepted A -> another process replaces A with B -> Save must never silently overwrite B. Test local files, replacement-by-rename, symlink paths, repeated external saves and delayed/slow storage where practicable. Recheck startup/idle performance.
### G12 — V1 Product Closure / Six-Menu Competitive Qualification
Status: PENDING

Close all v1 MUST features, packaging/install behavior, the frozen **File/Edit/Search/View/Document/Help** architecture, offline Help and keyboard documentation, True-GTK regression and anti-bloat audit. Verify that command authority, menu labels, accelerators and Help remain synchronized; no top-level Tools/Window/Format/Language/Session/Plugins menu appears. Verify Preferences does not duplicate direct persistent View commands, representation conversion remains explicit and distinct from Save, System Information is folded into About, and Check Now is routed through Properties/monitoring rather than diagnostic-menu expansion.

Establish a common external FIRST_EDITABLE oracle before any hard Graphium-vs-comparator editable-readiness claim. Publish Graphium FIRST_VISIBLE and exact internal FIRST_EDITABLE/RSS receipts and report gaps honestly against Leafpad, L3afpad, Mousepad and FeatherPad. V1 competitive closure requires: no perceptible quick-edit regression versus the lightweight set; no silent Save normalization; no silent overwrite after accepted identity becomes stale; exact Saved/Modified through Undo/Redo/late Save; useful persistent conveniences without preference-platform bloat; low-noise monitoring; continued identity as a plain-text quick editor rather than a reduced IDE; and no known pathological logical-line shape silently admitted into a renderer path already demonstrated to hang.
### G13 — Crash Recovery Cache
Status: **POST-V1 HIGH-PRIORITY BACKLOG**

Evaluate a local recovery cache separate from the user's file: never confused with Save, never silently mutates the target, deleted after accepted Save/Discard, used only for crash/termination recovery. This precedes optional spellcheck because recovery is more directly relevant to the target-user evidence.

### G14 — Offline Spellcheck
Status: **POST-V1 OPTIONAL BACKLOG**

Evaluate bounded offline spellcheck only after v1/recovery fundamentals. It must initialize lazily and must not damage startup or idle budgets.

## Permanent routing rules

1. Serial Gxx only; no G05 implementation while G04 is open.
2. Canonical authority remains exactly three documents.
3. Source audits, matrices, receipts, benchmark JSON and User Guide are non-canonical evidence/product material summarized into the MO.
4. Graphium and Calamus evolve independently after provenance-recorded extraction.
5. Every visible function added or materially changed updates the offline User Guide/shortcut documentation in the same candidate.
6. Every new accelerator is checked against the active Linux Mint/Cinnamon global bindings; `Ctrl+Alt+L` is forbidden.
7. Verified dead code is removed rather than retained as speculative compatibility surface; cleanup must rerun full tests/gates.
8. Mature-source audit is falsification-oriented: record the Graphium assumption, contradictory mature evidence, viable alternative and resulting decision before ADOPT/ADAPT/REJECT/DEFER.
9. A harness/oracle stop is classified before product repair. It is not a reason to cycle candidates by trial-and-error.
10. Safety and content neutrality are never performance toggles.
11. Permanent competitive qualification uses Leafpad, L3afpad, Mousepad and FeatherPad; missing comparator evidence blocks the comparative receipt rather than being silently omitted.
12. Recovery, if implemented post-v1, is a cache separate from the user target and never gains implicit Save authority.
