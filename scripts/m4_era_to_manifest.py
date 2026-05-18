"""M4 — write `era` into corpus/manifest.json from the composer→era table.

Reads `corpus/composer_era.csv` (hand-curated, one row per unique
composer string seen in `manifest.json`) and tags every piece with
its composer's era. Lets the M4 feed (spec §7) filter by period
without needing to teach the manifest a new normalization pass.

The era taxonomy is coarse on purpose:
  renaissance | baroque | classical | romantic | modern | traditional | unknown

The mapping is the curator's call, not a hard musicological boundary.
Composers who straddle eras (Piccinini, Ferrabosco I/II, Polak) land
in whichever era best describes the bulk of their guitar/lute output.
Anonymous lute-book entries are tagged by the era of the source
manuscript when known.

Usage:
    python scripts/m4_era_to_manifest.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from m1_common import MANIFEST_PATH, REPO_ROOT, load_manifest


DEFAULT_TABLE = REPO_ROOT / "corpus" / "composer_era.csv"
VALID_ERAS = frozenset({
    "renaissance", "baroque", "classical",
    "romantic", "modern", "traditional", "unknown",
})


def load_era_table(path: Path) -> dict[str, str]:
    table: dict[str, str] = {}
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            composer = (row.get("composer") or "").strip()
            era = (row.get("era") or "").strip().lower()
            if not composer or not era:
                continue
            if era not in VALID_ERAS:
                raise ValueError(
                    f"{path}: era {era!r} for {composer!r} not in {sorted(VALID_ERAS)}"
                )
            table[composer] = era
    return table


def apply_era(manifest: dict, table: dict[str, str]) -> tuple[int, int, set[str]]:
    """Mutate manifest in place. Return (updated, skipped, unmapped_set)."""
    updated = 0
    skipped = 0
    unmapped: set[str] = set()
    for piece in manifest.get("pieces", []):
        meta = piece.get("metadata", {})
        composer = meta.get("composer_normalized") or meta.get("composer") or ""
        era = table.get(composer)
        if era is None:
            unmapped.add(composer)
            skipped += 1
            continue
        piece["era"] = era
        updated += 1
    return updated, skipped, unmapped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", type=Path, default=DEFAULT_TABLE)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args()

    if not args.table.exists():
        print(f"Missing {args.table}.", file=sys.stderr)
        return 1

    table = load_era_table(args.table)
    manifest = load_manifest()
    updated, skipped, unmapped = apply_era(manifest, table)

    args.manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"==> Wrote era to {updated} entries; {skipped} unmapped.")
    if unmapped:
        print("    Unmapped composer strings (add to composer_era.csv):")
        for c in sorted(unmapped):
            print(f"      {c!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
