# Graphium — Canonical Roadmap

Canonical document 2 of 3.
Initial freeze: 2026-08-13 — G00.

## Serial roadmap

### G00 — Architecture Bootstrap / Technology & Boundary Contract
Status: **FROZEN / HEADLESS VERIFIED / AUTHORIZED AS INITIAL CANONICAL REPOSITORY BASELINE**

Freeze product identity, Python/GTK technology, package boundaries, XDG isolation, one-document/one-writer authority rules, W116 selective-extraction policy, canonical-document cap and architectural gates. No feature implementation and no desktop attempt.

### G01 — Document Identity / Load / Serialize Foundation
Status: PENDING

Extract/adapt W116 document identity, stable loader and serializer into Graphium namespace. Freeze general-purpose filename/encoding/BOM/EOL semantics. Headless only unless a GTK need is discovered and justified.

### G02 — History / Editor Transaction / Savepoint Session
Status: PENDING

Port history, editor transaction and single-document savepoint-aware session. Preserve state-ID dirty semantics across Undo/Redo.

### G03 — Guarded Save / Save As Foundation
Status: PENDING

Port guarded writer and save service with alias/topology/race protection, atomic commit and mixed-EOL consent contract. No alternate physical writer.

### G04 — Thin GTK Editor Shell + Core File Lifecycle
Status: PENDING

Create first Graphium GTK shell around Gtk.TextView. Wire New/Open/Save/Save As/Quit and explicit Saved/Modified projection through G01-G03 authorities. First normal desktop candidate belongs here, not G00.

### G05 — Search / Replace + Go to Line
Status: PENDING

Port/adapt pure search and line-only navigation. Find, Replace One/All, next/previous, case/whole-word and Go to Line.

### G06 — View Core / Status
Status: PENDING

Word Wrap, Line Numbers, Font, Zoom, Status Bar with line/column, words/chars, encoding/EOL and Saved/Modified. Zoom is new Graphium view-only state.

### G07 — Recent / Copy / Version / Properties
Status: PENDING

Recent Files, Save a Copy, Save Version Copy and Graphium-specific Properties. W115 Research dossier is forbidden wholesale; only safety projection semantics may be extracted.

### G08 — Printing Closure
Status: PENDING

Adapt Calamus PrintRuntime for Graphium Print and Print Preview; add new Page Setup / PrintSettings authority. Freeze pagination/margins from Graphium requirements, not the old fixed-lines-per-page constant.

### G09 — Basic Text Transformations
Status: PENDING

Uppercase, Lowercase, Title Case, Duplicate Line/Selection, Move Lines, Trim Trailing Spaces, Remove Extra Spaces, Join Lines and Reflow Paragraph. Selective pure extraction only.

### G10 — Preferences / Appearance / Desktop Polish
Status: PENDING

Small settings schema, System/Light/Dark, editor preferences, optional DnD open and window geometry. No Calamus configuration compatibility layer.

### G11 — Live External-File Safety
Status: PENDING

New observation-only live monitor for changed/deleted/replaced file states. Integrate decisions through the existing document session and guarded writer; no second file authority.

### G12 — V1 Product Closure
Status: PENDING

User Guide, Keyboard Shortcuts, About, menu/scope audit, end-to-end regression, True-GTK closure and packaging readiness. Confirm every v1 MUST is present and every rejected cluster remains absent.

### G13 — Offline Spellcheck (Post-v1 Optional)
Status: BACKLOG / NOT PART OF V1 CLOSURE

Evaluate selective port of the existing offline Hunspell subsystem only if it remains bounded and does not delay or complicate v1 closure.

## Routing rules

1. Serial Gxx only.
2. Feature creep is not admitted by moving items into an earlier Gxx without updating this canonical roadmap.
3. The three-document canonical cap is permanent.
4. Evidence, probes, matrices and receipts are non-canonical and are summarized into the MO.
5. Graphium and Calamus evolve independently after extraction.
