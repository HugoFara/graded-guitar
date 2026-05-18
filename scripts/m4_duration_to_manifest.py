"""M4 — write duration_seconds into corpus/manifest.json.

Reads `corpus/features.csv` (output of `scripts/m2_features.py`) and
adds a `duration_seconds` field to every manifest entry that has a
`duration_sec_approx` row. The web feed (spec §7 M4) shows estimated
length on every card; this script is the bridge between the M2 feature
extractor and the M3+ web app.

The number is coarse — `scripts/m2_features.py` documents the formula
and its caveats (single tempo, single time signature, fallback to a
per-note walk when those are missing). Treat it as "ballpark", not
"timer."

Usage:
    python scripts/m2_features.py            # refresh features.csv
    python scripts/m4_duration_to_manifest.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from m1_common import MANIFEST_PATH, REPO_ROOT, load_manifest


DEFAULT_FEATURES = REPO_ROOT / "corpus" / "features.csv"


def apply_durations(manifest: dict, durations: dict[str, float]
                    ) -> tuple[int, int]:
    """Mutate manifest in place. Return (updated, skipped_no_duration)."""
    updated = 0
    skipped = 0
    for piece in manifest.get("pieces", []):
        cid = piece.get("candidate_id")
        if not cid or cid not in durations:
            skipped += 1
            continue
        piece["duration_seconds"] = durations[cid]
        updated += 1
    return updated, skipped


def load_durations(features_path: Path) -> dict[str, float]:
    durations: dict[str, float] = {}
    with features_path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            cid = row.get("candidate_id", "")
            value = (row.get("duration_sec_approx") or "").strip()
            if not cid or not value:
                continue
            try:
                durations[cid] = float(value)
            except ValueError:
                continue
    return durations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=DEFAULT_FEATURES)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args()

    if not args.features.exists():
        print(f"Missing {args.features}. Run scripts/m2_features.py first.",
              file=sys.stderr)
        return 1

    durations = load_durations(args.features)
    manifest = load_manifest()
    updated, skipped = apply_durations(manifest, durations)

    args.manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"==> Updated {updated} manifest entries; {skipped} had no duration.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
