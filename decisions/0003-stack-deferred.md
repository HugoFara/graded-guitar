# 0003 — Stack choice deferred to Milestone 1

- **Status:** Accepted
- **Date:** 2026-05-17

## Context

Spec Milestone 0 lists "Stack choices recorded with rationale" as a deliverable. The temptation is to pick a frontend framework, backend language, database, ORM, and notation library now and freeze them.

Two problems with that:

1. The first real work (Milestone 1) is a **data ingest pipeline** over IMSLP MusicXML. That work is heavily Python-flavoured (music21, lxml) regardless of what the web app eventually looks like. Picking the web stack before we've handled a single MusicXML file is premature.
2. Spec §6 explicitly says "Build on the FOSS notation ecosystem. Reuse existing rendering and analysis libraries; do not rewrite what already exists." The choice of rendering library (OpenSheetMusicDisplay vs. alphaTab vs. Verovio) has cascading effects — alphaTab gives us notation + tab + playback + loop + tempo in one library and directly maps to Milestone 3's deliverables; OSMD and Verovio are notation-only and would require separate playback. That choice deserves its own ADR with the advisor's input on rendering correctness.

Spec §10 flags premature optimization as a failure mode. Locking the stack before we know the data shape is the same failure mode wearing different clothes.

## Decision

Defer the full stack choice. For Milestone 0 we commit only to:

- **Pipeline language: Python 3.11+** for ingest and ML work. Justified by `music21` (BSD-3), `lxml`, scikit-learn / xgboost being the canonical MusicXML and ML toolchain.
- **Repository layout: monorepo.** Pipeline and (eventual) web app live in the same git repo so the corpus, grading model, and player evolve together.
- **CI: GitHub Actions.** Default for public GitHub repos; zero infra to manage.

Everything else — web framework, notation library, database, auth — is decided at the start of the milestone that first needs it, with its own ADR.

## Consequences

- Milestone 0 ships without any installed dependencies; the repository is documentation and data only. The README's quickstart reflects this honestly.
- We will write 0004 (pipeline scaffolding) at the start of Milestone 1, 0005 (notation/playback library) at the start of Milestone 3, etc.
- If a contributor wants to propose a stack now anyway, the conversation happens in an ADR PR rather than in commit messages.
