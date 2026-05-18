"""Regression tests for the M2 feature, grader, and label-bias scripts.

Same lightweight pattern as `test_m1_validation.py`: stdlib only +
project deps (lxml for parsing tiny inline MusicXML fragments).
Self-contained — no pytest.

Run with:
    python scripts/tests/test_m2.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lxml import etree  # noqa: E402

from m2_features import (  # noqa: E402
    _pitch_fingering_stats,
    _pitch_min_fret,
)
from m2_baseline_grader import (  # noqa: E402
    _band_for,
    _percentile_ranks,
    GRADE_BANDS,
    RULE_FEATURES,
    grade_corpus,
)
from m2_label_bias import _era_of  # noqa: E402


_PASS = "\033[32mok  "
_FAIL = "\033[31mFAIL"
_END = "\033[0m"


def _note_xml(steps_and_octaves: list[tuple[str, int, bool]]) -> etree._Element:
    """Build a minimal score-partwise root with one measure of notes.

    `steps_and_octaves` items are (step, octave, in_chord_continuation).
    First note in a chord has in_chord_continuation=False; subsequent
    chord notes set it True (emits a leading <chord/> per MusicXML).
    """
    parts: list[str] = []
    for step, octave, chord_cont in steps_and_octaves:
        chord_tag = "<chord/>" if chord_cont else ""
        parts.append(
            f"<note>{chord_tag}"
            f"<pitch><step>{step}</step><octave>{octave}</octave></pitch>"
            f"<duration>1</duration><type>quarter</type>"
            "</note>"
        )
    xml = (
        "<?xml version='1.0'?>"
        "<score-partwise><part id='P1'><measure number='1'>"
        + "".join(parts)
        + "</measure></part></score-partwise>"
    )
    return etree.fromstring(xml.encode("utf-8"))


# ---------- _pitch_min_fret -------------------------------------------------

def test_pitch_min_fret_open_strings() -> None:
    # MIDI 40, 45, 50, 55, 59, 64 are all open strings → fret 0.
    for midi in (40, 45, 50, 55, 59, 64):
        assert _pitch_min_fret(midi) == 0, f"midi {midi} should be fret 0"


def test_pitch_min_fret_below_low_e_is_unreachable() -> None:
    assert _pitch_min_fret(39) is None, "MIDI 39 is below low E in standard tuning"
    assert _pitch_min_fret(38) is None, "MIDI 38 (drop-D) unreachable in standard"


def test_pitch_min_fret_above_high_e_24_is_unreachable() -> None:
    assert _pitch_min_fret(89) is None, "MIDI 89 is above 24th-fret high E"


def test_pitch_min_fret_high_notes_use_string_1() -> None:
    # P=65 (F4) → only string 1 fret 1 is the lowest fret option.
    assert _pitch_min_fret(65) == 1
    # P=72 (C5) → string 1 fret 8.
    assert _pitch_min_fret(72) == 8
    # P=88 → string 1 fret 24, top of range.
    assert _pitch_min_fret(88) == 24


def test_pitch_min_fret_picks_lowest_across_strings() -> None:
    # MIDI 50 (D3): reachable on string 6 fret 10, string 5 fret 5, string 4 fret 0.
    # Lowest is 0.
    assert _pitch_min_fret(50) == 0
    # MIDI 44 (Ab2): only string 6 fret 4 is in range; string 5 would need fret -1.
    assert _pitch_min_fret(44) == 4


# ---------- _pitch_fingering_stats ------------------------------------------

def test_pitch_fingering_empty_score() -> None:
    root = _note_xml([])
    s = _pitch_fingering_stats(root)
    assert s == {
        "pitch_min_fret_max": None,
        "pitch_min_fret_p90": None,
        "pitch_position_shifts": None,
    }


def test_pitch_fingering_max_and_p90() -> None:
    # Low E (fret 0), middle C (3rd string fret 5 → wait check: C4=60, string 3=G3=55 → fret 5).
    # High E (string 1 fret 12 since E5=76, 76-64=12).
    root = _note_xml([
        ("E", 2, False),  # MIDI 40, fret 0
        ("C", 4, False),  # MIDI 60, fret 0 on string 2 (B3=59, fret 1) or string 3 (G3=55, fret 5) — min 1
        ("E", 5, False),  # MIDI 76, fret 12
    ])
    s = _pitch_fingering_stats(root)
    assert s["pitch_min_fret_max"] == 12
    # p90 with 3 sorted [0,1,12] → index round(0.9*2)=2 → 12
    assert s["pitch_min_fret_p90"] == 12


def test_pitch_fingering_position_shifts_counted_on_melodic_jumps() -> None:
    # Three notes: fret 0, fret 12 (Δ=12, shift), fret 1 (Δ=11, shift).
    root = _note_xml([
        ("E", 2, False),  # fret 0
        ("E", 5, False),  # fret 12
        ("F", 4, False),  # fret 1 on string 1
    ])
    s = _pitch_fingering_stats(root)
    assert s["pitch_position_shifts"] == 2


def test_pitch_fingering_skips_chord_continuation_for_shifts() -> None:
    # First note fret 0; then a chord of two notes (fret 0 leader + chord continuation
    # at fret 12, which must NOT count as a shift because <chord/> means simultaneous).
    # Then a melodic note at fret 0 (no shift from the leader).
    root = _note_xml([
        ("E", 2, False),   # melodic, fret 0
        ("E", 2, False),   # melodic next, fret 0 — Δ=0, no shift
        ("E", 5, True),    # chord continuation (simultaneous with previous) — skipped
        ("E", 2, False),   # melodic again, fret 0 from previous melodic (fret 0): Δ=0
    ])
    s = _pitch_fingering_stats(root)
    assert s["pitch_position_shifts"] == 0


# ---------- _percentile_ranks ----------------------------------------------

def test_percentile_ranks_unique_values() -> None:
    ranks = _percentile_ranks([1.0, 2.0, 3.0, 4.0])
    assert ranks[1.0] == 0.0
    assert abs(ranks[2.0] - 33.333333) < 1e-3
    assert abs(ranks[3.0] - 66.666666) < 1e-3
    assert ranks[4.0] == 100.0


def test_percentile_ranks_ties_get_average_rank() -> None:
    ranks = _percentile_ranks([1.0, 1.0, 2.0, 2.0])
    # Two 1s get average of ranks 1+2 → midpoint between 0 and 33.3.
    assert ranks[1.0] == ranks[1.0]  # same key, same value
    assert abs(ranks[1.0] - (100 * (1.5 - 1) / 3)) < 1e-6
    assert abs(ranks[2.0] - (100 * (3.5 - 1) / 3)) < 1e-6


def test_percentile_ranks_single_value() -> None:
    ranks = _percentile_ranks([5.0])
    assert ranks[5.0] == 0.0


# ---------- _band_for ------------------------------------------------------

def test_band_for_low_high_and_boundaries() -> None:
    assert _band_for(0.0) == "3"
    assert _band_for(19.99) == "3"
    assert _band_for(20.0) == "5"
    assert _band_for(50.0) == "6"
    assert _band_for(99.0) == "8"
    assert _band_for(100.0) == "8"


def test_grade_bands_partition_full_range() -> None:
    # Each band's hi == next band's lo (no gaps, no overlaps).
    for (lo1, hi1, _), (lo2, hi2, _) in zip(GRADE_BANDS, GRADE_BANDS[1:]):
        assert hi1 == lo2, f"gap or overlap between {hi1} and {lo2}"


# ---------- grade_corpus end-to-end ----------------------------------------

def _make_row(cid: str, vals: dict[str, float | str]) -> dict[str, str]:
    row = {
        "candidate_id": cid,
        "source": "test:source",
        "title": "test",
        "composer_normalized": "Test Composer",
        "grade": "",
        "grade_source": "",
    }
    for k, v in vals.items():
        row[k] = "" if v is None else str(v)
    return row


def test_grade_corpus_assigns_a_grade_to_every_row() -> None:
    rows = [
        _make_row("a", {f: 1 for f in RULE_FEATURES}),
        _make_row("b", {f: 5 for f in RULE_FEATURES}),
        _make_row("c", {f: 10 for f in RULE_FEATURES}),
    ]
    out = grade_corpus(rows)
    assert len(out) == 3
    for r in out:
        assert r["predicted_grade"] in {label for _, _, label in GRADE_BANDS}
        assert r["composite_percentile"] != ""


def test_grade_corpus_orders_predictions_with_feature_magnitude() -> None:
    # Build a sloped synthetic corpus: each piece's features grow linearly.
    rows = [
        _make_row(f"p{i}", {f: i for f in RULE_FEATURES})
        for i in range(10)
    ]
    out = grade_corpus(rows)
    composites = [float(r["composite_percentile"]) for r in out]
    # Strictly monotone (each piece is uniquely larger than the last).
    assert composites == sorted(composites)
    # Smallest piece lands in lowest band; largest in highest.
    assert out[0]["predicted_grade"] == GRADE_BANDS[0][2]
    assert out[-1]["predicted_grade"] == GRADE_BANDS[-1][2]


# ---------- _era_of --------------------------------------------------------

def test_era_of_exact_match() -> None:
    assert _era_of("John Dowland") == "Renaissance"
    assert _era_of("Sylvius Leopold Weiss") == "Baroque"
    assert _era_of("Fernando Sor") == "Classical"


def test_era_of_anon_variants_route_to_renaissance() -> None:
    assert _era_of("Anon") == "Renaissance"
    assert _era_of("Anon Dd.2.11 f.8") == "Renaissance"
    assert _era_of("Anon: Hirsch Lute Book") == "Renaissance"


def test_era_of_source_marker_overrides_unknown_composer() -> None:
    # Composer not in the map, but the source-manuscript marker pins it.
    assert _era_of("Some Unknown Person, Cosens Lute Book") == "Renaissance"


def test_era_of_strips_attribution_prefix() -> None:
    assert _era_of("Attr. John Dowland") == "Renaissance"
    assert _era_of("? Francis Cutting") == "Renaissance"
    assert _era_of("after John Dowland") == "Renaissance"


def test_era_of_case_insensitive_match() -> None:
    assert _era_of("MARTIN PEERSON") == "Renaissance"
    assert _era_of("john dowland") == "Renaissance"


def test_era_of_prefix_match_for_date_suffixed_names() -> None:
    assert _era_of("John Danyel 1564 –") == "Renaissance"
    assert _era_of("Francis Cutting Cozens Lute Book") == "Renaissance"


def test_era_of_unknown_for_truly_unrecognised_names() -> None:
    assert _era_of("Zzzz Madeup") == "Unknown"
    assert _era_of("") == "Unknown"


# ---------- runner ---------------------------------------------------------

def main() -> int:
    tests = [(name, obj) for name, obj in globals().items()
             if name.startswith("test_") and callable(obj)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"{_PASS}{_END} {name}")
        except AssertionError as e:
            failed += 1
            print(f"{_FAIL}{_END} {name}: {e}")
        except Exception as e:
            failed += 1
            print(f"{_FAIL}{_END} {name}: {type(e).__name__}: {e}")
    print()
    if failed:
        print(f"\033[31mFAILED ({failed}/{len(tests)})\033[0m")
        return 1
    print(f"\033[32mOK ({len(tests)} tests)\033[0m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
