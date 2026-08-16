# M6 Closed-beta triage runbook

Per spec §7 M6: *"Bug triage process; weekly review of incoming
reports."* This is that process. Short, opinionated, written for one
maintainer. Revise once the beta is actually running.

## Incoming channels

1. **GitHub issues** with the `m6-beta` label — created via
   `.github/ISSUE_TEMPLATE/beta-feedback.yml`. The structured fields
   make these the easiest to triage.
2. **Direct email** to `github@hugofara.net` — including
   "Share signals" attachments. File a stub issue for the email
   thread so triage notes have one home.
3. **In-app grade votes** — these don't need triage individually;
   they feed into the M2-successor training/audit pipeline. See
   "Vote signals" below.

## Weekly review (≈30 min)

Set aside one hour each week. Skip the meeting if there are no open
items; do not skip the *checking* step.

1. **Open the m6-beta label.** Sort by oldest. For each:
   - **Bug** → label by severity (`s:1` user-blocking, `s:2`
     annoying, `s:3` cosmetic). s:1 is fixed inside the week,
     s:2/s:3 land in the next batch.
   - **Grading** → leave the issue open as a tracking ticket and
     check whether the reporter's vote is already in the signal
     stream. If yes, no action — the data is captured. If they
     didn't vote, reply asking them to.
   - **Feed** → reproduce locally with the reporter's declared
     level. Either ticket a feed-heuristic ADR follow-up or close
     with explanation.
   - **UI / copy** → batch up; address every 2-3 weeks in a single
     polish PR.
   - **Performance** → measure before triaging. The TTI test in
     `web/tests/e2e/tti.spec.ts` is the authoritative number.
2. **Reply to every open issue at least once.** A "saw this,
   working on it" reply within seven days is the social contract;
   silence breaks the beta.
3. **Snapshot the metrics.** In `docs/outreach/beta-log.md`,
   append a one-line entry: `2026-MM-DD: N invited, N onboarded, N
   returned ≥1 day, N issues open / closed this week, N votes this
   week`. The first two columns let us track the spec §7 M6 close
   gates ("≥20 users onboarded, ≥10 returned on a separate day").

## Vote signals

Grade votes are not bugs; they're data. They live in users'
browsers until they hit "Share signals…" on the profile page.

When a "Share signals" attachment arrives:

1. Save the JSON under `~/graded-guitar-private/beta-signals/` (NOT
   in the repo — these files include declared levels and timestamps
   that we treat as private). Add the local path to a checklist
   somewhere obvious.
2. The aggregate stays private during the beta. We will only
   redistribute summary statistics in the eventual M2-successor
   write-up (e.g., "13 of 47 voted-on pieces had ≥3 disagreement
   votes, all in the +1/-1 grade range").
3. Once we have ≥20 attachments, run the (yet-to-be-written)
   `scripts/m6_vote_audit.py` to surface disagreement clusters
   against `dummy-v0`. That's the input the advisor will react to.

## Stop-the-line conditions

If any of these triggers during the beta, pause invitations:

- **Crash on landing** for any browser on the supported matrix
  (current Firefox, current Chromium-based, current Safari).
  Severity s:1, fix-first.
- **Privacy concern** raised by any user — "did you collect X
  without telling me?" Audit immediately, reply same-day.
- **Pedagogical complaint** of the form "this grader is so bad
  it's harmful" — pause invitations, document, and bring the case
  to the advisor pipeline ahead of normal cadence.

## Out of scope until M7

These are valid beta findings to *log* but **not** to act on
during M6:

- Server-backed accounts (still local-only per ADR 0012).
- Real OMR pipeline (deferred per ADR 0015).
- Editing / fingering / audio listening (spec §4 says no).

Closing-as-wontfix is fine; cite the spec or ADR.
