"""M1.2 — Fetch candidate files from every discovery source.

Reads every corpus/candidates.*.json, downloads each candidate, and
content-addresses the bytes by sha256 under corpus/raw/. Skips files
already cached. Source-specific paths:

- IMSLP / GitHub: HTTP fetch of a MusicXML or MXL file.
- Mutopia: HTTP fetch of a .ly file, then LilyPond → MusicXML
  conversion via scripts/m1_lilypond.py. Each `\\score` block in the
  source becomes its own raw file, keyed by `<candidate_id>#movementNN`.

Maintains corpus/cache/fetch_log.json mapping candidate_id (including
synthetic #movement suffixes) → sha256 + fetch metadata, so re-runs are
idempotent.

Usage:
    python scripts/m1_fetch.py
    python scripts/m1_fetch.py --limit 50          # only fetch first 50 missing
    python scripts/m1_fetch.py --force             # ignore cache, re-download
    python scripts/m1_fetch.py --min-interval 2.0  # extra-polite

See decisions/0005-ingest-pipeline.md and 0007-mutopia-source.md.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from m1_common import (
    CACHE_DIR,
    RAW_DIR,
    RateLimitedSession,
    ensure_corpus_dirs,
    load_candidates,
    read_json,
    sha256_bytes,
    write_json_atomic,
)

FETCH_LOG_PATH = CACHE_DIR / "fetch_log.json"

# IMSLP shows a disclaimer interstitial unless this cookie is set. The name
# has historically been `imslpDisclaimerAccepted`; we set a few likely
# variants to maximise the chance of bypassing the interstitial.
DISCLAIMER_COOKIES = {
    "imslpDisclaimerAccepted": "yes",
    "imslp_wikiLanguageSelectorLanguage": "en",
}

MUSICXML_MAGIC = (
    b"<?xml",
    b"<score-partwise",
    b"<score-timewise",
    b"<!DOCTYPE score-partwise",
)
MXL_MAGIC = b"PK\x03\x04"   # zip signature


def detect_format(blob: bytes) -> str | None:
    """Return 'musicxml', 'mxl', or None if neither."""
    head = blob[:64]
    if blob.startswith(MXL_MAGIC):
        return "mxl"
    if any(head.lstrip().startswith(magic) for magic in MUSICXML_MAGIC):
        return "musicxml"
    # Some files start with a BOM
    if blob.startswith(b"\xef\xbb\xbf") and b"<?xml" in blob[:128]:
        return "musicxml"
    return None


def fetch_one(
    session: RateLimitedSession, url: str
) -> tuple[bytes, str] | tuple[None, str]:
    """Returns (blob, format) or (None, reason)."""
    try:
        for cookie_name, cookie_value in DISCLAIMER_COOKIES.items():
            session.session.cookies.set(cookie_name, cookie_value, domain="imslp.org")
        resp = session.get(url, allow_redirects=True)
    except Exception as exc:
        return None, f"network_error: {exc}"
    if resp.status_code != 200:
        return None, f"http_{resp.status_code}"
    blob = resp.content
    if not blob:
        return None, "empty_body"
    fmt = detect_format(blob)
    if fmt is None:
        return None, "format_undetected"
    return blob, fmt


def save_blob(blob: bytes, fmt: str) -> tuple[str, Path]:
    digest = sha256_bytes(blob)
    ext = "mxl" if fmt == "mxl" else "musicxml"
    path = RAW_DIR / f"{digest}.{ext}"
    if not path.exists():
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(blob)
        tmp.replace(path)
    return digest, path


def fetch_mutopia(
    session: RateLimitedSession, candidate: dict[str, Any],
    entries: dict[str, Any], stats: dict[str, int],
) -> None:
    """Download a Mutopia .ly file and convert it via the LilyPond
    wrapper. Each `\\score` block becomes its own entry in `entries`
    keyed `<parent_cid>#movementNN`. The parent cid gets a "container"
    entry so we don't re-fetch on subsequent runs."""
    # Lazy import — only needed when Mutopia candidates are present.
    from m1_lilypond import convert_lilypond

    parent_cid = candidate["candidate_id"]
    url = candidate["file_url"]
    try:
        resp = session.get(url, allow_redirects=True)
    except Exception as exc:
        entries[parent_cid] = {
            "status": "failed", "reason": f"network_error: {exc}",
            "url": url, "container": True,
        }
        stats["failed"] += 1
        print(f"    FAILED (network): {exc}")
        return
    if resp.status_code != 200 or not resp.content:
        entries[parent_cid] = {
            "status": "failed", "reason": f"http_{resp.status_code}",
            "url": url, "container": True,
        }
        stats["failed"] += 1
        print(f"    FAILED: http_{resp.status_code}")
        return

    ly_text = resp.content.decode("utf-8", errors="replace")
    result = convert_lilypond(ly_text)

    if not result.movements:
        entries[parent_cid] = {
            "status": "failed", "reason": "no_movements_produced",
            "url": url, "container": True,
        }
        stats["failed"] += 1
        print(f"    FAILED: wrapper produced no movements")
        return

    movement_entries = []
    for mv in result.movements:
        movement_cid = f"{parent_cid}#movement{mv.movement_index:02d}"
        if not mv.success:
            entries[movement_cid] = {
                "status": "failed",
                "reason": mv.failure_reason or "LY_CONVERSION_FAILED",
                "detail": mv.failure_detail or "",
                "fallbacks": mv.fallbacks_applied,
                "parent": parent_cid,
            }
            stats["failed"] += 1
            movement_entries.append((movement_cid, False))
            continue
        digest, path = save_blob(mv.musicxml_bytes, "musicxml")
        entries[movement_cid] = {
            "status": "ok",
            "sha256": digest,
            "format": "musicxml",
            "size_bytes": len(mv.musicxml_bytes),
            "path": str(path.relative_to(RAW_DIR.parent.parent)),
            "url": url,
            "parent": parent_cid,
            "fallbacks": mv.fallbacks_applied,
            "ly_metrics": {"parts": mv.parts, "measures": mv.measures,
                           "notes": mv.notes},
        }
        stats["fetched"] += 1
        movement_entries.append((movement_cid, True))

    # Container entry — records what was produced so re-runs skip.
    entries[parent_cid] = {
        "status": "container",
        "url": url,
        "container": True,
        "source_score_count": result.source_score_count,
        "header_metadata": result.metadata,
        "movements": [
            {"candidate_id": cid, "ok": ok} for cid, ok in movement_entries
        ],
    }
    ok_count = sum(1 for _, ok in movement_entries if ok)
    print(f"    OK: {ok_count}/{len(movement_entries)} movements clean "
          f"(score_count={result.source_score_count})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force", action="store_true",
                        help="Ignore fetch_log and re-download everything.")
    parser.add_argument("--min-interval", type=float, default=1.0)
    args = parser.parse_args()

    ensure_corpus_dirs()
    candidates = load_candidates()
    if not candidates:
        print("No candidates.*.json found. Run a discovery script first "
              "(e.g. scripts/m1_discover_github.py).",
              file=sys.stderr)
        return 1

    fetch_log: dict[str, Any] = read_json(
        FETCH_LOG_PATH, default={"version": 1, "entries": {}}
    )
    entries: dict[str, Any] = fetch_log.get("entries", {})

    session = RateLimitedSession(min_interval_s=args.min_interval)

    stats = {"fetched": 0, "cached": 0, "failed": 0}
    failures: list[dict[str, Any]] = []

    for i, c in enumerate(candidates, 1):
        cid = c["candidate_id"]
        if not args.force and cid in entries:
            stats["cached"] += 1
            continue
        if args.limit is not None and stats["fetched"] >= args.limit:
            break
        url = c["file_url"]
        source = c.get("source", "")
        print(f"  [{i}/{len(candidates)}] {cid} -> {url}")

        if source == "mutopia":
            fetch_mutopia(session, c, entries, stats)
        else:
            result, info = fetch_one(session, url)
            if result is None:
                stats["failed"] += 1
                failures.append({"candidate_id": cid, "url": url, "reason": info})
                entries[cid] = {
                    "status": "failed",
                    "reason": info,
                    "url": url,
                }
                print(f"    FAILED: {info}")
            else:
                digest, path = save_blob(result, info)
                stats["fetched"] += 1
                entries[cid] = {
                    "status": "ok",
                    "sha256": digest,
                    "format": info,
                    "size_bytes": len(result),
                    "path": str(path.relative_to(RAW_DIR.parent.parent)),
                    "url": url,
                }
                print(f"    OK: {info}, {len(result)} bytes, "
                      f"sha256={digest[:12]}…")

        # Flush log every 10 candidates so a crash doesn't lose progress.
        if (stats["fetched"] + stats["failed"]) % 10 == 0:
            write_json_atomic(FETCH_LOG_PATH, {"version": 1, "entries": entries})

    write_json_atomic(FETCH_LOG_PATH, {"version": 1, "entries": entries})

    print(
        f"==> Fetched {stats['fetched']}, cached {stats['cached']}, "
        f"failed {stats['failed']}"
    )
    if failures:
        print(f"    First failures: {failures[:3]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
