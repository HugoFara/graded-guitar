"""M2 sanity check — does dummy-v0 grade well-known pieces plausibly?

Looks up ~30 classical-guitar pieces with broad community consensus on
difficulty in `corpus/manifest.json` and emits a Markdown comparison
table to `corpus/dummy_v0_consensus_check.md`.

This is a self-audit, not an advisor review. The reviewer's argument
(external review, 2026-05-18): if dummy-v0 is wildly off on pieces
where every teacher would agree on the rough difficulty band, the
model has bigger problems than "needs an advisor." If it's roughly
right on the easy cases, that's a real signal we can act on before any
advisor is in the loop.

The consensus grades below are deliberately bands, not points — three
teachers might say a piece is grade 4 / 5 / 4-5, and that's the
expected level of precision. We use a single integer per row for
table-rendering convenience; "within ±1 of the band" is the bar.

Usage:
    python scripts/m2_consensus_check.py
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from m1_common import REPO_ROOT


MANIFEST = REPO_ROOT / "corpus" / "manifest.json"
REPORT = REPO_ROOT / "corpus" / "dummy_v0_consensus_check.md"


# (title_pattern, composer_pattern, consensus_grade, note)
# Patterns are matched case-insensitively against the unicode-folded
# title and composer. They are intentionally loose — the manifest's
# metadata is heterogeneous (arranger vs. composer, with/without opus,
# with/without "No. N" suffixes).
@dataclass(frozen=True)
class Probe:
    title: str
    composer: str
    consensus: int
    note: str


PROBES: list[Probe] = [
    # Tárrega — distinctive titles. Note that the corpus pieces tagged
    # "(Theme)" are short (~20s) theme statements, not the full work;
    # consensus reflects that, NOT the full performance grade.
    Probe(r"^adelita$", "tarrega", 4, "Adelita — short character piece"),
    Probe(r"^lagrima$", "tarrega", 4, "Lágrima — lyrical, grade 4"),
    Probe(r"recuerdos.*theme", "tarrega", 4,
          "Recuerdos de la Alhambra (Theme only, ~20s) — no tremolo, grade 4. "
          "Full piece would be 9-10."),
    Probe(r"^capricho.*arabe$", "tarrega", 7,
          "Capricho Árabe — full piece (~240s), grade 7"),
    Probe(r"capricho.*arabe.*theme", "tarrega", 4,
          "Capricho Árabe (Theme only, ~19s) — grade 4"),
    Probe(r"estudio.*a minor", "tarrega", 4, "Tárrega Estudio in A minor — grade 3-4"),

    # Albéniz — Asturias is theme-only in the corpus (17s)
    Probe(r"asturias.*theme", "albeniz", 4,
          "Asturias (Theme only, ~17s) — grade 4. Full Leyenda would be 8."),

    # Carcassi — bare "Etude N" titles, can't map to Op. 60 numbering cleanly.
    # Probe a few spread across the set.
    Probe(r"^etude 1$", "carcassi", 4, "Carcassi Etude 1 — early study"),
    Probe(r"^etude 7$", "carcassi", 5, "Carcassi Etude 7 — middle of the set"),
    Probe(r"^etude 10$", "carcassi", 6, "Carcassi Etude 10 — later study"),

    # Sor — 24 Studies, broad band
    Probe(r"^24 studies for the guitar$", "sor", 5,
          "Sor 24 Studies — set spans grade 3-8; check median plausibility"),

    # Giuliani — 24 Studies, similar spread
    Probe(r"^24 studies for the guitar$", "giuliani", 5,
          "Giuliani 24 Studies — similar spread to Sor's set"),

    # Renaissance/Baroque Chaconnes — corpus has 6+ lute versions
    Probe(r"^chaconne$", "bach|visee|mouton|boismortier|anon", 7,
          "Lute Chaconnes — grade 6-8"),

    # Bach — Bourrée from BWV 996 / Lute Suite No. 1
    Probe(r"^bouree$|^bourree$|bourr.e", "bach", 5,
          "Bourrée from BWV 996 — grade 5-6"),

    # Bach — bare-title Preludes (transcribed)
    Probe(r"^prelude$", "bach", 6, "Bach Prelude (transcribed) — grade 5-7"),

    # Villa-Lobos — only the theme is in the corpus (~29s)
    Probe(r"prelude.*villa|villa.*prelude|prelude no\.?\s*1.*theme",
          "villa-lobos", 4, "Villa-Lobos Prelude No. 1 (Theme only, ~30s) — grade 4-5"),

    # Aguado — Petites Pièces are mostly primer; the corpus has many,
    # graded as a curator set
    Probe(r"^six petites pieces, no\.?\s*1$", "aguado", 4,
          "Aguado Six Petites Pièces No. 1 — primer"),

    # Aguado — Les Favorites, intermediate dance pieces
    Probe(r"^les favorites$", "aguado", 5, "Aguado Les Favorites — grade 4-6"),

    # Traditional — Greensleeves (basic arrangement)
    Probe(r"^greensleeves$", "traditional english", 3,
          "Greensleeves traditional arrangement — grade 2-3"),

    # Dowland — Renaissance lute, well-represented in corpus.
    # Curator (delcamp-eric-crouch) grades these high; that's fine —
    # this row tests whether the curator's grade survives the pipeline.
    Probe(r"galliard", "dowland", 6, "Dowland galliards — grade 5-7"),
    Probe(r"pavan", "dowland", 6, "Dowland pavanes — grade 5-7"),

    # Holborne — well-represented, simpler than Dowland's fantasies
    Probe(r"galliard", "holborne", 5, "Holborne galliards — grade 4-6"),
    Probe(r"pavan", "holborne", 5, "Holborne pavanes — grade 4-6"),

    # Sor — Six divertissements (Op. 1 / Op. 8 sets, varies by ms.)
    Probe(r"six divertissements", "sor", 6, "Sor Six divertissements — grade 5-7"),

    # Op. 29 — Sor's Op. 29 studies (advanced)
    Probe(r"opus 29|op\.?\s*29", "sor", 6, "Sor Op. 29 — grade 6-7"),

    # Caprice (Carcassi)
    Probe(r"caprice", "carcassi", 5, "Carcassi Caprices — grade 4-6"),

    # Bacheler — courtly Elizabethan lute
    Probe(r"pavan|galliard", "bacheler", 6, "Daniel Bacheler — grade 5-7"),

    # Cutting — Elizabethan lute, mostly division-on-a-ground pieces
    Probe(r"galliard|division|alman", "francis cutting", 5,
          "Francis Cutting — Elizabethan lute, grade 4-6"),

    # Anonymous Renaissance
    Probe(r"^almain$|^almand$|^alman$|^almaine$", "anon|english|holborne", 4,
          "Renaissance Almain/Alman — grade 3-5"),

    # Aguado — 8 Petites Pièces (the more advanced set)
    Probe(r"^8 petites pieces$", "aguado", 6, "Aguado 8 Petites Pièces — grade 5-7"),

    # Foscarini — early Baroque guitar/theorbo
    Probe(r"corrente|courante|gagliarda|sarabanda", "foscarini", 6,
          "Foscarini early-Baroque dances — grade 5-7"),

    # John Dowland Lachrimae / Flow My Tears
    Probe(r"lachrimae|flow.*tears", "dowland", 7,
          "Dowland Lachrimae / Flow My Tears — grade 6-8"),
]


def _fold(s: str) -> str:
    """Lowercase + accent-strip for fuzzy match."""
    norm = unicodedata.normalize("NFKD", s)
    return "".join(c for c in norm if not unicodedata.combining(c)).lower()


def _match(probe: Probe, pieces: list[dict]) -> list[dict]:
    title_re = re.compile(probe.title, re.IGNORECASE)
    composer_re = re.compile(probe.composer, re.IGNORECASE)
    out = []
    for p in pieces:
        title = _fold(p.get("metadata", {}).get("title", ""))
        composer = _fold(p.get("metadata", {}).get("composer", ""))
        if title_re.search(title) and composer_re.search(composer):
            out.append(p)
    return out


def _grade_of(piece: dict) -> tuple[str | None, str]:
    """Return (grade, source) preferring curator over model."""
    if "grade" in piece and piece["grade"]:
        return str(piece["grade"]), piece.get("grade_source", "curator")
    if "model_grade" in piece and piece["model_grade"]:
        return str(piece["model_grade"]), piece.get("model_grade_source", "model")
    return None, "none"


def _row(probe: Probe, matches: list[dict]) -> tuple[str, int | None, list[str]]:
    """Reduce matches to one row.

    For a unique match, return its grade verbatim.
    For multiple matches (e.g. "24 Studies" with 39 separate pieces),
    return the median grade and report the spread — the question is
    whether the *centre* of the bucket is in the consensus band, not
    whether any individual entry is.
    """
    if not matches:
        return ("—", None, ["no match in corpus"])
    grades: list[int] = []
    sources: set[str] = set()
    for p in matches:
        grade_str, source = _grade_of(p)
        sources.add(source)
        if grade_str:
            try:
                grades.append(int(grade_str))
            except ValueError:
                pass
    if not grades:
        return ("—", None, [f"{len(matches)} match(es), no grades"])
    grades.sort()
    median = grades[len(grades) // 2]
    source_str = "+".join(sorted(sources))
    notes = []
    if len(matches) == 1:
        display = f"{median} ({source_str})"
    else:
        display = (f"{median} (median of {len(grades)}; "
                   f"range {grades[0]}-{grades[-1]}; {source_str})")
        notes.append(f"{len(matches)} candidates")
    return (display, median, notes)


def main() -> int:
    if not MANIFEST.exists():
        print(f"missing {MANIFEST}", file=sys.stderr)
        return 1
    manifest = json.loads(MANIFEST.read_text())
    pieces = manifest.get("pieces", [])

    lines: list[str] = []
    lines.append("# dummy-v0 consensus check")
    lines.append("")
    lines.append("Self-audit per ADR 0013: check whether dummy-v0 places")
    lines.append("well-known pieces in roughly the right difficulty band.")
    lines.append("Consensus grades come from the author's reading of the")
    lines.append("RCM / Trinity / ABRSM classical-guitar syllabi and the")
    lines.append("Delcamp grading discussions; treat each row as a band")
    lines.append("(consensus ± 1) rather than a point.")
    lines.append("")
    lines.append(f"- Manifest: `{MANIFEST.relative_to(REPO_ROOT)}` "
                 f"({len(pieces)} pieces)")
    lines.append("")
    lines.append("| Probe | Consensus | Corpus grade | Δ | Verdict | Notes |")
    lines.append("|---|---:|---|---:|---|---|")

    hits = 0
    misses = 0
    no_match = 0
    sum_abs_delta = 0
    within_one = 0

    for probe in PROBES:
        matches = _match(probe, pieces)
        display, predicted, notes = _row(probe, matches)
        if predicted is None:
            verdict = "no match" if not matches else "no grade"
            no_match += 1
            delta_cell = "—"
        else:
            delta = predicted - probe.consensus
            sum_abs_delta += abs(delta)
            if abs(delta) <= 1:
                verdict = "✓"
                within_one += 1
                hits += 1
            elif abs(delta) <= 2:
                verdict = "~"
                hits += 1
            else:
                verdict = "✗"
                misses += 1
            delta_cell = f"{delta:+d}"

        note_text = "; ".join([probe.note, *notes])
        lines.append(
            f"| {probe.title} / {probe.composer} | {probe.consensus} | "
            f"{display} | {delta_cell} | {verdict} | {note_text} |"
        )

    n_scored = hits + misses
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Probes attempted: **{len(PROBES)}**")
    lines.append(f"- Matched + graded: **{n_scored}**")
    lines.append(f"- No match / no grade: **{no_match}**")
    if n_scored:
        lines.append(f"- Within ±1 of consensus: **{within_one}/{n_scored}** "
                     f"({100 * within_one / n_scored:.0f}%)")
        lines.append(f"- Within ±2 of consensus: **{hits}/{n_scored}** "
                     f"({100 * hits / n_scored:.0f}%)")
        lines.append(f"- Mean |Δ|: **{sum_abs_delta / n_scored:.2f}**")
    lines.append("")
    lines.append("## Reading this report")
    lines.append("")
    lines.append("- **✓** = within ±1 grade (the band the consensus column")
    lines.append("  represents). This is the bar the spec §7 M2 advisor")
    lines.append("  validation will eventually use.")
    lines.append("- **~** = within ±2 grades. Not great, not catastrophic.")
    lines.append("- **✗** = off by 3+ grades. Worth investigating; the")
    lines.append("  model is making a categorical mistake on a piece")
    lines.append("  whose difficulty is broadly agreed on.")
    lines.append("- **no match** = the corpus doesn't contain this piece,")
    lines.append("  or the title/composer pattern is too tight. Worth")
    lines.append("  diversifying the corpus (see ADR 0013 follow-ups).")
    lines.append("")
    lines.append("## Caveats")
    lines.append("")
    lines.append("- Curator grades (`delcamp-eric-crouch`) bypass dummy-v0")
    lines.append("  entirely — those rows test the *curator's* alignment with")
    lines.append("  syllabus consensus, not the model's. Curator tends to")
    lines.append("  grade Renaissance/Baroque lute repertoire 1-2 grades")
    lines.append("  above syllabus norms; that's a Delcamp-vs-syllabus")
    lines.append("  taste difference, not a pipeline bug.")
    lines.append("- Several Tárrega / Albéniz / Villa-Lobos entries in the")
    lines.append("  corpus are theme-statement excerpts (~20-30s), not full")
    lines.append("  performances. Consensus is calibrated to the excerpt, not")
    lines.append("  the full work. The full pieces would land much higher")
    lines.append("  on the grade scale.")
    lines.append("- This is **not** an advisor review. It's an author-run")
    lines.append("  smoke test against pieces with broad syllabus consensus.")
    lines.append("  Spec §7 M2 still gates on a real advisor reviewing 50")
    lines.append("  randomly graded pieces, with a 40/50 plausibility bar.")

    REPORT.write_text("\n".join(lines) + "\n")
    print(f"wrote {REPORT.relative_to(REPO_ROOT)}")
    print(f"  matched: {n_scored}/{len(PROBES)} probes")
    if n_scored:
        print(f"  within ±1: {within_one}/{n_scored} ({100 * within_one / n_scored:.0f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
