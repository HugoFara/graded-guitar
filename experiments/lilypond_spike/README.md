# LilyPond GitHub-repo diversification spike

A one-day spike (2026-05-19) to test whether three small CC-licensed
classical-guitar LilyPond repos on GitHub / personal sites could
materially diversify the corpus — specifically by adding 19th-century
classical-guitar pieces the proposal flagged as the canon gap (Coste,
Mertz, Llobet, Barrios, more Carcassi).

Not wired into M1. Outcome recorded in ADR
[0017](../../decisions/0017-lilypond-spike-closed.md).

## Sources probed

| Source | License | .ly files | Classical-guitar repertoire? |
|---|---|---:|---|
| [yawnoc/guitar](https://github.com/yawnoc/guitar) | CC0 | 13 | 5 solo pieces (Lágrima, Sor op 35/13, Dowland Fantasia 7, El Vito, Recuerdos — 2 timing variants), 1 quartet (6 part-files), 1 set of duration demos |
| [davesque/classical-guitar-lessons](https://github.com/davesque/classical-guitar-lessons) | MIT | 3 | 1 piece (Paganini Romanze), 2 pedagogical exercises |
| [savarese.org/music](https://www.savarese.org/music/arrangements.html) | "Copyright Savarese" on transcriptions; no .ly downloads — only PDF | 0 | 28 pieces; PDF-only |
| [musetrainer/library](https://github.com/musetrainer/library) | (.mxl, n/a) | 0 | 0 (69 piano arrangements, off-genre) |

## What the probe does

`probe.py` runs every .ly through `scripts/m1_lilypond.convert_lilypond`
(the patched python-ly used by Mutopia ingest, ADR 0007), inlining
`\include` files so the converter sees self-contained sources.

## Result (2026-05-19 run)

```
yawnoc/.durations/recuerdos-accurate   blocks=1 clean=0/1  NO_NOTES
yawnoc/.durations/recuerdos-readable   blocks=1 clean=0/1  NO_NOTES
yawnoc/dowland-fantasia-7              blocks=2 clean=0/2  NO_NOTES x2
yawnoc/el-vito                         blocks=1 clean=0/1  NO_NOTES
yawnoc/lagrima                         blocks=1 clean=0/1  NO_NOTES
yawnoc/sor-c-major-35-13               blocks=2 clean=0/2  NO_NOTES x2
yawnoc/tetris-quartet (×6 part-files)  blocks=6 clean=0/6  OUT_OF_GUITAR_RANGE_LOW x5, NO_PARTS x1
davesque/e-phrygian                    blocks=1 clean=1/1  exercise
davesque/romanze                       blocks=1 clean=1/1  Paganini repertoire
davesque/shifting                      blocks=1 clean=1/1  exercise

Aggregate: 3 / 16 clean (19%)
Repertoire-shape ingestable: 1 piece (davesque/romanze)
```

## Why yawnoc collapses

Every yawnoc piece parses to MusicXML but with **zero notes**. The
files rely on `conway.ily`, a 320-line helper with custom Scheme
functions (`globalSettings`, `colourOne`, `triplet`, `barNumberCheck`)
and aggressive `\override` / `\set` calls. python-ly emits dozens of
"MarkupCommand not implemented", "SchemeList not implemented",
"Keyword not implemented" warnings per file and produces an empty
`<part-list>` — picked up downstream by `NO_NOTES`.

The Mutopia files python-ly handles correctly use only vanilla
LilyPond syntax. Yawnoc is idiomatic LilyPond *for humans typesetting
guitar music*, which is exactly the dialect python-ly doesn't speak.
Fixing this would require shelling out to the real `lilypond`
binary's MusicXML backend (not pip-installable, requires the full
LilyPond install, ~250 MB) — out of proportion for a 5-piece yield.

## Why davesque under-yields

Two of three .ly files are pedagogical exercises (`e-phrygian` is
a scale, `shifting` is a position-shift drill) — neither is
classical-guitar repertoire for spec §3's audience. Only `romanze`
is a real piece, and it's a single Paganini arrangement that's
already represented in the public-domain Mutopia corpus.

## Savarese: dead end on close inspection

The `lilypond.html` page on savarese.org is an *article* about how
the site owner uses LilyPond, not a directory of .ly downloads. The
arrangement index (`/music/arrangements.html`) lists 28 pieces
including Lágrima, La Catedral, Adelita, but every per-piece page
links only to PDFs under `/downloads/sheetmusic/`. The site footer
reads "Copyright © 2022 D. F. Savarese" — these are his
transcriptions, not redistributable source files.

## Verdict

LilyPond-on-GitHub as a diversification path is closed under the
current python-ly-only converter. The proposal's premise
(*"Your existing python-ly Mutopia converter already gets you from
LilyPond to MusicXML"*) holds for vanilla LilyPond but not for the
human-typeset classical-guitar dialect used in the highest-quality
repo on the list.

Conclusion in ADR 0017.

## Reproducing

```bash
cd /tmp && rm -rf lilypond_spike && mkdir lilypond_spike && cd lilypond_spike
git clone --depth=1 https://github.com/yawnoc/guitar.git yawnoc
git clone --depth=1 https://github.com/davesque/classical-guitar-lessons.git davesque
cd <repo>
.venv/bin/python experiments/lilypond_spike/probe.py
```
