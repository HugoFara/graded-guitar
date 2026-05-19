# 0017 — LilyPond GitHub-repo diversification spike: closed

- **Status:** Accepted
- **Date:** 2026-05-19

## Context

An external review on 2026-05-19 re-raised corpus diversification
after ADR 0014 closed the previous round. Three small CC-licensed
classical-guitar LilyPond repos were proposed as cheap top-ups,
on the premise that the patched python-ly converter from
ADR [0007](./0007-mutopia-source.md) would handle them as it does
Mutopia files:

- [yawnoc/guitar](https://github.com/yawnoc/guitar) (CC0) — proposal
  flagged as "excellent quality".
- [davesque/classical-guitar-lessons](https://github.com/davesque/classical-guitar-lessons)
  (MIT) — pedagogical repository.
- [savarese.org/music](https://www.savarese.org/music/) — classical-
  guitar transcriptions said to be in LilyPond source.

The hope was 19th-century repertoire (Tárrega, Sor, Coste, Mertz,
Llobet) at low engineering cost — the gaps ADR 0014 flagged as
"target these next" but never sourced.

The spike was: clone the repos, run every .ly through
`scripts/m1_lilypond.convert_lilypond`, count clean conversions,
decide. Probe artifacts under
[`experiments/lilypond_spike/`](../experiments/lilypond_spike/).

## Findings

**Aggregate yield: 3/16 clean conversions, of which only 1
(Paganini Romanze, in davesque) is repertoire-shape.** The rest
are pedagogical exercises or off-shape (quartet parts, duration
demos).

The three sources failed for three distinct reasons:

- **yawnoc/guitar (0/13 clean).** Files parse to valid MusicXML
  but with empty `<part-list>` / zero notes — caught downstream by
  `NO_NOTES`. The repo uses a 320-line `conway.ily` helper full of
  custom Scheme functions (`globalSettings`, `barNumberCheck`,
  `triplet`, custom `\override`s) that python-ly silently no-ops on.
  This is idiomatic LilyPond *for humans typesetting guitar music* —
  exactly the dialect python-ly doesn't speak. The Mutopia files
  python-ly handles use only vanilla syntax.
- **davesque/classical-guitar-lessons (3/3 clean, 1 repertoire).**
  Converter works fine. Yield: one Paganini Romanze. The other two
  files are scale and position-shift exercises, not pieces for the
  spec §3 audience.
- **savarese.org/music (0/n).** On close inspection,
  `lilypond.html` is an article about the site owner's typesetting
  workflow, not a directory of downloads. The arrangement index
  lists 28 pieces but every per-piece page links only to PDFs
  under `/downloads/sheetmusic/`. The site footer reads
  *"Copyright © 2022 D. F. Savarese"* — transcriptions, not source
  files, not redistributable.

For completeness, the proposal also mentioned
[musetrainer/library](https://github.com/musetrainer/library) (no
.ly files, 69 piano-arrangement .mxl files — off-genre).

## Decision

1. **Do not ingest from yawnoc, davesque, savarese, or
   musetrainer/library.** A 1-piece yield does not justify a new
   ADR + a new discover script + per-source license review.

2. **Do not invest in a real-LilyPond conversion path
   (shelling out to the `lilypond` binary's MusicXML backend) on
   the strength of this spike.** That would be the only way to
   recover yawnoc's 5 pieces, and it would add a 250 MB system
   dependency to ingest. We'd want a much larger LilyPond-repo
   pipeline first to justify it.

3. **Close the "small LilyPond GitHub repos" lead at ADR level.**
   The reproducible-scraping diversification frontier (per
   ADR 0014) remains: PDMX is in (ADR 0015), the next material
   lever is ClassClef (ADR 0015 follow-up #2) or OMR (also
   ADR 0015).

## Consequences

**Commits us to:**

- No further casual-LilyPond-repo probes without first having a
  concrete signal of a larger yield (e.g. a single repo with
  100+ vanilla-LilyPond classical-guitar files). The bar is higher
  after this spike.
- ClassClef outreach as the next corpus action when corpus
  diversification re-enters scope. ADR 0015 already records the
  ask.

**Costs:**

- The 19th-century-canon gap (Coste, Mertz, Llobet, Barrios,
  more Carcassi) remains an open weakness in the corpus. ADR 0014's
  framing applies: "important for completeness but not for the
  MVP-user moment" — the spec §3 audience is mostly served by
  what we have.

**Forecloses:**

- Nothing structural. If a vanilla-LilyPond classical-guitar repo
  surfaces later, it slots into the existing Mutopia path
  (`m1_lilypond.py` is source-agnostic; a discover script is the
  only new code needed).

**Follow-ups:**

- None. The probe artifacts stay under
  `experiments/lilypond_spike/` so a future probe can re-run the
  numbers if python-ly improves or a real-LilyPond shell-out path
  is reconsidered.
