#!/usr/bin/env python3
"""Regression tests for M1 validation gates.

Stdlib + project deps only — no pytest. Each test builds a minimal
synthetic MusicXML blob and asserts the expected outcome from
`m1_validate.validate_one` (catches already-converted artifacts) and
`m1_lilypond._structural_check` (catches future conversions before
they're ever written to disk).

Run directly:
    python3 scripts/tests/test_m1_validation.py

Or via the repo self-check (scripts/check.sh).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from m1_lilypond import _structural_check  # noqa: E402
from m1_validate import validate_one  # noqa: E402


# ---------- builders ------------------------------------------------------

def _score(notes_xml: str, parts: int = 1, clef_sign: str = "G",
           title: str = "Test Piece",
           composer: str = "Test Composer") -> bytes:
    """Wrap a chunk of <note> XML in a minimal valid score-partwise document."""
    part_list = "".join(
        f'<score-part id="P{i+1}"><part-name>Guitar</part-name></score-part>'
        for i in range(parts)
    )
    parts_xml = "".join(
        f'<part id="P{i+1}"><measure number="1">'
        f'<attributes><clef><sign>{clef_sign}</sign></clef></attributes>'
        f'{notes_xml}</measure></part>'
        for i in range(parts)
    )
    return (
        '<?xml version="1.0"?>'
        '<score-partwise>'
        f'<work><work-title>{title}</work-title></work>'
        f'<identification><creator type="composer">{composer}</creator></identification>'
        f'<part-list>{part_list}</part-list>'
        f'{parts_xml}'
        '</score-partwise>'
    ).encode("utf-8")


def _pitched_note(step: str, octave: int, alter: int = 0) -> str:
    alter_xml = f'<alter>{alter}</alter>' if alter else ''
    return (
        f'<note><pitch><step>{step}</step>{alter_xml}'
        f'<octave>{octave}</octave></pitch>'
        f'<duration>1</duration><type>quarter</type></note>'
    )


def _many(note_xml: str, n: int) -> str:
    return note_xml * n


# ---------- tests ---------------------------------------------------------

def test_validate_rejects_sub_drop_d() -> None:
    # 20 in-range notes plus one A1 (MIDI 33) — well below the drop-D gate.
    xml = _score(_many(_pitched_note("E", 3), 20) + _pitched_note("A", 1))
    outcome = validate_one(xml, "musicxml")
    assert not outcome["ok"], "expected rejection"
    assert outcome["code"] == "OUT_OF_GUITAR_RANGE_LOW", (
        f"expected OUT_OF_GUITAR_RANGE_LOW, got {outcome['code']}"
    )
    assert "min MIDI=33" in outcome["detail"], outcome["detail"]


def test_validate_accepts_drop_d_exactly() -> None:
    # 20 in-range notes plus one D2 (MIDI 38) — equal to the gate, accepted.
    xml = _score(_many(_pitched_note("E", 3), 20) + _pitched_note("D", 2))
    outcome = validate_one(xml, "musicxml")
    assert outcome["ok"], f"expected accept, got {outcome.get('code')}"


def test_lilypond_structural_check_rejects_sub_drop_d() -> None:
    xml = _score(_many(_pitched_note("E", 3), 20) + _pitched_note("C", 1))
    ok, code, detail = _structural_check(xml)
    assert not ok
    assert code == "OUT_OF_GUITAR_RANGE_LOW", code
    assert detail["min_midi"] == 24, detail
    assert detail["below_gate"] == 1, detail


def test_lilypond_structural_check_accepts_in_range() -> None:
    xml = _score(_many(_pitched_note("E", 3), 16))
    ok, code, _ = _structural_check(xml)
    assert ok, f"expected accept, got code={code}"


# ---------- runner --------------------------------------------------------

def main() -> int:
    tests = [
        test_validate_rejects_sub_drop_d,
        test_validate_accepts_drop_d_exactly,
        test_lilypond_structural_check_rejects_sub_drop_d,
        test_lilypond_structural_check_accepts_in_range,
    ]
    failures: list[tuple[str, str]] = []
    for t in tests:
        try:
            t()
            print(f"  ok   {t.__name__}")
        except AssertionError as e:
            failures.append((t.__name__, str(e) or "(no message)"))
            print(f"  FAIL {t.__name__}: {e}")
    if failures:
        print(f"\n{len(failures)} of {len(tests)} tests failed", file=sys.stderr)
        return 1
    print(f"\nOK ({len(tests)} tests)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
