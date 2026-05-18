# 0015 — OMR feasibility spike

- **Status:** Accepted
- **Date:** 2026-05-18

## Context

ADR 0014 closed by recording that the free-licensed classical-guitar
MusicXML ceiling without OMR is ~1,000-1,500 pieces, with the
existing Renaissance/Baroque/Classical-pedagogical era skew.

The reviewer (external review, 2026-05-18) flagged OMR as priority
#4: *"Confront the OMR question now, not later... Start a research
spike now — evaluate `oemer`, `homr`, the new vision-LM approaches —
so you have a credible answer to 'how do you get to 10K pieces' by
the time anyone with funding or scale interests asks. This doesn't
mean building OMR; it means knowing what building OMR would cost."*

This ADR is that gauge. The output is a recommendation, not a
commitment to build.

## The 2026 OMR landscape

### Open-source OMR tools

| Tool | License | Maturity | Output | Active | Notes |
|---|---|---|---|---|---|
| **Audiveris** | AGPL-3.0 | Production-grade, ~10+ years | MusicXML 4.0 | Yes; ~6-12mo release cadence | GUI-first; review/correction baked in. The honest workhorse. |
| **oemer** | MIT | Research-quality | MusicXML | Last release Nov 2024 | Single-image PNG/JPG; trained on piano data; no guitar-specific results published. |
| **homr** | AGPL-3.0 | Active research project | MusicXML | Updated Apr 2026 | UNet+transformer; "focuses on pitch and rhythm; neglects dynamics, articulation, double sharps/flats." Successor to oemer. |
| **LEGATO** | MIT (code); model license unspecified | Research preprint, Jun 2025 | ABC notation (not MusicXML) | New | Vision-LM (frozen Llama 3.2-11B-Vision encoder + transformer decoder). State-of-the-art per benchmarks; ships two HuggingFace checkpoints. |

Commercial options exist (SmartScore, PhotoScore, Soundslice's hosted
service) but per-piece licensing makes them unattractive for bulk
ingest of public-domain repertoire.

### Accuracy reality check

The recent benchmarks are sobering for "process 1,000 IMSLP PDFs
unsupervised":

- **LEGATO** (state-of-the-art per its own paper): **52.1%** TEDn on
  the OpenScore String Quartets benchmark, **29.7%** on IMSLP Piano
  Scores. (TEDn = tree-edit-distance, normalized; higher is better.)
  Significantly better than prior open-source baselines (SMT++ at
  97.9% / 97.7% is closed-source). Read: open-source OMR is improving
  fast but is still far from a "press the button, get MusicXML" black
  box for IMSLP-quality scans.
- **Audiveris** does not publish accuracy numbers but the project's
  own documentation states: *"the accuracy of the OMR engine is still
  far from perfection, the Audiveris application provides a graphical
  user interface specifically focused on quick verification and
  manual correction of the OMR outputs."*
- **homr** documentation: *"errors exist but overall structure
  remains accurate."*

### Classical-guitar-specific risks

None of these tools publishes evaluation results on classical-guitar
notation specifically. Guitar adds three failure modes that the
piano/string-quartet benchmarks don't stress:

- **Single staff with polyphonic voices** — guitar music routinely
  voices 3-4 independent lines on one staff with stem-up / stem-down
  conventions. OMR systems trained on piano (two staves, one voice
  each in most beginner repertoire) may collapse voices.
- **Tab notation alongside standard notation** — common in
  pedagogical editions. None of the tools handle tab + notation
  cleanly; outputs would need post-filtering.
- **Fingering / position markings** — left-hand digits in circles,
  right-hand letters, barré indicators. Universally lost; this is
  not a deal-breaker (we render notation, not pedagogy markup) but
  noted.

### Vision-language models (GPT-5, Claude 4, Gemini)

Recent papers benchmark VLMs on OCR-like tasks; none yet on OMR at
production-grade quality. The frontier-model OMR demos online are
single-bar parlour tricks, not corpus-scale tools. Cost would also
dominate: at $0.01-$0.10 per page on commercial APIs, 5,000 IMSLP
PDFs averaging 6 pages each = $300-$3,000. Not blocking, but not
free either. Defer until the open-source path is exhausted.

## A non-OMR finding worth flagging first

While researching OMR, the spike uncovered a path that may resolve
the corpus question **without invoking OMR at all**:

**PDMX** — *Public Domain MusicXML Dataset*
([Long, Liu et al., 2024](https://arxiv.org/abs/2409.10831);
[Zenodo record 15571083](https://zenodo.org/records/15571083);
[GitHub pnlong/PDMX](https://github.com/pnlong/PDMX)).

- **250,000+ MusicXML scores** scraped from MuseScore's public-domain
  pool, the largest copyright-free symbolic-music corpus available.
- **License: CC-BY 4.0** (per the Zenodo record). Compatible with
  our MIT license under attribution.
- Ships as a 35.9 GB tarball on Zenodo. The MusicXML-only subset
  (`mxl.tar.gz`) is **1.9 GB** — practical to download today.
- **Per-piece metadata includes a `tracks` column** identifying
  instrument/part names. This means filtering for classical-guitar
  pieces is a CSV-grep, not an inference run.
- Includes a `no_license_conflict` subset (222,856 songs) which the
  authors recommend over the full set.

**If PDMX contains even 2,000 classical-guitar pieces under the
"no_license_conflict" subset, that single source more than triples
our corpus and bypasses every concern in this ADR.** ADR 0014's
audit missed PDMX because the prior probe was looking at archives,
not academic datasets.

A second potential source surfaced too: **ClassClef** — ~5,914
classical-guitar tabs in PDF + GuitarPro format. The GAPS dataset
authors (Yang & Steidl 2024, arXiv:2408.08653) obtained explicit
permission from the site owner. We'd need the same. GuitarPro files
can be converted to MusicXML by MuseScore CLI or alphaTab — no OMR
needed, since GuitarPro is already structured.

## Decision

1. **Defer building an OMR pipeline.** OMR is *credible enough* as
   an eventual scaling path but not the right tool for this session.
   Two real costs would slow the project disproportionately:
   - **Review workflow.** Even at 80% accuracy (optimistic for
     LEGATO/homr/Audiveris on classical-guitar PDFs), every output
     needs human eyeballs before it enters the corpus. The advisor
     review backlog is already the bottleneck (ADR 0010, 0013);
     adding an OMR-review step compounds it.
   - **GPU infra for research-grade models.** LEGATO needs a GPU
     for tractable inference. We're a static-Pages project with no
     server; running OMR in our pipeline today means a developer's
     machine, which is fine for one-off batches but hostile to
     reproducibility.

2. **Pursue PDMX as the next corpus expansion.** This is a
   one-session probe with a clear go/no-go criterion: download
   `mxl.tar.gz` + `metadata.tar.gz` from Zenodo, filter the `tracks`
   column for "Classical Guitar" / "Guitar" / equivalent labels,
   count what falls out of the `no_license_conflict` subset, and
   spot-check 20 random hits for actual classical-guitar repertoire
   (vs. fingerstyle pop / tabs / chord charts, which MuseScore also
   hosts). If we get ≥1,000 classical-guitar pieces, we ingest the
   subset via a new `m1_discover_pdmx.py` and ADR 0014's frontier
   moves materially.

3. **Pursue ClassClef as the second candidate.** Smaller potential
   (5,914 pieces, of which some fraction is duplicated with Mutopia
   / Guitar Loot), needs site-owner permission, but the GAPS
   precedent shows it's obtainable. GuitarPro → MusicXML via
   MuseScore CLI is well-trodden and yields cleaner files than OMR.

4. **Keep OMR on a watch list, not a backlog.** Re-evaluate when
   one of three things happens:
   - PDMX + ClassClef + Mutopia + Guitar Loot together still leave a
     visible gap in modern repertoire (likely; copyright keeps most
     20th-century classical guitar out of *every* free source).
   - A new open-source OMR model lands that publishes credible
     classical-guitar evaluation (single-staff polyphonic, fingering
     intact). LEGATO's authors or another group will likely do this
     within 12-24 months.
   - We have advisor/beta-tester capacity to operate an OMR review
     queue at scale, which is the actual bottleneck.

5. **If OMR becomes the right call later, the recommended starting
   point is Audiveris.** Reasoning: production-grade maturity,
   MusicXML 4.0 output (matches our canonical format), GUI-baked
   review workflow that doesn't require us to design one, AGPL is a
   non-issue for ingest-time use (we don't redistribute Audiveris;
   we redistribute its MusicXML outputs). LEGATO/homr are
   research-grade and worth re-probing after they ship 1.0
   releases.

## Consequences

**Commits us to:**

- Running the PDMX probe as the next corpus action. Concretely:
  download from Zenodo, write a one-screen `scripts/m1_discover_pdmx.py`
  that reads `PDMX.csv` + filters by tracks column, run validate,
  see what survives. Expected outcome: a number we can act on
  inside a week.
- Maintaining the existing source pipeline (Guitar Loot, Mutopia,
  GitHub) unchanged. PDMX is additive.

**Costs:**

- Two more probe sessions (PDMX, then ClassClef) before we know if
  the OMR question is genuinely on the critical path or genuinely
  deferrable. That's the right cost — finding out PDMX has 5,000
  classical-guitar pieces would save us a quarter of OMR-tool
  research.

**Forecloses:**

- Nothing structural. The ingest pipeline (ADR 0005) handles new
  MusicXML sources additively. An OMR source would also be additive
  when we add it.

**Follow-ups (in order):**

1. **PDMX probe.** ~1 day. Output: `scripts/m1_discover_pdmx.py`
   + the count of classical-guitar pieces, both before and after the
   `no_license_conflict` filter, with 20-piece spot-check.
2. **ClassClef outreach.** Email the site owner asking permission
   to ingest in the same terms GAPS got. Async; while we wait, do
   the PDMX work.
3. **GAPS dataset evaluation.** The 300-piece GAPS corpus
   (arXiv:2408.08653) is small but high-quality and explicitly
   classical-guitar. Even if license precludes redistribution, it's
   useful as a test set for *our* future grading model — a small
   advisor-quality validation set we didn't have before.
4. **Re-open this ADR if any of the three watch-list triggers fires.**
