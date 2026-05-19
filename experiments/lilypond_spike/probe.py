"""Run scripts/m1_lilypond.convert_lilypond on yawnoc + davesque .ly files.

Yawnoc files use \include "../conway.ily" — inline the include so the
converter sees a self-contained file."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

REPO = Path("/home/h/Documents/dev/hu/graded-guitar")
sys.path.insert(0, str(REPO / "scripts"))

from m1_lilypond import convert_lilypond, find_score_blocks  # noqa: E402

SPIKE = Path("/tmp/lilypond_spike")


def inline_includes(ly_text: str, base: Path) -> str:
    out_lines: list[str] = []
    for line in ly_text.splitlines(keepends=True):
        s = line.strip()
        if s.startswith("\\include"):
            # Match \include "path"
            start = line.find('"')
            end = line.rfind('"')
            if start >= 0 and end > start:
                rel = line[start + 1: end]
                inc = (base / rel).resolve()
                if inc.exists():
                    out_lines.append(f"% inlined include {rel}\n")
                    out_lines.append(inc.read_text())
                    out_lines.append(f"\n% end inlined {rel}\n")
                    continue
        out_lines.append(line)
    return "".join(out_lines)


def run_one(label: str, ly_path: Path) -> dict:
    src = ly_path.read_text()
    src = inline_includes(src, ly_path.parent)
    blocks = find_score_blocks(src)
    result = convert_lilypond(src)
    movements = result.movements
    clean = sum(1 for m in movements if m.musicxml_bytes is not None)
    return {
        "label": label,
        "path": str(ly_path),
        "score_blocks": len(blocks),
        "movements_returned": len(movements),
        "movements_clean": clean,
        "errors": [m.failure_reason for m in movements if m.musicxml_bytes is None][:3],
        "notes": sum(m.notes for m in movements if m.success),
        "measures": sum(m.measures for m in movements if m.success),
    }


def main() -> int:
    targets: list[tuple[str, Path]] = []
    for ly in sorted((SPIKE / "yawnoc").rglob("*.ly")):
        if ly.parent.name == ".durations":
            label = f"yawnoc/.durations/{ly.stem}"
        else:
            label = f"yawnoc/{ly.parent.name}"
        targets.append((label, ly))
    for ly in sorted((SPIKE / "davesque").rglob("*.ly")):
        targets.append((f"davesque/{ly.stem}", ly))

    print(f"==> Testing {len(targets)} .ly files")
    total_blocks = 0
    total_clean = 0
    for label, ly in targets:
        r = run_one(label, ly)
        total_blocks += r["score_blocks"]
        total_clean += r["movements_clean"]
        print(
            f"  {label:50s} blocks={r['score_blocks']} clean={r['movements_clean']}/{r['movements_returned']}  errs={r['errors']}"
        )
    print(f"\n==> Aggregate: {total_clean}/{total_blocks} clean ({total_clean/max(total_blocks,1)*100:.0f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
