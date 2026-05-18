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

## What's gitignored

- `raw/` — content-addressed cache of downloaded files (`{sha256}.musicxml` or `{sha256}.mxl`). Populated by `scripts/m1_fetch.py`.
- `normalized/` — normalized MusicXML per accepted piece, keyed by stable piece ID.
- `cache/` — HTTP cache, intermediate artifacts.

Bulk MusicXML is kept out of the repo so cloning stays fast and so we don't redistribute upstream files. Anyone can rebuild `raw/` and `normalized/` from the committed JSON by re-running the pipeline.

## Running the pipeline

```bash
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
```

`scripts/m1_discover_github.py` uses the `gh` CLI for auth and rate-limit handling — log in with `gh auth login` first.

Each script is idempotent: running it again with no upstream changes is a no-op. See `decisions/0005-ingest-pipeline.md` for the architecture and `decisions/0006-github-as-source.md` for source-selection rationale.
