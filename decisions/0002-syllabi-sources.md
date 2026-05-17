# 0002 — Syllabi sources: RCM, Trinity, ABRSM

- **Status:** Accepted
- **Date:** 2026-05-17

## Context

Spec Milestone 0 requires three syllabi selected for grading labels. These provide the ground-truth training set for the Milestone 2 grading model: pieces with a known, expert-assigned grade.

The three major English-language conservatory syllabi covering classical guitar are:

- **RCM** — Royal Conservatory of Music (Canada). Classical Guitar Syllabus, 10-grade scale.
- **Trinity College London** — Classical Guitar Syllabus, Initial + Grades 1–8.
- **ABRSM** — Associated Board of the Royal Schools of Music. Classical Guitar Syllabus, Initial + Grades 1–8 (added in 2020).

All three publish piece lists publicly on their websites and via downloadable PDFs. The piece lists themselves are factual data (work + composer + grade) and are used here under fair-use / database-rights as reference labels, not republished as scores.

## Decision

Target three syllabi: RCM, Trinity, ABRSM. Store each as structured JSON under `/syllabi/` conforming to [`syllabi/schema.json`](../syllabi/schema.json).

Grade scale: each syllabus keeps its native grade labels. A separate mapping (added in Milestone 2 alongside the model) reconciles them onto a unified 1–10 scale.

## Consequences

- We do **not** redistribute the syllabus PDFs themselves; we extract only the piece-grade tuples needed for labelling.
- Population of the JSON files is part of Milestone 0 completion. Each file lists its source URL and the date the data was extracted, so we can re-verify against future syllabus revisions.
- If a syllabus changes editions during the project, we capture the new edition as a separate file (e.g. `rcm-2027.json`) rather than mutating the old one — training-set reproducibility (Milestone 2 validation check) depends on this.
- Advisor must approve the cross-syllabus grade mapping before the grading model is trained (spec §5, Milestone 2).
