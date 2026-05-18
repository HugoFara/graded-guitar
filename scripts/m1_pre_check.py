"""M1 pre-check — mechanical sanity checks across the accepted manifest.

Reads corpus/manifest.json, parses each normalized MusicXML file once,
and flags pieces that look suspicious on cheap-to-compute criteria the
musical advisor (ADR 0004) shouldn't have to spend time on:

  - multi-staff scores (piano/duo that slipped past parts==1)
  - non-treble or missing clef
  - pitch range outside a 6-string guitar
  - chord stacks larger than 6 notes
  - fragments (very few measures or notes)
  - suspicious title / composer strings (test files, GitHub usernames)
  - per-Delcamp-grade feature spread (Guitar Loot only)

Writes a punch list to corpus/spot_check.md. Does NOT modify the
manifest — this is read-only triage, not a re-validation pass.

Usage:
    python scripts/m1_pre_check.py
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from lxml import etree

from m1_common import CORPUS_DIR, MANIFEST_PATH, REPO_ROOT


SPOT_CHECK_PATH = CORPUS_DIR / "spot_check.md"

STEP_TO_SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# Guitar range gates. Standard 6-string in standard tuning is E2 (40) to
# roughly E6 (88) at the 24th fret of the high E string. We flag pieces
# that go below the drop-D low D (D2 = 38) or above E6 (88) — those are
# almost certainly not standard classical guitar.
MIDI_LOW_GATE = 38
MIDI_HIGH_GATE = 88

# Physically impossible on 6 strings. We allow 6 (full strum) and only
# flag 7+ — some MusicXML encoders write a melody note + 6-note chord as
# a single 7-note stack even though it'd be rolled in performance.
MAX_CHORD_GATE = 7

# Fragments — pedagogically useless and usually OMR/test files.
MIN_MEASURES = 8
MIN_NOTES = 16

# Title strings that pass the PLACEHOLDER_TITLES gate in m1_validate but
# still look like test/demo/dataset files. Matched as whole words
# (case-insensitive) so "Testament" doesn't trip "test" and "Mademoiselle"
# doesn't trip "demo".
SUSPICIOUS_TITLE_TOKENS = (
    "demo",
    "demo1",
    "test",
    "test1",
    "example",
    "sample",
    "asdf",
    "noname",
    "scratch",
    "placeholder",
    "lorem",
)
_SUSPICIOUS_TITLE_RE = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in SUSPICIOUS_TITLE_TOKENS) + r")\b",
    re.IGNORECASE,
)

# Composer-looks-like-a-GitHub-username heuristic: short, no spaces,
# starts with a lowercase letter or digit. Real composers virtually
# always have a capitalized surname.
_USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9_\-]{1,15}$")


def parse_xml(path: Path) -> etree._Element | None:
    try:
        return etree.parse(str(path)).getroot()
    except (etree.XMLSyntaxError, OSError):
        return None


def count_staves(root: etree._Element) -> int:
    staves: set[int] = set()
    for staff_node in root.xpath("//*[local-name()='note']/*[local-name()='staff']"):
        try:
            staves.add(int((staff_node.text or "").strip()))
        except ValueError:
            continue
    return max(1, len(staves))


def collect_clefs(root: etree._Element) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for clef in root.xpath("//*[local-name()='clef']"):
        sign_n = clef.xpath("./*[local-name()='sign']")
        line_n = clef.xpath("./*[local-name()='line']")
        oct_n = clef.xpath("./*[local-name()='clef-octave-change']")
        sign = (sign_n[0].text if sign_n else "").strip().upper()
        line = (line_n[0].text if line_n else "").strip()
        oct_change = (oct_n[0].text if oct_n else "0").strip()
        out.append((sign, line, oct_change))
    return out


def clef_looks_guitar(clefs: list[tuple[str, str, str]]) -> bool:
    """Standard classical-guitar clef is treble 8vb (G, line 2, -1).

    We also accept plain treble (octave-change 0), since many encoders
    don't bother with the -1. Pure bass clef alone is the red flag.
    """
    if not clefs:
        return False
    for sign, _line, _oct in clefs:
        if sign == "G":
            return True
    return False


def collect_midi_pitches(root: etree._Element) -> list[int]:
    pitches: list[int] = []
    for pitch in root.xpath("//*[local-name()='pitch']"):
        step_n = pitch.xpath("./*[local-name()='step']")
        octave_n = pitch.xpath("./*[local-name()='octave']")
        alter_n = pitch.xpath("./*[local-name()='alter']")
        if not step_n or not octave_n:
            continue
        try:
            step = (step_n[0].text or "").strip().upper()
            octave = int((octave_n[0].text or "").strip())
            alter = int((alter_n[0].text or "0").strip()) if alter_n else 0
        except (ValueError, AttributeError):
            continue
        if step not in STEP_TO_SEMI:
            continue
        pitches.append((octave + 1) * 12 + STEP_TO_SEMI[step] + alter)
    return pitches


def max_chord_size(root: etree._Element) -> int:
    """Largest simultaneous note count in any chord.

    MusicXML encodes a chord as a sequence of <note> siblings where all
    but the first carry a <chord/> child. A <rest> or any non-chord
    <note> closes the previous chord group.
    """
    biggest = 0
    current = 0
    for note in root.xpath("//*[local-name()='note']"):
        if note.xpath("./*[local-name()='rest']"):
            biggest = max(biggest, current)
            current = 0
            continue
        if note.xpath("./*[local-name()='chord']"):
            current += 1
        else:
            biggest = max(biggest, current)
            current = 1
    return max(biggest, current)


def measure_count(root: etree._Element) -> int:
    return len(root.xpath("//*[local-name()='part'][1]/*[local-name()='measure']"))


def note_count(root: etree._Element) -> int:
    return len(
        root.xpath(
            "//*[local-name()='note'][not(./*[local-name()='rest'])]"
        )
    )


def suspicious_title(title: str) -> str | None:
    t = title.strip()
    if not t:
        return None
    m = _SUSPICIOUS_TITLE_RE.search(t)
    if m:
        return m.group(1).lower()
    tl = t.lower()
    if tl.isdigit() and len(tl) <= 2:
        return "digits-only"
    if len(tl) <= 2:
        return "too-short"
    return None


def looks_like_username(composer: str) -> bool:
    return bool(_USERNAME_RE.match(composer.strip()))


def piece_short_id(piece: dict[str, Any]) -> str:
    """Compact identifier for the report. Strips the long file_url."""
    cid = piece.get("candidate_id", "")
    # gh:owner/repo@branch:path/file.xml  →  gh:owner/repo:.../file.xml
    if cid.startswith("gh:") and ":" in cid[3:]:
        head, _, tail = cid.rpartition(":")
        return f"{head.split('@')[0]}:.../{Path(tail).name}"
    if cid.startswith("guitarloot:"):
        return f"guitarloot:{Path(cid.split(':',1)[1]).name}"
    if cid.startswith("mutopia:"):
        return cid  # already concise
    return cid


def check_piece(piece: dict[str, Any]) -> dict[str, Any]:
    rel_path = piece.get("normalized_path", "")
    full = REPO_ROOT / rel_path
    if not full.exists():
        return {"flags": [("FILE_MISSING", rel_path)], "stats": None}

    root = parse_xml(full)
    if root is None:
        return {"flags": [("XML_PARSE_FAILED", rel_path)], "stats": None}

    staves = count_staves(root)
    clefs = collect_clefs(root)
    pitches = collect_midi_pitches(root)
    chord = max_chord_size(root)
    measures = measure_count(root)
    notes = note_count(root)
    title = (piece.get("metadata") or {}).get("title", "")
    composer = (piece.get("metadata") or {}).get("composer", "")

    flags: list[tuple[str, str]] = []
    if staves > 1:
        flags.append(("MULTI_STAFF", f"{staves} staves"))
    if not clef_looks_guitar(clefs):
        signs = ",".join(sorted({c[0] or "?" for c in clefs})) or "(none)"
        flags.append(("NON_TREBLE_CLEF", f"clef signs: {signs}"))
    if pitches:
        lo, hi = min(pitches), max(pitches)
        if lo < MIDI_LOW_GATE:
            flags.append(("OUT_OF_RANGE_LOW", f"min MIDI={lo}"))
        if hi > MIDI_HIGH_GATE:
            flags.append(("OUT_OF_RANGE_HIGH", f"max MIDI={hi}"))
    else:
        flags.append(("NO_PITCHES", "score has no pitched notes"))
    if chord > MAX_CHORD_GATE:
        flags.append(("CHORD_TOO_LARGE", f"{chord} simultaneous notes"))
    if measures < MIN_MEASURES:
        flags.append(("FRAGMENT_MEASURES", f"{measures} measures"))
    if notes < MIN_NOTES:
        flags.append(("FRAGMENT_NOTES", f"{notes} notes"))
    tt = suspicious_title(title)
    if tt:
        flags.append(("SUSPICIOUS_TITLE", f"{title!r} — matched {tt!r}"))
    if looks_like_username(composer):
        flags.append(("COMPOSER_LIKE_USERNAME", f"composer={composer!r}"))

    notes_per_measure = (notes / measures) if measures else 0.0

    return {
        "flags": flags,
        "stats": {
            "staves": staves,
            "midi_lo": min(pitches) if pitches else None,
            "midi_hi": max(pitches) if pitches else None,
            "max_chord": chord,
            "measures": measures,
            "notes": notes,
            "notes_per_measure": notes_per_measure,
        },
    }


def render_flag_section(
    label: str, flag_code: str, by_code: dict[str, list[tuple[dict[str, Any], str]]]
) -> list[str]:
    entries = by_code.get(flag_code, [])
    out = [f"### {label} — {len(entries)}", ""]
    if not entries:
        out.append("- (none)")
        out.append("")
        return out
    for piece, detail in entries[:25]:
        meta = piece.get("metadata") or {}
        out.append(
            f"- `{piece_short_id(piece)}` — "
            f"{meta.get('composer','?')} / {meta.get('title','?')} — {detail}"
        )
        out.append(f"  - file: `{piece.get('normalized_path','')}`")
        if piece.get("page_url"):
            out.append(f"  - source: {piece['page_url']}")
    if len(entries) > 25:
        out.append(f"- … and {len(entries) - 25} more")
    out.append("")
    return out


def main() -> int:
    if not MANIFEST_PATH.exists():
        print(f"manifest not found at {MANIFEST_PATH}", file=sys.stderr)
        return 1
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    pieces = manifest.get("pieces", [])
    print(f"==> Pre-checking {len(pieces)} pieces from {MANIFEST_PATH.name}")

    by_code: dict[str, list[tuple[dict[str, Any], str]]] = defaultdict(list)
    flag_counts: Counter[str] = Counter()
    grade_features: dict[str, list[dict[str, Any]]] = defaultdict(list)
    clean_pieces = 0

    for i, piece in enumerate(pieces, 1):
        if i % 100 == 0:
            print(f"    {i}/{len(pieces)}")
        result = check_piece(piece)
        if result["stats"] is None:
            for code, detail in result["flags"]:
                by_code[code].append((piece, detail))
                flag_counts[code] += 1
            continue

        if not result["flags"]:
            clean_pieces += 1
        for code, detail in result["flags"]:
            by_code[code].append((piece, detail))
            flag_counts[code] += 1

        if piece.get("grade"):
            grade_features[piece["grade"]].append({
                "candidate_id": piece["candidate_id"],
                "title": (piece.get("metadata") or {}).get("title", ""),
                "stats": result["stats"],
            })

    lines: list[str] = [
        "# M1 spot-check punch list",
        "",
        "Mechanical pre-checks across `corpus/manifest.json`. Generated by "
        "`scripts/m1_pre_check.py`. This is **not** the formal advisor review "
        "(ADR 0004 hard gate). It's a punch list of pieces the advisor should "
        "not have to look at because they have an obvious mechanical problem.",
        "",
        f"- Pieces checked: **{len(pieces)}**",
        f"- Clean (no flags): **{clean_pieces}**",
        f"- Pieces with at least one flag: **{len(pieces) - clean_pieces}**",
        "",
        "## Flag counts",
        "",
    ]
    if flag_counts:
        for code, n in flag_counts.most_common():
            lines.append(f"- `{code}` — {n}")
    else:
        lines.append("- (none)")
    lines.append("")

    lines.append("## Flagged pieces")
    lines.append("")
    section_order = [
        ("Multi-staff (likely not solo guitar)", "MULTI_STAFF"),
        ("No treble clef present", "NON_TREBLE_CLEF"),
        ("Pitch below drop-D low D (MIDI 38)", "OUT_OF_RANGE_LOW"),
        ("Pitch above high-E 24th fret (MIDI 88)", "OUT_OF_RANGE_HIGH"),
        ("Chord stack > 6 notes (physically impossible)", "CHORD_TOO_LARGE"),
        ("Fragment: < 8 measures", "FRAGMENT_MEASURES"),
        ("Fragment: < 16 notes", "FRAGMENT_NOTES"),
        ("Score has no pitched notes", "NO_PITCHES"),
        ("Suspicious title (demo / test / sample / etc.)", "SUSPICIOUS_TITLE"),
        ("Composer looks like a GitHub username", "COMPOSER_LIKE_USERNAME"),
        ("Could not read normalized file", "FILE_MISSING"),
        ("XML failed to parse", "XML_PARSE_FAILED"),
    ]
    for label, code in section_order:
        lines.extend(render_flag_section(label, code, by_code))

    # Per-Delcamp-grade feature spread — sanity check that grades roughly
    # track piece complexity.
    if grade_features:
        lines.append("## Per-grade feature spread (Guitar Loot)")
        lines.append("")
        lines.append(
            "For each Delcamp grade band, the median values across all pieces "
            "in that band. If the medians don't roughly trend upward with "
            "grade, the labels are either inconsistent or the features are "
            "uninformative — both interesting for M2."
        )
        lines.append("")
        lines.append(
            "| Grade | n | median notes/measure | median max-chord | "
            "median measures | median notes |"
        )
        lines.append("|------:|--:|---------------------:|-----------------:|"
                     "----------------:|-------------:|")
        for grade in sorted(grade_features, key=lambda g: int(g)):
            entries = grade_features[grade]
            npm = statistics.median(e["stats"]["notes_per_measure"] for e in entries)
            mc = statistics.median(e["stats"]["max_chord"] for e in entries)
            mm = statistics.median(e["stats"]["measures"] for e in entries)
            mn = statistics.median(e["stats"]["notes"] for e in entries)
            lines.append(
                f"| G{grade} | {len(entries)} | {npm:.2f} | {mc:.0f} | "
                f"{mm:.0f} | {mn:.0f} |"
            )
        lines.append("")

    SPOT_CHECK_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"==> Wrote {SPOT_CHECK_PATH}")
    print(f"    Clean pieces: {clean_pieces}/{len(pieces)}")
    for code, n in flag_counts.most_common():
        print(f"    {code}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
