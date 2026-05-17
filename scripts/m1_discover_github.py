"""M1.1 (GitHub) — Discover MusicXML files for classical guitar on GitHub.

Runs a set of `gh search code` queries, deduplicates results by (repo, path),
fetches each repo's default branch + SPDX license, and writes candidate
entries to corpus/candidates.github.json. No file downloads — that's M1.2.

Uses the `gh` CLI for auth and rate-limit handling. You must be logged in
(`gh auth status`).

Usage:
    python scripts/m1_discover_github.py
    python scripts/m1_discover_github.py --query-set basic
    python scripts/m1_discover_github.py --queries "guitar extension:musicxml" \
        --queries "classical guitar extension:musicxml"
    python scripts/m1_discover_github.py --dry-run

See decisions/0006-github-as-source.md.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.parse
from dataclasses import dataclass, asdict
from typing import Any

from m1_common import (
    CORPUS_DIR,
    ensure_corpus_dirs,
    write_json_atomic,
)

CANDIDATES_PATH = CORPUS_DIR / "candidates.github.json"

# Multiple targeted queries to bypass GitHub's 1000-result-per-query cap.
# Loose at discovery; validation enforces the actual classical-guitar bar.
DEFAULT_QUERIES = [
    "guitar extension:musicxml",
    "classical guitar extension:musicxml",
    "tarrega extension:musicxml",
    "sor extension:musicxml",
    "villa-lobos extension:musicxml",
    "carcassi extension:musicxml",
    "carulli extension:musicxml",
    "giuliani extension:musicxml",
    "aguado extension:musicxml",
    "barrios extension:musicxml",
    "brouwer extension:musicxml",
    "ponce extension:musicxml",
    "guitar extension:mxl",
]

PER_PAGE_LIMIT = 1000      # gh search code hard cap
DEFAULT_PER_QUERY = 100    # one page; raises the per-query limit only on demand
DEFAULT_INTER_QUERY_S = 3  # seconds between search queries to stay under
                           # GitHub's secondary rate limit (30 search/min)


@dataclass
class GhCandidate:
    candidate_id: str
    source: str
    repo: str
    ref: str
    path: str
    page_url: str
    file_url: str
    license: str
    license_spdx: str
    composer: str
    format_label: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def gh_search_code(query: str, limit: int, retries: int = 2) -> list[dict[str, Any]]:
    cmd = [
        "gh", "search", "code",
        "--json", "repository,path",
        "--limit", str(limit),
        query,
    ]
    for attempt in range(retries + 1):
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            try:
                return json.loads(proc.stdout or "[]")
            except json.JSONDecodeError as exc:
                print(f"  ! could not parse gh output for {query!r}: {exc}",
                      file=sys.stderr)
                return []
        stderr = proc.stderr.lower()
        if "rate limit" in stderr and attempt < retries:
            wait = 60 * (attempt + 1)
            print(f"  ... rate limited on {query!r}, sleeping {wait}s",
                  file=sys.stderr)
            time.sleep(wait)
            continue
        print(f"  ! gh search failed for {query!r}: {proc.stderr.strip()[:200]}",
              file=sys.stderr)
        return []
    return []


def gh_repo_meta(owner_repo: str) -> dict[str, Any]:
    """Fetch default branch + SPDX license for a repo. Empty dict on failure."""
    cmd = [
        "gh", "api", f"/repos/{owner_repo}",
        "--jq",
        '{default_branch, license_spdx: (.license.spdx_id // "unknown"), '
        'license_name: (.license.name // "unknown"), '
        'archived: .archived, fork: .fork}',
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return {}
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {}


def gh_walk_repo(owner_repo: str, ref: str) -> list[str]:
    """List every .musicxml/.mxl blob path in a repo's tree at the given ref.

    Uses GitHub's recursive trees API. Truncated trees are not retried — the
    log warns instead, since hitting that limit on a repertoire repo would
    be a surprise worth investigating manually.
    """
    cmd = [
        "gh", "api", f"/repos/{owner_repo}/git/trees/{ref}?recursive=1",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        print(f"  ! gh tree fetch failed for {owner_repo}@{ref}: "
              f"{proc.stderr.strip()[:200]}", file=sys.stderr)
        return []
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return []
    if payload.get("truncated"):
        print(f"  ! tree truncated for {owner_repo}@{ref}; some files missed",
              file=sys.stderr)
    paths: list[str] = []
    for node in payload.get("tree", []):
        if node.get("type") != "blob":
            continue
        path = node.get("path", "")
        low = path.lower()
        if low.endswith(".musicxml") or low.endswith(".mxl"):
            paths.append(path)
    return paths


def build_candidate(repo: str, path: str, meta: dict[str, Any]) -> GhCandidate:
    ref = meta.get("default_branch") or "HEAD"
    quoted_path = urllib.parse.quote(path)
    file_url = f"https://raw.githubusercontent.com/{repo}/{ref}/{quoted_path}"
    page_url = f"https://github.com/{repo}/blob/{ref}/{quoted_path}"
    fmt = "mxl" if path.lower().endswith(".mxl") else "musicxml"
    return GhCandidate(
        candidate_id=f"gh:{repo}@{ref}:{path}",
        source="github",
        repo=repo,
        ref=ref,
        path=path,
        page_url=page_url,
        file_url=file_url,
        license=meta.get("license_name", "unknown"),
        license_spdx=meta.get("license_spdx", "unknown"),
        composer="",  # extracted in M1.3 from the MusicXML itself
        format_label=fmt,
    )


def discover(
    queries: list[str], per_query_limit: int, skip_forks: bool,
    inter_query_s: float, walk_repos: list[str],
) -> list[GhCandidate]:
    seen: set[tuple[str, str]] = set()  # (repo, path)
    raw_hits: list[tuple[str, str]] = []
    repo_meta_cache: dict[str, dict[str, Any]] = {}

    def _meta(repo: str) -> dict[str, Any]:
        if repo not in repo_meta_cache:
            repo_meta_cache[repo] = gh_repo_meta(repo)
        return repo_meta_cache[repo]

    for qi, q in enumerate(queries):
        if qi > 0 and inter_query_s > 0:
            time.sleep(inter_query_s)
        print(f"==> Query: {q!r}")
        hits = gh_search_code(q, per_query_limit)
        print(f"    {len(hits)} result(s)")
        for h in hits:
            repo = h.get("repository", {}).get("nameWithOwner", "")
            path = h.get("path", "")
            if not repo or not path:
                continue
            key = (repo, path)
            if key in seen:
                continue
            seen.add(key)
            raw_hits.append((repo, path))

    # Tree-walk extra repos so we pick up every MusicXML file, not only the
    # ones that surfaced in search (which is incomplete + path-keyword
    # biased).
    for repo in walk_repos:
        meta = _meta(repo)
        ref = meta.get("default_branch") or "HEAD"
        print(f"==> Walk: {repo}@{ref}")
        paths = gh_walk_repo(repo, ref)
        print(f"    {len(paths)} MusicXML/MXL blob(s)")
        for path in paths:
            key = (repo, path)
            if key in seen:
                continue
            seen.add(key)
            raw_hits.append((repo, path))

    print(f"==> {len(raw_hits)} unique (repo, path) pair(s)")

    candidates: list[GhCandidate] = []
    for i, (repo, path) in enumerate(raw_hits, 1):
        meta = _meta(repo)
        if skip_forks and meta.get("fork"):
            continue
        candidates.append(build_candidate(repo, path, meta))
        if i % 50 == 0:
            print(f"    ...resolved {i}/{len(raw_hits)}")

    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--query",
        action="append",
        dest="queries",
        help="Override default query set (repeatable).",
    )
    parser.add_argument(
        "--per-query-limit",
        type=int,
        default=DEFAULT_PER_QUERY,
        help=f"Max results per query. Default {DEFAULT_PER_QUERY}; gh hard "
             f"cap is {PER_PAGE_LIMIT} (every 100 = +1 API call → +1 toward "
             f"the 30/min secondary limit).",
    )
    parser.add_argument(
        "--inter-query-sleep",
        type=float,
        default=DEFAULT_INTER_QUERY_S,
        help="Seconds to sleep between search queries (rate-limit politeness).",
    )
    parser.add_argument(
        "--walk-repo",
        action="append",
        dest="walk_repos",
        default=[],
        help="Walk the full tree of owner/repo and include every "
             ".musicxml/.mxl blob as a candidate (repeatable). Useful for "
             "repos we trust where keyword-search misses files.",
    )
    parser.add_argument(
        "--keep-forks",
        action="store_true",
        help="Include forks (default: exclude).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write candidates.github.json; just print counts.",
    )
    args = parser.parse_args()

    ensure_corpus_dirs()
    queries = args.queries or DEFAULT_QUERIES
    candidates = discover(
        queries=queries,
        per_query_limit=args.per_query_limit,
        skip_forks=not args.keep_forks,
        inter_query_s=args.inter_query_sleep,
        walk_repos=args.walk_repos,
    )

    print(f"==> {len(candidates)} candidate(s) after dedup + filtering")
    if candidates:
        license_counts: dict[str, int] = {}
        for c in candidates:
            license_counts[c.license_spdx] = license_counts.get(c.license_spdx, 0) + 1
        top = sorted(license_counts.items(), key=lambda x: -x[1])[:8]
        print("    License (SPDX) distribution:")
        for spdx, n in top:
            print(f"      {spdx}: {n}")

    if args.dry_run:
        for c in candidates[:10]:
            print(f"  {c.candidate_id}  [{c.license_spdx}]")
        if len(candidates) > 10:
            print(f"  ... and {len(candidates) - 10} more")
        return 0

    payload = {
        "version": 2,
        "source": "github",
        "queries": queries,
        "items": [c.to_dict() for c in candidates],
    }
    write_json_atomic(CANDIDATES_PATH, payload)
    print(f"==> Wrote {CANDIDATES_PATH.relative_to(CANDIDATES_PATH.parents[1])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
