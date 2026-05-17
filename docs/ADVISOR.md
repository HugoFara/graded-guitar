# Musical Advisor Agreement

Per [`project-spec.md`](../project-spec.md) §5, this project cannot advance past Milestone 1 without a classical guitar teacher or conservatory-trained player acting as **musical advisor**. This document is the written record of that engagement.

## Status

- **Advisor:** _to be filled in_
- **Affiliation:** _to be filled in_
- **Engagement confirmed on:** _YYYY-MM-DD_
- **Compensation:** _paid / unpaid / honorarium / credit-only — record what was agreed_

> Spec §5 validation check: "Musical advisor has confirmed availability in writing." Once this section is filled in and countersigned (commit by the advisor, or a co-signed PR), Milestone 0 can close on this item.

## Scope of the role

The advisor's responsibilities, copied verbatim from spec §5:

- Validate the grading rubric before training begins.
- Spot-check the difficulty model's output on real pieces.
- Approve the level-placement onboarding flow.
- Sign off before public beta.

In addition, drawn from the milestone validation checks:

- **Milestone 1.** Spot-check 20 random pieces and confirm metadata is correct.
- **Milestone 2.** Approve the feature set before training. Review 50 sampled gradings; at least 40 must be "plausible" (within one grade of the advisor's own assessment) before we advance. Stop condition: <80% plausible → revisit features.
- **Milestone 3.** Confirm rendered notation looks correct on 10 sample pieces; same for tab view.
- **Milestone 4.** Review feeds at three different declared levels; confirm each looks pedagogically reasonable. If a placement quiz is used, advisor designs the questions.
- **Milestone 6.** Sign off before public launch. If sign-off is declined, the launch is deferred (spec stop condition).

## Time commitment

A rough, honest estimate so the advisor can decide whether they can take this on:

| Milestone | Approx. advisor time                                                                |
| --------- | ----------------------------------------------------------------------------------- |
| M1        | 1–2 hours (metadata spot-check on 20 pieces)                                        |
| M2        | 4–8 hours (feature set review + 50-piece grading review, possibly two rounds)       |
| M3        | 1–2 hours (notation + tab spot-check on 10 pieces)                                  |
| M4        | 2–3 hours (feed review at 3 levels; quiz design if applicable)                      |
| M6        | 2–4 hours (beta feedback review + launch sign-off)                                  |

Total across the MVP: roughly 10–20 hours, spread over the project's lifetime.

## What the advisor can expect from the team

- Clear, batched asks. No "can you look at this real quick" pings — reviews are scheduled and bundled.
- The pieces and gradings to review will be delivered as a short list (title, composer, IMSLP link, current grade) plus the player URL once Milestone 3 is up.
- Final say on pedagogically loaded calls (grading correctness, notation correctness, level placement). Spec §1: "Pedagogical correctness outranks technical elegance."
- Public credit in the README and on the site (unless the advisor prefers anonymity).

## Sign-off

> Once the advisor has read this document and agreed, both parties commit their names below in a PR. That PR is the "written confirmation" required by Milestone 0.

- Advisor: _________________________ Date: __________
- Project owner: ___________________ Date: __________
