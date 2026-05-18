# PDMX classical-guitar probe — report

Per ADR 0015: probe PDMX for classical-guitar coverage
before committing to OMR. Filter is *solo nylon-guitar
piece in the no_license_conflict subset* (= MuseScore
MIDI program 24, single track, clean copyright metadata).
Each candidate is then run through our existing
`m1_validate.py` classical-guitar bar (see ADR 0005).

## Loose filter (nylon + no_license_conflict)

- Candidates after CSV filter: **660**
- Files actually validated (in tarball): **660**
- Accepted by m1_validate: **307** (47%)
- Rejected: **353**

### Rejections by code

- `MISSING_TITLE` — 191
- `MISSING_COMPOSER` — 103
- `TAB_ONLY` — 33
- `PLACEHOLDER_METADATA` — 12
- `MULTI_STAFF_PITCHED` — 10
- `OUT_OF_GUITAR_RANGE_LOW` — 2
- `FRAGMENT` — 2

## Strict filter (+ classical genre OR known composer)

- Candidates after CSV filter: **293**
- Files actually validated (in tarball): **293**
- Accepted by m1_validate: **189** (65%)
- Rejected: **104**

### Rejections by code

- `MISSING_TITLE` — 75
- `MISSING_COMPOSER` — 17
- `TAB_ONLY` — 5
- `MULTI_STAFF_PITCHED` — 3
- `PLACEHOLDER_METADATA` — 2
- `OUT_OF_GUITAR_RANGE_LOW` — 1
- `FRAGMENT` — 1

## Top composers in the strict-accepted set

- 24× Francisco Tárrega (1852 - 1909)
- 20× Luigi Legnani(1790 - 1877)
- 17× Francisco Tárrega(1852 - 1909)
- 11× NA
- 8× Isaac Albéniz (1860 - 1909)
- 6× Isaac Albéniz(1860 - 1909)
- 5× Fernando Sor
- 4× Anonymous
- 4× Mauro Giuliani (1781-1828)
- 3× Johann Sebastian Bach
- 3× Joaquín Turina Pérez (1882 - 1949)
- 2× Mauro Giuliani
- 2× Robert de Visée
- 2× Matteo Carcassi
- 2× Ferdinando Carulli (1770-1841)
- 2× Chopin
- 2× Ferdinando Carulli
- 2× John Dowland
- 1× François Campion (1686-1746) Arr.Marieh
- 1× Paul de SENNEVILLE Olivier Toussaint
- 1× Johann Sebastian Guitar Bach BWV Anh. 114
- 1× By Monte Carlo & Alma Sanders. Arr solo guitar G.Dempsey
- 1× Ð. Ð. ÐÐÑ ÐÐµÑÐµÐÐ¾ÐÐµÐ½ÐÐµ Ð. ÐÐµÐ³Ð¾Ð²ÐÐ
- 1× Franz Schubert arr. Johann Kaspar Mertz
- 1× Francisco Tárrega (1852-1909)

## Go/no-go reading

Per ADR 0015 the threshold for proceeding to full PDMX
ingest is **≥1,000 plausible classical-guitar pieces**
after validation. Compare the strict-accepted count above
against:

- Current corpus: **801** accepted pieces
- Guitar Loot share today: **53%** (the diversification target)
- A 400-piece PDMX addition would put Guitar Loot at ~36%,
  which crosses the reviewer's <40% bar.

If strict-accepted < 200, the corpus impact is real but
small — consider whether ClassClef outreach is a faster
next step. If strict-accepted ≥ 400, write a discover
script and ingest.
