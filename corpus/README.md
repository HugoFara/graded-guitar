# corpus/

Output of the M1 ingest pipeline.

## What's committed

- `candidates.{source}.json` — one file per discovery source (e.g. `candidates.github.json`, `candidates.imslp.json`). Each lists every MusicXML file the discovery script found, regardless of whether it's been fetched or accepted. Output of `scripts/m1_discover_{source}.py`.
- `manifest.json` — accepted pieces, with provenance, canonical metadata, and hashes. Output of `scripts/m1_validate.py`. **This is the source of truth for the corpus.**
- `rejected.json` — pieces that failed validation, each with a reason code. Output of `scripts/m1_validate.py`.
- `report.md` — human-readable summary (counts, top rejection reasons, top composers).
- `spot_check.md` — mechanical pre-check punch list (range outliers, fragments, suspicious metadata). Output of `scripts/m1_pre_check.py`. Distinct from the formal advisor 20-piece spot-check.
- `features.csv` — one row per accepted piece with the M2 grading-feature set. Output of `scripts/m2_features.py`. See `decisions/0009-m2-grading-inputs.md` for column definitions.
- `feature_audit.md` — per-grade, per-source distribution summary of `features.csv`, plus pairwise correlation flags. Output of `scripts/m2_feature_audit.py`. Intended as the advisor's entry point to the Phase 1 feature list.
- `label_bias.md` — composer/era confound diagnostics on the Delcamp-graded subset. Output of `scripts/m2_label_bias.py`. Quantifies the per-composer grading pattern in the Guitar Loot corpus; flags features whose variance is dominated by composer identity.
- `baseline_grades.csv` — predicted grade for every piece from a fixed, hand-readable rule (percentile-composite over a small feature subset). Output of `scripts/m2_baseline_grader.py`. **Not a model.** Intended to give the advisor a concrete prediction to react to.
- `baseline_grader.md` — confusion matrix and agreement rate of the baseline rule against Delcamp labels. Companion to `baseline_grades.csv`.
- `dummy_advisor_grades.csv` — **PLACEHOLDER LABELS** for ~50 ungraded pieces, seeded from the baseline grader and stratified across eras. Output of `scripts/m2_dummy_advisor.py`. Every row carries `grade_source = dummy-advisor-v0`. Replace the `dummy_grade` column when the real advisor engages.
- `dummy_advisor_grades.md` — per-era + per-grade distribution of the dummy sample, plus advisor swap-in instructions.
- `model_dummy_v0.json` — trained dummy-v0 logistic-regression weights, scaler, and feature order. Output of `scripts/m2_train.py`. **Not advisor-blessed.** Reload-friendly without sklearn.
- `model_grades.csv` — per-piece prediction + probabilities from `dummy-v0`. Carries the `model_version` tag in every row.
- `model_eval.md` — 5-fold CV, per-era breakdown, composer-out probe. Output of `scripts/m2_eval.py`. Numbers describe how well the pipeline reproduces dummy labels, not how well it grades difficulty.
- `m3_render_check.md` — mechanical alphaTab render smoke test (10 seeded-random pieces) + TTI measurement. Output of `web/tests/e2e/*` + `web/scripts/render-report.mjs`. Tracks the spec §7 M3 close gates that don't need the advisor.

## What's gitignored

- `raw/` — content-addressed cache of downloaded files (`{sha256}.musicxml` or `{sha256}.mxl`). Populated by `scripts/m1_fetch.py`.
- `normalized/` — normalized MusicXML per accepted piece, keyed by stable piece ID.
- `cache/` — HTTP cache, intermediate artifacts.

Bulk MusicXML is kept out of the repo so cloning stays fast and so we don't redistribute upstream files. Anyone can rebuild `raw/` and `normalized/` from the committed JSON by re-running the pipeline.

## Web read surface

The M3 web app (`web/`, ADR 0011) reads `manifest.json` and the normalized
MusicXML files directly. The contract between the pipeline and the player
is the following subset of each piece entry — any change to these field
names must update `web/src/lib/manifest.ts` in the same commit.

| Field                  | Used for                                                |
| ---------------------- | ------------------------------------------------------- |
| `candidate_id`         | URL routing (`/piece/:cid`).                            |
| `source`               | Surfaced on the piece detail header.                    |
| `file_url`             | "Upstream ↗" link (informational; not loaded).          |
| `page_url`             | "Upstream ↗" link target.                               |
| `normalized_path`      | Resolves to `web/public/musicxml/<filename>` at build.  |
| `metadata.title`       | Display + search.                                       |
| `metadata.composer`    | Display + search + sort.                                |
| `grade` / `grade_source`           | Curator grade; preferred over model.       |
| `model_grade` / `model_grade_source` | Fallback grade; placeholder badge if source starts with `dummy-`. |
| `duration_seconds`     | Approximate playback duration, shown on feed cards (M4). |

Other fields (hashes, license, parts, key_fifths, opus, instrument tokens)
are present in the manifest but not consumed by the web app at v0.1.

`duration_seconds` is written by `scripts/m4_duration_to_manifest.py`,
which joins the `duration_sec_approx` column from `corpus/features.csv`
back into the manifest. The number is a coarse estimate (single tempo,
single time signature, fallback to a per-note walk when those are
absent); it shouldn't be read as ground truth.

`web/scripts/copy-corpus.mjs` (run via `pnpm predev` / `prebuild`) mirrors
`manifest.json` to `web/public/manifest.json` and the normalized files to
`web/public/musicxml/`. Both destinations are gitignored — they're built
artifacts of the M1 pipeline output.

## Running the pipeline

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Run any/all discovery sources (each writes its own candidates.{source}.json):
python scripts/m1_discover_github.py
python scripts/m1_discover_imslp.py
# Fetch + validate operate on the union of every candidates.*.json:
python scripts/m1_fetch.py
python scripts/m1_validate.py
# Feature extraction over the accepted manifest:
python scripts/m2_features.py
# Distributional audit (for advisor review):
python scripts/m2_feature_audit.py
python scripts/m2_label_bias.py
python scripts/m2_baseline_grader.py
# Dummy-v0 training pipeline (placeholder labels; see ADR 0010):
python scripts/m2_dummy_advisor.py
python scripts/m2_train.py
python scripts/m2_eval.py
python scripts/m2_apply_to_manifest.py
```

`scripts/m1_discover_github.py` uses the `gh` CLI for auth and rate-limit handling — log in with `gh auth login` first.

Each script is idempotent: running it again with no upstream changes is a no-op. See `decisions/0005-ingest-pipeline.md` for the architecture and `decisions/0006-github-as-source.md` for source-selection rationale.
