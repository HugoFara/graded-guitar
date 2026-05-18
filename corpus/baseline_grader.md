# M2 baseline grader

- Pieces graded by rule: **801 / 801**
- Of those, **427** also have a Delcamp grade for comparison.

Output of `scripts/m2_baseline_grader.py`. The rule:

1. For each feature in the rule set, compute the corpus percentile.
2. Composite = mean of the per-feature percentiles (equal weights).
3. Map composite percentile to a grade band:

| composite percentile | grade |
| --- | --- |
| [0, 20) | G3 |
| [20, 35) | G5 |
| [35, 55) | G6 |
| [55, 80) | G7 |
| [80, 101) | G8 |

Rule features (all monotone with Delcamp grade in `feature_audit.md`):

- `midi_max`
- `max_chord_stack`
- `voice_count_max`
- `polyphonic_measure_ratio`
- `measure_count`

**No threshold tuning against labels.** The cut points are fixed anchors over the empirical Delcamp range, not optimised. The purpose is to give the advisor something concrete to react to, not to win an accuracy benchmark.

## Confusion matrix

Rows = Delcamp grade, columns = rule prediction.

| Delcamp \ rule | G3 | G4 | G5 | G6 | G7 | G8 | G9 | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| G3 | · | · | · | 2 | 2 | · | · | 4 |
| G4 | · | · | · | 3 | 3 | · | · | 6 |
| G5 | · | · | 2 | 15 | 22 | · | · | 39 |
| G6 | 1 | · | 1 | 37 | 64 | · | · | 103 |
| G7 | · | · | 2 | 41 | 110 | 5 | · | 158 |
| G8 | · | · | 1 | 29 | 77 | 2 | · | 109 |
| G9 | · | · | · | · | 8 | · | · | 8 |

## Agreement headline

- **Exact match:** 151 / 427 (35.4%)
- **Within ±1 grade:** 354 / 427 (82.9%)

Context: the corpus is composer-confounded (see `corpus/label_bias.md`) — most Delcamp grades are constant within composer. The rule does *not* see composer, so its predictions will scatter inside each composer's actual grade. Read low exact-match alongside the confusion matrix, not in isolation.

## Per-Delcamp-grade hit rate

| Delcamp grade | n | exact | within ±1 |
| --- | --- | --- | --- |
| G3 | 4 | 0 (0%) | 0 (0%) |
| G4 | 6 | 0 (0%) | 0 (0%) |
| G5 | 39 | 2 (5%) | 17 (44%) |
| G6 | 103 | 37 (36%) | 102 (99%) |
| G7 | 158 | 110 (70%) | 156 (99%) |
| G8 | 109 | 2 (2%) | 79 (72%) |
| G9 | 8 | 0 (0%) | 0 (0%) |

## Examples

Five pieces where the rule agrees with Delcamp exactly:

- G6 (rule G6, composite 50.3) — Anon Dd.2.11 f.8, *Dargesson*
- G6 (rule G6, composite 53.9) — Anon, *Jour Desiré*
- G5 (rule G5, composite 27.7) — Anon (Combined sources, *Pastyme*
- G6 (rule G6, composite 46.0) — Anon, *Sick, Sick and Very Sick*
- G7 (rule G7, composite 76.6) — Daniel Bacheler, *Fantasy*

Five pieces with the largest disagreement:

- Delcamp G3 vs rule G7 (Δ=+4, composite 73.8) — Richard Allison, *Sharp Pavan (2c)*
- Delcamp G3 vs rule G7 (Δ=+4, composite 63.9) — Richard Allison, *De La Tromba Pavan*
- Delcamp G8 vs rule G5 (Δ=-3, composite 34.6) — William Corkine, *Perlude (Prelude) 2.23*
- Delcamp G4 vs rule G7 (Δ=+3, composite 57.2) — Anon: Hirsch Lute Book, *19.Ground*
- Delcamp G4 vs rule G7 (Δ=+3, composite 58.8) — Anon: Hirsch Lute Book, *51. Fantasy*

