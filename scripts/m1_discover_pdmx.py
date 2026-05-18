"""M1.1 (PDMX) — ingest classical-guitar pieces from the PDMX dataset.

PDMX is the Public Domain MusicXML Dataset (Long et al., NeurIPS
2024) — 254K MusicXML scores scraped from MuseScore's public-domain
pool, distributed as CC-BY-4.0 on Zenodo. We filter the
`no_license_conflict` subset for *solo nylon-guitar* pieces (General
MIDI program 24, single track) and ingest the surviving .mxl files.

Unlike the GitHub / Mutopia / Guitar Loot discover scripts, PDMX is
shipped as a single 1.9 GB local tarball. This script reads the
tarball directly: it extracts the eligible .mxl bytes into
`corpus/raw/` under content-addressed sha256 names and updates
`corpus/cache/fetch_log.json` so `m1_validate.py` picks them up on
its next run. No HTTP fetch is needed.

The downloads themselves (`PDMX.csv` and `mxl.tar.gz`) live under
`experiments/pdmx_probe/` and are gitignored. See:
- decisions/0015-omr-feasibility-spike.md (the strategic call)
- experiments/pdmx_probe/report.md (the dry-run probe numbers)

Usage:
    python scripts/m1_discover_pdmx.py
    python scripts/m1_discover_pdmx.py --limit 50  # debug
    python scripts/m1_discover_pdmx.py --csv path --tarball path
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import tarfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from m1_common import (
    CACHE_DIR,
    CORPUS_DIR,
    RAW_DIR,
    ensure_corpus_dirs,
    read_json,
    write_json_atomic,
)


CANDIDATES_PATH = CORPUS_DIR / "candidates.pdmx.json"
FETCH_LOG_PATH = CACHE_DIR / "fetch_log.json"

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = REPO_ROOT / "experiments" / "pdmx_probe" / "PDMX.csv"
DEFAULT_TARBALL = REPO_ROOT / "experiments" / "pdmx_probe" / "mxl.tar.gz"

NYLON = "24"  # General MIDI: Acoustic Guitar (nylon) = classical guitar.

# CC-BY-4.0 covers the *dataset*; individual works are mostly cc-zero
# (CC0) or publicdomain marker. Both are redistributable without
# attribution; we still record per-piece licensing for transparency.
LICENSE_SPDX_BY_CSV_VALUE = {
    "cc-zero": "CC0-1.0",
    "publicdomain": "PD-Marker",
}


@dataclass
class PdmxCandidate:
    candidate_id: str
    source: str
    file_url: str
    page_url: str
    license: str
    license_spdx: str
    composer: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _is_eligible(row: dict[str, str]) -> bool:
    """Loose filter: solo nylon-guitar, no_license_conflict subset.

    The probe (experiments/pdmx_probe/report.md) confirmed this surfaces
    660 candidates of which 307 survive m1_validate. We intentionally
    do NOT narrow further at discover time — let the validator decide.
    Pieces that fail validation are logged as rejections, which is the
    same treatment every other source gets.
    """
    if row["n_tracks"] != "1":
        return False
    if NYLON not in row["tracks"].split("-"):
        return False
    if row["subset:no_license_conflict"] != "True":
        return False
    return True


def _candidate_id_from_mxl_path(mxl_path: str) -> str:
    """Strip the leading "./" and the .mxl extension to get a stable id.

    Example: "./mxl/1/11/QmbbXYZ….mxl" → "pdmx:QmbbXYZ…"

    The trailing component (the IPFS-style content hash) is unique
    across all of PDMX, so the candidate_id remains stable across
    re-runs even if the directory layout changes upstream.
    """
    stem = Path(mxl_path).name.removesuffix(".mxl")
    return f"pdmx:{stem}"


def _gather_candidates(csv_path: Path, limit: int | None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not _is_eligible(row):
                continue
            rows.append(row)
            if limit is not None and len(rows) >= limit:
                break
    return rows


def _save_blob(blob: bytes, ext: str) -> tuple[str, Path]:
    """Mirror m1_fetch.save_blob() so artefacts land in the same shape."""
    digest = hashlib.sha256(blob).hexdigest()
    path = RAW_DIR / f"{digest}.{ext}"
    if not path.exists():
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(blob)
        tmp.replace(path)
    return digest, path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    p.add_argument("--tarball", type=Path, default=DEFAULT_TARBALL)
    p.add_argument("--limit", type=int, default=None,
                   help="Stop after N candidates (debug).")
    args = p.parse_args()

    if not args.csv.exists():
        print(f"missing CSV: {args.csv}", file=sys.stderr)
        print("Download from https://zenodo.org/records/15571083", file=sys.stderr)
        return 1
    if not args.tarball.exists():
        print(f"missing tarball: {args.tarball}", file=sys.stderr)
        return 1

    ensure_corpus_dirs()

    rows = _gather_candidates(args.csv, args.limit)
    print(f"==> {len(rows)} eligible CSV rows")

    # Index by the in-tarball path so a single pass over the tarball
    # extracts everything in tar-write order (much faster than seek-
    # to-each-file).
    by_tarpath: dict[str, dict[str, str]] = {}
    for row in rows:
        # CSV column 'mxl' values look like "./mxl/1/11/Qmbb….mxl";
        # tar members look like "mxl/1/11/Qmbb….mxl".
        tarpath = row["mxl"].lstrip("./")
        by_tarpath[tarpath] = row

    fetch_log: dict[str, Any] = read_json(
        FETCH_LOG_PATH, default={"version": 1, "entries": {}}
    )
    entries: dict[str, Any] = fetch_log.get("entries", {})

    candidates: list[PdmxCandidate] = []
    extracted = 0
    cached = 0
    with tarfile.open(args.tarball, "r:gz") as tar:
        for member in tar:
            if not member.isfile():
                continue
            tarpath = member.name.lstrip("./")
            row = by_tarpath.get(tarpath)
            if row is None:
                continue
            cid = _candidate_id_from_mxl_path(tarpath)

            if cid in entries and entries[cid].get("status") == "ok":
                cached += 1
                # Still emit the candidate row so m1_validate has the
                # license/source/composer metadata available.
            else:
                f = tar.extractfile(member)
                blob = f.read() if f else b""
                if not blob:
                    entries[cid] = {
                        "status": "failed",
                        "reason": "EMPTY_TAR_MEMBER",
                        "url": f"tarball:{args.tarball.name}#{tarpath}",
                    }
                    continue
                digest, path = _save_blob(blob, "mxl")
                entries[cid] = {
                    "status": "ok",
                    "sha256": digest,
                    "format": "mxl",
                    "size_bytes": len(blob),
                    "path": str(path.relative_to(RAW_DIR.parent.parent)),
                    "url": f"tarball:{args.tarball.name}#{tarpath}",
                }
                extracted += 1

            license_csv = row.get("license") or ""
            license_spdx = LICENSE_SPDX_BY_CSV_VALUE.get(
                license_csv, license_csv.upper() or "unknown"
            )
            candidates.append(PdmxCandidate(
                candidate_id=cid,
                source="pdmx",
                # The "URL" here is a stable reference to the dataset
                # entry, not a fetchable HTTP URL. Zenodo doesn't expose
                # per-file URLs; the page_url points to the dataset
                # record. This is honest provenance even if downstream
                # tools have to know what 'tarball:' means.
                file_url=f"tarball:{args.tarball.name}#{tarpath}",
                page_url="https://zenodo.org/records/15571083",
                license=row.get("license_url") or license_csv or "unknown",
                license_spdx=license_spdx,
                composer=row.get("composer_name") or "",
            ))

            # Flush periodically so a crash mid-tarball doesn't lose work.
            if (extracted + cached) % 100 == 0:
                write_json_atomic(FETCH_LOG_PATH, {"version": 1, "entries": entries})

    write_json_atomic(FETCH_LOG_PATH, {"version": 1, "entries": entries})

    payload = {
        "version": 2,
        "source": "pdmx",
        "source_host": "zenodo.org",
        "items": [c.to_dict() for c in candidates],
    }
    write_json_atomic(CANDIDATES_PATH, payload)

    print(f"==> Extracted: {extracted}; cached: {cached}")
    print(f"==> Wrote {CANDIDATES_PATH.relative_to(REPO_ROOT)} "
          f"({len(candidates)} candidates)")
    print(f"==> Updated {FETCH_LOG_PATH.relative_to(REPO_ROOT)}")
    print("Next: python scripts/m1_validate.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
