"""Guitar Loot discovery probe.

Walks every solo / duet / lyra-viol composer page on guitarloot.org.uk,
extracts .mxl (compressed MusicXML) links, and looks for per-piece grade
annotations (Delcamp 1-10 scale, per page-47/page-48/). Reports aggregate
counts so we can decide whether to integrate Guitar Loot as a third M1
source.

Not part of the M1 pipeline. Outputs go to /tmp/guitarloot-probe by
default and are not committed.

Usage:
    python3 experiments/guitarloot_probe/probe.py
    python3 experiments/guitarloot_probe/probe.py --workdir /tmp/x --limit 5
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from lxml import html as lxml_html


BASE = "https://www.guitarloot.org.uk"
USER_AGENT = (
    "graded-guitar/0.1 (+https://github.com/HugoFara/graded-guitar; "
    "probe; contact github@hugofara.net)"
)

# From sitemap (https://www.guitarloot.org.uk/sitemap/). Each entry is
# (label, path). Labels echo the sitemap so the report is readable.
PAGES: list[tuple[str, str]] = [
    # Solo Music - Anonymous sources
    ("Anon Sources: B - C", "/page-6/page-7/page-8/"),
    ("Anon Sources: F - H", "/page-6/page-7/page-9/"),
    ("Anon Sources: Holmes", "/page-6/page-7/page-46/"),
    ("Anon Sources: M", "/page-6/page-7/page-10/"),
    ("Anon Sources: P - W", "/page-6/page-7/page-11/"),
    ("Anon - Non UK sources", "/page-6/page-13/"),
    # Solo Music - Named composers
    ("Richard Allison", "/page-6/page/"),
    ("Daniel Bacheler", "/page-6/page-2/"),
    ("Francis Cutting", "/page-6/page-3/"),
    ("John Danyel", "/page-6/page-12/"),
    ("John Dowland", "/page-6/page-14/"),
    ("Alfonso Ferrabosco 1", "/page-6/page-15/"),
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
    ("Other non UK Composers", "/page-6/page-31/"),
    ("Other Solo Music", "/page-6/page-45/"),
    # Ensembles
    ("Guitar Duets", "/page-33/page-35/"),
    ("Guitar Trios", "/page-33/page-36/"),
    ("Guitar - other", "/page-33/page-34/"),
    # Lyra Viol transcribed
    ("Lyra Viol Solos - Corkine", "/page-37/page-38/"),
    ("Lyra Viol Solos - Hume", "/page-37/page-41/"),
    ("Lyra Viol Solos - other", "/page-37/page-42/"),
    ("Lyra Viol Duets - Ford", "/page-37/page-39/"),
    ("Lyra Viol Duets - Hume", "/page-37/page-43/"),
    ("Lyra Viol Duets - other", "/page-37/page-44/"),
    ("Lyra Viol Trios", "/page-37/page-40/"),
]


# Grade annotation heuristic. The site uses the Delcamp 1-10 scale,
# described on /page-47/page-48/. Likely appearances next to a piece
# title: "Grade 3", "Gr 3", "(grade 3)", "[3]", etc. We try a few
# patterns and report which one matched so we can tune later.
GRADE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("grade-word", re.compile(r"\bgrade\s*[:#]?\s*(\d{1,2})\b", re.I)),
    ("gr-abbrev", re.compile(r"\bgr\.?\s*(\d{1,2})\b", re.I)),
    ("bracket", re.compile(r"[\[(]\s*(?:grade\s*)?(\d{1,2})\s*[\])]", re.I)),
    ("level-word", re.compile(r"\blevel\s*[:#]?\s*(\d{1,2})\b", re.I)),
]


@dataclass
class PageResult:
    label: str
    path: str
    status: int = 0
    error: str = ""
    mxl_count: int = 0
    pdf_count: int = 0
    mid_count: int = 0
    mxl_urls: list[str] = field(default_factory=list)
    mxl_with_grade: int = 0
    grade_distribution: dict[str, int] = field(default_factory=dict)
    grade_pattern_hits: dict[str, int] = field(default_factory=dict)
    sample_grade_hits: list[dict[str, str]] = field(default_factory=list)


def fetch(url: str) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:  # noqa: BLE001
        return 0, repr(e).encode("utf-8", errors="replace")


def extract_text_near(elem) -> str:
    """Return a chunk of text around `elem` likely to carry annotations.

    We walk to the nearest block-level ancestor (li, p, tr, div) and
    flatten its text — link captions, surrounding labels, etc.
    """
    cur = elem
    for _ in range(6):
        if cur is None:
            break
        tag = (cur.tag or "").lower() if hasattr(cur, "tag") else ""
        if tag in {"li", "p", "tr", "div", "td"}:
            return " ".join(cur.itertext()).strip()
        cur = cur.getparent()
    # Fall back to immediate parent's text.
    parent = elem.getparent()
    if parent is not None:
        return " ".join(parent.itertext()).strip()
    return (elem.text or "")


def detect_grade(context_text: str) -> tuple[str | None, str | None]:
    """Return (grade_str, pattern_label) or (None, None)."""
    for label, pat in GRADE_PATTERNS:
        m = pat.search(context_text)
        if m:
            value = m.group(1)
            try:
                n = int(value)
            except ValueError:
                continue
            if 1 <= n <= 10:
                return str(n), label
    return None, None


def probe_page(label: str, path: str) -> PageResult:
    url = BASE + path
    result = PageResult(label=label, path=path)
    status, body = fetch(url)
    result.status = status
    if status != 200 or not body:
        result.error = body.decode("utf-8", errors="replace")[:200] if body else "no body"
        return result

    try:
        tree = lxml_html.fromstring(body)
    except Exception as e:  # noqa: BLE001
        result.error = f"parse failed: {e!r}"
        return result

    # Find every anchor with an .mxl / .pdf / .mid href.
    for a in tree.iter("a"):
        href = a.get("href") or ""
        href_l = href.lower()
        if href_l.endswith(".mxl") or href_l.endswith(".musicxml") or href_l.endswith(".xml"):
            abs_url = urllib.parse.urljoin(url, href)
            result.mxl_count += 1
            result.mxl_urls.append(abs_url)
            context = extract_text_near(a)
            grade, pattern_label = detect_grade(context)
            if grade is not None:
                result.mxl_with_grade += 1
                result.grade_distribution[grade] = result.grade_distribution.get(grade, 0) + 1
                result.grade_pattern_hits[pattern_label] = (
                    result.grade_pattern_hits.get(pattern_label, 0) + 1
                )
                if len(result.sample_grade_hits) < 3:
                    result.sample_grade_hits.append({
                        "url": abs_url,
                        "grade": grade,
                        "pattern": pattern_label,
                        "context": context[:200],
                    })
        elif href_l.endswith(".pdf"):
            result.pdf_count += 1
        elif href_l.endswith(".mid") or href_l.endswith(".midi"):
            result.mid_count += 1

    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workdir", default="/tmp/guitarloot-probe", type=Path)
    ap.add_argument("--limit", type=int, default=0, help="Probe only the first N pages (0 = all)")
    ap.add_argument("--delay", type=float, default=1.0, help="Seconds between requests (be polite)")
    args = ap.parse_args()

    args.workdir.mkdir(parents=True, exist_ok=True)

    pages = PAGES[: args.limit] if args.limit else PAGES
    results: list[PageResult] = []

    for i, (label, path) in enumerate(pages, 1):
        print(f"[{i:>2}/{len(pages)}] {label:<32} {path}", flush=True)
        result = probe_page(label, path)
        results.append(result)
        if result.status != 200:
            print(f"            !! status={result.status} error={result.error}")
        else:
            grade_pct = (
                f"{(100 * result.mxl_with_grade / result.mxl_count):.0f}%"
                if result.mxl_count
                else "—"
            )
            print(
                f"            mxl={result.mxl_count:>3}  pdf={result.pdf_count:>3}  "
                f"mid={result.mid_count:>3}  graded={result.mxl_with_grade:>3} ({grade_pct})"
            )
        if i < len(pages):
            time.sleep(args.delay)

    # Aggregate.
    total_mxl = sum(r.mxl_count for r in results)
    total_with_grade = sum(r.mxl_with_grade for r in results)
    total_pdf = sum(r.pdf_count for r in results)
    grade_dist: dict[str, int] = {}
    pattern_dist: dict[str, int] = {}
    for r in results:
        for g, n in r.grade_distribution.items():
            grade_dist[g] = grade_dist.get(g, 0) + n
        for p, n in r.grade_pattern_hits.items():
            pattern_dist[p] = pattern_dist.get(p, 0) + n

    summary = {
        "pages_probed": len(results),
        "pages_ok": sum(1 for r in results if r.status == 200),
        "pages_error": [
            {"label": r.label, "path": r.path, "status": r.status, "error": r.error}
            for r in results
            if r.status != 200
        ],
        "total_mxl": total_mxl,
        "total_pdf": total_pdf,
        "total_mxl_with_grade": total_with_grade,
        "grade_distribution": {k: grade_dist[k] for k in sorted(grade_dist, key=int)},
        "grade_pattern_hits": pattern_dist,
        "per_page": [
            {
                "label": r.label,
                "path": r.path,
                "status": r.status,
                "mxl": r.mxl_count,
                "pdf": r.pdf_count,
                "mid": r.mid_count,
                "mxl_with_grade": r.mxl_with_grade,
                "grade_distribution": r.grade_distribution,
                "sample_grade_hits": r.sample_grade_hits,
            }
            for r in results
        ],
    }

    json_path = args.workdir / "probe.json"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print()
    print("=" * 60)
    print(f"Pages probed:       {summary['pages_probed']}")
    print(f"Pages OK:           {summary['pages_ok']}")
    if summary["pages_error"]:
        print(f"Pages with errors:  {len(summary['pages_error'])}")
        for e in summary["pages_error"]:
            print(f"   - {e['label']} ({e['path']}): status={e['status']}")
    print(f"Total .mxl links:   {total_mxl}")
    print(f"Total .pdf links:   {total_pdf}")
    if total_mxl:
        pct = 100 * total_with_grade / total_mxl
        print(f"Grade-annotated:    {total_with_grade}/{total_mxl} ({pct:.1f}%)")
    if grade_dist:
        dist_str = ", ".join(f"{g}:{grade_dist[g]}" for g in sorted(grade_dist, key=int))
        print(f"Grade distribution: {dist_str}")
    if pattern_dist:
        print(f"Pattern hits:       {pattern_dist}")
    print(f"JSON report:        {json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
