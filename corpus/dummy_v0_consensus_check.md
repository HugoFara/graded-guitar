# dummy-v0 consensus check

Self-audit per ADR 0013: check whether dummy-v0 places
well-known pieces in roughly the right difficulty band.
Consensus grades come from the author's reading of the
RCM / Trinity / ABRSM classical-guitar syllabi and the
Delcamp grading discussions; treat each row as a band
(consensus ± 1) rather than a point.

- Manifest: `corpus/manifest.json` (801 pieces)

| Probe | Consensus | Corpus grade | Δ | Verdict | Notes |
|---|---:|---|---:|---|---|
| ^adelita$ / tarrega | 4 | 3 (dummy-v0) | -1 | ✓ | Adelita — short character piece |
| ^lagrima$ / tarrega | 4 | 3 (dummy-v0) | -1 | ✓ | Lágrima — lyrical, grade 4 |
| recuerdos.*theme / tarrega | 4 | 3 (dummy-v0) | -1 | ✓ | Recuerdos de la Alhambra (Theme only, ~20s) — no tremolo, grade 4. Full piece would be 9-10. |
| ^capricho.*arabe$ / tarrega | 7 | 7 (dummy-v0) | +0 | ✓ | Capricho Árabe — full piece (~240s), grade 7 |
| capricho.*arabe.*theme / tarrega | 4 | 3 (dummy-v0) | -1 | ✓ | Capricho Árabe (Theme only, ~19s) — grade 4 |
| estudio.*a minor / tarrega | 4 | 3 (dummy-v0) | -1 | ✓ | Tárrega Estudio in A minor — grade 3-4 |
| asturias.*theme / albeniz | 4 | 3 (dummy-v0) | -1 | ✓ | Asturias (Theme only, ~17s) — grade 4. Full Leyenda would be 8. |
| ^etude 1$ / carcassi | 4 | 3 (dummy-v0) | -1 | ✓ | Carcassi Etude 1 — early study |
| ^etude 7$ / carcassi | 5 | 3 (dummy-v0) | -2 | ~ | Carcassi Etude 7 — middle of the set |
| ^etude 10$ / carcassi | 6 | 7 (dummy-v0) | +1 | ✓ | Carcassi Etude 10 — later study |
| ^24 studies for the guitar$ / sor | 5 | 5 (median of 22; range 3-7; dummy-v0) | +0 | ✓ | Sor 24 Studies — set spans grade 3-8; check median plausibility; 22 candidates |
| ^24 studies for the guitar$ / giuliani | 5 | 5 (median of 24; range 3-7; dummy-v0) | +0 | ✓ | Giuliani 24 Studies — similar spread to Sor's set; 24 candidates |
| ^chaconne$ / bach|visee|mouton|boismortier|anon | 7 | 7 (median of 6; range 7-7; delcamp-eric-crouch) | +0 | ✓ | Lute Chaconnes — grade 6-8; 6 candidates |
| ^bouree$|^bourree$|bourr.e / bach | 5 | 6 (dummy-v0) | +1 | ✓ | Bourrée from BWV 996 — grade 5-6 |
| ^prelude$ / bach | 6 | 6 (median of 2; range 5-6; dummy-v0) | +0 | ✓ | Bach Prelude (transcribed) — grade 5-7; 2 candidates |
| prelude.*villa|villa.*prelude|prelude no\.?\s*1.*theme / villa-lobos | 4 | 3 (dummy-v0) | -1 | ✓ | Villa-Lobos Prelude No. 1 (Theme only, ~30s) — grade 4-5 |
| ^six petites pieces, no\.?\s*1$ / aguado | 4 | 5 (median of 2; range 3-5; dummy-v0) | +1 | ✓ | Aguado Six Petites Pièces No. 1 — primer; 2 candidates |
| ^les favorites$ / aguado | 5 | 7 (median of 10; range 5-7; dummy-v0) | +2 | ~ | Aguado Les Favorites — grade 4-6; 10 candidates |
| ^greensleeves$ / traditional english | 3 | 3 (dummy-v0) | +0 | ✓ | Greensleeves traditional arrangement — grade 2-3 |
| galliard / dowland | 6 | 8 (median of 20; range 7-8; delcamp-eric-crouch) | +2 | ~ | Dowland galliards — grade 5-7; 20 candidates |
| pavan / dowland | 6 | 8 (median of 4; range 7-8; delcamp-eric-crouch) | +2 | ~ | Dowland pavanes — grade 5-7; 4 candidates |
| galliard / holborne | 5 | 6 (median of 10; range 6-6; delcamp-eric-crouch) | +1 | ✓ | Holborne galliards — grade 4-6; 10 candidates |
| pavan / holborne | 5 | 6 (median of 10; range 6-6; delcamp-eric-crouch) | +1 | ✓ | Holborne pavanes — grade 4-6; 10 candidates |
| six divertissements / sor | 6 | 7 (median of 4; range 5-7; dummy-v0) | +1 | ✓ | Sor Six divertissements — grade 5-7; 4 candidates |
| opus 29|op\.?\s*29 / sor | 6 | 7 (dummy-v0) | +1 | ✓ | Sor Op. 29 — grade 6-7 |
| caprice / carcassi | 5 | 3 (median of 5; range 3-6; dummy-v0) | -2 | ~ | Carcassi Caprices — grade 4-6; 5 candidates |
| pavan|galliard / bacheler | 6 | 7 (median of 4; range 7-7; delcamp-eric-crouch) | +1 | ✓ | Daniel Bacheler — grade 5-7; 4 candidates |
| galliard|division|alman / francis cutting | 5 | 7 (median of 12; range 7-8; delcamp-eric-crouch) | +2 | ~ | Francis Cutting — Elizabethan lute, grade 4-6; 12 candidates |
| ^almain$|^almand$|^alman$|^almaine$ / anon|english|holborne | 4 | — | — | no match | Renaissance Almain/Alman — grade 3-5; no match in corpus |
| ^8 petites pieces$ / aguado | 6 | 7 (median of 7; range 5-7; dummy-v0) | +1 | ✓ | Aguado 8 Petites Pièces — grade 5-7; 7 candidates |
| corrente|courante|gagliarda|sarabanda / foscarini | 6 | 6 (median of 3; range 6-6; delcamp-eric-crouch) | +0 | ✓ | Foscarini early-Baroque dances — grade 5-7; 3 candidates |
| lachrimae|flow.*tears / dowland | 7 | 8 (median of 2; range 7-8; delcamp-eric-crouch) | +1 | ✓ | Dowland Lachrimae / Flow My Tears — grade 6-8; 2 candidates |

## Summary

- Probes attempted: **32**
- Matched + graded: **31**
- No match / no grade: **1**
- Within ±1 of consensus: **25/31** (81%)
- Within ±2 of consensus: **31/31** (100%)
- Mean |Δ|: **0.97**

## Reading this report

- **✓** = within ±1 grade (the band the consensus column
  represents). This is the bar the spec §7 M2 advisor
  validation will eventually use.
- **~** = within ±2 grades. Not great, not catastrophic.
- **✗** = off by 3+ grades. Worth investigating; the
  model is making a categorical mistake on a piece
  whose difficulty is broadly agreed on.
- **no match** = the corpus doesn't contain this piece,
  or the title/composer pattern is too tight. Worth
  diversifying the corpus (see ADR 0013 follow-ups).

## Caveats

- Curator grades (`delcamp-eric-crouch`) bypass dummy-v0
  entirely — those rows test the *curator's* alignment with
  syllabus consensus, not the model's. Curator tends to
  grade Renaissance/Baroque lute repertoire 1-2 grades
  above syllabus norms; that's a Delcamp-vs-syllabus
  taste difference, not a pipeline bug.
- Several Tárrega / Albéniz / Villa-Lobos entries in the
  corpus are theme-statement excerpts (~20-30s), not full
  performances. Consensus is calibrated to the excerpt, not
  the full work. The full pieces would land much higher
  on the grade scale.
- This is **not** an advisor review. It's an author-run
  smoke test against pieces with broad syllabus consensus.
  Spec §7 M2 still gates on a real advisor reviewing 50
  randomly graded pieces, with a 40/50 plausibility bar.
