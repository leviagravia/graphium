# Graphium — Canonical Roadmap

Canonical document 2 of 3.
Initial freeze: 2026-08-13 — G00.
Rebaseline: 2026-08-14 — target-user research + Performance & Perceived Latency Budget.

## Product direction

Graphium is routed as a **fast, simple and safe native GTK single-document text editor** for Linux. The primary migration audience is the quick-edit user of Leafpad/L3afpad and the quick-edit segment of Mousepad. The roadmap therefore prefers invisible maturity over visible feature accumulation.

Permanent competitive reference set: **Leafpad / L3afpad / Mousepad**.

Primary differentiators to preserve through v1:

1. transparent strong file safety without UI bloat;
2. encoding/BOM/EOL clarity and preservation;
3. fast startup and fast time-to-editable;
4. essential preferences that persist;
5. mature Print / Print Preview / Page Setup;
6. compact status information: line/column, words/chars, encoding/EOL, Saved/Modified;
7. Save a Copy / Save Version Copy without rebinding the active document;
8. System/Light/Dark without a theme subsystem.

Deliberate non-goals remain: tabs, syntax highlighting, IDE facilities, plugins, workspace/project systems and feature-platform expansion.

## Cross-cutting gate — Performance & Perceived Latency Budget

The Architecture Contract section 12 is binding on all desktop-capable work items. Comparative benchmarks against Leafpad, L3afpad and Mousepad become mandatory at G04 and remain permanent thereafter.

Benchmark checkpoints:

- **G04** — first GTK baseline and admission ceiling;
- **G06** — after line numbers/font/zoom/status;
- **G08** — verify print subsystem remains off startup critical path;
- **G10** — after preferences/appearance/desktop polish;
- **G11** — verify live file monitoring adds no unacceptable startup/idle regression;
- **G12** — final v1 competitive closure.

No later feature may buy convenience by silently crossing the permanent regression budget.

## Serial roadmap

### G00 — Architecture Bootstrap / Technology & Boundary Contract
Status: **CLOSED / CERTIFIED / PUBLISHED**

Published commit: `1e9db0eed37d0c860c36c1e07c0dc77bbf59ff95`
Certified tree: `2023683019894366729e3ddc5f3652dbe9d5d0c2`

Freeze product identity, Python/GTK technology, package boundaries, XDG isolation, one-document/one-writer authority rules, W116 selective-extraction policy, canonical-document cap and architectural gates. No feature implementation and no desktop attempt.

### G01 — Document Identity / Load / Serialize Foundation
Status: **CLOSED / CERTIFIED / PUBLISHED**

Published commit: `bf7878c3cdc5cf895b0ffba86b854860c34936a4`
Certified tree: `2334e0c71f01a1b0a30bcb9298911c7c0cafe042`

Extract/adapt W116 document identity, stable loader and serializer into Graphium namespace. Freeze general-purpose filename/encoding/BOM/EOL semantics. Headless only unless a GTK need is discovered and justified.

G01 also records the target-user research and freezes the permanent Performance & Perceived Latency Budget; this changes no G01 runtime scope and requires no GTK benchmark yet.

### G02 — History / Editor Transaction / Savepoint Session
Status: **OPEN / CONTRACT FROZEN / HEADLESS VALIDATED / FINALIZATION READY**

Port/adapt bounded history, editor transaction and single-document savepoint-aware session. Preserve monotonic non-reused state-ID dirty semantics across Undo/Redo, exact rollback, caret/selection restoration and late-save correctness. Keep the headless core completely GTK-free and write-free. G02 intentionally adds no visible complexity for Leafpad/L3afpad/Mousepad-style quick-edit users.

### G03 — Guarded Save / Save As Foundation
Status: PENDING

Port guarded writer and save service with alias/topology/race protection, atomic commit and mixed-EOL consent contract. No alternate physical writer. Performance optimization must not weaken safety or durability semantics.

### G04 — Thin GTK Editor Shell + Core File Lifecycle + First Performance Baseline
Status: PENDING

Create the first Graphium GTK shell around Gtk.TextView. Wire New/Open/Save/Save As/Quit and explicit Saved/Modified projection through G01-G03 authorities.

This is the first normal desktop candidate and the **mandatory first competitive benchmark gate**. Measure Leafpad, L3afpad, Mousepad and Graphium on the T480 using the Architecture Contract workloads. Graphium must satisfy the G04 admission ceilings before G05 feature expansion. Establish a reproducible non-root benchmark harness and record comparator versions.

### G05 — Search / Replace + Go to Line
Status: PENDING

Port/adapt pure search and line-only navigation. Find, Replace One/All, next/previous, case/whole-word and Go to Line. No regex requirement in v1. No syntax-highlighting dependency.

### G06 — View Core / Compact Status + Performance Checkpoint
Status: PENDING

Word Wrap, Line Numbers, Font, Zoom and Status Bar. Status must remain compact and useful: line/column, words/chars, encoding/EOL and Saved/Modified. Persist the user-facing view choices that materially reduce repetitive setup.

Repeat the permanent comparator benchmark and enforce the post-G04 regression budget.

### G07 — Recent / Copy / Version / Properties
Status: PENDING

Recent Files, Save a Copy, Save Version Copy and Graphium-specific Properties. W115 Research dossier is forbidden wholesale; only safety projection semantics may be extracted. Recent-file maintenance must not become startup-critical.

### G08 — Printing Closure + Startup Isolation Checkpoint
Status: PENDING

Adapt Calamus PrintRuntime for Graphium Print and Print Preview; add new Page Setup / PrintSettings authority. Freeze pagination/margins from Graphium requirements, not the old fixed-lines-per-page constant.

Printing is a maturity feature for the target audience, but its subsystem must remain lazy enough that a user who merely opens a text file does not pay a significant startup cost. Repeat the relevant performance checkpoint.

### G09 — Basic Text Transformations
Status: PENDING

Uppercase, Lowercase, Title Case, Duplicate Line/Selection, Move Lines, Trim Trailing Spaces, Remove Extra Spaces, Join Lines and Reflow Paragraph. Selective pure extraction only. No macro or extensibility framework.

### G10 — Preferences / Appearance / Desktop Polish + Performance Checkpoint
Status: PENDING

Small settings schema, System/Light/Dark, font/wrap/line-number/status persistence, tab-width/spaces-tabs policy, optional DnD open and window geometry. No Calamus configuration compatibility layer.

Re-measure startup/open latency and RSS. Preference loading and appearance initialization must remain bounded.

### G11 — Live External-File Safety + Performance Checkpoint
Status: PENDING

New observation-only live monitor for changed/deleted/replaced file states. Integrate decisions through the existing document session and guarded writer; no second file authority.

This is a principal Graphium differentiator for Leafpad/L3afpad/Mousepad quick-edit users. Verify that monitoring does not create an unacceptable startup, CPU-wake or idle-memory regression.

### G12 — V1 Product Closure / Competitive Qualification
Status: PENDING

User Guide, Keyboard Shortcuts, About, menu/scope audit, end-to-end regression, True-GTK closure and packaging readiness. Confirm every v1 MUST is present and every rejected cluster remains absent.

Mandatory final competitive qualification:

- benchmark Graphium against Leafpad, L3afpad and Mousepad on the T480;
- evaluate Architecture Contract G12 targets;
- publish median/p90 latency and RSS receipt;
- confirm safety has not been disabled or bypassed for benchmark runs;
- do not claim "fast" if the competitive target is materially missed without an explicit user-authorized rebaseline.

### G13 — Offline Spellcheck (Post-v1 Optional)
Status: BACKLOG / NOT PART OF V1 CLOSURE

Evaluate selective port of the existing offline Hunspell subsystem only if it remains bounded. It must load lazily and must not damage the v1 performance budget.

## Target-user findings routed into roadmap

### Leafpad / L3afpad migration target

Preserve:
- immediate startup and one-file/one-window mental model;
- very small visible command surface;
- basic plain-text focus.

Improve without bloat:
- strong external-change and save safety;
- persistent wrap/font/view preferences;
- character/word count;
- modern System/Light/Dark appearance;
- mature print workflow;
- explicit encoding/EOL state;
- safe copy/version operations.

### Mousepad migration target

Target the **quick-edit** user who values speed and simplicity. Do not chase users whose reason for choosing Mousepad is tabs, syntax highlighting or code-editor behavior. Those are intentionally outside Graphium v1.

## Routing rules

1. Serial Gxx only.
2. Feature creep is not admitted by moving items into an earlier Gxx without updating this canonical roadmap.
3. The three-document canonical cap is permanent.
4. Evidence, probes, benchmark receipts, matrices and release receipts are non-canonical and are summarized into the MO.
5. Graphium and Calamus evolve independently after extraction.
6. From G04 onward, comparator benchmarks against Leafpad/L3afpad/Mousepad are permanent closure evidence.
7. A performance regression blocker is treated like any other gate failure: diagnose before adding further product scope.
