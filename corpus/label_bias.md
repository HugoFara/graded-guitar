# M2 label-bias audit

- Graded pieces: **427** (out of 801 in `features.csv`)
- Distinct composers in graded subset: **124**
- Grades present: G3, G4, G5, G6, G7, G8, G9

Output of `scripts/m2_label_bias.py`. Every Delcamp-graded piece in the corpus comes from Guitar Loot (Eric Crouch's Renaissance / Baroque arrangements), so the question is not just *which features predict grade* but *do those features actually measure difficulty, or do they just identify the composer Crouch was grading?* Everything below is descriptive — no model fitting.

## 1. Composer × grade cross-tab (top 20)

| composer | n | G3 | G4 | G5 | G6 | G7 | G8 | G9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Anon | 52 | · | 2 | 11 | 14 | 25 | · | · |
| John Dowland | 45 | · | · | · | · | · | 45 | · |
| Anthony Holborne | 33 | · | · | · | 33 | · | · | · |
| William Corkine | 22 | · | · | · | · | · | 22 | · |
| Francis Cutting | 16 | · | · | · | · | 16 | · | · |
| Jakub Polak | 13 | · | · | · | 13 | · | · | · |
| Daniel Bacheler | 12 | · | · | · | · | 12 | · | · |
| Giovanni Paolo Foscarini | 12 | · | · | · | 12 | · | · | · |
| Thomas Robinson | 11 | · | · | 11 | · | · | · | · |
| Tobias Hume | 10 | · | · | · | · | 10 | · | · |
| Anon, Pickering Lute Book | 8 | · | · | · | · | 8 | · | · |
| John Danyel | 7 | · | · | · | · | · | · | 7 |
| Henry Purcell | 7 | · | · | · | · | 7 | · | · |
| Francis Pilkington | 6 | · | · | · | 6 | · | · | · |
| Sylvius Leopold Weiss | 6 | · | · | · | · | · | 6 | · |
| Alessandro Piccinini | 5 | · | · | · | 5 | · | · | · |
| Richard Allison | 4 | 4 | · | · | · | · | · | · |
| Cuthbert Hely | 4 | · | · | · | · | · | 4 | · |
| Esaias Reusner | 4 | · | · | · | · | 4 | · | · |
| Domenico Pellegrini | 4 | · | · | 4 | · | · | · | · |

_Remaining 104 composers: 146 pieces._

## 2. Per-composer grade dispersion

Composers whose pieces all sit at one grade contribute zero within-composer variation. A model trained on this subset can't learn 'what makes a hard Dowland harder than an easy Dowland' if every Dowland piece is labelled the same.

| distinct grades per composer | composers | pieces |
| --- | --- | --- |
| 1 | 123 | 375 |
| 4 | 1 | 52 |

**375 / 427 graded pieces (87.8%) come from composers whose entire output in this corpus sits at a single grade.**

Composers spanning more than one grade:

- **Anon** (n=52): G4, G5, G6, G7

## 3. Per-grade composer concentration

For each grade: how many composers contribute, what share the top composer holds, and the Herfindahl index (1.0 = monopoly, 1/k = uniform over k composers).

| grade | n | composers | top-1 share | top-3 share | Herfindahl |
| --- | --- | --- | --- | --- | --- |
| G3 | 4 | 1 | 100.0% | 100.0% | 1.00 |
| G4 | 6 | 3 | 50.0% | 100.0% | 0.39 |
| G5 | 39 | 12 | 28.2% | 66.7% | 0.18 |
| G6 | 103 | 22 | 32.0% | 58.3% | 0.16 |
| G7 | 158 | 60 | 15.8% | 33.5% | 0.06 |
| G8 | 109 | 27 | 41.3% | 67.0% | 0.22 |
| G9 | 8 | 2 | 87.5% | 100.0% | 0.78 |

## 4. Era × grade

| era | G3 | G4 | G5 | G6 | G7 | G8 | G9 | total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Renaissance | 4 | 6 | 30 | 86 | 120 | 97 | 8 | 351 |
| Baroque | · | · | 9 | 17 | 37 | 12 | · | 75 |
| Classical | · | · | · | · | 1 | · | · | 1 |

## 5. Per-feature composer η² (between-composer variance share)

For each feature, the fraction of total variance that is between-composer rather than within-composer. η² close to 1 means knowing the composer almost fully determines the feature value — i.e. the feature is a composer proxy. η² close to 0 means the feature varies within each composer's catalogue and can carry actual difficulty signal.

_Restricted to composers with ≥5 graded pieces: 16 composers, 265 pieces._

| feature | η² | n |
| --- | --- | --- |
| `ornament_mordent` | 0.63 | 265 |
| `pitch_position_shifts` | 0.31 | 265 |
| `duration_sec_approx` | 0.29 | 252 |
| `note_count` | 0.28 | 265 |
| `measure_count` | 0.21 | 265 |
| `midi_range` | 0.19 | 265 |
| `ornament_trill` | 0.18 | 265 |
| `smallest_division` | 0.16 | 265 |
| `tied_count` | 0.16 | 265 |
| `voice_count_max` | 0.16 | 265 |
| `max_chord_stack` | 0.16 | 265 |
| `midi_max` | 0.16 | 265 |
| `tempo_bpm` | 0.16 | 252 |
| `pitch_min_fret_max` | 0.15 | 265 |
| `grace_count` | 0.15 | 265 |
| `pitch_min_fret_p90` | 0.15 | 265 |
| `midi_median` | 0.15 | 265 |
| `dotted_count` | 0.14 | 265 |
| `polyphonic_measure_ratio` | 0.11 | 265 |
| `midi_min` | 0.10 | 265 |
| `key_fifths` | 0.09 | 265 |
| `meter_changes` | 0.08 | 265 |
| `key_changes` | 0.07 | 265 |
| `tuplet_count` | 0.03 | 265 |

## 6. Bottom line

- **123 of 124 composers** have all their graded pieces at one grade. Together they account for **87.8% of the graded corpus**.
- **82.2% of graded pieces are Renaissance** (by the hand-curated era map). The labelled subset is not a representative sample of the classical-guitar repertoire — it is a sample of one curator's lute-transcription set.
- The advisor question is therefore not just *which features go into the model*, but **whether Delcamp-on-Crouch should be the primary label at all**, or whether it should be one signal among several (e.g. paired with a small advisor-graded calibration set spanning eras and difficulty).

