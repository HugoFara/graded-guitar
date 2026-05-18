# M2 feature audit

- Pieces: **801**
- Pieces with curator grade: **427**
- Grades present: G3, G4, G5, G6, G7, G8, G9
- Sources: github, guitarloot, mutopia
- Correlation threshold for flagging: |r| ≥ 0.7

Output of `scripts/m2_feature_audit.py`. Inputs come from `corpus/features.csv` (see `scripts/m2_features.py` and `decisions/0009-m2-grading-inputs.md`). This file is meant to be the advisor's entry point to the M2 feature list — everything below is a deterministic summary, not a model decision.

## Per-grade summary (median)

| feature | G3 (n=4) | G4 (n=6) | G5 (n=39) | G6 (n=103) | G7 (n=158) | G8 (n=109) | G9 (n=8) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| midi_min | 52.0 | 52.0 | 52.0 | 52.0 | 52.0 | 52.0 | 52.0 |
| midi_max | 84.0 | 83.5 | 84.0 | 84.0 | 84.5 | 85.0 | 88.0 |
| midi_range | 32.5 | 31.5 | 32.0 | 32.0 | 33.0 | 34.0 | 36.0 |
| midi_median | 71.5 | 73.0 | 71.0 | 71.0 | 71.5 | 73.0 | 73.5 |
| key_fifths | 2.0 | 1.5 | 1.0 | 1.0 | 1.0 | 1.0 | 0.5 |
| key_changes | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| tempo_bpm | 56.0 | 76.0 | 76.0 | 76.0 | 76.0 | 72.0 | 66.0 |
| meter_changes | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| smallest_division | 32.0 | 16.0 | 16.0 | 16.0 | 16.0 | 16.0 | 32.0 |
| dotted_count | 52.5 | 32.5 | 26.0 | 36.0 | 38.5 | 42.0 | 76.5 |
| tied_count | 8.0 | 16.0 | 18.0 | 14.0 | 19.0 | 22.0 | 43.0 |
| tuplet_count | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| max_chord_stack | 3.5 | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 | 4.0 |
| polyphonic_measure_ratio | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| voice_count_max | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 |
| ornament_mordent | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| ornament_trill | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| ornament_turn | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| grace_count | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| harmonic_count | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| barre_count | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| position_shift_proxy | — | — | — | — | — | — | — |
| pitch_min_fret_max | 20.0 | 19.5 | 20.0 | 20.0 | 20.5 | 21.0 | 24.0 |
| pitch_min_fret_p90 | 14.5 | 15.5 | 15.0 | 15.0 | 15.0 | 16.0 | 18.0 |
| pitch_position_shifts | 157.0 | 112.0 | 98.0 | 109.0 | 125.0 | 124.0 | 321.0 |
| measure_count | 40.5 | 48.5 | 35.0 | 38.0 | 48.0 | 42.0 | 86.0 |
| note_count | 716.5 | 486.0 | 350.0 | 424.0 | 493.0 | 454.0 | 1092.0 |
| duration_sec_approx | 150.0 | 116.5 | 80.7 | 105.0 | 120.0 | 123.5 | 308.65 |

## Per-source summary (median)

| feature | github (n=41) | guitarloot (n=428) | mutopia (n=332) |
| --- | --- | --- | --- |
| midi_min | 45.0 | 52.0 | 52.0 |
| midi_max | 72.0 | 84.0 | 79.0 |
| midi_range | 25.0 | 33.0 | 29.0 |
| midi_median | 60.0 | 72.0 | 67.0 |
| key_fifths | 0.0 | 1.0 | 1.0 |
| key_changes | 1.0 | 1.0 | 1.0 |
| tempo_bpm | 80.0 | 74.0 | 84.0 |
| meter_changes | 1.0 | 1.0 | 1.0 |
| smallest_division | 8.0 | 16.0 | 16.0 |
| dotted_count | 3.0 | 38.5 | 11.0 |
| tied_count | 0.0 | 18.0 | 0.0 |
| tuplet_count | 0.0 | 0.0 | 0.0 |
| max_chord_stack | 2.0 | 3.0 | 3.0 |
| polyphonic_measure_ratio | 0.12 | 1.0 | 1.0 |
| voice_count_max | 1.0 | 3.0 | 2.0 |
| ornament_mordent | 0.0 | 0.0 | 0.0 |
| ornament_trill | 0.0 | 0.0 | 0.0 |
| ornament_turn | 0.0 | 0.0 | 0.0 |
| grace_count | 0.0 | 0.0 | 0.0 |
| harmonic_count | 0.0 | 0.0 | 0.0 |
| barre_count | 0.0 | 0.0 | 0.0 |
| position_shift_proxy | 28.0 | — | — |
| pitch_min_fret_max | 8.0 | 20.0 | 15.0 |
| pitch_min_fret_p90 | 4.0 | 15.0 | 12.0 |
| pitch_position_shifts | 6.0 | 115.5 | 35.0 |
| measure_count | 12.0 | 44.0 | 25.0 |
| note_count | 91.0 | 473.0 | 233.0 |
| duration_sec_approx | 27.4 | 115.65 | 92.4 |

## Overall distribution per feature

- **`midi_min`** — n=801 · med=52.0 (p25=50.0, p75=52.0) · range=[38.0, 65.0]
- **`midi_max`** — n=801 · med=83.0 (p25=79.0, p75=86.0) · range=[58.0, 98.0]
- **`midi_range`** — n=801 · med=32.0 (p25=29.0, p75=34.0) · range=[3.0, 59.0]
- **`midi_median`** — n=801 · med=71.0 (p25=66.0, p75=73.0) · range=[44.0, 78.0]
- **`key_fifths`** — n=786 · med=1.0 (p25=0.0, p75=2.0) · range=[-4.0, 5.0]
- **`key_changes`** — n=801 · med=1.0 (p25=1.0, p75=1.0) · range=[0.0, 2.0]
- **`tempo_bpm`** — n=466 · med=76.0 (p25=68.0, p75=86.0) · range=[0.0, 250.0]
- **`meter_changes`** — n=801 · med=1.0 (p25=1.0, p75=1.0) · range=[1.0, 4.0]
- **`smallest_division`** — n=801 · med=16.0 (p25=16.0, p75=32.0) · range=[1.0, 64.0]
- **`dotted_count`** — n=801 · med=24.0 (p25=9.0, p75=46.0) · range=[0.0, 221.0]
- **`tied_count`** — n=801 · med=4.0 (p25=0.0, p75=22.0) · range=[0.0, 309.0]
- **`tuplet_count`** — n=801 · med=0.0 (p25=0.0, p75=0.0) · range=[0.0, 510.0]
- **`max_chord_stack`** — n=801 · med=3.0 (p25=2.0, p75=3.0) · range=[0.0, 6.0]
- **`polyphonic_measure_ratio`** — n=801 · med=1.0 (p25=1.0, p75=1.0) · range=[0.0, 1.0]
- **`voice_count_max`** — n=801 · med=3.0 (p25=2.0, p75=3.0) · range=[0.0, 4.0]
- **`ornament_mordent`** — n=801 · med=0.0 (p25=0.0, p75=0.0) · range=[0.0, 15.0]
- **`ornament_trill`** — n=801 · med=0.0 (p25=0.0, p75=0.0) · range=[0.0, 8.0]
- **`ornament_turn`** — n=801 · med=0.0 (p25=0.0, p75=0.0) · range=[0.0, 0.0]
- **`grace_count`** — n=801 · med=0.0 (p25=0.0, p75=0.0) · range=[0.0, 92.0]
- **`harmonic_count`** — n=801 · med=0.0 (p25=0.0, p75=0.0) · range=[0.0, 0.0]
- **`barre_count`** — n=801 · med=0.0 (p25=0.0, p75=0.0) · range=[0.0, 0.0]
- **`position_shift_proxy`** — n=2 · med=28.0 (p25=25.0, p75=31.0) · range=[25.0, 31.0]
- **`pitch_min_fret_max`** — n=801 · med=19.0 (p25=15.0, p75=22.0) · range=[0.0, 24.0]
- **`pitch_min_fret_p90`** — n=801 · med=14.0 (p25=10.0, p75=16.0) · range=[0.0, 21.0]
- **`pitch_position_shifts`** — n=801 · med=69.0 (p25=33.0, p75=140.0) · range=[0.0, 537.0]
- **`measure_count`** — n=801 · med=35.0 (p25=20.0, p75=54.0) · range=[5.0, 308.0]
- **`note_count`** — n=801 · med=346.0 (p25=200.0, p75=570.0) · range=[18.0, 2350.0]
- **`duration_sec_approx`** — n=460 · med=113.7 (p25=66.3, p75=176.8) · range=[14.4, 1087.1]

## Flagged collinearity

Pairs with |r| ≥ 0.7 on the shared non-empty subset. High correlation isn't fatal — gradient-boosted trees handle it — but the advisor may want to keep only the more interpretable feature from each pair.

| feature A | feature B | r |
| --- | --- | --- |
| `midi_max` | `pitch_min_fret_max` | +0.99 |
| `midi_median` | `pitch_min_fret_p90` | +0.94 |
| `pitch_min_fret_max` | `pitch_min_fret_p90` | +0.93 |
| `midi_max` | `pitch_min_fret_p90` | +0.92 |
| `midi_median` | `pitch_min_fret_max` | +0.88 |
| `midi_max` | `midi_median` | +0.87 |
| `pitch_position_shifts` | `note_count` | +0.85 |
| `measure_count` | `duration_sec_approx` | +0.84 |
| `note_count` | `duration_sec_approx` | +0.81 |
| `measure_count` | `note_count` | +0.81 |
| `midi_min` | `midi_median` | +0.80 |
| `pitch_position_shifts` | `measure_count` | +0.78 |
| `midi_min` | `pitch_min_fret_p90` | +0.75 |
| `pitch_position_shifts` | `duration_sec_approx` | +0.73 |

## Coverage gaps

- `tempo_bpm`: 335 / 801 pieces missing (41.8%)
- `smallest_division`: 0 / 801 pieces missing (0.0%)
- `duration_sec_approx`: 341 / 801 pieces missing (42.6%)
- `position_shift_proxy`: 799 / 801 pieces missing (99.8%)
- `key_fifths`: 15 / 801 pieces missing (1.9%)

