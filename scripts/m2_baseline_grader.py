"""M2.4 — Rule-based baseline grader over `corpus/features.csv`.

Assigns a tentative grade to every piece in the corpus using fixed,
hand-readable rules. **No model fitting, no threshold tuning against
labels.** The point is to give the advisor a concrete starting object
to react to ("does this rule produce the grade you would assign?")
without committing to any ML or to thresholds the advisor hasn't seen.

Method:
  1. Pick a small fixed set of features with positive expected
     correlation to difficulty: highest pitch, polyphonic density,
     voice count, polyphony coverage, length. Each is sourced from
     `corpus/features.csv` (see `scripts/m2_features.py`).
  2. For each piece, compute the corpus percentile of each feature.
  3. Composite percentile = mean of those per-feature percentiles
     (equal weights — no fitting).
  4. Map composite percentile → grade band using a fixed cut table
     spanning G3–G8 (the empirical range of the Delcamp labels we
     have; see `corpus/label_bias.md`).

Outputs:
  - `corpus/baseline_grades.csv` — one row per piece with composite
    score, predicted grade, and (where present) the Delcamp grade.
  - `corpus/baseline_grader.md` — confusion matrix vs Delcamp,
    exact / off-by-one agreement rates, per-grade hit rate, and
    a handful of high- and low-agreement examples.

Pure stdlib.

Usage:
    python scripts/m2_baseline_grader.py
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

from m1_common import REPO_ROOT


DEFAULT_IN_PATH = REPO_ROOT / "corpus" / "features.csv"
DEFAULT_OUT_CSV = REPO_ROOT / "corpus" / "baseline_grades.csv"
DEFAULT_OUT_MD = REPO_ROOT / "corpus" / "baseline_grader.md"

# Features the rule uses. All have ≥90% coverage in the current corpus
# (see `corpus/feature_audit.md`) and all trend with grade in the
# per-grade median table. Equal-weighted on purpose: weighting by
# correlation with labels would be ML in disguise.
RULE_FEATURES = [
    "midi_max",                  # ceiling of pitch — higher positions are harder
    "max_chord_stack",           # densest simultaneous chord
    "voice_count_max",           # max independent voices
    "polyphonic_measure_ratio",  # fraction of measures with simultaneity
    "measure_count",             # length proxy
]

# Composite percentile cut points → grade band. Anchored to the
# Delcamp range we actually have in the corpus (G3 to G9, with
# G6–G8 dominant). Lower bounds are inclusive, upper bounds are
# exclusive except the last.
GRADE_BANDS: list[tuple[float, float, str]] = [
    (0.0,   20.0,  "3"),
    (20.0,  35.0,  "5"),
    (35.0,  55.0,  "6"),
    (55.0,  80.0,  "7"),
    (80.0, 101.0,  "8"),
]


def _to_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _percentile_ranks(values: list[float]) -> dict[float, float]:
    """Map each distinct value to its percentile rank (0-100).

    Uses the 'average' definition: values equal to v get the average
    of the ranks they would occupy under any tie-breaker. Returns a
    dict keyed by raw value.
    """
    s = sorted(values)
    n = len(s)
    out: dict[float, float] = {}
    i = 0
    while i < n:
        j = i
        while j < n and s[j] == s[i]:
            j += 1
        avg_rank = (i + 1 + j) / 2  # 1-indexed average rank within ties
        out[s[i]] = 100 * (avg_rank - 1) / max(n - 1, 1)
        i = j
    return out


def _band_for(percentile: float) -> str:
    for lo, hi, label in GRADE_BANDS:
        if lo <= percentile < hi:
            return label
    return GRADE_BANDS[-1][2]


def grade_corpus(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return rows enriched with composite_percentile and predicted_grade."""
    # Per-feature percentile lookup, built on the non-empty subset.
    feature_pct: dict[str, dict[float, float]] = {}
    for f in RULE_FEATURES:
        vs = [_to_float(r[f]) for r in rows]
        vs = [v for v in vs if v is not None]
        feature_pct[f] = _percentile_ranks(vs)

    enriched: list[dict[str, str]] = []
    for r in rows:
        pcts: list[float] = []
        per_feature: dict[str, float | None] = {}
        for f in RULE_FEATURES:
            v = _to_float(r[f])
            if v is None:
                per_feature[f] = None
                continue
            p = feature_pct[f].get(v)
            per_feature[f] = p
            if p is not None:
                pcts.append(p)
        if not pcts:
            composite = None
            predicted = ""
        else:
            composite = sum(pcts) / len(pcts)
            predicted = _band_for(composite)
        enriched.append({
            "candidate_id": r["candidate_id"],
            "source": r["source"],
            "title": r["title"],
            "composer_normalized": r["composer_normalized"],
            "grade": r.get("grade", ""),
            "grade_source": r.get("grade_source", ""),
            "predicted_grade": predicted,
            "composite_percentile": (
                f"{composite:.1f}" if composite is not None else ""
            ),
            **{
                f"{f}_pct": (
                    f"{per_feature[f]:.1f}" if per_feature[f] is not None else ""
                )
                for f in RULE_FEATURES
            },
        })
    return enriched


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def render_report(enriched: list[dict[str, str]]) -> str:
    labelled = [r for r in enriched if r["grade"] and r["predicted_grade"]]
    grades = sorted(
        {r["grade"] for r in labelled} | {r["predicted_grade"] for r in labelled},
        key=lambda x: int(x) if x.isdigit() else 99,
    )

    lines: list[str] = []
    lines.append("# M2 baseline grader")
    lines.append("")
    lines.append(f"- Pieces graded by rule: **{sum(1 for r in enriched if r['predicted_grade'])} / {len(enriched)}**")
    lines.append(f"- Of those, **{len(labelled)}** also have a Delcamp grade for comparison.")
    lines.append("")
    lines.append("Output of `scripts/m2_baseline_grader.py`. The rule:")
    lines.append("")
    lines.append("1. For each feature in the rule set, compute the corpus percentile.")
    lines.append("2. Composite = mean of the per-feature percentiles (equal weights).")
    lines.append("3. Map composite percentile to a grade band:")
    lines.append("")
    lines.append("| composite percentile | grade |")
    lines.append("| --- | --- |")
    for lo, hi, label in GRADE_BANDS:
        lines.append(f"| [{lo:.0f}, {hi:.0f}) | G{label} |")
    lines.append("")
    lines.append("Rule features (all monotone with Delcamp grade in `feature_audit.md`):")
    lines.append("")
    for f in RULE_FEATURES:
        lines.append(f"- `{f}`")
    lines.append("")
    lines.append(
        "**No threshold tuning against labels.** The cut points are fixed "
        "anchors over the empirical Delcamp range, not optimised. The "
        "purpose is to give the advisor something concrete to react to, "
        "not to win an accuracy benchmark."
    )
    lines.append("")

    if not labelled:
        return "\n".join(lines) + "\n"

    # Confusion matrix.
    matrix: dict[tuple[str, str], int] = Counter(
        (r["grade"], r["predicted_grade"]) for r in labelled
    )
    lines.append("## Confusion matrix")
    lines.append("")
    lines.append("Rows = Delcamp grade, columns = rule prediction.")
    lines.append("")
    header = ["Delcamp \\ rule"] + [f"G{g}" for g in grades] + ["n"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for g in grades:
        row_n = sum(1 for r in labelled if r["grade"] == g)
        cells = [f"G{g}"]
        for p in grades:
            cnt = matrix.get((g, p), 0)
            cells.append(str(cnt) if cnt else "·")
        cells.append(str(row_n))
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    # Headline agreement metrics.
    exact = sum(1 for r in labelled if r["grade"] == r["predicted_grade"])
    off_by_one = sum(
        1 for r in labelled
        if abs(int(r["grade"]) - int(r["predicted_grade"])) <= 1
    )
    lines.append("## Agreement headline")
    lines.append("")
    lines.append(f"- **Exact match:** {exact} / {len(labelled)} "
                 f"({100 * exact / len(labelled):.1f}%)")
    lines.append(f"- **Within ±1 grade:** {off_by_one} / {len(labelled)} "
                 f"({100 * off_by_one / len(labelled):.1f}%)")
    lines.append("")
    lines.append(
        "Context: the corpus is composer-confounded "
        "(see `corpus/label_bias.md`) — most Delcamp grades are constant "
        "within composer. The rule does *not* see composer, so its "
        "predictions will scatter inside each composer's actual grade. "
        "Read low exact-match alongside the confusion matrix, not in "
        "isolation."
    )
    lines.append("")

    # Per-grade hit rate (Delcamp G_x → fraction predicted G_x).
    lines.append("## Per-Delcamp-grade hit rate")
    lines.append("")
    lines.append("| Delcamp grade | n | exact | within ±1 |")
    lines.append("| --- | --- | --- | --- |")
    for g in grades:
        subset = [r for r in labelled if r["grade"] == g]
        if not subset:
            continue
        e = sum(1 for r in subset if r["predicted_grade"] == g)
        o = sum(1 for r in subset
                if abs(int(g) - int(r["predicted_grade"])) <= 1)
        lines.append(
            f"| G{g} | {len(subset)} | "
            f"{e} ({100*e/len(subset):.0f}%) | "
            f"{o} ({100*o/len(subset):.0f}%) |"
        )
    lines.append("")

    # Concrete examples.
    lines.append("## Examples")
    lines.append("")
    by_disagreement = sorted(
        labelled,
        key=lambda r: abs(int(r["grade"]) - int(r["predicted_grade"])),
    )
    lines.append("Five pieces where the rule agrees with Delcamp exactly:")
    lines.append("")
    for r in by_disagreement[:5]:
        lines.append(f"- G{r['grade']} (rule G{r['predicted_grade']}, "
                     f"composite {r['composite_percentile']}) — "
                     f"{r['composer_normalized']}, *{r['title']}*")
    lines.append("")
    lines.append("Five pieces with the largest disagreement:")
    lines.append("")
    for r in reversed(by_disagreement[-5:]):
        delta = int(r["predicted_grade"]) - int(r["grade"])
        lines.append(f"- Delcamp G{r['grade']} vs rule G{r['predicted_grade']} "
                     f"(Δ={delta:+d}, composite {r['composite_percentile']}) — "
                     f"{r['composer_normalized']}, *{r['title']}*")
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in-path", type=Path, default=DEFAULT_IN_PATH,
                        dest="in_path")
    parser.add_argument("--out-csv", type=Path, default=DEFAULT_OUT_CSV)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
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

    enriched = grade_corpus(rows)
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    write_csv(enriched, args.out_csv)
    args.out_md.write_text(render_report(enriched), encoding="utf-8")
    print(f"==> Wrote {args.out_csv}")
    print(f"==> Wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
