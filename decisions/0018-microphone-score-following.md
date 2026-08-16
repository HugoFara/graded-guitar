# 0018 — Microphone score following as a grading instrument

- **Status:** Accepted
- **Date:** 2026-08-16

## Context

M2 has been the blocking milestone since 2026-05-18. Every grade in
`corpus/manifest.json` is `dummy-v0` (ADR 0010). Spec §5 makes a
musical advisor a hard dependency, no advisor has been engaged
(ADR 0004), and ADR 0013 built the parallel path — beta users as a
grading signal — precisely because the advisor may never materialize
on a timeline that matches the project's energy.

`corpus/m2_grading_worksheet.md` is the current fallback: the product
owner grading 50 pieces by hand. It has been open and unfilled since
2026-05-27. The reason is stated plainly by its author: his playing
level does not cover the range the worksheet asks him to grade. Rows
23–26, 33, 47–50 ask for a judgement on grade-7 material from someone
who cannot play grade-7 material. A number entered there would be a
guess wearing the costume of a label.

The proposal is to stop asking the human for a number and instead
measure the thing the number is a proxy for: microphone capture plus
score following, producing a per-bar record of where a player
hesitates, slows, stops, or restarts.

Spec §4 listed *"Audio listening / pitch detection / 'did the user
played it correctly' feedback"* as an explicit MVP non-goal, and §10
lists any pull toward §4 as a stop-and-escalate failure mode. This
ADR is that escalation, resolved.

## The reframe

The §4 ban was written against a **practice-feedback feature** — the
Yousician/Rocksmith surface where the app tells the user how well they
played. That is still a non-goal and remains one; §4 now says so
explicitly.

What M8 adopts is a **measurement instrument**. The output is a
difficulty estimate of the *piece*, not an assessment of the *player*.
This is the same signal ADR 0013 already committed to collecting from
beta users — `(user_level, piece, status)` triples — at roughly three
orders of magnitude more resolution. A `too_hard` click is one bit per
piece. A stumble map is a per-bar tempo curve with hesitation and
restart annotations.

Framed that way, M8 is not new scope. It is ADR 0013's instrument,
built properly.

## The confound, stated up front

A stumble map measures the interaction of piece and player. With a
single player, piece difficulty and player ability are not separately
identifiable: "Hugo fell apart in bar 3" is equally well explained by
a hard piece or a weak player, and the data cannot distinguish them.
Above the player's ceiling the signal saturates — every grade 7, 8 and
9 piece produces the same reading ("failed early"), which is one bit,
not a grade.

This is a real limitation, not a detail to be discovered later. Three
mitigations are therefore load-bearing and are written into the
milestone as validation checks:

1. **Anchor calibration.** The player records the seven anchor pieces
   already listed in `corpus/m2_grading_worksheet.md` (Lágrima ≈ 4,
   Bourrée BWV 996 ≈ 5, Capricho Árabe ≈ 7, …), whose community grades
   are settled. Those observations pin a personal difficulty curve to
   the public 1–10 scale. Without anchors we get an ordering; with
   them we get grades.

2. **Censoring above the ceiling.** A piece the player cannot get
   through is recorded as a *lower bound* (`>= ceiling`), never as a
   point estimate. Bounds are legitimate data — they are how survival
   analysis handles exactly this — but silently treating one as a
   grade would inject systematic error at the top of the scale, which
   is where the corpus is already weakest.

3. **Per-`(player, piece)` from day one.** The data model never
   aggregates to a bare per-piece number. When M6 beta players at
   differing levels arrive, their takes are the multi-rater data that
   breaks the confound properly. A schema that assumed one player
   would have to be migrated at exactly the moment the data got good.

## Technical decisions

### Chroma features, not pitch detection

Classical guitar is polyphonic — three and four independent voices on
one staff is ordinary repertoire, not an edge case. Monophonic pitch
trackers (YIN, pYIN, CREPE) return one f0 per frame and fail on any
chord. Polyphonic transcription is an open research problem and a bad
dependency for a static-Pages project.

Chroma — 12-bin pitch-class energy — sidesteps both. It is the
standard feature for score alignment, it handles polyphony natively
because it never has to decide how many notes are sounding, and it
degrades gracefully under the room noise, string buzz and nail attack
that a real guitar recording carries. We pay for that with octave
blindness, which alignment does not need.

The reference side applies the same harmonic model as the observed
side (partials at 1/h weight over six harmonics, so a plucked note
deposits energy at its pitch class plus the fifth and major third
above). Matching a harmonically-smeared observation against a
one-hot symbolic reference is the single most common way this class
of aligner is built wrong.

### One model, two decodings

Reference position is modelled as a hidden state with:

- observation likelihood from chroma cosine distance,
- a transition prior favouring forward motion at the current tempo
  estimate, allowing 0..3 frame advances for hesitation and rushing,
- a small uniform jump probability, which is what makes restarts
  representable at all.

That last point is the reason we are not using plain DTW. DTW paths
are monotonic; "the player went back to bar 5 and started again" is
not a monotonic path and no amount of band tuning expresses it. The
uniform jump term gets restarts, repeated practice loops, and skipped
passages for free.

The same model is decoded two ways:

- **Online, forward filtering** — drives the live cursor.
- **Offline, Viterbi** — drives every recorded measurement.

### The live cursor is a display, not the measurement

This is the decision most likely to be quietly reversed later, so:
a follower that loses its place produces a trace that is
indistinguishable from a player who stumbled. If measurements came
from the live path, the grading signal would be contaminated by
tracker error in exactly the region where the data matters most —
hard passages, where both the player and the tracker struggle.

All recorded measurements come from the offline Viterbi pass over the
stored chroma frames, which sees the whole take, runs backward as
well as forward, and has no latency budget. The live cursor exists
because playing to a moving cursor is a better experience than playing
to a stopwatch, and for no other reason.

### Audio does not leave the browser

Consistent with ADR 0012 (local-only accounts) and ADR 0016
(signal egress via mailto). We store derived chroma frames, not audio.
Chroma is 12 floats per frame at ~20 Hz — about 1 KB/s, and it is not
reconstructible into speech or recognisable audio. Raw PCM is never
persisted and never transmitted.

## Decision

1. **Withdraw §4 non-goal #2 and add Milestone 8.** The withdrawal is
   bounded: assessment of playing quality, scoring of the user, and
   gamified accuracy remain non-goals and are now written into §4 as
   such.

2. **M8 is exempt from the milestone ordering rule.** It is numbered
   last so M0–M7 numbering stays stable for the 17 ADRs that reference
   it, but it runs in parallel starting now. Its output feeds M2.

3. **M8 is not an MVP gate.** §8 updated: the MVP can ship without a
   microphone; it cannot ship without credible grades.

4. **The stop condition is the synthetic ±1 bar target.** If the
   aligner cannot localize an injected hesitation, tempo change and
   restart to within one bar on a perturbed synthetic performance with
   known ground truth, it is measuring itself. Its output does not
   enter M2 labels until it passes.

5. **The advisor requirement is unchanged.** M8 produces a
   measurement, not a pedagogical blessing. Spec §7 M2 still gates on
   advisor sign-off and §7 M7 still gates public launch on it. This is
   the same complementarity ADR 0013 established.

## Consequences

**Commits us to:**

- A signal-processing surface in a project that had none. New code
  under `web/src/lib/listen/`, tested without a microphone via
  synthetic chroma fixtures.
- A take-history store, versioned and exported alongside statuses and
  votes, per `(profile, piece)`.
- A privacy-note update covering microphone access and what is
  derived, stored, and never stored.
- Keeping the anchor set current. If `corpus/m2_grading_worksheet.md`
  anchors change, the calibration changes with them.

**Costs:**

- The largest single scope addition since M3. Honest accounting: this
  is a feature the spec explicitly excluded, adopted because the
  alternative — waiting for an advisor — has not worked for three
  months.
- Browser microphone access is a permission prompt on first use, which
  is friction on a page that currently asks for nothing.
- Alignment quality is an empirical question. The stop condition
  exists because there is a real chance the answer is "not good
  enough," and we would rather find that out against synthetic ground
  truth than after feeding bad labels into the grader.

**Forecloses:**

- Nothing structural. If M8 fails its stop condition, the code is
  deletable and M2 is exactly where it is today.

**Follow-ups:**

1. Chroma, reference-building, alignment and stumble-metric core, with
   unit tests against synthetic perturbations. This is where the stop
   condition is evaluated.
2. Capture layer (`getUserMedia` + analyser → chroma frames) and take
   storage.
3. Practice UI: mic opt-in, live cursor, post-take stumble map.
4. Anchor calibration pass — the product owner records the seven
   anchor pieces; check whether the recovered curve reproduces their
   known grades within ±1.
5. Only then: feed derived estimates into the M2 label set, and revisit
   `corpus/m2_grading_worksheet.md` with measurement rather than guess.
