"""M2.3 — Label-bias diagnostics for `corpus/features.csv`.

Quantifies how much of the Delcamp grade signal is actually
composer/era signal. The 427 graded pieces are all Guitar Loot
(Crouch's Renaissance/Baroque arrangements), and an early sanity
check showed that Crouch assigned grades *per-composer*, not per-piece
— e.g. every Dowland is G8, every Holborne is G6. This script makes
that pattern explicit, in a form the advisor can read before
authorising Phase 2 of ADR 0009.

Outputs a single markdown report at `corpus/label_bias.md`.

Sections:
  1. Composer × grade cross-tab (top composers).
  2. Per-composer grade dispersion — composers whose pieces all sit
     at one grade can't teach the model within-composer difficulty.
  3. Per-grade composer concentration — top-1 / top-3 share, plus
     Herfindahl index. Reveals which grades are essentially one
     composer.
  4. Era × grade — hand-curated era map over the top composers.
  5. Per-feature composer η² (between-composer variance / total).
     Features with η² close to 1 are composer proxies.
  6. Bottom-line text summary.

Stdlib only.

Usage:
    python scripts/m2_label_bias.py
    python scripts/m2_label_bias.py --out /tmp/bias.md
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

from m1_common import REPO_ROOT


DEFAULT_IN_PATH = REPO_ROOT / "corpus" / "features.csv"
DEFAULT_OUT_PATH = REPO_ROOT / "corpus" / "label_bias.md"

META_COLUMNS = {
    "candidate_id", "source", "title", "composer_normalized",
    "grade", "grade_source", "time_sig",
}

# Hand-curated era assignments for composers present in the graded
# subset. Built from Guitar Loot's top composers plus common classical-
# era names. Composers not matched land in "Unknown" — the report
# makes the unmapped share visible so the advisor can see what's
# missing. Era buckets are coarse on purpose: the goal is to expose
# stylistic confounding, not to do musicology.
COMPOSER_ERA: dict[str, str] = {
    # Renaissance / Jacobean lute (~1500-1620)
    "John Dowland": "Renaissance",
    "Anthony Holborne": "Renaissance",
    "William Corkine": "Renaissance",
    "Francis Cutting": "Renaissance",
    "Jakub Polak": "Renaissance",
    "Daniel Bacheler": "Renaissance",
    "Thomas Robinson": "Renaissance",
    "Tobias Hume": "Renaissance",
    "John Danyel": "Renaissance",
    "Francis Pilkington": "Renaissance",
    "Luis de Milán": "Renaissance",
    "Alonso Mudarra": "Renaissance",
    "Vincenzo Galilei": "Renaissance",
    "Adrian Le Roy": "Renaissance",
    "Anon": "Renaissance",
    "Anon, Pickering Lute Book": "Renaissance",
    "Richard Allison": "Renaissance",
    "Cuthbert Hely": "Renaissance",
    "Michelangelo Galilei": "Renaissance",
    "Thomas Smyth": "Renaissance",
    "Alfonso Ferrabosco 1": "Renaissance",
    "Alfonso Ferrabosco the younger": "Renaissance",
    "Robert Johnson": "Renaissance",
    "Martin Peerson": "Renaissance",
    "Nicolaes Vallet": "Renaissance",
    "Joseph Sherlie": "Renaissance",
    "John Whitfield": "Renaissance",
    "Nicholas Strogers": "Renaissance",
    "Augustine Bassano": "Renaissance",
    "William Hollis": "Renaissance",
    "Michael Cavendish": "Renaissance",
    "Thomas Vautor": "Renaissance",
    "Hans Leo Hassler": "Renaissance",
    "P Guedron": "Renaissance",
    "Pierre Guédron": "Renaissance",
    "Anthony de Countie": "Renaissance",
    "Germain Pinel, Pickering Lute Book": "Renaissance",
    # Baroque (~1620-1750)
    "Giovanni Paolo Foscarini": "Baroque",
    "Sylvius Leopold Weiss": "Baroque",
    "Henry Purcell": "Baroque",
    "Robert de Visée": "Baroque",
    "Robert de Visee": "Baroque",
    "Gaspar Sanz": "Baroque",
    "Johann Sebastian Bach": "Baroque",
    "J.S. Bach": "Baroque",
    "Alessandro Piccinini": "Baroque",
    "Esaias Reusner": "Baroque",
    "Domenico Pellegrini": "Baroque",
    "Johann Hieronymous Kapsberger": "Baroque",
    "Jean Mercure": "Baroque",
    "Daniel Purcell": "Baroque",
    "William Lawes": "Baroque",
    "Robert Ballard": "Baroque",
    "Jacques Gallot": "Baroque",
    "Germain Pinel": "Baroque",
    "Gaultier": "Baroque",
    "Simon Ives": "Baroque",
    "Jean-Baptiste Besard": "Baroque",
    "Charles Mouton": "Baroque",
    "Enemond Gaultier": "Baroque",
    "H. I. F. von Biber": "Baroque",
    "Johann Hermann Schein": "Baroque",
    "Philip van Wilder": "Renaissance",
    "Phillip Franz Le Sage de Richée": "Baroque",
    "Edward Pierce": "Renaissance",
    "Newman": "Renaissance",
    "Baruch Bulman": "Renaissance",
    "Ambrose Lupo": "Renaissance",
    "Richard Green": "Renaissance",
    # Casing / spelling variants emitted by Guitar Loot.
    "MARTIN PEERSON": "Renaissance",
    "Anthoy Holborne": "Renaissance",
    "Silvius Leopold Weiss": "Baroque",
    "Silvius Leopold WEISS": "Baroque",
    "Alfonso Ferrabosco I": "Renaissance",
    "Alfonso Ferrabosco": "Renaissance",
    # More historical composers found in the long tail.
    "René Saman": "Renaissance",
    "Giulio Abondante": "Renaissance",
    "Joanambrosio Dalza": "Renaissance",
    "Joan Ambrosio Dalza": "Renaissance",
    "Marco dall'Aquila": "Renaissance",
    "Daniel Farrant": "Renaissance",
    "Jakup Polak": "Renaissance",
    "Jacob Polak": "Renaissance",
    "Emmanuel Adriaenssen": "Renaissance",
    "John Coprario": "Renaissance",
    "John McLauchland": "Renaissance",
    "David Grieve": "Renaissance",
    "Antonio Vivaldi": "Baroque",
    "Johann Hieronymus Kapsberger": "Baroque",
    "Dietrich Steffkins": "Baroque",
    "Joseph Bodin de Boismortier": "Baroque",
    "Dieterich Buxtehude": "Baroque",
    "Santiago de Murcia": "Baroque",
    "Carl Friedrich Abel": "Classical",
    # Classical (~1750-1820)
    "Fernando Sor": "Classical",
    "Mauro Giuliani": "Classical",
    "Matteo Carcassi": "Classical",
    "Dionisio Aguado": "Classical",
    "Ferdinando Carulli": "Classical",
    # Romantic (~1820-1900)
    "Francisco Tárrega": "Romantic",
    "Napoléon Coste": "Romantic",
    "Johann Kaspar Mertz": "Romantic",
    # Modern (post-1900)
    "Heitor Villa-Lobos": "Modern",
    "Agustín Barrios Mangoré": "Modern",
    "Leo Brouwer": "Modern",
    "Antonio Lauro": "Modern",
}

# Manuscript / source markers that confidently place a piece in the
# Renaissance / Jacobean era when its composer field is "Anon" or a
# source-suffixed variant ("Anon, Cosens Lute Book", etc.).
_RENAISSANCE_SOURCE_MARKERS = (
    "lute book", "16th century", "cosens lute", "balcarres",
    "pickering lute", "willoughby lute", "margaret board",
    "hirsch lute", "hisch lute", "cul ms", "dd.2.11", "dd. 2.11",
    "dd.9.33", "combined sources", "manuscrit d'haslemere",
    "dolmetsch library",
)

# Leading qualifiers we strip before mapping. "?" is the curator's
# uncertainty marker; "Attr." and "after" are attribution hedges. The
# underlying composer string after the prefix is what matters.
_NAME_PREFIXES = ("Attr. ", "Attr.", "after ", "? ", "?")

ERA_ORDER = ["Renaissance", "Baroque", "Classical", "Romantic", "Modern", "Unknown"]


def _to_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _era_of(composer: str) -> str:
    """Map a composer field to an era bucket.

    Order: strip attribution prefixes; exact dict match; Anon /
    source-manuscript pattern → Renaissance; longest dict-key prefix
    match (catches "John Danyel 1564 –" variants); fall back to
    "Unknown".
    """
    if not composer:
        return "Unknown"
    n = composer.strip()
    for pre in _NAME_PREFIXES:
        if n.startswith(pre):
            n = n[len(pre):].strip()
            break
    if n in COMPOSER_ERA:
        return COMPOSER_ERA[n]
    low = n.lower()
    if low.startswith("anon"):
        return "Renaissance"
    for marker in _RENAISSANCE_SOURCE_MARKERS:
        if marker in low:
            return "Renaissance"
    # Case-insensitive direct lookup (catches "MARTIN PEERSON" etc.).
    cf = n.casefold()
    for k, v in COMPOSER_ERA.items():
        if k.casefold() == cf:
            return v
    # Longest-prefix match across map keys so "John Danyel 1564 –" or
    # "Francis Cutting Cozens Lute Book" route to their named composer.
    best: tuple[int, str] | None = None
    for k, v in COMPOSER_ERA.items():
        if cf.startswith(k.casefold()) and (best is None or len(k) > best[0]):
            best = (len(k), v)
    if best is not None:
        return best[1]
    return "Unknown"


def _herfindahl(counts: list[int]) -> float:
    """Sum of squared shares. 1.0 = single composer; 1/k = uniform over k."""
    total = sum(counts)
    if total == 0:
        return 0.0
    return sum((c / total) ** 2 for c in counts)


def _eta_squared(values_by_group: dict[str, list[float]]) -> float | None:
    """Between-group variance / total variance for one feature.

    Returns None if too few groups have data or total variance is zero.
    """
    flat = [v for vs in values_by_group.values() for v in vs]
    if len(flat) < 30 or len(values_by_group) < 2:
        return None
    grand_mean = statistics.fmean(flat)
    ss_total = sum((x - grand_mean) ** 2 for x in flat)
    if ss_total == 0:
        return None
    ss_between = sum(
        len(vs) * (statistics.fmean(vs) - grand_mean) ** 2
        for vs in values_by_group.values()
        if vs
    )
    return ss_between / ss_total


def render_report(rows: list[dict[str, str]]) -> str:
    graded = [r for r in rows if r.get("grade")]
    if not graded:
        return "# M2 label-bias audit\n\nNo graded rows in input.\n"

    numeric_cols = [c for c in rows[0].keys() if c not in META_COLUMNS]

    grades = sorted(
        {r["grade"] for r in graded},
        key=lambda x: int(x) if x.isdigit() else 99,
    )
    composer_counts = Counter(r["composer_normalized"] for r in graded)

    lines: list[str] = []
    lines.append("# M2 label-bias audit")
    lines.append("")
    lines.append(f"- Graded pieces: **{len(graded)}** "
                 f"(out of {len(rows)} in `features.csv`)")
    lines.append(f"- Distinct composers in graded subset: **{len(composer_counts)}**")
    lines.append(f"- Grades present: {', '.join('G' + g for g in grades)}")
    lines.append("")
    lines.append(
        "Output of `scripts/m2_label_bias.py`. Every Delcamp-graded piece "
        "in the corpus comes from Guitar Loot (Eric Crouch's Renaissance / "
        "Baroque arrangements), so the question is not just *which features "
        "predict grade* but *do those features actually measure difficulty, "
        "or do they just identify the composer Crouch was grading?* "
        "Everything below is descriptive — no model fitting."
    )
    lines.append("")

    # ------ 1. Composer × grade cross-tab -----------------------------
    lines.append("## 1. Composer × grade cross-tab (top 20)")
    lines.append("")
    top_composers = [c for c, _ in composer_counts.most_common(20)]
    header = ["composer", "n"] + [f"G{g}" for g in grades]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for c in top_composers:
        by_g = Counter(r["grade"] for r in graded if r["composer_normalized"] == c)
        row = [c, str(composer_counts[c])] + [
            str(by_g.get(g, 0)) if by_g.get(g, 0) else "·"
            for g in grades
        ]
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    tail_n = sum(n for c, n in composer_counts.items() if c not in top_composers)
    lines.append(f"_Remaining {len(composer_counts) - len(top_composers)} composers: "
                 f"{tail_n} pieces._")
    lines.append("")

    # ------ 2. Per-composer grade dispersion --------------------------
    lines.append("## 2. Per-composer grade dispersion")
    lines.append("")
    lines.append(
        "Composers whose pieces all sit at one grade contribute zero "
        "within-composer variation. A model trained on this subset can't "
        "learn 'what makes a hard Dowland harder than an easy Dowland' "
        "if every Dowland piece is labelled the same."
    )
    lines.append("")
    composer_grade_sets: dict[str, set[str]] = defaultdict(set)
    for r in graded:
        composer_grade_sets[r["composer_normalized"]].add(r["grade"])
    bucket_n = Counter()
    bucket_pieces = Counter()
    for c, gset in composer_grade_sets.items():
        bucket_n[len(gset)] += 1
        bucket_pieces[len(gset)] += composer_counts[c]
    lines.append("| distinct grades per composer | composers | pieces |")
    lines.append("| --- | --- | --- |")
    for k in sorted(bucket_n.keys()):
        lines.append(f"| {k} | {bucket_n[k]} | {bucket_pieces[k]} |")
    pieces_single = bucket_pieces[1]
    pct_single = round(100 * pieces_single / len(graded), 1)
    lines.append("")
    lines.append(f"**{pieces_single} / {len(graded)} graded pieces ({pct_single}%) "
                 f"come from composers whose entire output in this corpus "
                 f"sits at a single grade.**")
    lines.append("")
    # Multi-grade composers, listed.
    multi = [(c, sorted(g, key=int)) for c, g in composer_grade_sets.items()
             if len(g) > 1]
    if multi:
        multi.sort(key=lambda x: (-composer_counts[x[0]], x[0]))
        lines.append("Composers spanning more than one grade:")
        lines.append("")
        for c, gs in multi:
            lines.append(f"- **{c}** (n={composer_counts[c]}): "
                         f"{', '.join('G' + g for g in gs)}")
        lines.append("")

    # ------ 3. Per-grade composer concentration -----------------------
    lines.append("## 3. Per-grade composer concentration")
    lines.append("")
    lines.append("For each grade: how many composers contribute, what share "
                 "the top composer holds, and the Herfindahl index "
                 "(1.0 = monopoly, 1/k = uniform over k composers).")
    lines.append("")
    lines.append("| grade | n | composers | top-1 share | top-3 share | Herfindahl |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for g in grades:
        subset = [r for r in graded if r["grade"] == g]
        c_counts = Counter(r["composer_normalized"] for r in subset)
        n = len(subset)
        top1 = c_counts.most_common(1)[0][1] if c_counts else 0
        top3 = sum(v for _, v in c_counts.most_common(3))
        h = _herfindahl(list(c_counts.values()))
        lines.append(f"| G{g} | {n} | {len(c_counts)} | "
                     f"{round(100*top1/n, 1)}% | "
                     f"{round(100*top3/n, 1)}% | "
                     f"{h:.2f} |")
    lines.append("")

    # ------ 4. Era × grade --------------------------------------------
    lines.append("## 4. Era × grade")
    lines.append("")
    eras_used = [e for e in ERA_ORDER
                 if any(_era_of(r["composer_normalized"]) == e for r in graded)]
    lines.append("| era | " + " | ".join(f"G{g}" for g in grades) + " | total |")
    lines.append("| " + " | ".join(["---"] * (len(grades) + 2)) + " |")
    for era in eras_used:
        cells = []
        total = 0
        for g in grades:
            n = sum(1 for r in graded
                    if r["grade"] == g and _era_of(r["composer_normalized"]) == era)
            cells.append(str(n) if n else "·")
            total += n
        lines.append(f"| {era} | " + " | ".join(cells) + f" | {total} |")
    lines.append("")
    unmapped = [r for r in graded
                if _era_of(r["composer_normalized"]) == "Unknown"]
    if unmapped:
        umc = Counter(r["composer_normalized"] for r in unmapped)
        lines.append(f"_{len(unmapped)} graded pieces are from composers "
                     f"not in the era map ({len(umc)} composers). "
                     f"Top unmapped:_")
        for c, n in umc.most_common(5):
            lines.append(f"  - {c} (n={n})")
        lines.append("")

    # ------ 5. Per-feature composer η² --------------------------------
    lines.append("## 5. Per-feature composer η² (between-composer variance share)")
    lines.append("")
    lines.append(
        "For each feature, the fraction of total variance that is "
        "between-composer rather than within-composer. η² close to 1 "
        "means knowing the composer almost fully determines the feature "
        "value — i.e. the feature is a composer proxy. η² close to 0 "
        "means the feature varies within each composer's catalogue and "
        "can carry actual difficulty signal."
    )
    lines.append("")
    eligible_composers = [c for c, n in composer_counts.items() if n >= 5]
    eligible_rows = [r for r in graded
                     if r["composer_normalized"] in eligible_composers]
    lines.append(f"_Restricted to composers with ≥5 graded pieces: "
                 f"{len(eligible_composers)} composers, {len(eligible_rows)} pieces._")
    lines.append("")
    results: list[tuple[str, float, int]] = []
    for col in numeric_cols:
        by_c: dict[str, list[float]] = defaultdict(list)
        for r in eligible_rows:
            v = _to_float(r[col])
            if v is not None:
                by_c[r["composer_normalized"]].append(v)
        eta = _eta_squared(by_c)
        n_obs = sum(len(vs) for vs in by_c.values())
        if eta is not None:
            results.append((col, eta, n_obs))
    results.sort(key=lambda x: -x[1])
    lines.append("| feature | η² | n |")
    lines.append("| --- | --- | --- |")
    for col, eta, n in results:
        lines.append(f"| `{col}` | {eta:.2f} | {n} |")
    lines.append("")

    # ------ 6. Bottom line --------------------------------------------
    lines.append("## 6. Bottom line")
    lines.append("")
    composers_at_single_grade = sum(1 for gset in composer_grade_sets.values()
                                    if len(gset) == 1)
    high_eta = [r for r in results if r[1] >= 0.7]
    only_renaissance_pct = round(100 * sum(
        1 for r in graded if _era_of(r["composer_normalized"]) == "Renaissance"
    ) / len(graded), 1)
    lines.append(
        f"- **{composers_at_single_grade} of {len(composer_counts)} composers** "
        f"have all their graded pieces at one grade. Together they account "
        f"for **{pct_single}% of the graded corpus**."
    )
    lines.append(
        f"- **{only_renaissance_pct}% of graded pieces are Renaissance** "
        f"(by the hand-curated era map). The labelled subset is not a "
        f"representative sample of the classical-guitar repertoire — it "
        f"is a sample of one curator's lute-transcription set."
    )
    if high_eta:
        names = ", ".join(f"`{c}`" for c, _, _ in high_eta[:5])
        lines.append(
            f"- **{len(high_eta)} features have η² ≥ 0.70 against composer** "
            f"(top: {names}). On the graded subset, these features are "
            f"effectively composer indicators; a model that uses them will "
            f"learn 'is this Dowland?' before it learns 'is this hard?'."
        )
    lines.append(
        "- The advisor question is therefore not just *which features go "
        "into the model*, but **whether Delcamp-on-Crouch should be the "
        "primary label at all**, or whether it should be one signal among "
        "several (e.g. paired with a small advisor-graded calibration set "
        "spanning eras and difficulty)."
    )
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in-path", type=Path, default=DEFAULT_IN_PATH,
                        dest="in_path")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_PATH)
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

    report = render_report(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(f"==> Wrote label-bias audit to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
