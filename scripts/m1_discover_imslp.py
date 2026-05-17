"""M1.1 — IMSLP MusicXML discovery for classical guitar.

Walks the IMSLP MediaWiki API for pages in the configured guitar category,
fetches each page's HTML, and extracts MusicXML file entries. Writes
corpus/candidates.imslp.json.

Empirically: as of the ADR-0006 run, IMSLP has zero classical-guitar
MusicXML files. The script is kept around so we can re-run it if the
upstream supply changes, but it's not the primary source.

No downloads of the MusicXML files themselves — that's M1.2.

Usage:
    python scripts/m1_discover_imslp.py
    python scripts/m1_discover_imslp.py --category "For guitar" --limit 200
    python scripts/m1_discover_imslp.py --dry-run

See decisions/0005-ingest-pipeline.md and 0006-github-as-source.md.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from lxml import html as lxml_html

from m1_common import (
    CORPUS_DIR,
    RateLimitedSession,
    ensure_corpus_dirs,
    write_json_atomic,
)

CANDIDATES_PATH = CORPUS_DIR / "candidates.imslp.json"

IMSLP_API = "https://imslp.org/api.php"
IMSLP_PAGE_URL = "https://imslp.org/wiki/{title}"
IMSLP_FILE_URL = "https://imslp.org/wiki/Special:ReverseLookup/{file_id}"

# Heuristic — IMSLP's wiki uses several near-equivalent category names. We
# try the user-supplied one first and let the empty result speak for itself.
DEFAULT_CATEGORY = "For guitar"

FILE_ID_RE = re.compile(r"/wiki/Special:ReverseLookup/(\d+)")
MUSICXML_TOKENS = ("musicxml", "mxl")


@dataclass
class Candidate:
    work_id: str
    file_id: str
    page_title: str
    page_url: str
    file_url: str
    format_label: str
    license: str
    composer: str

    @property
    def candidate_id(self) -> str:
        return f"imslp:{self.file_id}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source": "imslp",
            "work_id": self.work_id,
            "file_id": self.file_id,
            "page_title": self.page_title,
            "page_url": self.page_url,
            "file_url": self.file_url,
            "format_label": self.format_label,
            "license": self.license,
            "license_spdx": "unknown",
            "composer": self.composer,
        }


def iter_category_members(
    session: RateLimitedSession, category: str, limit: int | None
) -> Iterable[dict[str, Any]]:
    """Page through MediaWiki's list=categorymembers."""
    cmcontinue: str | None = None
    seen = 0
    while True:
        params = {
            "action": "query",
            "format": "json",
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmtype": "page",
            "cmlimit": "max",
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue
        resp = session.get(IMSLP_API, params=params)
        resp.raise_for_status()
        payload = resp.json()
        for member in payload.get("query", {}).get("categorymembers", []):
            yield member
            seen += 1
            if limit is not None and seen >= limit:
                return
        cmcontinue = payload.get("continue", {}).get("cmcontinue")
        if not cmcontinue:
            return


def extract_work_id(page_title: str) -> str:
    """The work_id is the URL-safe page title (slug). IMSLP uses underscores."""
    return page_title.replace(" ", "_")


def parse_file_rows(html_text: str) -> list[dict[str, str]]:
    """Find MusicXML file entries on a page.

    IMSLP's file-listing markup varies by template; we search for rows whose
    visible text mentions MusicXML and then pull the nearest ReverseLookup
    link plus any neighbouring license/format text.
    """
    doc = lxml_html.fromstring(html_text)
    results: list[dict[str, str]] = []

    # Strategy: find every <a> link to Special:ReverseLookup and walk up to a
    # containing block, then inspect that block's text for format/license.
    for anchor in doc.xpath("//a[contains(@href, 'Special:ReverseLookup/')]"):
        href = anchor.get("href", "")
        match = FILE_ID_RE.search(href)
        if not match:
            continue
        file_id = match.group(1)
        # Climb up to find a context block — div / li / tr — that contains
        # enough surrounding text to decide format/license.
        block = anchor
        for _ in range(6):
            parent = block.getparent()
            if parent is None:
                break
            block = parent
            text = " ".join(block.itertext()).lower()
            if "musicxml" in text or "mxl" in text:
                break
        else:
            continue
        block_text = " ".join(block.itertext())
        block_text_lower = block_text.lower()
        if not any(tok in block_text_lower for tok in MUSICXML_TOKENS):
            continue
        license_str = _extract_first_match(
            block_text,
            (
                "Creative Commons",
                "Public Domain",
                "CC0",
                "CC BY",
                "Copyright",
                "PD ",
            ),
        )
        results.append(
            {
                "file_id": file_id,
                "format_label": _shorten(block_text, 200),
                "license": license_str or "unknown",
            }
        )

    # Deduplicate by file_id, preserving the first occurrence (usually the
    # cleanest table row).
    seen_ids: set[str] = set()
    deduped: list[dict[str, str]] = []
    for row in results:
        if row["file_id"] in seen_ids:
            continue
        seen_ids.add(row["file_id"])
        deduped.append(row)
    return deduped


def _extract_first_match(text: str, needles: tuple[str, ...]) -> str | None:
    lower = text.lower()
    earliest: tuple[int, str] | None = None
    for needle in needles:
        idx = lower.find(needle.lower())
        if idx == -1:
            continue
        snippet = text[idx : idx + 80].strip()
        if earliest is None or idx < earliest[0]:
            earliest = (idx, snippet)
    return earliest[1] if earliest else None


def _shorten(text: str, n: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"


def extract_composer(html_text: str) -> str:
    """IMSLP renders the composer in the first <h2> on a work page (e.g.,
    'Sor, Fernando' as a link). Best-effort — empty string if not found."""
    doc = lxml_html.fromstring(html_text)
    nodes = doc.xpath("//h2[contains(@id, 'Composer') or .//*[@id='Composer']]")
    if not nodes:
        return ""
    # Walk forward from the composer header to the first link with /wiki/Category:.
    sibling = nodes[0].getnext()
    hops = 0
    while sibling is not None and hops < 4:
        for a in sibling.xpath(".//a[contains(@href, '/wiki/Category:')]"):
            text = a.text_content().strip()
            if text:
                return text
        sibling = sibling.getnext()
        hops += 1
    return ""


def discover(category: str, limit: int | None, session: RateLimitedSession) -> list[Candidate]:
    candidates: list[Candidate] = []
    member_iter = iter_category_members(session, category, limit)
    for i, member in enumerate(member_iter, 1):
        title = member.get("title", "")
        if not title or title.startswith(("Category:", "File:", "User:", "Talk:")):
            continue
        work_id = extract_work_id(title)
        page_url = IMSLP_PAGE_URL.format(title=work_id)
        try:
            html_text = _fetch_page_html(session, title)
        except Exception as exc:
            print(f"  warn: failed to fetch {title!r}: {exc}", file=sys.stderr)
            continue
        rows = parse_file_rows(html_text)
        if not rows:
            continue
        composer = extract_composer(html_text)
        for row in rows:
            candidates.append(
                Candidate(
                    work_id=work_id,
                    file_id=row["file_id"],
                    page_title=title,
                    page_url=page_url,
                    file_url=IMSLP_FILE_URL.format(file_id=row["file_id"]),
                    format_label=row["format_label"],
                    license=row["license"],
                    composer=composer,
                )
            )
        if i % 25 == 0:
            print(f"  ...processed {i} pages, {len(candidates)} candidates so far")
    return candidates


def _fetch_page_html(session: RateLimitedSession, title: str) -> str:
    """Use the parse API for clean HTML without the surrounding chrome."""
    resp = session.get(
        IMSLP_API,
        params={
            "action": "parse",
            "format": "json",
            "page": title,
            "prop": "text",
            "redirects": "1",
        },
    )
    resp.raise_for_status()
    payload = resp.json()
    return payload.get("parse", {}).get("text", {}).get("*", "") or ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--category",
        default=DEFAULT_CATEGORY,
        help="IMSLP category to walk (without 'Category:' prefix).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after this many category-member pages (debug).",
    )
    parser.add_argument(
        "--min-interval",
        type=float,
        default=1.0,
        help="Minimum seconds between HTTP calls (politeness).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write candidates.json; just print counts.",
    )
    args = parser.parse_args()

    ensure_corpus_dirs()
    session = RateLimitedSession(min_interval_s=args.min_interval)

    print(f"==> Discovering MusicXML files for Category:{args.category}")
    candidates = discover(args.category, args.limit, session)

    print(f"==> Found {len(candidates)} MusicXML candidate(s) "
          f"across {len({c.work_id for c in candidates})} work(s)")

    if args.dry_run:
        for c in candidates[:10]:
            print(f"  {c.work_id}  file={c.file_id}  composer={c.composer!r}")
        if len(candidates) > 10:
            print(f"  ... and {len(candidates) - 10} more")
        return 0

    payload = {
        "version": 2,
        "source": "imslp",
        "source_host": "imslp.org",
        "category": args.category,
        "items": [c.to_dict() for c in candidates],
    }
    write_json_atomic(CANDIDATES_PATH, payload)
    print(f"==> Wrote {CANDIDATES_PATH.relative_to(CANDIDATES_PATH.parents[1])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
