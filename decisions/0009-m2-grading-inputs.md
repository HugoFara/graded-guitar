# 0009 — M2 grading-model inputs and approach (scoping)

- **Status:** Proposed
- **Date:** 2026-05-18

## Context

Spec §7 M2 calls for a grading model that produces a 1–10 grade for every
piece in the corpus, with the explicit constraint that the **feature set
must be written down and approved by the advisor before training** and
that the advisor reviews 50 randomly graded pieces post-training. ADR
[0004](./0004-deferrals.md) makes advisor engagement a hard gate on M2.

Two facts have changed the landscape since the spec was written:

1. **ADR [0008](./0008-guitarloot-source.md) gave us 692 pieces with
   curator-assigned Delcamp 1-10 grades.** The spec assumed labels would
   come from the syllabi `pieces[]` arrays (which are still empty per
   ADR 0004). Guitar Loot's Eric Crouch has done the labelling work
   already, on a coherent Renaissance+Baroque subset. This is the only
   labelled subset we have today and the only one we can pre-build
   tooling against without inventing labels.
2. **The corpus shape is known.** 791 accepted pieces as of M1 close:
   ~692 graded (87% of Guitar Loot) and ~99 ungraded (Mutopia +
   GitHub). Grade distribution skews mid-range (G5-G8); G1-G2 and G10
   are sparse. Style coverage is Renaissance/Baroque (Guitar Loot) plus
   early-Romantic studies (Mutopia: Sor, Giuliani, Aguado, Carcassi).
   Modern repertoire (Brouwer, Villa-Lobos, post-1900) is absent.

The advisor's M1 spot-check and the syllabi `pieces[]` population both
remain blocking M2 hard gates. This ADR scopes the work that **can**
safely happen before those gates lift, and lists what must wait.

## Decision

Treat M2 as two phases: **feature-extraction tooling** (pre-advisor,
deterministic, no judgement calls) and **modeling+labelling**
(post-advisor, requires sign-off).

### Phase 1 — safe to build now

Write `scripts/m2_features.py`: a read-only pass over
`corpus/manifest.json` + each normalized MusicXML file, emitting one
feature row per piece into `corpus/features.parquet` (or `.csv` —
format decision deferred to first PR). Inputs come from MusicXML only;
no human grading involved. The output is data, not model decisions, so
the advisor can review the feature design end-to-end before any model
is fit.

The first-draft feature list, grouped by spec §7's hints and grouped by
extraction confidence (`★★★` mechanical / `★★` heuristic / `★` proxy):

- **Pitch range** — min MIDI, max MIDI, range span, median register
  `★★★`. Already partially computed (`m1_pre_check.py`, `m1_validate.py`).
- **Key signature** — fifths value, count of distinct keys per piece,
  number of accidentals outside the signature `★★★`. `m1_validate.py`
  already extracts the opening fifths.
- **Tempo and meter** — opening tempo BPM, time signature, count of
  meter changes `★★★`.
- **Rhythmic complexity** — smallest note division (1/16, 1/32, etc.),
  count of dotted/tied notes, count of triplet/tuplet markers, average
  notes per beat `★★`.
- **Polyphony** — max chord stack size, fraction of measures with ≥2
  simultaneous voices, total voice count per part `★★★`.
  `m1_pre_check.py` already counts chord stacks.
- **Ornamentation** — count of mordents, trills, grace notes, turns
  `★★★`. MusicXML has explicit tags for each.
- **Position and stretch (proxy)** — when `<technical>/<string>` and
  `<fret>` data are present (Guitar Loot likely; Mutopia likely not),
  count position-shifts as fret deltas > 4. When absent, derive a proxy
  from pitch + key context; mark the proxy as low-confidence `★ → ★★`.
- **Barré indicators** — count of `<technical>/<barre>` markers `★★`.
  Coverage is patchy; many editions don't notate barré at all.
- **Harmonics** — count of `<technical>/<harmonic>` markers `★★`.
- **Score length** — measure count, total note count, approximate
  duration in seconds (derived from tempo + meter + measure count)
  `★★★`.

Explicitly **not** in the first draft:
- Fingering. MusicXML's `<fingering>` is editor-specific and unreliable
  across Sibelius (Guitar Loot), LilyPond-derived (Mutopia), and
  hand-typeset GitHub sources. Including it would silently encode the
  arranger's hand size and the editor's preference rather than the
  piece's difficulty.
- Style/era. Easy to derive from composer dates but trivially
  collinear with composer identity; let the model find that itself if
  it helps.

#### Phase 1 follow-ups (built after the first draft)

- **`scripts/m2_feature_audit.py` → `corpus/feature_audit.md`** —
  per-grade and per-source median tables, full distributions, pairwise
  Pearson correlations at |r| ≥ 0.7. Surfaced that `position_shift_proxy`
  is 99.8% missing on this corpus because Sibelius-emitted MusicXML
  rarely carries `<technical>/<string>`+`<fret>`.
- **`scripts/m2_label_bias.py` → `corpus/label_bias.md`** — composer/era
  confound diagnostics on the Delcamp-graded subset. Concrete finding:
  **87.8% of graded pieces come from composers whose entire output
  in the corpus sits at a single Delcamp grade.** Only "Anon" (n=52)
  spans more than one grade (G4–G7). The grade variance is between
  composers, not within them. This sharpens the *primary label source*
  question below — Delcamp-on-Crouch is essentially a composer-attribution
  signal on this subset.
- **`scripts/m2_baseline_grader.py` → `corpus/baseline_grader.md`** —
  fixed-rule percentile-composite grader (5 features, equal weights,
  no tuning against labels). On the labelled subset: exact match 35%,
  within ±1 grade 83%. Intended as a concrete object for the advisor
  to react to, not a benchmark target.
- **Pitch-only fingering proxy** — `pitch_min_fret_max`,
  `pitch_min_fret_p90`, `pitch_position_shifts` added to
  `m2_features.py`. Lower-bound position load from the pitch stream
  alone (standard tuning); 100% coverage. Replaces the 99.8%-missing
  `position_shift_proxy` as the de facto position feature, though both
  are retained.

### Phase 2 — blocked on advisor

After advisor engagement (ADR 0004 gate):

1. **Advisor approves or revises the feature list.** Spec §7 makes this
   a precondition of training. Open the conversation with the Phase 1
   feature output and the per-feature confidence rating above; let the
   advisor cut or add.
2. **Choose primary label source.** Three plausible policies, ordered
   by amount of advisor-time required:
   - *Delcamp-only* (lowest effort): train on the 692 Guitar Loot
     pieces, treat Mutopia/GitHub as unlabelled, advisor spot-checks
     the predictions on those. Cheap but biased toward
     Renaissance/Baroque solo arrangements.
   - *Delcamp + syllabus calibration*: once syllabi `pieces[]` are
     populated (ADR 0004), use a small set of dual-labelled pieces
     (same piece both in a syllabus and on Guitar Loot) to fit a
     linear remap between scales. Better generalization across eras.
   - *Advisor-graded sample augmentation*: pay the advisor (or accept
     pro-bono time) to grade ~50 hand-picked Mutopia pieces filling
     gap composer/era cells. Highest cost, smallest risk of style
     bias.
   The choice depends on what the advisor's time budget actually is.
3. **Baseline model**: gradient-boosted trees (LightGBM or XGBoost) on
   the approved features, predicting integer grade with a regression
   loss + post-hoc rounding. Spec §7 explicitly accepts this. A linear
   ridge baseline runs alongside as a sanity floor.
4. **Evaluation protocol**:
   - Held-out test set: 20% of labelled pieces, stratified by grade.
   - Out-of-distribution probe: hold one composer family entirely out
     (e.g., all Carcassi) and report separate metrics. This catches
     "the model just memorized Sor".
   - Calibration plot per source — Guitar Loot grades may need a
     scalar shift relative to syllabus grades (ADR 0008 notes the
     Delcamp ↔ Trinity approximation is informal).
5. **Pass/fail thresholds**: spec §7 mandates ±1-grade accuracy ≥70%
   on holdout and ≥40/50 "plausible" on the advisor review (≥80% rate
   in spec §7's stop condition). These stay as written until the
   advisor proposes a revision.

### Phase 3 — corpus-wide prediction (post-validation)

Once a model passes the spec §7 thresholds, write its predictions into
`corpus/manifest.json` as `model_grade` + `model_grade_source =
"m2-v1@<sha>"`, preserving any existing curator-assigned `grade` field
under `grade` / `grade_source`. The web player (M3) reads
`model_grade` when no curator grade is present.

## Consequences

- **`scripts/m2_features.py` can land before the advisor is engaged.**
  It's a pure function of the M1 corpus, easy to revise, and gives the
  advisor a concrete starting artefact instead of an abstract list.
- **Delcamp grades become the most likely primary label source.** This
  collapses an M2 dependency on the syllabi `pieces[]` arrays — they
  remain valuable for calibration but stop being a strict
  precondition. ADR 0004's "syllabi populated before M2" hard gate is
  partially softened to "syllabi populated before M2 *evaluation*";
  this ADR does not unilaterally change ADR 0004, but flags the
  conflict for the advisor conversation.
- **Style coverage gap is acknowledged up front.** A model trained on
  Renaissance/Baroque + early-Romantic studies will under-predict
  difficulty on 20th-century repertoire. This is a corpus problem, not
  a model problem; M2 v1 ships with a documented scope note rather
  than a fix.
- **Per-piece `model_grade` writes invalidate one cached
  recommendation when the model is retrained.** M4 (recommendation
  feed) should treat the manifest as the source of truth and recompute
  on `model_grade_source` changes; noted here so M4 doesn't bake the
  current grades into its cache key.
- **No new dependencies committed.** `lightgbm` / `xgboost` /
  `scikit-learn` and the parquet writer are deferred to the
  Phase 2 PR. Spec §10 names premature optimization as a failure mode;
  the modeling stack stays unfrozen until we know what the approved
  feature list needs.
- **This ADR does not authorize training.** Phase 2 is conditional on
  advisor sign-off per spec §7 + ADR 0004; this document defines the
  shape of that conversation, not its outcome.

## Open questions for the advisor

These are the explicit decision points to bring to the first advisor
session, in priority order:

1. Of the Phase 1 feature list above, which features are load-bearing
   for difficulty and which are noise? Are there missing features
   (e.g., specific technique markers we didn't enumerate)?
2. Is Delcamp 1-10 a sound primary label scale, or should we map
   everything to RCM/Trinity/ABRSM before training?
3. The Renaissance/Baroque + early-Romantic style envelope is what we
   have. Is it acceptable for v1 to ship under-confident predictions
   on Modern repertoire, or should that gate launch?
4. Spec §7 mandates "≥40/50 plausible on advisor review." What does
   "plausible" mean operationally — within one grade, within two,
   binary playable/not?
