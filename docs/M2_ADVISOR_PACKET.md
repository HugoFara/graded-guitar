# M2 advisor packet

This is the single-page read for the M2 advisor session. It exists so the
session can spend its time on judgement calls rather than on navigation.
Counterpart of [`ADVISOR.md`](ADVISOR.md) (the engagement agreement) and
[`decisions/0009-m2-grading-inputs.md`](../decisions/0009-m2-grading-inputs.md)
(the scoping ADR).

## What we need from you

Per [project-spec.md](../project-spec.md) §7 and ADR 0009:

1. **Sign off (or revise) the M2 feature list** — features going into the
   grading model.
2. **Choose the primary label source** for training (see Q2 below).
3. **Define "plausible"** for the §7 spot-check (Q4 below).
4. **Schedule the M1 metadata spot-check** — 20 random pieces from
   `corpus/manifest.json`. Independent of M2; required for M1 close.

Everything else in the M2 plan is downstream of those four decisions.

## Headline finding the rest of the packet hinges on

The 427 pieces in our labelled subset are entirely from Guitar Loot
(Eric Crouch's Renaissance / Baroque lute transcriptions). Two
properties of that set:

- **The labels are essentially per-composer, not per-piece.** 123 of
  124 graded composers have all their pieces at a single Delcamp
  grade. Every Dowland is G8, every Holborne is G6, every Corkine is
  G8. Only "Anon" (n=52) spans more than one grade (G4–G7). 87.8% of
  graded pieces come from single-grade composers.
- **The style envelope is narrow.** 82% Renaissance, 18% Baroque,
  ~0% else.

Concretely: a model trained on this subset can't help learning
"is this Dowland?" before it learns "is this hard?" That doesn't mean
Delcamp is unusable — it means the *label policy* (Q2 below) is now
the load-bearing decision, not the feature list (Q1).

Sources for that finding: `corpus/label_bias.md` (the receipts).

## Reading order

In this order, ~30 minutes total:

1. **[`corpus/label_bias.md`](../corpus/label_bias.md)** — the composer /
   era confound analysis. Sections 1–3 are the load-bearing ones;
   §5 (η²) shows that the *features themselves* still carry
   within-composer variance, so the leakage is in the labels, not in
   the inputs.
2. **[`corpus/feature_audit.md`](../corpus/feature_audit.md)** —
   distributional summary of every feature, per grade and per source.
   Per-grade medians show which features trend monotonically with
   Delcamp grade.
3. **[`corpus/baseline_grader.md`](../corpus/baseline_grader.md)** —
   a deliberately simple rule-based grader (5 features, equal weights,
   no tuning) run against Delcamp. 35% exact, 83% within ±1. The
   confusion matrix and example disagreements are the part to react
   to — does the rule's prediction match your gut for the named
   pieces?
4. **[`decisions/0009-m2-grading-inputs.md`](../decisions/0009-m2-grading-inputs.md)**
   — the M2 scoping doc. Phase 1 (feature extraction tooling) is
   already built. Phase 2 starts only with your sign-off.

You can skip the schema/code; nothing in this packet asks you to read
Python.

## Open questions for the session

Restated from ADR 0009 §"Phase 2", with the label-bias finding folded in:

### Q1. Feature list

Of the features in `corpus/feature_audit.md`, which are load-bearing for
difficulty and which are noise? Anything obviously missing? Note that
`harmonic_count` and `barre_count` are zero across the corpus because
the Sibelius-emitted Guitar Loot files don't carry `<technical>` tags;
position load is approximated from pitch (`pitch_min_fret_*`) instead.

### Q2. Primary label source (the load-bearing question)

Three plausible policies, given the per-composer pattern above:

- **Delcamp-only** — cheapest. Train on the 427 graded pieces, accept
  that the model is partly a composer attribution model on
  Renaissance / Baroque material, ship with a documented style-coverage
  caveat.
- **Delcamp + syllabus calibration** — wait for syllabi `pieces[]` to
  be populated (currently empty per ADR 0004), use dual-labelled pieces
  (in both a syllabus and Guitar Loot) to fit a linear remap between
  scales. Better cross-era generalization; depends on syllabi work.
- **Delcamp + advisor-graded calibration sample** — you grade ~50
  hand-picked Mutopia / GitHub pieces filling era and difficulty gaps
  (Classical-era studies, Romantic, 20th-c.). Highest cost in your
  time, smallest risk of style bias. The label-bias finding pushes us
  toward this option as long as you have the time.

Which is preferable, and how much advisor time can we count on?

### Q3. Style coverage scope for v1

The corpus is Renaissance/Baroque-heavy by accident of source
availability. Is it acceptable for the M2 v1 model to ship with
under-confident or no predictions on Modern (Villa-Lobos, Brouwer,
Lauro) repertoire, or should that gate the launch?

### Q4. What "plausible" means

Spec §7 mandates "≥40 of 50 sampled gradings plausible" before M2 can
close. We need that operationalised. Three reasonable definitions:

- Within one grade of your own assessment.
- Within two grades.
- A binary "this is roughly the right difficulty for the player profile
  it would be recommended to."

Your call. We'll write whichever you pick into ADR 0009 as the
acceptance criterion.

## Hard gates this session unblocks

- **M1 close** (per ADR 0004): your written confirmation as advisor +
  the 20-piece metadata spot-check. M1 stays open until both land.
- **M2 Phase 2** (per ADR 0009): training starts only after the four
  questions above are answered. Nothing about the model is committed
  yet — no library choice, no training run, no manifest writes.
- **Public visibility** (ADR 0004): we keep the repo private until M3
  unless you have a reason it should flip earlier.

## What we will *not* do without you

- Train any grading model.
- Write `model_grade` into `corpus/manifest.json`.
- Advance to M3 (web player).

Everything in `scripts/m2_*.py` is read-only over the corpus and
describable as deterministic feature math. No judgement encoded in
code without your sign-off first.
