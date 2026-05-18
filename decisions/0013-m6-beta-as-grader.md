# 0013 — M6 framing: closed beta as the grading-signal path

- **Status:** Accepted
- **Date:** 2026-05-18

## Context

Spec §7 M2 ("Grading model v1") has a hard validation gate:

> Advisor's review of 50 sampled gradings: at least 40 judged "plausible."

Today every model grade in the corpus is from `dummy-v0`, a placeholder
trained on Delcamp grades plus synthetic advisor labels (ADR 0010).
No real musical advisor has signed off on anything. M3, M4, and M5
were built on top of that placeholder by design — the spec lets us
keep moving as long as the disclaimer is honest and the project will
not launch (M7) without a real grader.

The unresolved question, surfaced by an external review on
2026-05-18, is what M6 ("Closed beta") is *for*:

- **(a) Wait-for-advisor.** M6 is a stalling pattern. We don't run
  the beta until a single advisor has validated `dummy-v0` or its
  successor against §7 M2's 40-of-50 criterion. The risk: an advisor
  may never materialize on a timeline that matches the project's
  energy, and the closed beta becomes the bottleneck.
- **(b) Beta-as-grader.** M6 is the *path* to a real grader. The
  beta's primary deliverable is not "do real classical guitarists
  enjoy this?" — it's `(user_self_declared_level, piece, status)`
  triples that, in aggregate, *are* a grading signal. The advisor
  remains required for §7 M2 sign-off, but in parallel we collect
  human disagreement data at corpus scale instead of advisor scale.

(a) makes the advisor a critical single point of failure. (b) builds
a parallel path that yields a real signal even if the advisor
timeline slips, and the disclaimer that is currently a liability
("grades are placeholder") becomes the explicit beta pitch ("help us
fix the grades").

## Decision

1. **M6 is framed as a grading-signal collector.** The closed-beta
   prompt to users is, in plain language: *"We're building the
   grader together. Tell us when a piece is mis-graded for your
   level."* This does not replace the advisor — §7 M2 still gates on
   advisor sign-off — but it generates an independent signal stream
   in parallel.

2. **Status records carry the grade context at write time.** Every
   `setStatus` write snapshots `grade_at_record` and
   `grade_source_at_record` onto the record. Without this, a year's
   worth of `too_hard` feedback recorded against `dummy-v0` becomes
   silent noise (or active misinformation) the moment the grader
   changes. With it, we can:

   - Replay the signal against the new grader and flag the
     disagreements that would have been masked.
   - Discard signals recorded against grader versions we've since
     retired.
   - Compute corpus-wide disagreement reports without joining
     against historical manifest snapshots.

   Implemented in `web/src/lib/storage/status.ts` (record version
   bumped to v2; v1 imports still accepted). UI plumbing through
   `StatusSelector` reads the resolved grade off the piece detail
   page at the moment of judgment.

3. **An explicit "this grade feels wrong" affordance is on the M6
   to-do list.** Today the user's only signal channel is the five
   spec statuses. For M6 we add a lightweight, optional control —
   "Grade feels wrong: easier / harder / right" — that is *not* a
   status; it's a per-piece grade-disagreement vote. Stored
   alongside the status records, exported in the same backup.
   The spec's five statuses remain frozen.

4. **Cold-email outreach is non-blocking and starts now.** The
   advisor pipeline runs in parallel with everything else: 20
   cold emails per outreach pass (Delcamp forum, RCM/Trinity
   credentialed teachers on LinkedIn, conservatory faculty
   listings). Replies come in over days or weeks. We do not stall
   on advisor materialization; we stall product gates on advisor
   approval, which is different.

5. **§7 M7 ("Public launch") still requires advisor sign-off.**
   Beta-as-grader gives us a corpus-scale signal, not a pedagogical
   blessing. The two are complementary: the beta data tells us
   where the grader is wrong; the advisor tells us whether the
   grader is *pedagogically reasonable* once we've fixed it. We do
   not launch publicly on beta votes alone.

## Consequences

**Commits us to:**

- Storage shape: status records gain optional `grade_at_record` /
  `grade_source_at_record` fields. The wire format (export/import
  JSON) bumps to v2. v1 imports continue to work.
- A grade-disagreement affordance in the M6 UI (small scope: three
  buttons + an aggregate dashboard).
- A monthly cold-email outreach pass until a real advisor is
  engaged, tracked in `docs/ADVISOR.md`.
- A public framing — in the privacy note, on the landing footer, and
  in the M6 invite copy — that says explicitly: *grades are
  placeholder; your feedback is shaping them.*

**Costs:**

- Beta-data triage work later: when the grader changes, we have to
  decide for each historical record whether to replay, retain, or
  drop. Without the snapshot fields this is a guess; with them it
  is a query.
- The grade-disagreement affordance is a UI surface the spec doesn't
  require. We add it because the beta loses most of its value
  without it.
- Honesty surface area grows: more places where we have to
  truthfully say "this is a placeholder." We treat that as a
  feature, not a cost.

**Forecloses:**

- The wait-for-advisor framing. If an advisor lands tomorrow, great
  — we still run beta-as-grader. The two paths converge in §7 M7.

**Follow-ups:**

- Pre-M6 spike (2–4 hours): self-audit `dummy-v0` against ~30
  well-known pieces with broad community consensus on difficulty
  (e.g., Lágrima ≈ 4, Asturias ≈ 7, Carcassi Op. 60 No. 7 ≈ 4,
  Villa-Lobos Étude No. 1 ≈ 6). Output is a Markdown report.
  If `dummy-v0` is wildly off on easy consensus cases, the model
  has bigger problems than "needs an advisor."
- Pre-M6: add the grade-disagreement vote affordance, its storage,
  and an aggregate report view (probably read-only on `/library`).
- M6 invite copy explicitly frames the beta as grading-signal
  collection, not as feature feedback.
- Corpus diversification (see external review 2026-05-18) is a
  separate concern but interacts with this one: a 53%-Guitar-Loot
  corpus means beta votes are biased toward Renaissance/Baroque
  Delcamp grades. Get Guitar Loot under 40% before M6 opens.
