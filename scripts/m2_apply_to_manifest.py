"""M2 Phase 3 (early) — write model_grade into corpus/manifest.json.

Reads `corpus/model_grades.csv` (output of `scripts/m2_train.py`) and
writes two new fields onto every manifest entry that has a prediction:

  - `model_grade`: the predicted band ("3"–"9")
  - `model_grade_source`: a version tag — `"dummy-v0"` while we're on
    placeholder labels, advisor sign-off bumps this to `"m2-v1@<sha>"`.

Curator grades (`grade` / `grade_source`) are left untouched — model
predictions are an *additional* field, not a replacement. The web
player (M3) prefers `grade` over `model_grade` when both are present.

ADR 0009 deferred this step to "post-validation," and ADR 0010 records
the decision to run it under a dummy-vN flag specifically so M3 can
proceed end-to-end. The dummy version tag is the swap-in marker for
the real advisor model.

Usage:
    python scripts/m2_apply_to_manifest.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from m1_common import MANIFEST_PATH, REPO_ROOT, load_manifest


DEFAULT_PREDICTIONS = REPO_ROOT / "corpus" / "model_grades.csv"


def apply_predictions(manifest: dict, preds_by_cid: dict[str, dict[str, str]]
                      ) -> tuple[int, int]:
    """Mutate manifest in place. Return (updated, skipped_no_pred)."""
    updated = 0
    skipped = 0
    for piece in manifest.get("pieces", []):
        cid = piece.get("candidate_id")
        if not cid or cid not in preds_by_cid:
            skipped += 1
            continue
        row = preds_by_cid[cid]
        piece["model_grade"] = row["predicted_grade"]
        piece["model_grade_source"] = row["model_version"]
        updated += 1
    return updated, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path,
                        default=DEFAULT_PREDICTIONS)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args()

    if not args.predictions.exists():
        print(f"Missing {args.predictions}. Run scripts/m2_train.py first.",
              file=sys.stderr)
        return 1

    with args.predictions.open(encoding="utf-8") as fh:
        preds_by_cid = {r["candidate_id"]: r for r in csv.DictReader(fh)}

    manifest = load_manifest()
    updated, skipped = apply_predictions(manifest, preds_by_cid)

    args.manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"==> Updated {updated} manifest entries; {skipped} had no prediction.")
    if updated and preds_by_cid:
        version = next(iter(preds_by_cid.values()))["model_version"]
        print(f"    model_grade_source written as `{version}`. ")
        if "dummy" in version:
            print("    REMINDER: this is placeholder data. The advisor "
                  "must swap dummy labels before M2 closes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
