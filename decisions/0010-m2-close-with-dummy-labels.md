# 0010 — Close M2 pre-advisor with dummy labels

- **Status:** Accepted
- **Date:** 2026-05-18

## Context

ADR [0009](./0009-m2-grading-inputs.md) split M2 into Phase 1
(feature-extraction tooling, safe pre-advisor) and Phase 2
(training+labelling, advisor-gated). Phase 1 landed: feature CSV,
distributional audit, label-bias diagnostics, rule-based baseline grader.

ADR [0004](./0004-deferrals.md) makes advisor engagement a hard gate
on M2 Phase 2. Hiring the advisor turns out to be slow — months, not
days. Holding the project on `git status: clean` until that lands
freezes M3 (web player) too, because M3 needs `model_grade` written
onto every `manifest.json` entry to display predictions.

Two options:

1. **Wait for the advisor.** Spec-faithful. Project visibly stalls.
2. **Build M2 Phase 2 + start M3 against placeholder labels**,
   provided every artifact carries a dummy-version tag so nothing
   ships under the wrong banner.

Hugo picked (2). The cost is a small amount of cleanup work when the
advisor lands; the alternative was indefinite blockage.

## Decision

Run the full M2 Phase 2 pipeline now against dummy labels, and write
`model_grade` into the manifest, under these constraints:

- Every label, model file, and predicted grade carries a
  `dummy-v0` tag (or successor version) in a `*_source` field. A
  swap-in commit overwriting the labels is the entire promotion path
  to a real model — no architectural churn.
- The README and `corpus/README.md` carry a prominent banner pointing
  at this ADR.
- The advisor's hard gate is preserved: a real `model_grade_source` —
  `m2-v1@<sha>` per ADR 0009 §Phase 3 — is forbidden until the
  advisor has signed off per the spec §7 stop-conditions.

### Pipeline as built

Five new scripts; each idempotent and re-runnable in sequence:

1. **`scripts/m2_dummy_advisor.py` → `corpus/dummy_advisor_grades.csv`**
   Picks ~50 ungraded pieces stratified across `_era_of()` buckets
   (Renaissance/Baroque/Classical/Romantic/Modern/Unknown), seeded
   from the deterministic baseline grader's percentile-composite
   prediction. Every row has `grade_source = "dummy-advisor-v0"`.
   The advisor's swap-in path is "open this CSV, overwrite the
   `dummy_grade` column, bump the source tag, re-run the pipeline."
2. **`scripts/m2_train.py` → `corpus/model_dummy_v0.json` + `corpus/model_grades.csv`**
   Multinomial logistic regression on the numeric subset of
   `features.csv`, training labels = Delcamp grades from manifest
   + dummy advisor placeholders. Sparse classes (G4, G10) are
   collapsed into adjacent bands so the LBFGS solver converges.
   Model coefficients persist as JSON so M3 can score new pieces
   without bringing sklearn into the web stack.
3. **`scripts/m2_eval.py` → `corpus/model_eval.md`**
   Stratified 5-fold CV + in-sample per-era breakdown + a
   composer-out probe. The composer-out probe is the load-bearing
   number: per ADR 0009 + `label_bias.md` it's the realistic
   stress test, since Delcamp grades are largely composer attribution.
4. **`scripts/m2_apply_to_manifest.py`** writes `model_grade` +
   `model_grade_source = "dummy-v0"` onto every manifest entry,
   leaving curator `grade` / `grade_source` untouched. M3 reads
   `grade` when present, falls back to `model_grade`.
5. **Feature additions in `m2_features.py`:** `notes_per_measure`,
   `accidentals_outside_key`. Fills two of the gaps ADR 0009 Phase 1
   flagged. 100% coverage on the current corpus.

### New runtime dependencies

`requirements.txt` gains `scikit-learn==1.5.2` + a `numpy>=2.0,<3`
range. ADR 0009 deferred these to the Phase 2 PR; this is that PR,
under a dummy-data banner. The advisor still chooses the final model
family — GBM, ridge, ordinal LR — when they engage.

### What the advisor still owns

Unchanged from ADR 0009 § "Phase 2", but now the swap-in points are
concrete files/lines instead of decisions to be made:

- **Feature list** — `NUMERIC_FEATURES` in `scripts/m2_train.py`.
- **Primary label source** — overwrite `corpus/dummy_advisor_grades.csv`
  or change `m2_train.load_labelled()` to ignore it.
- **"Plausible" definition for §7 sign-off** — write into ADR 0009
  §"Phase 2" Q4.
- **Model family** — `_new_model()` in `scripts/m2_eval.py` +
  `m2_train.py`.
- **Eval thresholds** — ADR 0009 § "Phase 2" §5; spec §7 names
  ≥70% within-±1 + ≥40/50 plausible.

Nothing about the file layout, manifest schema, or M3 read path
depends on which of those choices the advisor makes.

## Consequences

- **M2 cannot formally close until the advisor signs off.** Spec §7
  is unchanged. This ADR closes M2 *operationally* (no pre-advisor
  Phase 2 work remaining) while the validation checks remain open.
- **`model_grade` is now in the manifest schema.** M3 can render it,
  but is bound by ADR contract to (a) prefer curator `grade` when
  present, and (b) surface the `model_grade_source` to the user so a
  player can see "this came from a placeholder model" until the
  swap-in happens.
- **New ML deps add ~70MB to the venv.** Trivial in dev; CI runs the
  self-check (which does not import sklearn) plus regression tests
  (which do). Future Phase 2 dep additions go in a follow-up ADR.
- **The 5-fold CV number (~35% exact, ~67% within ±1) sits below the
  spec §7 close criterion of ≥70% within-±1.** This is expected and
  documented inside `corpus/model_eval.md`: the labels are
  composer-attribution-confounded, the dummy advisor labels are
  baseline-grader echoes, so the model is essentially learning
  "predict the baseline grader." A real advisor session is the only
  thing that improves this number.
- **Reversibility:** every dummy-v0 file is regenerated by re-running
  the pipeline. Deleting `corpus/model_grades.csv` /
  `corpus/dummy_advisor_grades.csv` and re-running
  `scripts/m2_apply_to_manifest.py` is a clean reset. The
  `model_grade` writes in `manifest.json` overwrite each time the
  apply script runs.

## Open items the advisor will still close

- The Phase 2 questions in ADR 0009 §"Phase 2" remain open. This ADR
  does not pre-empt them — `dummy-v0` is plumbing, not opinion.
- 20-piece M1 metadata spot-check (per ADR 0004) is independent of M2
  and stays open.
