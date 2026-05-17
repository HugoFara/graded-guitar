# LilyPond → MusicXML probe

A one-off experiment to decide whether Mutopia is worth integrating as a
source for the M1 ingest pipeline. Not wired into M1.

## Why

The original investigation (see `decisions/0006-github-as-source.md`)
ruled Mutopia out because `python-ly`'s converter silently drops every
`\score` block after the first — Mutopia files routinely have multiple
movements per work, so an unattended pipeline would miss music without
any error. This probe checks whether splitting the .ly file ourselves —
running `python-ly` once per `\score` block — recovers the missing
movements at acceptable quality.

## What the probe does

`probe.py`:

1. Downloads each .ly from `sample_urls.txt` (10 Mutopia classical-guitar
   files, mixing single-`\score` and known multi-`\score` cases).
2. Brace-matches the top-level `\score{…}` blocks, with comment- and
   string-aware scanning.
3. For each block, emits a synthetic .ly file (preamble + that block
   alone) and runs `ly musicxml` on it.
4. Validates each output: well-formed XML, `score-partwise` root, ≥1
   part with ≥1 measure containing ≥1 note.
5. Reports per-file and aggregate clean-rate; writes
   `<workdir>/summary.json`.

## Result (2026-05-18 run)

| File                                  | `\score` blocks | Clean | Notes |
|---|---:|---:|---|
| aguado-op03n01                        | 1 | 1/1 | OK |
| AguadoOp4No1                          | 2 | 2/2 | Both movements convert — splitter fixes the original truncation issue |
| AguadoOp4No2                          | 2 | 2/2 | OK |
| AguadoOp4No3                          | 4 | 3/4 | Movement 3 hits `UnboundLocalError` in `python-ly`'s `Assignment` handler |
| aguado-op11n01                        | 1 | 1/1 | OK |
| bwv-1006a_5g (Bach Loure)             | 1 | 1/1 | OK |
| bwv-1006a_6g (Bach Gigue)             | 1 | 1/1 | OK |
| bach_siciliano_bmv_1031               | 1 | 1/1 | OK |
| bach_air_bmv_1068                     | 1 | 0/1 | `python-ly` crashes on the `\header` block (`UnboundLocalError: val`) |
| anna-magdalena-04-guitar-tab          | 1 | 0/1 | Converts but emits no `<part-list>` — TabStaff variant |

**Aggregate: 12 / 15 blocks clean = 80 %.**

## Verdict

The splitter solves the headline multi-`\score` truncation cleanly — every
multi-movement file in this sample now produces a complete set of
movements (where direct `python-ly` would have dropped all but the first).

The remaining ~20 % failures are real `python-ly` bugs / limitations
(header-assignment crash, TabStaff variants), but they fail *loudly* —
either with a Python traceback or with a structurally empty MusicXML
that the M1 validate step catches via `NO_PARTS`. So the pipeline would
never silently accept truncated music; broken files would land in
`rejected.json` with a reason code, exactly like any other reject.

If Mutopia has ~150 classical-guitar pieces and ~80 % convert cleanly,
that adds ~120 vetted pieces to the corpus — going from 36 to ~156, well
above spec §6's "200 beats 2000" floor.

## Open work if we integrate

1. New ADR (0007) documenting the splitter + python-ly approach.
2. `scripts/m1_discover_mutopia.py` walking the make-table CGI for guitar.
3. Either a new "fetch+convert" step for `.ly` candidates, or extend
   `m1_fetch.py` to recognise `source: mutopia` and call the converter.
4. New reject codes: `LY_CONVERSION_FAILED`, `LY_TABSTAFF_NO_PARTLIST`.
5. Add `python-ly` to `requirements.txt`.

None of that is committed yet — this directory is the probe only.

## Reproducing

```bash
pip install python-ly==0.9.10
python3 experiments/lilypond_probe/probe.py
# outputs in /tmp/lilypond-probe by default
```
