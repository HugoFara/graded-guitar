"""Shared utilities for the M1 ingest pipeline.

See decisions/0005-ingest-pipeline.md for the architecture.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "corpus"
RAW_DIR = CORPUS_DIR / "raw"
NORMALIZED_DIR = CORPUS_DIR / "normalized"
CACHE_DIR = CORPUS_DIR / "cache"

CANDIDATES_GLOB = "candidates.*.json"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
REJECTED_PATH = CORPUS_DIR / "rejected.json"
REPORT_PATH = CORPUS_DIR / "report.md"

USER_AGENT = (
    "graded-guitar/0.1 (+https://github.com/HugoFara/graded-guitar; "
    "research; contact github@hugofara.net)"
)
DEFAULT_MIN_INTERVAL_S = 1.0


@dataclass
class RateLimitedSession:
    """A requests.Session wrapper that enforces a minimum interval between calls."""

    min_interval_s: float = DEFAULT_MIN_INTERVAL_S
    session: requests.Session = None  # type: ignore[assignment]
    _last_call_ts: float = 0.0

    def __post_init__(self) -> None:
        if self.min_interval_s < 0.5:
            raise ValueError("min_interval_s must be >= 0.5 to stay polite")
        s = requests.Session()
        s.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
        retries = Retry(
            total=3,
            backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "HEAD"),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retries)
        s.mount("http://", adapter)
        s.mount("https://", adapter)
        self.session = s

    def _wait(self) -> None:
        elapsed = time.time() - self._last_call_ts
        if elapsed < self.min_interval_s:
            time.sleep(self.min_interval_s - elapsed)
        self._last_call_ts = time.time()

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        self._wait()
        kwargs.setdefault("timeout", 30)
        return self.session.get(url, **kwargs)


def ensure_corpus_dirs() -> None:
    CORPUS_DIR.mkdir(exist_ok=True)
    RAW_DIR.mkdir(exist_ok=True)
    NORMALIZED_DIR.mkdir(exist_ok=True)
    CACHE_DIR.mkdir(exist_ok=True)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def piece_id(work_id: str, file_id: str) -> str:
    """Stable identifier mapping 1:1 to upstream IMSLP."""
    return f"imslp-{work_id}-{file_id}"


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json_atomic(path: Path, data: Any) -> None:
    """Write JSON to a tmp file then rename — never leave a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


def load_candidates() -> list[dict[str, Any]]:
    """Load every candidates.*.json file in CORPUS_DIR and concatenate items.

    Each item must carry its own `candidate_id` and `source` fields. Items
    with duplicate candidate_ids keep the first occurrence; callers can
    inspect the warnings list for collisions.
    """
    items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for path in sorted(CORPUS_DIR.glob(CANDIDATES_GLOB)):
        payload = read_json(path, default={"items": []})
        for item in payload.get("items", []):
            cid = item.get("candidate_id")
            if not cid:
                continue
            if cid in seen_ids:
                continue
            seen_ids.add(cid)
            items.append(item)
    return items


def load_manifest() -> dict[str, Any]:
    return read_json(
        MANIFEST_PATH,
        default={"version": 1, "pieces": []},
    )


def load_rejected() -> dict[str, Any]:
    return read_json(
        REJECTED_PATH,
        default={"version": 1, "rejections": []},
    )
