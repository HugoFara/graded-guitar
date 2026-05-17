# 0006 — GitHub as primary discovery source for classical-guitar MusicXML

- **Status:** Accepted
- **Date:** 2026-05-18

## Context

Spec M1 assumes ≥500 IMSLP classical-guitar MusicXML files are reachable. M1.1 disproved that:

- IMSLP `Category:For guitar`, first 200 pages walked: **0** MusicXML candidates.
- IMSLP `Category:MusicXML files`: exists, but has no members.
- IMSLP full-text search for "MusicXML guitar": no hits.

OpenScore — floated as the obvious clean-license fallback — turned out to be Lieder + StringQuartets only. There is no OpenScore classical-guitar corpus.

Mutopia (~150 PD guitar pieces) is LilyPond-only. A separate investigation into LilyPond→MusicXML tooling is running in parallel; if it bears fruit, Mutopia gets its own ADR.

A probe of GitHub code search for `guitar extension:musicxml` returns 1380 total hits. Spot-check shows a mix of classical-guitar repertoire, tab transcriptions, ML training data, and library samples — i.e. real material, after filtering.

## Decision

**GitHub code search is the primary M1 discovery source.**

- Discovery is implemented as `scripts/m1_discover_github.py`, alongside the existing (and now empty-yielding) `scripts/m1_discover_imslp.py`.
- Each discovery script writes its own `corpus/candidates.{source}.json` file with the same item schema (source, candidate_id, file_url, license, …). `m1_fetch.py` and `m1_validate.py` read every `candidates.*.json` in `corpus/`.
- The unique key for a candidate, across all sources, is `candidate_id`. Convention: `gh:{owner}/{repo}@{ref}:{path}` for GitHub items, `imslp:{file_id}` for IMSLP items.
- Filtering at discovery is intentionally loose. The hard quality bar is applied at M1.3 validation (`MULTIPLE_PARTS`, `NON_GUITAR_INSTRUMENT`, etc.) — that's where pedagogical correctness gates entry to the corpus.

## Licensing

Each GitHub candidate carries the repo's SPDX license (`license_spdx` field, or `unknown` if the repo has no license metadata). For M1 we **store** licenses but do not yet filter on them. License-driven filtering for the public corpus is an M3 or M7 decision; recording the data now means we can apply any policy retroactively without re-running discovery.

A repo with no license effectively means "all rights reserved" in US/EU copyright. We capture that fact so a downstream policy can drop these from the public surface even if they passed validation.

## Idempotency / dedupe

- Within a source, `candidate_id` is unique. Re-running discovery overwrites the per-source file in place.
- Across sources, fetch keys on `candidate_id` to avoid double-downloads.
- Content-level deduplication (same MusicXML reposted in two different repos) is caught at M1.3 with reason code `DUPLICATE` (raw-bytes sha256 collision).

## Consequences

- The spec §7 M1 validation check "At least 500 distinct classical guitar pieces" becomes empirically driven rather than IMSLP-driven. We'll measure after first run and revise the spec note if needed.
- We accept that GitHub-discovered MusicXML has variable provenance and license clarity. The manifest preserves enough to retroactively filter.
- The pipeline is now multi-source; adding Mutopia, MuseScore.com, or others is a new `m1_discover_{name}.py` writing the same shape.
- Spec §6 "MusicXML canonical" is preserved — we ingest only files that are already MusicXML; converters from other formats (LilyPond, MuseScore) are out of scope until/unless their own ADR lands.
