# 0004 — Deliberate deferrals: repo visibility, advisor, syllabi data

- **Status:** Accepted
- **Date:** 2026-05-17

## Context

Spec Milestone 0 lists six validation checks. After the foundation commit, three of them are not yet satisfied:

1. **"Repository is public and reachable."** The repo is currently private on GitHub (`HugoFara/graded-guitar`).
2. **"Musical advisor has confirmed availability in writing."** Template at `docs/ADVISOR.md` exists; no advisor is named.
3. **"At least three syllabi have been sourced and their grade lists are stored in the repo as structured data."** Sources and schema are recorded; the `pieces` arrays in `syllabi/{rcm,trinity,abrsm}.json` are empty.

Spec §1: "If a milestone seems wrong, surface the concern and wait; do not silently re-scope." This ADR is that surfacing — we are choosing to advance work in a different order than the strict reading of M0 dictates, with reasons recorded here so it isn't drift.

## Decision

Defer all three items rather than block on them. Concretely:

- **Visibility — kept private until the project produces something useful.** Re-evaluate when M3 (web player) is up or when an external contributor is invited, whichever is first. Trigger to flip public: `gh repo edit HugoFara/graded-guitar --visibility public --accept-visibility-change-consequences`.
- **Musical advisor — deferred until a blocking point.** Spec §5 makes the advisor non-negotiable before M2 begins. Treat that as the hard gate: advisor must be engaged before any grading-model work, not before any work at all. M1 (data ingest) is technical-only and does not need pedagogical sign-off to start, even though spec M1 mentions a 20-piece spot-check at the end.
- **Syllabi piece-lists — deferred.** The schema, sources, and stubs are in place. The actual extraction (or extraction-and-advisor-review) happens once we have a real reason to need labelled data — which is at M2 grading-model work. Bundling it with the advisor engagement avoids a wasted pass.

## Consequences

- M0 validation checks are not all green; the project is operating with three known open items. They are explicitly tracked here, not invisible.
- **Hard gate before M2 begins:** the advisor must be engaged AND the three syllabi must be populated. Both are blockers for grading-model training, not nice-to-haves. Do not advance into M2 until both land.
- **Hard gate before public launch (M7) — and arguably before M3 closes:** the repo must be public. Adjust the trigger above as the project matures.
- This ADR is the audit trail for the deferrals. If a contributor later asks "why is M0 not actually done?", point them here.
- If any of these deferrals stops being deliberate and becomes accidental neglect, that is a §10 failure-mode warning sign — flag it.
