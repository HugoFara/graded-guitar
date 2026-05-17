# 0007 — Mutopia as a secondary source via patched python-ly

- **Status:** Accepted
- **Date:** 2026-05-18

## Context

ADR [0006](./0006-github-as-source.md) ruled Mutopia out: their files
are LilyPond-only, and the one pip-installable LilyPond → MusicXML
converter (`python-ly` 0.9.10, from the Frescobaldi project) silently
dropped every `\score` block after the first — meaning multi-movement
Mutopia works would lose music without surfacing an error. That's
disqualifying for a corpus pipeline.

A subsequent probe (`experiments/lilypond_probe/`) showed that
pre-splitting top-level `\score{…}` blocks and converting each
separately bypasses the truncation. A second pass with `python-ly`
called as a library (not via the `ly` CLI) plus two targeted
monkey-patches fixes two other recurrent crashes on Mutopia files:

- `ParseSource.Assignment` — fails to initialise `val` for value types
  outside its known set (Markup / String / Scheme / UserCommand),
  raising `UnboundLocalError` that kills the whole conversion. Patch:
  catch and skip the offending assignment.
- `Bar.inject_voice` — indexes `new_voice.obj_list[0]` without checking
  emptiness, raising `IndexError` on empty-voice placeholders. Patch:
  no-op when the voice has no objects; swallow IndexError otherwise.

After the patches + the `\score` splitter + a couple of fallbacks
(strip `\header` and retry; substitute `TabStaff` → `Staff`; strip the
`TabStaff` block entirely), the 10-piece probe yields **14/15 blocks
(93%) of clean MusicXML**, up from 12/15 (80%) before patches.

Mutopia hosts roughly 150 classical-guitar pieces; at this conversion
rate we expect ~120 to land cleanly. Combined with the existing
GitHub-based corpus (43 accepted of which ~36 are real classical
guitar), Mutopia roughly quadruples our supply — close enough to spec
§6's "200 beats 2000" floor that it stops being a credible concern.

## Decision

Add Mutopia as a secondary discovery source. Concretely:

- **`scripts/m1_lilypond.py`** — wrapper module. Imports `python-ly`
  as a library, applies the two monkey-patches at import time, runs
  `convert_lilypond(ly_text)`, returns one `MovementResult` per
  `\score` block. Each movement is either an `ok` MusicXML byte string
  or a structured failure with reason code.
- **`scripts/m1_discover_mutopia.py`** — walks
  `cgibin/make-table.cgi?Instrument=Guitar` paginated. One candidate
  per .ly URL. `candidate_id = mutopia:<path_no_ext>`, `format_label =
  "lilypond"`.
- **`scripts/m1_fetch.py`** — dispatches on `source` per candidate. For
  `source == "mutopia"`, downloads the .ly, calls the wrapper, and
  writes one `corpus/raw/<sha256>.musicxml` per produced movement plus
  a fetch_log entry keyed `<parent_id>#movementNN`. The parent
  candidate_id gets a `status: container` entry so re-runs skip it.
- **`scripts/m1_validate.py`** — when looking up candidate metadata for
  `...#movementNN`-style ids, falls back to the parent (strip suffix).
  Adds `LY_CONVERSION_FAILED` to the reject-code enum so Mutopia
  conversion failures are reported distinctly from network failures.

### Failure modes we accept

Even with the patches, ~7% of `\score` blocks won't convert cleanly.
The known unrecoverable case is dual-staff files where the LilyPond
source carries both notation (`Staff`) and tablature (`TabStaff`)
contexts in a `StaffGroup` (e.g. Mutopia's Anna Magdalena guitar-tab
edition). python-ly emits no part-list in that configuration and our
TabStaff fallbacks don't break the deadlock. These end up in
`rejected.json` with `LY_CONVERSION_FAILED` and `NO_PARTS`, exactly
like any other reject — visible, not silent.

### What this ADR does NOT do

- It does **not** make python-ly a hard runtime requirement of the
  whole pipeline. The IMSLP and GitHub discovery paths don't need it;
  only Mutopia fetches do. The wrapper module is imported lazily in
  `m1_fetch.py` when a Mutopia candidate is encountered.
- It does **not** upstream the patches to python-ly. The monkey-patch
  approach keeps us isolated from upstream — we don't depend on bug
  fixes that may never be merged. If we revisit later, a PR to
  python-ly is a contained one-day task.
- It does **not** attempt LilyPond → MusicXML for non-Mutopia sources.
  This ADR is specifically about Mutopia integration; other LilyPond
  sources (Wikifonia mirrors, etc.) would need their own ADR even
  though they could reuse `m1_lilypond.py`.

## License handling

Mutopia files declare their license in the `\header` block as
`mutopiacopyright` — typically "Public Domain", "Creative Commons
Attribution-ShareAlike 3.0 Unported", or similar. The wrapper extracts
header metadata; we surface `mutopiacopyright` into the manifest's
`license` field per piece. SPDX mapping is best-effort (we tag
"Public Domain" as `CC-PDM-1.0` only when the string matches; else
`unknown`).

## Consequences

- `python-ly==0.9.10` is added to `requirements.txt`. Pinned; the
  monkey-patches reference specific internal methods and would need
  reviewing if we upgrade.
- M1 conversion is now non-deterministic in one narrow sense: python-ly
  emits warnings to stderr and the conversion order matters for some
  edge cases. Across two consecutive runs, output bytes should be
  identical; if they aren't, we have a `python-ly` ordering bug to
  surface as a real issue.
- The corpus grows by ~120 pieces. The §7 M1 "≥40 pieces" bar set in
  the previous round becomes immediately exceeded; the actual number
  is reported in `corpus/report.md`.
- Mutopia files come with rich `\header` metadata (composer, opus,
  date, copyright) that we now capture. This improves manifest quality
  vs. the GitHub-sourced pieces where most repos lack license metadata.
