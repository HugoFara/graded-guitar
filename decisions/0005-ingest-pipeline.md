# 0005 — M1 ingest pipeline architecture

- **Status:** Accepted
- **Date:** 2026-05-17

## Context

Milestone 1 needs a reproducible pipeline that turns IMSLP classical guitar scores into a clean, normalized MusicXML corpus with provenance and an ingest report (spec §7, M1). Several choices need locking before code lands so M1.1–M1.4 land coherently.

## Decision

### Pipeline shape

Three scripts, each runnable independently, communicating via files in `corpus/`:

```
scripts/m1_discover.py  →  corpus/candidates.json
scripts/m1_fetch.py     →  corpus/raw/{sha256}.{musicxml,mxl}
scripts/m1_validate.py  →  corpus/manifest.json + corpus/rejected.json + corpus/report.md
```

A small shared module `scripts/m1_common.py` holds paths, atomic-write helpers, and the rate-limited HTTP session.

### What goes in git

- **Committed:** `corpus/candidates.json`, `corpus/manifest.json`, `corpus/rejected.json`, `corpus/report.md`, `corpus/README.md`.
- **Gitignored:** `corpus/raw/`, `corpus/normalized/`, `corpus/cache/`.

The committed JSON + the pipeline are enough to reconstruct the corpus from IMSLP at any time. Bulk MusicXML files don't belong in the repo: they're large, redistribution would entangle us in per-file IMSLP licenses, and keeping them out keeps the repo cloneable in seconds.

### Stable identifiers

- **Piece ID:** `imslp-{work_id}-{file_id}`. Maps 1:1 to upstream so a re-discovered file is recognizable.
- **Raw cache key:** sha256 of the file bytes. Different IMSLP file IDs that point to the same content collapse to one cache entry; mutation upstream produces a new cache entry.

### Idempotency contract

`manifest.json` is the source of truth for what's been accepted. Each script:

- Reads the manifest first.
- Skips work whose IMSLP file ID is already present AND whose upstream sha256 matches.
- Re-processes if the upstream sha256 changed (records a `superseded` entry in the rejected log pointing to the new manifest entry).

A second consecutive run with no upstream changes is a no-op: it produces zero diffs in committed files.

### Dependencies

- **Python 3.11+** (already in ADR 0003).
- **`requests`** — retries, timeouts, sessions, headers. Justified over `urllib` by retry/backoff handling and a cleaner cookie jar for IMSLP's disclaimer flow.
- **`lxml`** — parsing and (optionally) XSD validation of MusicXML. Faster and more permissive than stdlib `xml.etree`; the de-facto standard.

Both pinned in `requirements.txt`. No other M1 dependencies.

### Reject reason codes (enum)

Stored in `rejected.json` as a stable string identifier so the rejection list is reviewable and filterable:

| Code                       | Meaning                                                          |
| -------------------------- | ---------------------------------------------------------------- |
| `XML_MALFORMED`            | File does not parse as XML.                                      |
| `XML_NOT_MUSICXML`         | Root element isn't `score-partwise` or `score-timewise`.         |
| `NO_PARTS`                 | MusicXML has no `<part>` element.                                |
| `MULTIPLE_PARTS`           | More than one part (ensemble / accompanied — out of scope).      |
| `NON_GUITAR_INSTRUMENT`    | Part's instrument metadata doesn't match a guitar.               |
| `MISSING_TITLE`            | `<work-title>` empty or absent.                                  |
| `MISSING_COMPOSER`         | No composer creator entry.                                       |
| `PLACEHOLDER_METADATA`     | Title/composer is a known empty-template placeholder (Music21, "Untitled score", "Partition sans titre", …). |
| `PATH_NOISE`               | Candidate path matches a known noise pattern (ear-training, OMR datasets, ML training dumps). |
| `DUPLICATE`                | Same sha256 already accepted under a different candidate id.     |
| `FETCH_FAILED`             | HTTP error or empty body on download.                            |
| `MXL_EXTRACTION_FAILED`    | `.mxl` zip couldn't be opened or didn't contain a score XML.     |
| `SUPERSEDED`               | Upstream changed; replaced by a newer entry. (Soft-rejected.)    |

Adding a new code is a follow-up ADR or PR note; removing one is forever (it appears in historical rejection logs).

### Rate limiting & politeness

`m1_common.py` exposes a single shared `requests.Session` with:

- User-Agent string identifying this project and a contact URL.
- Min interval 1.0 s between IMSLP requests (configurable, never below 0.5 s).
- Retry on 429/5xx with exponential backoff, max 3 retries.
- Respect `Retry-After` if present.

### What this ADR does NOT decide

- Where the corpus lives in production (post-M1). For now, local-only is fine.
- Cross-syllabus labelling. That waits for advisor + populated syllabi (ADR 0004 gates).
- Storage backend for the eventual public corpus (S3? Git LFS? Separate releases repo?). Decide at M3 when the web player needs it.

## Consequences

- The repo stays light: every file in `corpus/` that's committed is JSON or markdown.
- Anyone can clone the repo, run `pip install -r requirements.txt`, then `python scripts/m1_discover.py && python scripts/m1_fetch.py && python scripts/m1_validate.py` and get a byte-for-byte equivalent corpus (modulo upstream IMSLP changes, which the manifest will pick up as supersessions).
- The rejection list is a structured, reviewable artifact. Advisor or maintainer can grep `rejected.json` for `NON_GUITAR_INSTRUMENT` and audit our classification heuristic.
- We commit to two third-party deps (`requests`, `lxml`). Adding more in M1 requires updating this ADR.
- The pipeline can be run in parts. If discovery is fine and fetch is partially done, validate operates on whatever raw files exist — useful for iterating on the validation rules without re-downloading.
