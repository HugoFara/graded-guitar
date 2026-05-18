"""PDMX classical-guitar probe.

Filters PDMX.csv for solo nylon-guitar pieces in the
no_license_conflict subset, then runs our existing m1_validate
validator on each .mxl file extracted from the PDMX mxl tarball.
Writes report.md alongside this script.

Goal: gauge how many of the 660 candidates survive our classical-
guitar-solo bar (rejects multi-part, tab-only, fragments, off-range,
etc.). See decisions/0015-omr-feasibility-spike.md.

Usage:
    cd experiments/pdmx_probe
    python probe.py [--limit N] [--seed S]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import tarfile
from collections import Counter
from pathlib import Path

# Import the validator without going through m1_common's directory layout
SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from m1_validate import validate_one  # noqa: E402

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "PDMX.csv"
TAR_PATH = HERE / "mxl.tar.gz"
REPORT_PATH = HERE / "report.md"
CANDIDATES_JSON = HERE / "candidates.json"

NYLON = "24"  # General MIDI: Acoustic Guitar (nylon)


def gather_candidates(strict_classical: bool) -> list[dict]:
    """Filter PDMX.csv to solo nylon-guitar candidates.

    If `strict_classical`, also require either genres='classical' OR
    a known classical-era composer name (loose substring match) — this
    is the higher-precision filter to gauge how many are actual
    classical-guitar repertoire vs. fingerstyle pop / soundtrack arrs.
    """
    classical_composers = (
        "tarrega", "tárrega", "sor", "carcassi", "giuliani", "carulli",
        "aguado", "albeniz", "albéniz", "bach", "legnani", "coste",
        "tedesco", "rodrigo", "barrios", "brouwer", "ponce",
        "villa-lobos", "villa lobos", "regondi", "mertz", "diabelli",
        "weiss", "dowland", "cutting", "holborne", "mudarra",
        "narvaez", "narváez", "milán", "milan", "anonymous", "anon",
        "satie", "turina", "rameau", "scarlatti", "weiss", "ferrer",
        "tárrega", "alais", "torroba", "moreno", "lhoyer", "kuffner",
        "küffner", "kreutzer", "kost", "knjze", "horetzky",
    )
    out = []
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["n_tracks"] != "1":
                continue
            if NYLON not in row["tracks"].split("-"):
                continue
            if row["subset:no_license_conflict"] != "True":
                continue
            if strict_classical:
                composer = row["composer_name"].lower()
                genre = row["genres"].lower()
                if "classical" not in genre and not any(
                    cn in composer for cn in classical_composers
                ):
                    continue
            out.append(row)
    return out


def run_validate(candidates: list[dict], limit: int | None) -> dict:
    """Open the mxl tarball, validate each candidate's MXL bytes.

    Returns a dict with counts per outcome + the accepted list.
    """
    if limit:
        candidates = candidates[:limit]
    paths_wanted = {c["mxl"].lstrip("./"): c for c in candidates}
    accepted = []
    rejected: list[dict] = []
    by_code: Counter = Counter()
    seen = 0
    with tarfile.open(TAR_PATH, "r:gz") as tar:
        for member in tar:
            if not member.isfile():
                continue
            # Tarball entries are like "mxl/1/11/Qmbb….mxl"; CSV refs are
            # "./mxl/1/11/Qmbb….mxl". Strip the optional leading "./" on
            # both sides.
            name = member.name.lstrip("./")
            cand = paths_wanted.get(name)
            if cand is None:
                continue
            seen += 1
            try:
                blob = tar.extractfile(member).read()
            except (KeyError, AttributeError):
                rejected.append({"path": name, "code": "EXTRACT_FAILED"})
                by_code["EXTRACT_FAILED"] += 1
                continue
            result = validate_one(blob, "mxl")
            if result.get("ok"):
                accepted.append({
                    "path": name,
                    "composer": cand["composer_name"],
                    "title": cand["title"],
                    "genre": cand["genres"],
                    "n_bars": cand["song_length.bars"],
                    "n_notes": cand["n_notes"],
                    "metadata": result.get("metadata", {}),
                })
            else:
                code = result.get("code", "UNKNOWN")
                by_code[code] += 1
                rejected.append({
                    "path": name,
                    "composer": cand["composer_name"],
                    "title": cand["title"],
                    "code": code,
                    "detail": result.get("detail", ""),
                })
            if seen % 50 == 0:
                print(f"  validated {seen}/{len(paths_wanted)}…", file=sys.stderr)
    return {
        "n_candidates": len(paths_wanted),
        "n_validated": seen,
        "n_accepted": len(accepted),
        "n_rejected": len(rejected),
        "rejection_counts": dict(by_code),
        "accepted": accepted,
        "rejected": rejected,
    }


def write_report(loose: dict, strict: dict) -> None:
    lines: list[str] = []
    lines.append("# PDMX classical-guitar probe — report")
    lines.append("")
    lines.append("Per ADR 0015: probe PDMX for classical-guitar coverage")
    lines.append("before committing to OMR. Filter is *solo nylon-guitar")
    lines.append("piece in the no_license_conflict subset* (= MuseScore")
    lines.append("MIDI program 24, single track, clean copyright metadata).")
    lines.append("Each candidate is then run through our existing")
    lines.append("`m1_validate.py` classical-guitar bar (see ADR 0005).")
    lines.append("")

    for label, r in [("Loose filter (nylon + no_license_conflict)", loose),
                     ("Strict filter (+ classical genre OR known composer)", strict)]:
        lines.append(f"## {label}")
        lines.append("")
        n = r["n_candidates"]
        v = r["n_validated"]
        a = r["n_accepted"]
        rej = r["n_rejected"]
        rate = (100 * a / v) if v else 0
        lines.append(f"- Candidates after CSV filter: **{n}**")
        lines.append(f"- Files actually validated (in tarball): **{v}**")
        lines.append(f"- Accepted by m1_validate: **{a}** ({rate:.0f}%)")
        lines.append(f"- Rejected: **{rej}**")
        lines.append("")
        lines.append("### Rejections by code")
        lines.append("")
        for code, n in sorted(r["rejection_counts"].items(), key=lambda x: -x[1]):
            lines.append(f"- `{code}` — {n}")
        lines.append("")

    # Top composers in the strict-accepted set — quality signal
    lines.append("## Top composers in the strict-accepted set")
    lines.append("")
    comp = Counter(a["composer"] for a in strict["accepted"])
    for name, n in comp.most_common(25):
        lines.append(f"- {n}× {name}")
    lines.append("")

    lines.append("## Go/no-go reading")
    lines.append("")
    lines.append("Per ADR 0015 the threshold for proceeding to full PDMX")
    lines.append("ingest is **≥1,000 plausible classical-guitar pieces**")
    lines.append("after validation. Compare the strict-accepted count above")
    lines.append("against:")
    lines.append("")
    lines.append("- Current corpus: **801** accepted pieces")
    lines.append("- Guitar Loot share today: **53%** (the diversification target)")
    lines.append("- A 400-piece PDMX addition would put Guitar Loot at ~36%,")
    lines.append("  which crosses the reviewer's <40% bar.")
    lines.append("")
    lines.append("If strict-accepted < 200, the corpus impact is real but")
    lines.append("small — consider whether ClassClef outreach is a faster")
    lines.append("next step. If strict-accepted ≥ 400, write a discover")
    lines.append("script and ingest.")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {REPORT_PATH}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--limit", type=int, default=None,
                   help="Validate only the first N candidates (debug).")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    random.seed(args.seed)

    if not CSV_PATH.exists() or not TAR_PATH.exists():
        print("Missing PDMX.csv or mxl.tar.gz — run the curl downloads first.",
              file=sys.stderr)
        return 1

    loose = gather_candidates(strict_classical=False)
    strict = gather_candidates(strict_classical=True)
    print(f"loose candidates:  {len(loose)}")
    print(f"strict candidates: {len(strict)}")

    # The validator wants extracted .mxl bytes; we read them from the
    # tarball. Run both passes so the report shows the full filter funnel.
    print("Running validator on loose set…")
    loose_r = run_validate(loose, args.limit)
    print(f"  loose accepted: {loose_r['n_accepted']}/{loose_r['n_validated']}")
    print("Running validator on strict set…")
    strict_r = run_validate(strict, args.limit)
    print(f"  strict accepted: {strict_r['n_accepted']}/{strict_r['n_validated']}")

    write_report(loose_r, strict_r)

    CANDIDATES_JSON.write_text(
        json.dumps({"loose": loose_r, "strict": strict_r}, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {CANDIDATES_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
