# 0008 — Guitar Loot as a third source with curator-assigned grades

- **Status:** Accepted
- **Date:** 2026-05-18

## Context

ADR [0006](./0006-github-as-source.md) settled GitHub code-search as the
primary discovery source after IMSLP came back empty. ADR
[0007](./0007-mutopia-source.md) added Mutopia via patched python-ly,
roughly tripling the corpus to 374 accepted solo pieces.

A probe of <https://www.guitarloot.org.uk/> —
`experiments/guitarloot_probe/` — found **529 MusicXML files** across
41 composer/category pages, with direct `.mxl` URLs in a stable
path layout (`/Scores/{Category}/{Composer}/{piece}.mxl`). Each file is
a Sibelius 18.4 export with populated `<work-title>`, `<creator
type="composer">` (including dates), `<creator type="lyricist">` for
the arranger, and a `<rights>` block.

Two properties make this source qualitatively different from IMSLP /
GitHub / Mutopia:

1. **87% of files (459/529) carry a difficulty grade in the page text**
   on the Delcamp 1-10 scale. Distribution skews mid-range
   (G5: 44, G6: 109, G7: 169, G8: 118, with tails at G3, G4, G9). This
   is hand-assigned by the site's maintainer, Eric Crouch, who is also
   the arranger. The remaining 13% ungraded are ensemble pieces
   (Guitar Duets/Trios, Lyra Viol Duets/Trios) plus a single
   .mxl-less composer page (Wilson).
2. **License is permissive with attribution.** The `<rights>` element
   reads, verbatim: *"You may freely use or adapt this arrangement
   provided you acknowledge me as its source."* That is friendlier
   than the informal "use what you like, mention this site" we
   observed at the bottom of the homepage — the per-file rights
   string is closer to CC-BY in spirit, though no SPDX identifier is
   declared.

The combination is rare: a coherent, hand-arranged, hand-graded,
permissively-licensed corpus of ~459 solo classical-guitar pieces in
clean MusicXML. The grades are particularly valuable for M2
(grading model) because they provide a labeled training signal that
otherwise requires the advisor and the syllabi to produce by hand.

Stylistic scope is narrow: Renaissance and Baroque arrangements
originally written for lute, baroque guitar, or lyra viol. That
complements rather than overlaps with Mutopia (which is heavy on
Sor/Giuliani/Aguado/Carcassi early-Romantic studies). Together the two
sources should cover Renaissance → Romantic, leaving Modern (Brouwer,
Villa-Lobos, etc.) for later work.

## Decision

Add Guitar Loot as a third discovery source.

### Scripts

- **`scripts/m1_discover_guitarloot.py`** — walks the 41
  composer/category pages enumerated in
  `experiments/guitarloot_probe/probe.py`'s `PAGES` list. For each
  `<a href="…/Foo.mxl">` it emits one candidate. `candidate_id =
  guitarloot:<relative_path_no_ext>` (e.g.
  `guitarloot:Scores/EnglishMusic/Dowland/FantasyP5GtrAS`). The
  discover script scrapes the surrounding block text for a Delcamp
  grade annotation (`grade N` / `gr N` / `(N)` / `level N`), recording
  it as `grade` (string `"1".."10"`) with `grade_source =
  "delcamp-eric-crouch"`.
- **`scripts/m1_fetch.py`** — **no source-specific branch needed.**
  The generic fetch path already handles `.mxl` (zip-magic detection,
  byte-content addressing). The mutopia branch is the special case;
  guitarloot reuses the IMSLP/GitHub code path.
- **`scripts/m1_validate.py`** — already unzips `.mxl` containers and
  reads inner `<score-partwise>`. The one change is to pass
  `grade`, `grade_source`, and `arranger` through from the candidate
  into the manifest entry, alongside the existing `license` /
  `license_spdx` fields.

### Candidate schema additions

Fields added (optional everywhere — only guitarloot populates them
today):

- `grade` — string `"1".."10"` or empty if ungraded.
- `grade_source` — opaque tag for the grading authority. Today only
  `"delcamp-eric-crouch"`. M2's grading model will write a separate
  `model_grade` field with its own `grade_source`.
- `arranger` — string from the second `<creator type="lyricist">` in
  Sibelius output, where Eric Crouch records arrangement attribution.

### Failure modes we accept

- **Ensemble pages will be auto-rejected** as `MULTIPLE_PARTS` by the
  existing validator (Guitar Duets / Trios / Lyra Viol Duets / Trios
  = ~70 pieces). This is correct per spec §5 — classical guitar
  *solo* is the focus at launch. The rejections are visible in
  `corpus/rejected.json` with reason code `MULTIPLE_PARTS`, exactly
  like any other reject.
- **Wilson page has 0 .mxl** — 17 PDFs but no MusicXML. Either the
  maintainer hasn't typeset Wilson yet or the .mxl files are pending.
  Discovery yields zero candidates from that page; no rejection
  entry is created.
- **Single-curator source.** Eric Crouch is the only contributor.
  If the site disappears, our raw files survive (content-addressed
  in `corpus/raw/`, gitignored) but `file_url`s in the manifest go
  dead. Mitigation: the per-piece bytes are content-hashed; a future
  M3+ mirror can re-host. We do **not** preemptively mirror to git
  LFS — `corpus/raw/` is gitignored to keep the repo light, and the
  spec §5 non-goals exclude us hosting redistribution-restricted
  content until the licensing story is clarified.
- **One curator's grades, not RCM/Trinity/ABRSM.** The Delcamp scale
  approximates Trinity 1-8 per the site's own
  [`/page-47/page-48/`](https://www.guitarloot.org.uk/page-47/page-48/),
  but it is not a syllabus. We store grades under
  `grade_source = "delcamp-eric-crouch"` so the advisor and the M2
  model can treat them as one input among several, not the truth.

### What this ADR does NOT do

- It does **not** alter the spec §7 M1 "≥40 pieces" bar. The bar was
  lowered to reflect empirical scarcity; we've blown past it twice
  now (GitHub, then Mutopia, now Guitar Loot) and will report the
  actual number in `corpus/report.md`.
- It does **not** make grading-data ingestion a contract. The
  grade fields are best-effort scrape output and may be wrong for
  individual pieces. The advisor's M1 spot-check should explicitly
  sample some graded entries and confirm or revise. M2's model
  trains on whatever subset the advisor signs off on.
- It does **not** introduce per-piece license filtering. The
  `<rights>` text is captured verbatim into `manifest.json`;
  redistribution decisions are an M3/M7 concern per spec §6.
- It does **not** generalize to "other websites with curated MXL".
  Adding another such source would need its own ADR and discovery
  script. The probe script is reusable for any site with predictable
  per-composer page layouts.

## Consequences

- The corpus grows by an expected ~459 solo pieces (529 MusicXML
  files minus ~70 ensemble rejections minus a handful of
  metadata-clean rejections). Combined with current 374, expect
  roughly **800 accepted pieces**, comfortably exceeding the
  original spec §7 M1 floor of 500 *and* the lowered floor of 40.
- The manifest gains a hand-graded subset usable as M2 training
  data. That collapses one M2 dependency: we no longer need the
  syllabi `pieces` arrays populated *before* M2 starts to have any
  labeled data — though the syllabi remain the canonical reference
  for grade calibration (ADR 0004 hard gate stands).
- The `<rights>` text we capture is closer to CC-BY than the
  original site-wide blurb suggested. SPDX mapping is still
  best-effort `unknown`; we surface the verbatim string in the
  manifest so a human can decide redistribution scope later.
- A new optional dependency on `urllib.parse` and the existing
  `lxml.html` for page scraping — no new packages in
  `requirements.txt`.
- `scripts/check.sh` adds
  `scripts/m1_discover_guitarloot.py` to the required-files list so
  CI fails fast if the script is deleted.
