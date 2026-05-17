"""LilyPond → MusicXML probe.

Downloads a sample of Mutopia classical-guitar .ly files, splits each into
its top-level `\\score{…}` blocks, runs `python-ly`'s `ly musicxml` per
block, and checks whether the resulting MusicXML is structurally usable.

Purpose: decide whether Mutopia is worth integrating as an M1 source.
"Clean" output means: well-formed XML, score-partwise root, ≥1 part with
≥1 measure containing ≥1 note.

Not part of the M1 pipeline. Outputs go to a working directory (default
/tmp/lilypond-probe) and are not committed.

Usage:
    pip install python-ly                 # 0.9.10 known-good
    python3 experiments/lilypond_probe/probe.py
    python3 experiments/lilypond_probe/probe.py --workdir /tmp/x --urls custom.txt
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree


HERE = Path(__file__).resolve().parent
DEFAULT_URLS_FILE = HERE / "sample_urls.txt"
DEFAULT_WORKDIR = Path("/tmp/lilypond-probe")


def fetch_text(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "graded-guitar/0.1 (+research; github@hugofara.net)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def strip_comments_for_scan(src: str) -> str:
    """Return a copy of `src` with comments and string literals blanked out
    (replaced with spaces, length-preserving) so brace counting is correct.

    We don't remove them — that would shift offsets. We just neutralise
    their content so `{` / `}` inside don't fool the counter."""
    out = list(src)
    i = 0
    n = len(src)
    while i < n:
        ch = src[i]
        # %{ ... %} block comment
        if ch == "%" and i + 1 < n and src[i + 1] == "{":
            j = src.find("%}", i + 2)
            if j == -1:
                j = n
            else:
                j += 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
            continue
        # % line comment
        if ch == "%":
            j = src.find("\n", i)
            j = n if j == -1 else j
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
            continue
        # "..." string
        if ch == '"':
            j = i + 1
            while j < n and src[j] != '"':
                if src[j] == "\\" and j + 1 < n:
                    j += 2
                else:
                    j += 1
            for k in range(i, min(j + 1, n)):
                if out[k] != "\n":
                    out[k] = " "
            i = j + 1
            continue
        i += 1
    return "".join(out)


SCORE_TOKEN = re.compile(r"\\score\b")


def find_score_blocks(src: str) -> list[tuple[int, int]]:
    """Find every top-level `\\score { … }` block and return (start, end)
    offsets into `src`. `end` is one past the closing brace."""
    scan = strip_comments_for_scan(src)
    blocks: list[tuple[int, int]] = []
    for m in SCORE_TOKEN.finditer(scan):
        # Find the opening brace after \score
        i = m.end()
        while i < len(scan) and scan[i] not in "{":
            if not scan[i].isspace():
                # something other than whitespace before `{` — not a block form
                break
            i += 1
        if i >= len(scan) or scan[i] != "{":
            continue
        # Count braces from depth 1
        depth = 1
        j = i + 1
        while j < len(scan) and depth > 0:
            c = scan[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            j += 1
        if depth != 0:
            continue
        blocks.append((m.start(), j))  # end is one past final `}`
    return blocks


def split_score_blocks(src: str) -> list[str]:
    """For each top-level `\\score` block, build a self-contained .ly with
    the file's preamble (everything before the first `\\score`) + that
    block. Returns the list of synthesised .ly contents.

    If there's zero or one block, returns [src] unchanged."""
    blocks = find_score_blocks(src)
    if len(blocks) <= 1:
        return [src]
    preamble_end = blocks[0][0]
    preamble = src[:preamble_end]
    out: list[str] = []
    for start, end in blocks:
        out.append(preamble + src[start:end] + "\n")
    return out


def run_ly_to_musicxml(ly_text: str, out_path: Path) -> tuple[bool, str]:
    """Convert one .ly source to MusicXML at out_path. Returns (ok, stderr)."""
    in_path = out_path.with_suffix(".ly")
    in_path.write_text(ly_text, encoding="utf-8")
    proc = subprocess.run(
        ["ly", "-o", str(out_path), "musicxml", str(in_path)],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0 or not out_path.exists():
        return False, (proc.stderr or proc.stdout or "ly failed")[:400]
    return True, proc.stderr[:400] if proc.stderr else ""


def validate_musicxml(xml_path: Path) -> tuple[bool, dict]:
    """Return (clean, details). Clean = well-formed, score-partwise root,
    ≥1 part with ≥1 measure containing ≥1 note."""
    try:
        root = etree.parse(str(xml_path)).getroot()
    except etree.XMLSyntaxError as e:
        return False, {"reason": "XML_MALFORMED", "detail": str(e)[:100]}
    tag = etree.QName(root).localname
    if tag not in ("score-partwise", "score-timewise"):
        return False, {"reason": "XML_NOT_MUSICXML", "detail": tag}
    parts = root.xpath("//*[local-name()='part-list']/*[local-name()='score-part']")
    if not parts:
        return False, {"reason": "NO_PARTS", "detail": ""}
    notes = root.xpath("//*[local-name()='note']")
    measures = root.xpath("//*[local-name()='measure']")
    if not notes:
        return False, {"reason": "NO_NOTES", "detail": f"{len(measures)} measures"}
    return True, {
        "parts": len(parts),
        "measures": len(measures),
        "notes": len(notes),
    }


@dataclass
class FileResult:
    url: str
    name: str
    source_score_count: int
    converted_blocks: int = 0
    clean_blocks: int = 0
    block_details: list[dict] = field(default_factory=list)
    fatal_error: str = ""


def probe_one(url: str, workdir: Path) -> FileResult:
    name = url.rsplit("/", 1)[-1].removesuffix(".ly")
    res = FileResult(url=url, name=name, source_score_count=0)
    try:
        src = fetch_text(url)
    except Exception as e:
        res.fatal_error = f"download failed: {e}"
        return res
    blocks_src = split_score_blocks(src)
    res.source_score_count = len(find_score_blocks(src))
    blocks_to_try = blocks_src if res.source_score_count >= 1 else [src]

    for i, ly_text in enumerate(blocks_to_try):
        out_xml = workdir / f"{name}__movement{i+1:02d}.musicxml"
        ok, stderr = run_ly_to_musicxml(ly_text, out_xml)
        if not ok:
            res.block_details.append({
                "block": i + 1, "clean": False,
                "reason": "ly_conversion_failed",
                "detail": stderr[:200],
            })
            continue
        res.converted_blocks += 1
        clean, details = validate_musicxml(out_xml)
        if clean:
            res.clean_blocks += 1
        details["block"] = i + 1
        details["clean"] = clean
        if stderr:
            details["ly_stderr_head"] = stderr.splitlines()[0][:140]
        res.block_details.append(details)
    return res


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--urls", default=str(DEFAULT_URLS_FILE),
                        help="File with one .ly URL per line")
    parser.add_argument("--workdir", default=str(DEFAULT_WORKDIR),
                        help="Where to write downloaded .ly + converted .musicxml")
    args = parser.parse_args()

    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    urls = [
        line.strip() for line in Path(args.urls).read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    print(f"==> Probing {len(urls)} URLs into {workdir}")

    results: list[FileResult] = []
    for url in urls:
        print(f"\n--- {url}")
        r = probe_one(url, workdir)
        if r.fatal_error:
            print(f"    FATAL: {r.fatal_error}")
        else:
            print(f"    \\score blocks in source: {r.source_score_count}")
            print(f"    converted: {r.converted_blocks}/"
                  f"{max(r.source_score_count, 1)}   "
                  f"clean (validates): {r.clean_blocks}")
            for d in r.block_details:
                line = f"      block {d['block']}: clean={d['clean']}"
                if d.get("reason"):
                    line += f"  reason={d['reason']}"
                if d.get("parts") is not None:
                    line += (f"  parts={d['parts']} "
                             f"measures={d['measures']} notes={d['notes']}")
                if d.get("ly_stderr_head"):
                    line += f"  stderr={d['ly_stderr_head']!r}"
                print(line)
        results.append(r)

    # Aggregate
    total_blocks_expected = sum(max(r.source_score_count, 1) for r in results
                                if not r.fatal_error)
    total_blocks_clean = sum(r.clean_blocks for r in results)
    fully_clean_files = sum(
        1 for r in results
        if not r.fatal_error
        and r.clean_blocks == max(r.source_score_count, 1)
        and r.clean_blocks > 0
    )
    partial_files = sum(
        1 for r in results
        if not r.fatal_error
        and 0 < r.clean_blocks < max(r.source_score_count, 1)
    )
    failed_files = sum(
        1 for r in results
        if not r.fatal_error and r.clean_blocks == 0
    )
    fatal_files = sum(1 for r in results if r.fatal_error)

    print("\n==> Summary")
    print(f"    files probed:                {len(results)}")
    print(f"    fully clean (all blocks ok): {fully_clean_files}")
    print(f"    partial (some blocks ok):    {partial_files}")
    print(f"    no clean blocks at all:      {failed_files}")
    print(f"    fatal (download fail):       {fatal_files}")
    print(f"    blocks expected:             {total_blocks_expected}")
    print(f"    blocks clean:                {total_blocks_clean} "
          f"({100*total_blocks_clean/max(1,total_blocks_expected):.0f}%)")

    summary_path = workdir / "summary.json"
    summary_path.write_text(json.dumps([{
        "url": r.url, "name": r.name,
        "source_score_count": r.source_score_count,
        "converted_blocks": r.converted_blocks,
        "clean_blocks": r.clean_blocks,
        "blocks": r.block_details,
        "fatal_error": r.fatal_error,
    } for r in results], indent=2))
    print(f"\n==> Full per-block summary: {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
