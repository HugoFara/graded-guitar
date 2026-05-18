"""M2.2 — Distributional audit of corpus/features.csv.

Reads the M2 feature extract, computes per-grade summary statistics for
each numeric feature, and flags pairs of features with Pearson
correlation above a threshold. Writes a single markdown report at
`corpus/feature_audit.md` intended to be the advisor's entry point
into the Phase 1 feature list (see decisions/0009-m2-grading-inputs.md).

Pure stdlib + no model fitting. The advisor reads this *before*
authorising Phase 2 training.

Usage:
    python scripts/m2_feature_audit.py
    python scripts/m2_feature_audit.py --out /tmp/audit.md
    python scripts/m2_feature_audit.py --corr-threshold 0.8
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from m1_common import REPO_ROOT


DEFAULT_IN_PATH = REPO_ROOT / "corpus" / "features.csv"
DEFAULT_OUT_PATH = REPO_ROOT / "corpus" / "feature_audit.md"

# Columns that aren't features (skip in numeric summaries).
META_COLUMNS = {
    "candidate_id", "source", "title", "composer_normalized",
    "grade", "grade_source", "time_sig",
}


def _to_float(value: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _summary(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"n": 0}
    s = sorted(values)
    n = len(s)
    return {
        "n": n,
        "min": round(s[0], 2),
        "p25": round(s[n // 4], 2),
        "median": round(statistics.median(s), 2),
        "p75": round(s[(3 * n) // 4], 2),
        "max": round(s[-1], 2),
        "mean": round(statistics.fmean(s), 2),
    }


def _format_summary(s: dict[str, float | int]) -> str:
    if s.get("n", 0) == 0:
        return "—"
    return (f"n={s['n']} · "
            f"med={s['median']} (p25={s['p25']}, p75={s['p75']}) · "
            f"range=[{s['min']}, {s['max']}]")


def render_report(rows: list[dict[str, str]], corr_threshold: float) -> str:
    numeric_cols = [
        c for c in rows[0].keys()
        if c not in META_COLUMNS
    ]

    # Per-column overall + per-grade distributions.
    overall: dict[str, list[float]] = {c: [] for c in numeric_cols}
    by_grade: dict[str, dict[str, list[float]]] = {
        c: defaultdict(list) for c in numeric_cols
    }
    by_source: dict[str, dict[str, list[float]]] = {
        c: defaultdict(list) for c in numeric_cols
    }
    for r in rows:
        grade = r.get("grade") or ""
        source = (r.get("source") or "").split(":", 1)[0]
        for c in numeric_cols:
            v = _to_float(r[c])
            if v is None:
                continue
            overall[c].append(v)
            if grade:
                by_grade[c][grade].append(v)
            if source:
                by_source[c][source].append(v)

    grades = sorted(
        {g for r in rows if (g := r.get("grade"))},
        key=lambda x: int(x) if x.isdigit() else 99,
    )
    sources = sorted({
        (r.get("source") or "").split(":", 1)[0]
        for r in rows
        if r.get("source")
    })

    # Pairwise Pearson correlations on shared non-empty rows.
    correlations: list[tuple[str, str, float]] = []
    for i, a in enumerate(numeric_cols):
        for b in numeric_cols[i + 1:]:
            xs, ys = [], []
            for r in rows:
                va = _to_float(r[a])
                vb = _to_float(r[b])
                if va is None or vb is None:
                    continue
                xs.append(va)
                ys.append(vb)
            if len(xs) < 30:
                continue
            try:
                corr = statistics.correlation(xs, ys)
            except statistics.StatisticsError:
                continue
            correlations.append((a, b, corr))

    high_corr = sorted(
        [(a, b, c) for (a, b, c) in correlations if abs(c) >= corr_threshold],
        key=lambda t: -abs(t[2]),
    )

    # --------- render -----------------------------------------------
    lines: list[str] = []
    lines.append("# M2 feature audit")
    lines.append("")
    lines.append(f"- Pieces: **{len(rows)}**")
    labelled = sum(1 for r in rows if r.get("grade"))
    lines.append(f"- Pieces with curator grade: **{labelled}**")
    lines.append(f"- Grades present: {', '.join('G' + g for g in grades) or '(none)'}")
    lines.append(f"- Sources: {', '.join(sources) or '(none)'}")
    lines.append(f"- Correlation threshold for flagging: |r| ≥ {corr_threshold}")
    lines.append("")
    lines.append("Output of `scripts/m2_feature_audit.py`. Inputs come from "
                 "`corpus/features.csv` (see `scripts/m2_features.py` and "
                 "`decisions/0009-m2-grading-inputs.md`). This file is meant "
                 "to be the advisor's entry point to the M2 feature list — "
                 "everything below is a deterministic summary, not a model "
                 "decision.")
    lines.append("")

    # Per-grade summary table — pivots on Delcamp grade.
    lines.append("## Per-grade summary (median)")
    lines.append("")
    header = ["feature"] + [f"G{g} (n={len(by_grade[numeric_cols[0]].get(g, []))})" for g in grades]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for c in numeric_cols:
        row = [c]
        for g in grades:
            vs = by_grade[c].get(g, [])
            if not vs:
                row.append("—")
            else:
                row.append(f"{round(statistics.median(vs), 2)}")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    # Per-source summary — different sources have different style coverage.
    lines.append("## Per-source summary (median)")
    lines.append("")
    s_header = ["feature"] + [f"{s} (n={len(by_source[numeric_cols[0]].get(s, []))})" for s in sources]
    lines.append("| " + " | ".join(s_header) + " |")
    lines.append("| " + " | ".join(["---"] * len(s_header)) + " |")
    for c in numeric_cols:
        row = [c]
        for s in sources:
            vs = by_source[c].get(s, [])
            if not vs:
                row.append("—")
            else:
                row.append(f"{round(statistics.median(vs), 2)}")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    # Overall distribution for each feature — full quartiles.
    lines.append("## Overall distribution per feature")
    lines.append("")
    for c in numeric_cols:
        s = _summary(overall[c])
        lines.append(f"- **`{c}`** — {_format_summary(s)}")
    lines.append("")

    # Correlation flags — pairs the model will see as redundant.
    lines.append("## Flagged collinearity")
    lines.append("")
    if not high_corr:
        lines.append(f"No pairs at |r| ≥ {corr_threshold}.")
    else:
        lines.append(
            f"Pairs with |r| ≥ {corr_threshold} on the shared non-empty subset. "
            "High correlation isn't fatal — gradient-boosted trees handle it — "
            "but the advisor may want to keep only the more interpretable "
            "feature from each pair."
        )
        lines.append("")
        lines.append("| feature A | feature B | r |")
        lines.append("| --- | --- | --- |")
        for a, b, c in high_corr:
            lines.append(f"| `{a}` | `{b}` | {c:+.2f} |")
    lines.append("")

    # Pieces with missing key features — useful for spotting extraction gaps.
    lines.append("## Coverage gaps")
    lines.append("")
    interesting = [
        "tempo_bpm", "smallest_division", "duration_sec_approx",
        "position_shift_proxy", "key_fifths",
    ]
    for c in interesting:
        missing = sum(1 for r in rows if not r.get(c))
        pct = round(100 * missing / len(rows), 1)
        lines.append(f"- `{c}`: {missing} / {len(rows)} pieces missing ({pct}%)")
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in-path", type=Path, default=DEFAULT_IN_PATH,
                        dest="in_path")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_PATH)
    parser.add_argument("--corr-threshold", type=float, default=0.7)
    args = parser.parse_args()

    if not args.in_path.exists():
        print(f"Missing {args.in_path}. Run scripts/m2_features.py first.",
              file=sys.stderr)
        return 1

    with args.in_path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        print(f"{args.in_path} has no rows.", file=sys.stderr)
        return 1

    report = render_report(rows, args.corr_threshold)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(f"==> Wrote audit to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
