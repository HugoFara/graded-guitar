"""M1.1 (Guitar Loot) — Discover classical-guitar MusicXML on guitarloot.org.uk.

Walks the 41 composer / category pages catalogued by the
`experiments/guitarloot_probe/` probe. For each `.mxl` anchor, emits
one candidate carrying composer (from the page heading), title (from
the anchor text), the Delcamp 1-10 grade if present in the surrounding
text, and the per-piece `<rights>` license string — actually captured
at fetch time from the file itself; at discovery time we just record
the site-wide license blurb.

Each candidate writes to corpus/candidates.guitarloot.json. The
discovery script does NOT download the .mxl files; that's m1_fetch.py's
job and it already handles .mxl via the generic IMSLP/GitHub path.

Usage:
    python scripts/m1_discover_guitarloot.py
    python scripts/m1_discover_guitarloot.py --limit-pages 5
    python scripts/m1_discover_guitarloot.py --min-interval 2.0

See decisions/0008-guitarloot-source.md.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
from dataclasses import asdict, dataclass, field
from typing import Any

from lxml import html as lxml_html

from m1_common import (
    CORPUS_DIR,
    RateLimitedSession,
    ensure_corpus_dirs,
    write_json_atomic,
)

CANDIDATES_PATH = CORPUS_DIR / "candidates.guitarloot.json"

BASE = "https://www.guitarloot.org.uk"

# Per-piece license string is declared in <rights> inside every .mxl
# (see Dowland FantasyP5GtrAS.mxl): "You may freely use or adapt this
# arrangement provided you acknowledge me as its source." We record the
# verbatim string at discover time so the manifest carries it even if
# the file itself is gone or the bytes change. SPDX has no exact match;
# this is closest to CC-BY in spirit.
SITE_LICENSE = (
    "You may freely use or adapt this arrangement "
    "provided you acknowledge me as its source."
)
SITE_LICENSE_SPDX = "unknown"

GRADE_SOURCE = "delcamp-eric-crouch"

# (composer-or-category-label, page-path). Composer label becomes a
# discovery-time hint; the canonical composer name is later replaced by
# the one in <creator type="composer"> at validate time.
PAGES: list[tuple[str, str]] = [
    # Solo Music - Anonymous sources
    ("Anonymous (English, B-C)", "/page-6/page-7/page-8/"),
    ("Anonymous (English, F-H)", "/page-6/page-7/page-9/"),
    ("Anonymous (Holmes)", "/page-6/page-7/page-46/"),
    ("Anonymous (English, M)", "/page-6/page-7/page-10/"),
    ("Anonymous (English, P-W)", "/page-6/page-7/page-11/"),
    ("Anonymous (Non-UK)", "/page-6/page-13/"),
    # Solo Music - Named composers
    ("Richard Allison", "/page-6/page/"),
    ("Daniel Bacheler", "/page-6/page-2/"),
    ("Francis Cutting", "/page-6/page-3/"),
    ("John Danyel", "/page-6/page-12/"),
    ("John Dowland", "/page-6/page-14/"),
    ("Alfonso Ferrabosco I", "/page-6/page-15/"),
    ("Giovanni Paulo Foscarini", "/page-6/page-77/"),
    ("Cuthbert Hely", "/page-6/page-75/"),
    ("Anthony Holborne", "/page-6/page-16/"),
    ("John & Robert Johnson", "/page-6/page-17/"),
    ("Johann Kapsberger", "/page-6/page-18/"),
    ("Jean Mercure", "/page-6/page-19/"),
    ("Domenico Pellegrini", "/page-6/page-20/"),
    ("Alessandro Piccinini", "/page-6/page-21/"),
    ("Francis Pilkington", "/page-6/page-22/"),
    ("Jakub Polak", "/page-6/page-23/"),
    ("Esaias Reusner", "/page-6/page-24/"),
    ("Thomas Robinson", "/page-6/page-25/"),
    ("Nicolas Vallet", "/page-6/page-26/"),
    ("Sylvius Leopold Weiss", "/page-6/page-27/"),
    ("John Wilson", "/page-6/page-28/"),
    ("Other English Composers", "/page-6/page-29/"),
    ("Scottish Lute Music", "/page-6/page-30/"),
    ("Other Non-UK Composers", "/page-6/page-31/"),
    ("Other Solo Music", "/page-6/page-45/"),
    # Ensembles (will be rejected as MULTIPLE_PARTS by validator —
    # intentional; recorded so rejections show in corpus/rejected.json).
    ("Guitar Duets", "/page-33/page-35/"),
    ("Guitar Trios", "/page-33/page-36/"),
    ("Guitar Mixed Ensemble", "/page-33/page-34/"),
    # Lyra Viol transcribed
    ("William Corkine (Lyra Viol Solos)", "/page-37/page-38/"),
    ("Tobias Hume (Lyra Viol Solos)", "/page-37/page-41/"),
    ("Other Lyra Viol Solos", "/page-37/page-42/"),
    ("Thomas Ford (Lyra Viol Duets)", "/page-37/page-39/"),
    ("Tobias Hume (Lyra Viol Duets)", "/page-37/page-43/"),
    ("Other Lyra Viol Duets", "/page-37/page-44/"),
    ("Lyra Viol Trios", "/page-37/page-40/"),
]

GRADE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("grade-word", re.compile(r"\bgrade\s*[:#]?\s*(\d{1,2})\b", re.I)),
    ("gr-abbrev", re.compile(r"\bgr\.?\s*(\d{1,2})\b", re.I)),
    ("bracket", re.compile(r"[\[(]\s*(?:grade\s*)?(\d{1,2})\s*[\])]", re.I)),
    ("level-word", re.compile(r"\blevel\s*[:#]?\s*(\d{1,2})\b", re.I)),
]


@dataclass
class GuitarLootCandidate:
    candidate_id: str       # guitarloot:{relpath_no_ext}
    source: str             # "guitarloot"
    file_url: str           # absolute .mxl URL
    page_url: str           # composer/category page URL
    composer_hint: str      # from page label; canonical name comes from <creator>
    title_hint: str         # from anchor text
    grade: str              # "1".."10" or "" if not parseable
    grade_source: str       # "delcamp-eric-crouch" when grade present
    license: str
    license_spdx: str
    format_label: str       # "mxl"
    path: str               # relpath under /Scores/ — drives PATH_NOISE filter

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _context_text(elem) -> str:
    cur = elem
    for _ in range(6):
        if cur is None:
            break
        tag = (cur.tag or "").lower() if hasattr(cur, "tag") else ""
        if tag in {"li", "p", "tr", "div", "td"}:
            return " ".join(cur.itertext()).strip()
        cur = cur.getparent()
    parent = elem.getparent()
    if parent is not None:
        return " ".join(parent.itertext()).strip()
    return (elem.text or "")


def _detect_grade(text: str) -> str:
    for _, pat in GRADE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        try:
            n = int(m.group(1))
        except ValueError:
            continue
        if 1 <= n <= 10:
            return str(n)
    return ""


def _title_from_anchor(a) -> str:
    """Prefer the anchor's own text; fall back to a nearby strong/heading."""
    text = (a.text or "").strip()
    if text and text.lower() not in {"mxl", "musicxml", "xml", "download"}:
        return text
    # Walk up to the row/li/p and look for the first non-link strong text.
    cur = a.getparent()
    for _ in range(4):
        if cur is None:
            break
        for child in cur.iter():
            tag = (child.tag or "").lower() if hasattr(child, "tag") else ""
            if tag in {"strong", "b", "em", "i"}:
                t = " ".join(child.itertext()).strip()
                if t:
                    return t
        cur = cur.getparent()
    # Final fallback: stem of the file URL.
    href = (a.get("href") or "").rsplit("/", 1)[-1]
    return href.rsplit(".", 1)[0]


def _candidate_id_from_url(file_url: str) -> tuple[str, str]:
    """Return (candidate_id, repo_relative_path)."""
    parsed = urllib.parse.urlparse(file_url)
    path = parsed.path  # /Scores/EnglishMusic/Dowland/FantasyP5GtrAS.mxl
    stem = path.rsplit(".", 1)[0].lstrip("/")
    return f"guitarloot:{stem}", path.lstrip("/")


def discover_page(
    session: RateLimitedSession, composer_label: str, page_path: str
) -> list[GuitarLootCandidate]:
    page_url = BASE + page_path
    resp = session.get(page_url)
    if resp.status_code != 200 or not resp.content:
        print(f"  !! {composer_label}: http_{resp.status_code}", file=sys.stderr)
        return []
    try:
        tree = lxml_html.fromstring(resp.content)
    except Exception as exc:  # noqa: BLE001
        print(f"  !! {composer_label}: parse failed: {exc!r}", file=sys.stderr)
        return []

    candidates: list[GuitarLootCandidate] = []
    for a in tree.iter("a"):
        href = a.get("href") or ""
        href_l = href.lower()
        if not (href_l.endswith(".mxl") or href_l.endswith(".musicxml")
                or href_l.endswith(".xml")):
            continue
        file_url = urllib.parse.urljoin(page_url, href)
        cid, rel_path = _candidate_id_from_url(file_url)
        context = _context_text(a)
        grade = _detect_grade(context)
        title = _title_from_anchor(a)
        candidates.append(GuitarLootCandidate(
            candidate_id=cid,
            source="guitarloot",
            file_url=file_url,
            page_url=page_url,
            composer_hint=composer_label,
            title_hint=title,
            grade=grade,
            grade_source=GRADE_SOURCE if grade else "",
            license=SITE_LICENSE,
            license_spdx=SITE_LICENSE_SPDX,
            format_label="mxl",
            path=rel_path,
        ))
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit-pages", type=int, default=None)
    parser.add_argument("--min-interval", type=float, default=1.0)
    args = parser.parse_args()

    ensure_corpus_dirs()
    session = RateLimitedSession(min_interval_s=args.min_interval)

    pages = PAGES[: args.limit_pages] if args.limit_pages else PAGES
    all_candidates: list[GuitarLootCandidate] = []
    seen_ids: set[str] = set()
    per_page_counts: list[tuple[str, int, int]] = []

    for i, (label, path) in enumerate(pages, 1):
        print(f"[{i:>2}/{len(pages)}] {label:<40} {path}")
        page_cands = discover_page(session, label, path)
        kept = 0
        graded = 0
        for c in page_cands:
            if c.candidate_id in seen_ids:
                continue
            seen_ids.add(c.candidate_id)
            all_candidates.append(c)
            kept += 1
            if c.grade:
                graded += 1
        per_page_counts.append((label, kept, graded))
        print(f"            mxl={kept:>3}  graded={graded:>3}")

    grade_dist: dict[str, int] = {}
    for c in all_candidates:
        if c.grade:
            grade_dist[c.grade] = grade_dist.get(c.grade, 0) + 1

    payload = {
        "version": 1,
        "source": "guitarloot",
        "site_license": SITE_LICENSE,
        "grade_source": GRADE_SOURCE,
        "summary": {
            "total_candidates": len(all_candidates),
            "graded": sum(1 for c in all_candidates if c.grade),
            "grade_distribution": {k: grade_dist[k] for k in sorted(grade_dist, key=int)},
            "pages_walked": len(pages),
        },
        "items": [c.to_dict() for c in all_candidates],
    }
    write_json_atomic(CANDIDATES_PATH, payload)

    print()
    print(f"==> Discovered {len(all_candidates)} .mxl candidates "
          f"across {len(pages)} pages")
    print(f"==> Graded: {payload['summary']['graded']}/"
          f"{len(all_candidates)}")
    if grade_dist:
        dist = ", ".join(f"G{k}:{grade_dist[k]}" for k in sorted(grade_dist, key=int))
        print(f"    Grade distribution: {dist}")
    print(f"==> Wrote {CANDIDATES_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
