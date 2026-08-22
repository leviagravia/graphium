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
Status: **CLOSED / CERTIFIED / PUBLISHED**

Published commit: `283f1aa5352c2403ac9e0a945b87cc82cd08cff0`
Certified publication tree: `5e2aa256a47739c45f9c79f39a9685b5c6a454d6`
Validated product tree: `9138a273c2363ef2d43adf64470b3273d49c8eae`

Desktop certification and publication completed on 2026-08-14: 196/196 non-desktop tests PASS, strict gates PASS, True-GTK bounded-responsiveness PASS, NON_UNIQUE topology PASS, active Cinnamon shortcut audit PASS, exact FIRST_EDITABLE admission PASS, common FIRST_VISIBLE comparison PASS against Leafpad/L3afpad/Mousepad/FeatherPad, human desktop validation 4/4 PASS, product equivalence PASS for 62 runtime/user-help files, HEAD=origin/main=remote main, worktree CLEAN and final publication phase `G04_PUBLICATION_PASS`.

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
Status: **CLOSED / CERTIFIED / PUBLISHED**

Published commit: `a9083daf22ab23cf6cd20841be643510e35d700d`
Certified tree: `12d55249263e006cc68fa304f3c3cc2a9ef73acb`
Validated product tree: `295fa67e4943c35d80e605e214e51ee861350fe6`

Establish the top-level **Search** command authority with Find…, Find Next, Find Previous, Replace… and Go to Line…. Next/Previous are true commands shared by menu/shortcuts/Help rather than UI-private buttons.

Frozen G05 scope after direct G04 source audit and mature-source falsification audit:
- literal current-document search only; no regex, fuzzy or multi-file search;
- query and replacement fields are single-line Unicode text; query is non-empty, replacement may be empty;
- Match Case is adopted; Whole Word and search history are deferred;
- one automatic wrap for Find Next/Previous, with no wrap preference;
- current match is the native selection; eager highlight-all/background scanning is rejected;
- Find/Find Next/Find Previous never alter editor state identity/history/Saved-Modified;
- Replace One uses one-click acquisition: replace current exact match or acquire the next match and replace it in the same activation;
- Replace All freezes non-overlapping matches from the original source, precomputes the final text, verifies G04 renderability before mutation, applies changes in descending source-offset order, and advances exactly one DeltaHistory state/Undo group;
- replacement is applied through Graphium-owned expected-delete/inverse-rollback programmatic delta handling, not legacy full-document snapshot transactions and not a generic renderer-guard bypass;
- Go to Line is a simple 1-based bounded line navigation command;
- explicit-command scanning only: no persistent index, worker or background search state; case-insensitive working memory is logical-line bounded; Find Next/Previous do not materialize all matches; Replace All is fail-closed above 50,000 frozen source matches or the DeltaHistory Undo payload budget.

Trustworthiness tests MUST cover ASCII, Unicode casefold and exact original offsets, empty/short/long replacements, selection/navigation boundaries, wrap, zero-change no-op semantics, stale-plan rejection, failure rollback, exact Saved/Modified through Replace/Undo/Redo, realistic large multiline documents, pathological-line guard interaction and Replace All as one logical Undo transaction. G05 closure also requires `LIGHTWEIGHT_BUDGET_GATE=PASS`.
### G06 — View Menu Core / Compact Status + Lightweight Presentation + Performance Checkpoint
Status: **CLOSED / CERTIFIED / PUBLISHED**

Published commit: `aae14ef000ea44674cb9bbb7b3a87e3af00c0b18`
Published tree: `c2b372082cf44280f9717045578822e7b92bef12`
Certified C2 tree: `52d4f07c4757e85f6ebeec87398ec8ec3b6e30bb`

Implement the direct **View** surface: Status Bar, Line Numbers, Word Wrap, Font family+size, Zoom In/Out/Reset and Full Screen. Appearance remains routed to G10 and is not implemented early. Compact status MUST show line/column + Saved/Modified + encoding/EOL without whole-document scanning. Word/character counts remain on-demand in G07 Statistics because G06 has no cheapness proof that would justify live document-wide analytics.

Frozen G06 decisions after direct G05 source audit, mature-source falsification audit and the T480 NON-CANDIDATE line-number probe:
- **Word Wrap = ADOPT**, using native `Gtk.WrapMode.WORD_CHAR`; persistent direct View setting.
- **Line Numbers = ADOPT**, using the native `Gtk.TextView` LEFT border window; draw only visible logical lines; wrapped display-line continuations receive no additional number; persistent direct View setting; no GtkSourceView, parallel scrolling widget, background index or line cache.
- **Status Bar = ADOPT**, compact and event-driven; persistent visibility; MUST fields only line/column + encoding/EOL + Saved/Modified.
- **Font = ADOPT**, persistent family+size applied through CSS/provider rather than deprecated `override_font`.
- **Zoom = ADOPT**, transient 100%-relative magnification separate from the configured font; Reset Zoom means 100%; no document/history/config mutation.
- **Full Screen = ADOPT**, transient window presentation state.
- **Toolbar = REJECT v1** after Lightweight Budget audit: the small Graphium command surface does not justify a duplicate button surface or toolbar state.
- **Appearance = DEFER G10**, preserving the serial roadmap.

Persistent direct View settings are stored in one small XDG product config and are written only on explicit user changes. No background settings writer, session database, scanner or settings platform is introduced. Repeat FIRST_EDITABLE and common FIRST_VISIBLE performance checkpoint against Leafpad/L3afpad/Mousepad/FeatherPad before G06 closure. G06 cannot close without `LIGHTWEIGHT_BUDGET_GATE=PASS`.
#- Performance checkpoint must include self-regression against the certified G04 T480 FIRST_EDITABLE/FIRST_VISIBLE Graphium baseline; time limit = max(+25%, +75 ms), RSS = max(+25%, +20 MiB). Cross-product FIRST_EDITABLE remains forbidden until G12.

## G07 — Recent / Save Copy / Version Copy / Properties / Statistics
Status: **CLOSED / CERTIFIED / PUBLISHED**
Historical implementation lineage: **IMPLEMENTATION R1 BUILT**, then desktop-certified/published after the frozen qualification chain.

Baseline: published G06 commit `aae14ef000ea44674cb9bbb7b3a87e3af00c0b18`, tree `c2b372082cf44280f9717045578822e7b92bef12`.

Complete the high-value **File/Document** conveniences without adding session/workspace state: Open Recent, Save a Copy, Save Version Copy, Graphium-specific Properties and on-demand Statistics. Recent is bounded file history only, not session restoration. Copy and Version Copy reuse the sole guarded writer but never rebind the active document, move the savepoint/history or touch Recent. Properties is a compact read-only surface for accepted logical/canonical identity, disk/representation facts and Saved/Modified; **Check Now** performs a fresh strong read-only observation and never accepts/reloads the session baseline. Statistics captures the live buffer only on explicit activation and computes document/selection Lines/Words/Characters in a pure GTK-free O(n) function.

Frozen G07 constraints: recent state is lazy atomic `XDG_STATE_HOME/graphium/recent-files.json`, schema `{"version":1,"paths":[...]}`, cap 10 and mode 0600; no DB/XBEL/global recent authority, session restoration, automatic backup, version timeline/index, background statistics, file monitor, Reload, second writer or second document authority. No new default G07 accelerator. Desktop/manual validation is forbidden until headless/strict architecture, Statistics performance, Lightweight Budget and real-App True-GTK gates pass.
### G08 — Page Setup / Print Preview / Print + Startup-Isolation Checkpoint
Status: **CLOSED / CERTIFIED / PUBLISHED**

Complete the **File** printing group with Page Setup…, Print Preview and Print…. Printing is desktop-complete but lazily initialized; dormant print code may not materially tax quick-edit startup. Page Setup is a Graphium authority rather than a fixed inherited pagination constant. Repeat startup-isolation/performance evidence.

**G08 responsiveness repair checkpoint (2026-08-19):** the initial synchronous design was measured on the T480 at ~109.6 s for a 1 MiB / 787-page export, while 5 KiB native Preview returned in ~45 ms. GTK-native `allow_async` + `done` made the 1 MiB Preview entry return in ~6 ms, but a real-mainloop diagnostic then localized the remaining freeze inside eager document-global `begin-print` pagination. The authorized second repair keeps native GTK/Pango/Cairo and moves measurement to bounded incremental `paginate` callbacks (16 KiB target / 64 logical lines, logical-line chunk boundaries). Exact-tree T480 requalification subsequently passed, including bounded callback latency, heartbeat responsiveness, cancel/done cleanup and document neutrality; no Graphium worker/service/custom preview/GtkSourceView was introduced.
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


G06 qualification rebaseline after the retired integrated NON-CANDIDATE line:
- `G06_INTEGRATED_CHECKPOINT_LINE=RETIRED`; no R3;
- next T480 run is a separately authorized **G06 product candidate**, not another checkpoint;
- candidate validation is a fresh-process gate matrix: published G04 regression, published
  G05 regression, G06 View semantics with exact clean lifecycle boundaries and zero expected
  modals, G06 View performance, topology/shortcut audit, FIRST_EDITABLE, common FIRST_VISIBLE
  comparators, G05 Search performance and G06 startup self-regression;
- outer timeouts are last-resort process containment; modal/lifecycle ownership belongs to
  the individual gate;
- manual G06 validation starts only after all automated lanes PASS.

G06 product-candidate freeze after modal/lifecycle re-audit:
- the product runtime is byte-for-byte unchanged from the pre-re-audit G06 implementation;
- only qualification harness/tests/authority/evidence changed during the re-audit;
- candidate automation uses separate fresh-process/fresh-XDG lanes and does not reuse the retired integrated checkpoint state;
- candidate packaging must pass directory/file permission-topology validation before manifest/tree checks.

G06 Candidate C1 performance stop and Lane-4 rebaseline:
- C1 functional G04/G05/G06 True-GTK lanes PASS; C1 stopped before manual validation in the
  old G06 View-performance lane; performance verdict remained UNRESOLVED;
- old repeated toggle/reset performance oracle is RETIRED as cumulative re-layout stress;
- new oracle is `SINGLE_TRANSITION_FRESH_PROCESS`: one discarded priming process plus seven
  measured fresh processes per scenario, fresh HOME/XDG, exactly one View transition each;
- latency ends on the first post-transition GTK `after-paint`; worker-local timeout is 30 s
  with a 15 s frame deadline; parent/lane timeout is containment only;
- scenarios: line-numbers-1m, wrap-1m, line-numbers-10m, wrap-10m, zoom-10m,
  font-apply-10m, status-1000-updates;
- all previous budgets remain frozen; Font Apply 10 MiB adds p90 <= 500 ms;
- no Graphium runtime change is permitted merely to repair the retired oracle;
- Candidate C2 may be built only from this redesigned qualification boundary and must be
  fully fresh-package qualified before any optional T480 execution.


### G06 closure / G07 handoff — 2026-08-16

G06 has a desktop-certified C2 product tree `52d4f07c4757e85f6ebeec87398ec8ec3b6e30bb`. The G06 publication payload changes canonical authority/evidence only; it does not alter the certified Graphium runtime. After the publication finalizer proves the remote real state, G06 is CLOSED/CERTIFIED/PUBLISHED.

**Next serial item: G07 — Recent / Save Copy / Version Copy / Properties / Statistics.** G07 MUST NOT implement before: read-only audit of the published G06 source, direct mature-source falsification audit, explicit ADOPT/ADAPT/REJECT/DEFER matrix, Lightweight Budget review and contract freeze. Priority mature sources are Mousepad 0.7.0, FeatherPad source-derived authority already preserved in the bundle, gedit/GNOME Text Editor, Leafpad/L3afpad for minimalism contrast, and Calamus W115/W116 provenance only as a design reference for Copy/Version Copy/Properties semantics (never as a runtime dependency).


### G07 R1 startup qualification correction — 2026-08-16

The first exact R1 T480 NON-CANDIDATE qualification passed all functional/True-GTK G04-G07 lanes, Statistics, View, topology, shortcut and Search gates but failed the startup self-regression gate. Failure-specific direct mature-source re-audit isolated document-grade `fsync(file)+fsync(directory)` in the new Recent convenience-store write on every successful Open. FeatherPad, GNOME Text Editor, Mousepad, gedit and NEdit all contradict the need for that durability level; Leafpad/L3afpad remain the minimalism negative oracle. The frozen Recent contract is clarified as `G07_RECENT_DURABILITY=ATOMIC_CONVENIENCE_NO_FSYNC`: retain 0600 complete-temp + atomic replace, remove only Recent fsync barriers. No document-save safety is weakened and no background service is introduced. A fresh T480 NON-CANDIDATE startup requalification is mandatory before any G07 desktop candidate.

G07 R1 comparator-stop re-audit (2026-08-17): a startup-repair NON-CANDIDATE rerun reached and passed
all Graphium product/view/statistics gates through Graphium FIRST_VISIBLE, then a single Leafpad launch
produced no new X11 top-level for the exact spawned PID. Direct mature-source re-audit of Leafpad,
L3afpad, Mousepad 0.7.0, FeatherPad and GNOME Text Editor confirms the exact-PID ownership oracle but
exposes two harness defects: missing explicit post-process X11 quiescence/block diagnostics, and an
anti-bloat Graphium self-gate incorrectly dependent on complete competitor telemetry. Runtime product
changes are forbidden for this stop. Harness-only repair: comparator blocks are exit-3 comparative
blocks with incremental partial receipts and no silent retry; G06 startup self-regression consumes only
Graphium measurements. Full comparative evidence remains mandatory before candidate promotion.


### G07 closure / G08 handoff — 2026-08-18

G07 completed the full desktop qualification on the T480. The certified publication-line source tree before authority-only closure is `12f24dbc265247bd9c014e2494fb91fc82f07af1`. Automated qualification passed 304/304 tests, strict architecture, G04/G05/G06/G07 True-GTK, contamination-aware G06 View performance, G07 Statistics performance, topology, Cinnamon shortcut audit, exact Graphium FIRST_EDITABLE, complete Graphium/Leafpad/L3afpad/Mousepad/FeatherPad FIRST_VISIBLE comparison, G05 Search performance and G06 startup self-regression. The user then reported **7/7 manual desktop tests PASS**. One valid product candidate attempt was consumed; earlier R1 desktop stops were classified as invalid execution/oracle-harness defects after failure-specific direct mature-source audits and do not count as product FAILs.

Publication may alter only the three canonical authority documents plus additive certification evidence; `graphium/`, `bin/`, user-facing product documentation, tests and qualification tools remain byte-for-byte equivalent to the certified G07 publication-line source. G07 is not called PUBLISHED until the finalizer proves the exact final tree, commits, pushes, fetches, verifies `HEAD=origin/main=remote main`, and leaves the worktree clean.

**Next serial item after publication: G08 — Page Setup / Print Preview / Print + Startup-Isolation Checkpoint.** G08 implementation is forbidden until a read-only audit of the real published G07 repository, a direct mature-source printing audit, an explicit ADOPT / ADAPT / REJECT / DEFER matrix, Lightweight Budget review, startup-isolation design and contract freeze are complete. Priority source authorities: Leafpad `src/gtkprint.c` as the thin GTK3 print-operation model; Mousepad `mousepad-print.c/.h` as the mature GTK3 print/settings model; gedit print job/preview/app page-setup code as the richer GTK3 contrast; FeatherPad `featherpad/printing.cpp/.h` and print-dialog call sites as the Qt lightweight-power contrast; GNOME Text Editor as a GTK4 modern contrast where printing support exists in the supplied source; L3afpad as minimalism/feature-pressure contrast. No web substitute is permitted for this audit.


### G08 implementation checkpoint — 2026-08-18

Published G07 baseline was independently proven on the T480 before G08 work began:
commit `7a3f49218dbabdbd6e47114a5fde2f4999f9c841`, tree
`198164be38e77538b92f45d5d53fe4b0c1929955`, with
`HEAD=origin/main=remote main` and a clean worktree.

The required read-only G07 audit, direct preserved mature-source printing audit, explicit
ADOPT/ADAPT/REJECT/DEFER matrix, Lightweight Budget and G08 contract freeze completed before
implementation. The isolated G08 implementation now contains the frozen File printing group,
strict lazy print-module/Page-Setup ownership, native GTK preview and Pango/Cairo pagination.
It is **not a desktop candidate**. Candidate attempts consumed remain **0/2**.

Before any candidate declaration the T480 NON-CANDIDATE PyGObject/GTK3 print-binding probe must
PASS, followed by the frozen True-GTK/hostile startup-isolation/performance and Lightweight Budget
gates. A probe failure is boundary evidence, not a product candidate FAIL, and requires direct
failure-specific mature-source re-audit before repair.


**G08 exact-once cleanup follow-up (2026-08-19):** the first incremental T480 requalification proved cheap begin-print and bounded paginate callbacks, then exposed duplicate Graphium render cleanup: native `end-print` was followed by `_clear_active()` invoking `job.end_print()` again from `done`. Failure-specific gedit/GNOME Text Editor re-audit confirmed separate ownership. The repair makes native `end-print` the normal one-time render cleanup and reserves the `done` fallback for paths where GTK never emitted it. Pagination is unchanged; NON-CANDIDATE requalification remains required.


### G08 closure / G09 handoff — 2026-08-20

G08 completed the full T480 qualification on exact certified product tree `420238bd82e7051fa01d002b92660a0ad4b1d40c`. Final predesktop qualification passed 319/319 non-desktop tests, strict gates, G04/G05/G06/G07 True-GTK regressions, G08 binding/hostile/startup-isolation lanes, incremental 1 MiB Preview responsiveness, topology, Cinnamon shortcut audit, hostile FIFO startup, G07-vs-G08 FIRST_EDITABLE startup delta, common FIRST_VISIBLE comparison, G06 startup self-regression, G05 Search performance, G06 View performance and G07 Statistics performance.

Candidate R1 consumed attempt 1/2 and was retired after a composite manual Test 6 FAIL. Failure-specific NON-CANDIDATE diagnosis on the unchanged product tree proved the product overlap/lifecycle behavior and localized the failure to an unowned human timing window. Candidate R2 therefore reused the same product tree and strengthened the validation oracle rather than changing runtime. R2 passed the full 20-lane automated matrix and manual Tests 1–5. Its initial Test 6 close check was an incomplete user procedure, not a product FAIL; the authorized manual reissue preserved the candidate and consumed no new attempt. The reissue passed responsiveness/Preview lifecycle and confirmed normal window close plus process exit. Final manual result: **6/6 PASS**. Candidate history remains 2/2 attempts used.

Publication preserves the certified runtime and user-facing implementation byte-for-byte. Only the three canonical authority documents, additive `G08_DESKTOP_CERTIFICATION_RECEIPT_20260820.txt` evidence and regenerated `evidence/SHA256SUMS.txt` differ from the certified tree. G08 becomes **CLOSED / CERTIFIED / PUBLISHED** only when the publication finalizer proves the target tree, commits, pushes, fetches, verifies `HEAD = origin/main = remote main`, and leaves the canonical worktree clean.

**Next serial item: G09 — Explicit Text Transformations Only / No Format-Menu Expansion.** G09 remains PENDING until a separate authorization and its own published-G08 read-only audit, mature-source review, Lightweight Budget check and contract freeze.

### G09 implementation checkpoint — 2026-08-20

The published-G08 source audit, direct mature-source audit, ADOPT/ADAPT/REJECT/DEFER matrix,
Lightweight Budget and contract freeze completed before implementation. G09 is now implemented in
an isolated copy as a NON-CANDIDATE: Edit -> Transform Text contains exactly Uppercase, Lowercase,
Duplicate Line / Selection, Move Lines Up, Move Lines Down and Trim Trailing Spaces. Move Lines
uses Alt+Up / Alt+Down; the other four commands have no default accelerator. No top-level Format
menu, GtkSourceView, background service, persistent transform settings or second mutation authority
was added.

The implementation reuses `NativeEditorController.apply_prevalidated_programmatic_group()` as the
sole mutation/Undo/rollback authority and adds one pure GTK-free planner. Build-host qualification is
35/35 focused and 354/354 full headless PASS. Desktop/True-GTK, Cinnamon collision, live canonical
Git and 1 MiB integrated action gates remain PRE-CANDIDATE work on the T480. Candidate attempts
remain 0/2 and Candidate R1 requires separate authorization only after that qualification passes.


### G09 closure / G10 handoff — 2026-08-21

G09 completed full T480 qualification on exact certified product tree
`92bcae4fcf72684872a9fa675007156bd0a4de3c`. PRE-CANDIDATE qualification PASSed before candidate
declaration. Candidate R1 then PASSed all 20 automated lanes. Manual Tests 1-4 PASSed in the original
run. The original Test 5 automatic disk postcondition PASSed, while the subsequent human FAIL was
classified after source-first/mature-source re-audit as an invalid manual-oracle false negative rather
than a product failure. A first manual-only reissue stopped before Graphium launch on a Bash harness
defect; the corrected reissue preserved the exact product tree, declared no R2, consumed no new
attempt and PASSed Tests 5-6. Composed manual result: **6/6 PASS**. Candidate-line accounting remains
**1/2 attempt used**, with no product FAIL.

The certified G09 surface is intentionally narrow: Edit -> Transform Text exposes Uppercase,
Lowercase, Duplicate Line / Selection, Move Lines Up, Move Lines Down and Trim Trailing Spaces;
Alt+Up/Alt+Down are the only new accelerators. G09 adds no top-level Format menu, GtkSourceView,
background work, persistent transform state, implicit Open/Save cleanup or second mutation/history
authority.

Publication preserves `graphium/`, `bin/`, `docs/user/`, `tests/` and `tools/` byte-for-byte from the
certified tree. Only the three canonical authority documents, additive
`G09_DESKTOP_CERTIFICATION_RECEIPT_20260821.txt` evidence and regenerated
`evidence/SHA256SUMS.txt` may differ. G09 becomes **CLOSED / CERTIFIED / PUBLISHED** only when the
publication finalizer proves the exact target tree, commits, pushes, fetches, verifies
`HEAD = origin/main = remote main`, and leaves the canonical worktree clean.

**Next serial item: G10 — Persistence Layer / Preferences Dialog without duplicating direct View
commands.** G10 remains PENDING until separate authorization plus a read-only audit of the published
G09 repository, direct mature-source review, explicit ADOPT / ADAPT / REJECT / DEFER matrix,
Lightweight Budget review and contract freeze. No G10 implementation is authorized by G09
publication.


GS07 VALIDATION REBASELINE (2026-08-21)
The active qualification architecture is permanent and concern-oriented: Behavioral/Unit, Integration/Filesystem, True-GTK Desktop, Packaging/Release. Historical Gxx qualification names and executable evidence/doc prose oracles are retired from active validation. G10 remains frozen until GS07 desktop rebaseline is proven on T480.

### GS07 structural validation cutover assessment — 2026-08-22

GS01-GS07 structural simplification has passed its formal T480 and anti-cosmetic assessment on
source tree `fc6673e35d4f47bbe74a9a6c0de3a3f44cca8c81`. Legacy G09 shadow equivalence, all four
permanent qualification authorities, deletion proof, authority/dependency reduction, no-shim,
packaging separation and product/release separation are PASS. Final mature-source comparison also
PASSes.

Status: **READY FOR CANONICAL CUTOVER, NOT YET CUT OVER**. G10 remains frozen at candidate 0/2 until
a separate GS07 canonical Git cutover transaction commits/pushes/verifies the rebaseline. Only after
that transaction passes may G10 resume from the simplified permanent qualification architecture.

### GS07 canonical cutover — 2026-08-22

GS07 is the canonical validation-architecture rebaseline after the authorized Git cutover succeeds.
The rebaseline preserves the G09 product behavior while replacing historical Gxx executable
validation with four permanent concern-oriented authorities and passing the binding net-reductive
structural gate. After cutover, **G10 is unfrozen with candidate attempts 0/2** and resumes from this
simplified qualification architecture. No retired Gxx harness or compatibility layer may be restored.
