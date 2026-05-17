# 0001 — License: MIT

- **Status:** Accepted
- **Date:** 2026-05-17

## Context

Spec §6 requires a permissive license (MIT or Apache-2.0) and a recorded decision. The project is FOSS, free at the point of use (§4 — no monetization), and depends on the existing FOSS notation ecosystem.

Both MIT and Apache-2.0 are spec-compatible. Apache-2.0 adds an explicit patent grant and a NOTICE mechanism; MIT is shorter and is the default in the JS/Node ecosystem where most of the web stack will live.

Patent exposure for this MVP is low: we are not implementing OMR, pitch detection, audio fingerprinting, or any other technique with a meaningful patent footprint (those are explicitly non-goals, §4). The notation libraries we will depend on (e.g. OpenSheetMusicDisplay, alphaTab, Verovio, music21) ship under a mix of MIT/BSD/MPL/LGPL — all compatible with an MIT downstream.

## Decision

MIT.

## Consequences

- Maximum permissiveness for contributors and downstream users; no NOTICE obligations for redistributors.
- No explicit patent grant. If the project later moves into territory with patent risk (e.g. OMR — see §9 post-MVP), we will revisit and likely supersede this ADR with Apache-2.0 for the affected components.
- All new files should carry no per-file license header; the top-level `LICENSE` covers the repo.
