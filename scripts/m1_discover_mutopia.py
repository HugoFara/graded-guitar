"""M1.1 (Mutopia) — Discover classical-guitar .ly files on Mutopia.

Walks the Mutopia `make-table.cgi?Instrument=Guitar` index pages
(paginated, 10 results per page) and extracts every .ly URL. Writes
candidates to corpus/candidates.mutopia.json.

Each candidate represents one .ly source file. At fetch time, the .ly
file is downloaded and the LilyPond → MusicXML wrapper splits it into
per-`\\score` movements; each movement becomes a separate raw file
keyed by `<candidate_id>#movement<NN>`.

Usage:
    python scripts/m1_discover_mutopia.py
    python scripts/m1_discover_mutopia.py --limit-pages 5

See decisions/0007-mutopia-source.md.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, asdict
from typing import Any

from m1_common import (
    CORPUS_DIR,
    RateLimitedSession,
    ensure_corpus_dirs,
    write_json_atomic,
)

CANDIDATES_PATH = CORPUS_DIR / "candidates.mutopia.json"

INDEX_BASE = "https://www.mutopiaproject.org/cgibin/make-table.cgi"
FTP_BASE = "https://www.mutopiaproject.org"

# Mutopia HTML lists files via direct anchor tags. Match href that ends in
# .ly (case-insensitive); accept absolute, protocol-relative, and relative
# (/ftp/...) forms.
LY_HREF_RE = re.compile(r"""href=["'](?P<href>[^"']+\.ly)["']""", re.IGNORECASE)


@dataclass
class MutopiaCandidate:
    candidate_id: str       # mutopia:{path_no_ext}
    source: str             # "mutopia"
    file_url: str           # absolute .ly URL
    page_url: str           # absolute URL to the piece's directory
    license: str            # always "Mutopia (CC or PD; see per-file)"
    license_spdx: str       # extracted at fetch time from the .ly header
    composer: str           # extracted at fetch time
    format_label: str       # "lilypond" (so fetch knows to convert)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _absolute(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return FTP_BASE + href
    return f"{FTP_BASE}/{href}"


def _candidate_from_url(url: str) -> MutopiaCandidate:
    # Mutopia URL: https://www.mutopiaproject.org/ftp/Composer/Opus/Piece/Piece.ly
    # Stable id strips host + .ly extension.
    path = url.split("mutopiaproject.org", 1)[-1]
    if path.startswith("/"):
        path = path[1:]
    stem = path.removesuffix(".ly")
    page_url = url.rsplit("/", 1)[0] + "/"
    return MutopiaCandidate(
        candidate_id=f"mutopia:{stem}",
        source="mutopia",
        file_url=url,
        page_url=page_url,
        license="Mutopia: per-file CC or PD",
        license_spdx="TBD",
        composer="",
        format_label="lilypond",
    )


def discover(session: RateLimitedSession, page_size: int,
             limit_pages: int | None) -> list[MutopiaCandidate]:
    seen: set[str] = set()
    candidates: list[MutopiaCandidate] = []
    page_idx = 0
    consecutive_empty = 0

    while True:
        if limit_pages is not None and page_idx >= limit_pages:
            break
        startat = page_idx * page_size
        params = {"Instrument": "Guitar", "startat": str(startat)}
        url = f"{INDEX_BASE}?Instrument=Guitar&startat={startat}"
        print(f"==> Page {page_idx + 1} (startat={startat}): {url}")
        try:
            resp = session.get(url)
        except Exception as exc:
            print(f"    page fetch failed: {exc}", file=sys.stderr)
            consecutive_empty += 1
            if consecutive_empty >= 2:
                break
            page_idx += 1
            continue
        if resp.status_code != 200:
            print(f"    HTTP {resp.status_code}", file=sys.stderr)
            consecutive_empty += 1
            if consecutive_empty >= 2:
                break
            page_idx += 1
            continue
        text = resp.text
        new_on_page = 0
        for m in LY_HREF_RE.finditer(text):
            href = m.group("href")
            full = _absolute(href)
            if full in seen:
                continue
            seen.add(full)
            new_on_page += 1
            candidates.append(_candidate_from_url(full))
        print(f"    {new_on_page} new .ly URL(s); {len(candidates)} total")
        if new_on_page == 0:
            consecutive_empty += 1
            if consecutive_empty >= 2:
                break
        else:
            consecutive_empty = 0
        page_idx += 1
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page-size", type=int, default=10,
                        help="Mutopia paginates 10 per page; keep at 10.")
    parser.add_argument("--limit-pages", type=int, default=None,
                        help="Stop after this many pages (debug).")
    parser.add_argument("--min-interval", type=float, default=1.0,
                        help="Seconds between HTTP calls.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ensure_corpus_dirs()
    session = RateLimitedSession(min_interval_s=args.min_interval)

    candidates = discover(session, args.page_size, args.limit_pages)
    print(f"\n==> {len(candidates)} candidate .ly file(s) total")

    if args.dry_run:
        for c in candidates[:10]:
            print(f"  {c.candidate_id}")
        if len(candidates) > 10:
            print(f"  ... and {len(candidates) - 10} more")
        return 0

    payload = {
        "version": 2,
        "source": "mutopia",
        "source_host": "mutopiaproject.org",
        "items": [c.to_dict() for c in candidates],
    }
    write_json_atomic(CANDIDATES_PATH, payload)
    print(f"==> Wrote {CANDIDATES_PATH.relative_to(CANDIDATES_PATH.parents[1])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
