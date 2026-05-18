"""M2.1 — Feature extraction over the M1 corpus.

Read-only pass over `corpus/manifest.json` plus each piece's normalized
MusicXML. Emits one row per piece into `corpus/features.csv` with the
feature set proposed in decisions/0009-m2-grading-inputs.md (Phase 1).

This is **scoping output**, not a training step. The advisor reviews
the columns and distributions before any model is fit. Nothing here
encodes a grading decision; every output is a deterministic function
of the score's MusicXML.

Usage:
    python scripts/m2_features.py
    python scripts/m2_features.py --limit 50
    python scripts/m2_features.py --out /tmp/probe.csv

See decisions/0009-m2-grading-inputs.md for the feature definitions.
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from lxml import etree

from m1_common import REPO_ROOT, load_manifest


CORPUS_DIR = REPO_ROOT / "corpus"
DEFAULT_OUT_PATH = CORPUS_DIR / "features.csv"

STEP_TO_SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# Output column order. Keep grade-related fields first so a spreadsheet
# user can sort by grade immediately; then features grouped by topic.
COLUMNS = [
    "candidate_id",
    "source",
    "title",
    "composer_normalized",
    "grade",
    "grade_source",
    # pitch (★★★)
    "midi_min",
    "midi_max",
    "midi_range",
    "midi_median",
    # key (★★★)
    "key_fifths",
    "key_changes",
    # tempo & meter (★★★)
    "tempo_bpm",
    "time_sig",
    "meter_changes",
    # rhythm (★★)
    "smallest_division",
    "dotted_count",
    "tied_count",
    "tuplet_count",
    "notes_per_measure",
    "accidentals_outside_key",
    # polyphony (★★★)
    "max_chord_stack",
    "polyphonic_measure_ratio",
    "voice_count_max",
    # ornamentation (★★★)
    "ornament_mordent",
    "ornament_trill",
    "ornament_turn",
    "grace_count",
    # technique (★★)
    "harmonic_count",
    "barre_count",
    "position_shift_proxy",
    "pitch_min_fret_max",
    "pitch_min_fret_p90",
    "pitch_position_shifts",
    # length (★★★)
    "measure_count",
    "note_count",
    "duration_sec_approx",
]


def _note_midi(pitch_el: etree._Element) -> int | None:
    step = pitch_el.findtext("{*}step")
    octave = pitch_el.findtext("{*}octave")
    if step is None or octave is None:
        return None
    semi = STEP_TO_SEMI.get(step.upper())
    if semi is None:
        return None
    try:
        oct_i = int(octave)
    except ValueError:
        return None
    alter_text = pitch_el.findtext("{*}alter")
    alter = 0
    if alter_text:
        try:
            alter = int(float(alter_text))
        except ValueError:
            alter = 0
    return (oct_i + 1) * 12 + semi + alter


def _smallest_division(root: etree._Element) -> int | None:
    """Return the largest denominator seen in any <type> element.

    MusicXML <type>quarter</type>/<type>16th</type>/etc. is the visual
    note duration; we treat the smallest-grained value across the score
    as a rough indicator of rhythmic complexity. Returns the denominator
    of the smallest type (e.g. 32 if 32nd notes appear, else 16, etc.).
    """
    type_to_denom = {
        "whole": 1, "half": 2, "quarter": 4, "eighth": 8,
        "16th": 16, "32nd": 32, "64th": 64, "128th": 128,
    }
    seen: list[int] = []
    for t in root.xpath("//*[local-name()='note']/*[local-name()='type']"):
        v = (t.text or "").strip().lower()
        if v in type_to_denom:
            seen.append(type_to_denom[v])
    return max(seen) if seen else None


def _opening_tempo(root: etree._Element) -> float | None:
    """First <sound tempo="..."> on the score, or None if absent."""
    for s in root.xpath("//*[local-name()='sound'][@tempo]"):
        try:
            return float(s.get("tempo"))
        except (TypeError, ValueError):
            continue
    # Some MusicXML uses <per-minute> inside <metronome>.
    for pm in root.xpath("//*[local-name()='per-minute']"):
        try:
            return float((pm.text or "").strip())
        except ValueError:
            continue
    return None


def _time_signature_changes(root: etree._Element) -> tuple[str, int]:
    """Return (opening time signature as 'N/D', count of distinct signatures)."""
    sigs: list[str] = []
    for t in root.xpath("//*[local-name()='time']"):
        beats = t.findtext("{*}beats")
        beat_type = t.findtext("{*}beat-type")
        if beats and beat_type:
            sigs.append(f"{beats.strip()}/{beat_type.strip()}")
    if not sigs:
        return "", 0
    distinct = len(set(sigs))
    return sigs[0], distinct


def _key_changes(root: etree._Element) -> tuple[str, int]:
    """Return (opening key fifths value, count of distinct fifths in score)."""
    fifths: list[str] = []
    for k in root.xpath("//*[local-name()='key']/*[local-name()='fifths']"):
        text = (k.text or "").strip()
        if text:
            fifths.append(text)
    if not fifths:
        return "", 0
    return fifths[0], len(set(fifths))


def _polyphony_stats(root: etree._Element) -> tuple[int, float, int]:
    """Return (max chord stack size, polyphonic-measure ratio, max voice count).

    A measure is "polyphonic" if any of its notes is part of a chord OR
    if it contains more than one distinct <voice> value.
    """
    max_stack = 0
    voice_max = 0
    measures = root.xpath("//*[local-name()='measure']")
    poly_measures = 0
    for m in measures:
        voices = set()
        # Walk notes; each <chord/> marker means "stacked on the previous note".
        notes = m.xpath("./*[local-name()='note']")
        stack = 0
        for n in notes:
            v = n.findtext("{*}voice")
            if v:
                voices.add(v.strip())
            if n.find("{*}chord") is not None:
                stack += 1
                if stack + 1 > max_stack:
                    max_stack = stack + 1
            else:
                stack = 0
        if voices:
            voice_max = max(voice_max, len(voices))
        if max_stack >= 2 or len(voices) >= 2:
            poly_measures += 1
    ratio = poly_measures / len(measures) if measures else 0.0
    return max_stack, round(ratio, 3), voice_max


def _ornament_counts(root: etree._Element) -> dict[str, int]:
    """Count common ornament markers in <notations><ornaments>...."""
    counts = {
        "mordent": len(root.xpath(
            "//*[local-name()='ornaments']/*[local-name()='mordent']"
        )) + len(root.xpath(
            "//*[local-name()='ornaments']/*[local-name()='inverted-mordent']"
        )),
        "trill": len(root.xpath(
            "//*[local-name()='ornaments']/*[local-name()='trill-mark']"
        )),
        "turn": len(root.xpath(
            "//*[local-name()='ornaments']/*[local-name()='turn']"
        )) + len(root.xpath(
            "//*[local-name()='ornaments']/*[local-name()='inverted-turn']"
        )),
    }
    return counts


def _grace_count(root: etree._Element) -> int:
    return len(root.xpath("//*[local-name()='note']/*[local-name()='grace']"))


def _harmonic_count(root: etree._Element) -> int:
    return len(root.xpath(
        "//*[local-name()='technical']/*[local-name()='harmonic']"
    ))


def _barre_count(root: etree._Element) -> int:
    return len(root.xpath(
        "//*[local-name()='technical']/*[local-name()='barre']"
    ))


def _position_shift_proxy(root: etree._Element) -> int | None:
    """Count fret-distance jumps > 4 between consecutive same-string notes.

    Only computable when <technical>/<string> and <fret> are present
    (Sibelius-emitted Guitar Loot files typically have these; LilyPond /
    Mutopia rarely do). Returns None when no string/fret data is found,
    so the caller can mark the cell as unknown rather than zero.
    """
    notes = root.xpath("//*[local-name()='note']")
    last_fret_by_string: dict[str, int] = {}
    shifts = 0
    seen_string_fret = False
    for n in notes:
        s = n.find("{*}notations/{*}technical/{*}string")
        f = n.find("{*}notations/{*}technical/{*}fret")
        if s is None or f is None:
            continue
        seen_string_fret = True
        try:
            string = (s.text or "").strip()
            fret = int((f.text or "0").strip())
        except ValueError:
            continue
        prev = last_fret_by_string.get(string)
        if prev is not None and abs(fret - prev) > 4:
            shifts += 1
        last_fret_by_string[string] = fret
    return shifts if seen_string_fret else None


# Standard-tuning MIDI for open strings 6 → 1 (low E to high E).
_OPEN_STRING_MIDI = (40, 45, 50, 55, 59, 64)
_FRET_RANGE_MAX = 24  # 24-fret guitar; classical tops out lower in practice.


def _pitch_min_fret(midi: int) -> int | None:
    """Lowest fret across any string in standard tuning that can sound `midi`.

    A lower bound on the left-hand position a player must reach: the
    note could be played higher up another string, but never lower.
    Returns None if the pitch is unreachable in standard tuning
    (below low E or above 24th-fret high E).
    """
    best: int | None = None
    for s in _OPEN_STRING_MIDI:
        f = midi - s
        if 0 <= f <= _FRET_RANGE_MAX:
            if best is None or f < best:
                best = f
    return best


def _pitch_fingering_stats(root: etree._Element) -> dict[str, int | None]:
    """Pitch-only proxies for left-hand position load.

    These fill the gap left by `_position_shift_proxy`, which needs
    explicit `<technical>/<string>/<fret>` and is therefore ~100%
    missing for engravers (Sibelius, LilyPond) that don't emit
    string/fret. The proxies here use the pitch sequence alone and
    are a lower bound: actual fingering may force a higher position
    to avoid string crossings.

    - `pitch_min_fret_max` — max min-fret across the piece.
    - `pitch_min_fret_p90` — 90th percentile.
    - `pitch_position_shifts` — melodic jumps in min-fret ≥ 4
      between consecutive non-chord notes (chord continuation notes,
      marked by a leading `<chord/>`, are skipped so each beat
      contributes a single position).
    """
    frets: list[int] = []
    melodic_frets: list[int] = []
    for n in root.xpath("//*[local-name()='note']"):
        p = n.find("{*}pitch")
        if p is None:
            continue
        midi = _note_midi(p)
        if midi is None:
            continue
        f = _pitch_min_fret(midi)
        if f is None:
            continue
        frets.append(f)
        if n.find("{*}chord") is None:
            melodic_frets.append(f)
    if not frets:
        return {
            "pitch_min_fret_max": None,
            "pitch_min_fret_p90": None,
            "pitch_position_shifts": None,
        }
    s = sorted(frets)
    n_total = len(s)
    p90_index = max(0, min(n_total - 1, int(round(0.9 * (n_total - 1)))))
    shifts = sum(
        1 for a, b in zip(melodic_frets, melodic_frets[1:])
        if abs(a - b) >= 4
    )
    return {
        "pitch_min_fret_max": max(frets),
        "pitch_min_fret_p90": s[p90_index],
        "pitch_position_shifts": shifts,
    }


# Pitch-class steps that the key signature implicitly sharps/flats, keyed by
# the MusicXML <fifths> value. Anything with an explicit <alter> on a note
# that doesn't match the active key counts as an accidental.
_KEY_SHARPS_ORDER = ["F", "C", "G", "D", "A", "E", "B"]
_KEY_FLATS_ORDER = ["B", "E", "A", "D", "G", "C", "F"]


def _expected_alter_for_key(fifths: int) -> dict[str, int]:
    """Map pitch step → expected alter (+1/-1/0) given a key fifths value."""
    out = {s: 0 for s in "CDEFGAB"}
    if fifths > 0:
        for s in _KEY_SHARPS_ORDER[: min(fifths, 7)]:
            out[s] = 1
    elif fifths < 0:
        for s in _KEY_FLATS_ORDER[: min(-fifths, 7)]:
            out[s] = -1
    return out


def _accidentals_outside_key(root: etree._Element) -> int:
    """Count notes whose <alter> disagrees with the active key signature.

    Tracks the current key per part as <key>/<fifths> elements appear.
    A note with an explicit <alter> different from the key-implied alter
    for its step counts; naturals against a sharped/flatted step also
    count. Chromaticism load proxy — high values flag heavy modulation
    or chromatic passagework.
    """
    count = 0
    for part in root.xpath("//*[local-name()='part']"):
        current_fifths = 0
        expected = _expected_alter_for_key(0)
        for el in part.iter():
            if not isinstance(el.tag, str):
                continue  # skip comments / processing instructions
            tag = etree.QName(el.tag).localname
            if tag == "fifths" and el.text:
                try:
                    current_fifths = int(el.text.strip())
                except ValueError:
                    continue
                expected = _expected_alter_for_key(current_fifths)
            elif tag == "note":
                p = el.find("{*}pitch")
                if p is None:
                    continue
                step_el = p.find("{*}step")
                if step_el is None or not step_el.text:
                    continue
                step = step_el.text.strip().upper()
                alter_el = p.find("{*}alter")
                if alter_el is None or not (alter_el.text or "").strip():
                    # Implicit natural — counts if the key would alter this step.
                    if expected.get(step, 0) != 0:
                        count += 1
                    continue
                try:
                    alter = int(float(alter_el.text.strip()))
                except ValueError:
                    continue
                if alter != expected.get(step, 0):
                    count += 1
    return count


def _notes_per_measure(root: etree._Element) -> float | None:
    """Average notes per measure across the score, rounded to one decimal.

    Coarse rhythmic-density proxy: a piece with 8 notes/measure is
    typically denser than one with 2. Doesn't normalise for time
    signature; combined with `time_sig` in the model, the model can
    learn the ratio if useful.
    """
    measures = root.xpath("//*[local-name()='measure']")
    if not measures:
        return None
    note_count = sum(
        len(m.xpath("./*[local-name()='note'][not(*[local-name()='rest'])]"))
        for m in measures
    )
    return round(note_count / len(measures), 1)


def _rhythm_misc(root: etree._Element) -> dict[str, int]:
    return {
        "dotted": len(root.xpath("//*[local-name()='note']/*[local-name()='dot']")),
        "tied": len(root.xpath("//*[local-name()='note']/*[local-name()='tie']")),
        "tuplet": len(root.xpath(
            "//*[local-name()='notations']/*[local-name()='tuplet']"
        )),
    }


def _duration_seconds(measure_count: int, tempo_bpm: float | None,
                      time_sig: str) -> float | None:
    """Approximate piece duration: assumes the opening tempo and meter
    hold for the whole piece. Wrong for accelerandos and meter changes,
    but useful as a coarse complexity proxy."""
    if not tempo_bpm or not time_sig or measure_count == 0:
        return None
    try:
        beats, beat_type = time_sig.split("/")
        beats_per_measure = float(beats)
        beat_type_i = int(beat_type)
    except (ValueError, AttributeError):
        return None
    # MusicXML <sound tempo="N"> is N quarter-notes per minute. Convert
    # the piece's beat-type to quarters: a beat of type 8 = half a quarter.
    quarters_per_beat = 4.0 / beat_type_i
    quarters_per_measure = beats_per_measure * quarters_per_beat
    quarters_total = quarters_per_measure * measure_count
    seconds = (quarters_total / tempo_bpm) * 60.0
    return round(seconds, 1)


def extract_features(root: etree._Element) -> dict[str, Any]:
    """Pure function: MusicXML root → flat dict of features."""
    notes = root.xpath("//*[local-name()='note']")
    pitches: list[int] = []
    for n in notes:
        p = n.find("{*}pitch")
        if p is not None:
            midi = _note_midi(p)
            if midi is not None:
                pitches.append(midi)

    measures = root.xpath("//*[local-name()='measure']")
    measure_count = len(measures)
    note_count = len(notes)

    midi_min = min(pitches) if pitches else None
    midi_max = max(pitches) if pitches else None
    midi_range = (midi_max - midi_min) if pitches else None
    midi_median = round(statistics.median(pitches), 1) if pitches else None

    key_fifths, key_changes = _key_changes(root)
    tempo_bpm = _opening_tempo(root)
    time_sig, meter_changes = _time_signature_changes(root)
    smallest = _smallest_division(root)

    max_stack, poly_ratio, voice_max = _polyphony_stats(root)
    rhythm = _rhythm_misc(root)
    notes_per_measure = _notes_per_measure(root)
    accidentals_oo_key = _accidentals_outside_key(root)
    ornaments = _ornament_counts(root)
    grace = _grace_count(root)
    harmonics = _harmonic_count(root)
    barre = _barre_count(root)
    pos_shifts = _position_shift_proxy(root)
    pitch_fingering = _pitch_fingering_stats(root)
    duration = _duration_seconds(measure_count, tempo_bpm, time_sig)

    return {
        "midi_min": midi_min,
        "midi_max": midi_max,
        "midi_range": midi_range,
        "midi_median": midi_median,
        "key_fifths": key_fifths,
        "key_changes": key_changes,
        "tempo_bpm": tempo_bpm,
        "time_sig": time_sig,
        "meter_changes": meter_changes,
        "smallest_division": smallest,
        "dotted_count": rhythm["dotted"],
        "tied_count": rhythm["tied"],
        "tuplet_count": rhythm["tuplet"],
        "notes_per_measure": notes_per_measure,
        "accidentals_outside_key": accidentals_oo_key,
        "max_chord_stack": max_stack,
        "polyphonic_measure_ratio": poly_ratio,
        "voice_count_max": voice_max,
        "ornament_mordent": ornaments["mordent"],
        "ornament_trill": ornaments["trill"],
        "ornament_turn": ornaments["turn"],
        "grace_count": grace,
        "harmonic_count": harmonics,
        "barre_count": barre,
        "position_shift_proxy": pos_shifts,
        "pitch_min_fret_max": pitch_fingering["pitch_min_fret_max"],
        "pitch_min_fret_p90": pitch_fingering["pitch_min_fret_p90"],
        "pitch_position_shifts": pitch_fingering["pitch_position_shifts"],
        "measure_count": measure_count,
        "note_count": note_count,
        "duration_sec_approx": duration,
    }


def _format_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None,
                        help="Process only the first N pieces (for probes).")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_PATH,
                        help=f"Output CSV path (default: {DEFAULT_OUT_PATH}).")
    args = parser.parse_args()

    manifest = load_manifest()
    pieces = manifest.get("pieces", [])
    if not pieces:
        print("No pieces in manifest. Run scripts/m1_validate.py first.",
              file=sys.stderr)
        return 1

    rows: list[dict[str, Any]] = []
    errors: list[tuple[str, str]] = []
    grade_counter: Counter[str] = Counter()

    iterable = pieces if args.limit is None else pieces[: args.limit]
    for i, piece in enumerate(iterable, 1):
        cid = piece.get("candidate_id", "")
        path = REPO_ROOT / piece["normalized_path"]
        try:
            root = etree.parse(str(path)).getroot()
        except Exception as exc:
            errors.append((cid, f"{type(exc).__name__}: {exc}"))
            continue
        feats = extract_features(root)
        meta = piece.get("metadata", {})
        row = {
            "candidate_id": cid,
            "source": piece.get("source", ""),
            "title": meta.get("title", ""),
            "composer_normalized": meta.get(
                "composer_normalized") or meta.get("composer", ""),
            "grade": piece.get("grade", ""),
            "grade_source": piece.get("grade_source", ""),
        }
        row.update(feats)
        rows.append(row)
        if row["grade"]:
            grade_counter[row["grade"]] += 1
        if i % 100 == 0:
            print(f"  {i}/{len(iterable)}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        for row in rows:
            w.writerow([_format_cell(row.get(col, "")) for col in COLUMNS])

    print(f"==> Wrote {len(rows)} feature rows to {args.out}")
    if grade_counter:
        labelled = sum(grade_counter.values())
        print(f"==> Labelled (Delcamp grades): {labelled} / {len(rows)}")
        dist = ", ".join(
            f"G{g}: {grade_counter[g]}"
            for g in sorted(grade_counter, key=lambda x: int(x))
        )
        print(f"    Distribution: {dist}")
    if errors:
        print(f"==> {len(errors)} pieces failed to parse:", file=sys.stderr)
        for cid, err in errors[:5]:
            print(f"    {cid}: {err}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
