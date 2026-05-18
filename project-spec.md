# graded-guitar — Project Specification

> **Working name:** graded-guitar (simple-and-boring; may rename when the project produces something useful)
> **Audience for this document:** the coding agent scaffolding the project, and the human team using it as the master checklist.
> **Status:** authoritative reference. Update this file when scope changes; do not silently diverge from it.

---

## 1. How to use this document

You are a coding agent assisting a small team in building an open-source web platform for classical guitar repertoire discovery. This file is the single source of truth for what is being built, in what order, and how to know each step is done.

Rules of engagement:

- **Follow the milestones in order.** Do not start a milestone until the previous one's validation checks pass.
- **Implementation choices are yours** — stack, libraries, schemas, file structure — unless this document explicitly constrains them. When you make a meaningful choice, record it in a `/decisions` log inside the repo with a one-paragraph rationale.
- **Features, intent, and validation are not yours to change.** If a milestone seems wrong, surface the concern and wait; do not silently re-scope.
- **When in doubt, choose the smaller scope.** Scope creep is the single largest risk to this project.
- **Pedagogical correctness outranks technical elegance.** If the musical advisor (see §5) says something is wrong, it is wrong — even if the model, the metric, or the code disagrees.

---

## 2. Project intent

A free, open-source web platform where classical guitarists discover sheet music matched to their playing level. Every score in the library is automatically graded by difficulty, so a user declares (or is placed at) a level and receives a feed of pieces they can actually play — not an undifferentiated wall of results.

The library is seeded from IMSLP's public-domain classical guitar repertoire. Scores are rendered in the browser as proper notation with optional tab, with playback, looping, and tempo control. Users track what they're playing; that signal feeds future recommendations.

This is not a notation editor, not a tab repository, not a tutorial site. It is a **discovery and practice surface** built on top of the existing FOSS notation ecosystem.

---

## 3. Audience and problem

**Primary user:** self-taught or returning-to-instrument classical guitarists, advanced beginner through intermediate (roughly Grades 2–7 on standard syllabi). They know how to read notation, own no teacher, and currently cannot find appropriate next pieces.

**The problem in one sentence:** existing sheet music sites are organized around popularity and title search, not player level, so the user wastes hours sorting through pieces that are either too easy to be worth their time or technically out of reach.

**The user's job-to-be-done:** "Show me five pieces I could realistically learn next, and let me try them right now in the browser."

---

## 4. Non-goals (explicitly out of scope for MVP)

The agent must not build, and must not be asked to build, any of the following before the MVP is shipped and validated:

- Optical Music Recognition (PDF/photo → notation). Long-term goal; not in MVP.
- Audio listening / pitch detection / "did the user play it correctly" feedback.
- Fingering suggestion or automated annotation.
- Genres other than classical guitar (no fingerstyle pop, no VGM, no other instruments).
- Mobile native apps (iOS/Android). Web only, responsive layout acceptable.
- Social features (comments, follows, sharing, forums).
- User-uploaded scores. Library is curated from IMSLP at MVP.
- Monetization, subscriptions, premium tiers. The project is FOSS and free at the point of use.
- Notation editing. Read-only display.
- Offline mode / PWA installation.

Any feature request matching the above is deferred to post-MVP roadmap (§9). Log the request; do not implement.

---

## 5. Roles and critical dependencies

**Non-negotiable, must be in place before Milestone 2 begins:** a classical guitar teacher or conservatory-trained player acting as **musical advisor**. This role is not optional and not substitutable by online research. The advisor's responsibilities:

- Validate the grading rubric before training begins.
- Spot-check the difficulty model's output on real pieces.
- Approve the level-placement onboarding flow.
- Sign off before public beta.

If the advisor is unavailable, the project stalls until one is found. Do not proceed without this role filled.

Other roles: ML engineer (grading model), generalist developer (everything else), product owner (the human asking the question).

---

## 6. Working principles

These principles override individual decisions when they conflict.

- **MusicXML is the canonical format.** All scores are stored, processed, and rendered from MusicXML. Do not invent a file format.
- **Build on the FOSS notation ecosystem.** Reuse existing rendering and analysis libraries; do not rewrite what already exists.
- **Classical guitar only at launch.** No exceptions. Expansion is a v2 conversation.
- **Ship narrow, then widen.** A working pipeline for 200 pieces beats a half-built pipeline for 2,000.
- **Pedagogical validity is a release blocker.** A milestone is not "done" until the advisor has reviewed the user-facing output.
- **Open from day one.** Public repo, permissive license (MIT or Apache-2.0 — agent chooses and records the decision), contribution guidelines drafted before public launch.

---

## 7. Milestones

Each milestone has a goal, deliverables, and validation checks. Do not advance to the next milestone until every check in the current one passes.

### Milestone 0 — Foundation

**Goal:** the project can be worked on. Decisions about scope, licensing, and advisor are settled before any code that matters is written.

**Deliverables:**
- Public repository with README, LICENSE, CONTRIBUTING, and this spec checked in.
- Decision log structure (`/decisions/`) in place.
- Stack choices recorded with rationale.
- Musical advisor identified and engaged (written agreement on scope and time commitment, not necessarily paid — but real).
- Three target syllabi selected for grading labels (recommended: RCM, Trinity, ABRSM classical guitar syllabi; agent verifies availability and licensing of grade lists).
- CI pipeline running tests on every PR.

**Validation checks:**
- [ ] Repository is public and reachable.
- [ ] Anyone can clone, install, and run the (empty) project in under 10 minutes following the README.
- [ ] License file is present and chosen license is recorded in the decision log.
- [ ] Musical advisor has confirmed availability in writing.
- [ ] At least three syllabi have been sourced and their grade lists are stored in the repo as structured data.
- [ ] CI passes on a trivial commit.

### Milestone 1 — Data ingest pipeline

**Goal:** a reproducible pipeline that turns publicly available classical-guitar scores into clean, normalized MusicXML the platform can use.

**Note on sources.** The original spec assumed IMSLP would provide ≥500 classical-guitar MusicXML files. The M1.1 discovery run (2026-05-17) walked IMSLP's `Category:For guitar` and found **zero** MusicXML files — IMSLP is overwhelmingly PDF scans. Three sources ended up wired: GitHub code-search + repo walks (ADR [0006](./decisions/0006-github-as-source.md)), Mutopia via a patched `python-ly` LilyPond→MusicXML converter (ADR [0007](./decisions/0007-mutopia-source.md)), and Guitar Loot (ADR [0008](./decisions/0008-guitarloot-source.md)) — a curated single-arranger Renaissance/Baroque collection whose ~530 .mxl files carry pre-assigned Delcamp 1-10 grades on 87% of entries. Pipeline architecture is in ADR [0005](./decisions/0005-ingest-pipeline.md).

**Deliverables:**
- Pipeline that identifies classical-guitar scores in MusicXML format from public sources (initially GitHub; pluggable per source).
- Normalization step: standardize metadata (composer, title, opus, key), validate the XML, reject malformed files.
- Storage layout for the normalized corpus, with provenance preserved (source repo / page link, sha256 of raw bytes).
- Ingest report: how many pieces processed, how many accepted, how many rejected and why.

**Validation checks:**
- [x] At least 40 distinct classical guitar pieces ingested and normalized, with a documented plan to grow (see *Grow plan* below). Original target was 500; lowered to reflect empirical scarcity of free-licensed classical-guitar MusicXML — spec §6 "ship narrow then widen" applies. **Current: 791 accepted pieces** as of 2026-05-18 (`corpus/report.md`).
- [ ] Each piece has accurate composer, title, and key metadata.
- [x] Every ingested piece can be opened by a standard MusicXML reader without errors. (Enforced by `m1_validate.py`: well-formed XML, `score-partwise` root, ≥1 part.)
- [x] Pipeline is idempotent: running it twice produces the same corpus. (Content-addressed by sha256 in `corpus/raw/`; `corpus/cache/fetch_log.json` skips re-fetches.)
- [x] Rejected pieces have a recorded reason; the rejection list is reviewable. (`corpus/rejected.json` with structured reason codes — see ADR 0005.)
- [x] Each piece's license is captured in the manifest (filtering for redistribution is an M3/M7 concern).
- [ ] Advisor spot-checks 20 random pieces and confirms metadata is correct.

**Grow plan.** Reaching 791 was achieved by adding sources opportunistically; the plan to keep growing is layered by how much work each requires.

- *No-effort* — re-running the existing pipeline periodically. Mutopia and Guitar Loot both add pieces over time; a quarterly re-run picks up new uploads on each.
- *Low-effort additions (one ADR + one discover script each)* — other curator-style sites with predictable layouts, especially those catalogued at [musicxml.com/music-in-musicxml](https://www.musicxml.com/music-in-musicxml/) (Folkoteca Galega, Hausmusik, and similar small per-composer archives). The Delcamp Forum sheet-music section is community-uploaded and carries grading discussion — would need careful license handling but is the obvious second graded source after Guitar Loot.
- *Medium-effort* — IMSLP API key crawl. IMSLP has individual per-work pages with occasional `.musicxml`/`.mxl` files even though `Category:MusicXML files` is empty for guitar; a per-work scrape would catch those. Wikifonia (defunct but mirrored on Internet Archive snapshots) would reuse `m1_lilypond.py` if its `.ly` files are still reachable.
- *Community-driven (post-M3 launch)* — a submission form on the platform itself, license outreach to publishers willing to release public-domain editions, and explicit asks to conservatory programs that already typeset guitar repertoire.

The pipeline is source-pluggable (`corpus/candidates.*.json` glob; per-source discover scripts; one `fetch.py` and one `validate.py`), so each new source is contained.

### Milestone 2 — Grading model (v1)

**Goal:** every piece in the corpus has a difficulty grade (1–10 or syllabus-equivalent) that a human classical guitarist would find plausible.

**Deliverables:**
- Defined feature set extracted from MusicXML (the agent proposes; advisor approves before training). Plausible candidates: position-shift count, max stretch, polyphonic voice density, ornament density, key signature, tempo, rhythmic complexity, barré indicators — but advisor's input on this list is required.
- Training set built from syllabus pieces with known grades.
- Baseline grading model (any sensible approach — handcrafted features + gradient boosting is fine for v1).
- Held-out evaluation: accuracy, confusion matrix, per-grade error rate.
- Advisor review of 50 randomly graded pieces from the full corpus.

**Validation checks:**
- [ ] Feature set has been written down and explicitly approved by the advisor.
- [ ] Model is trained on syllabus data and evaluated on a holdout set.
- [ ] Holdout accuracy within ±1 grade for at least 70% of pieces.
- [ ] Advisor's review of 50 sampled gradings: at least 40 judged "plausible" (i.e., within one grade of the advisor's own assessment).
- [ ] Every piece in the corpus has a grade attached.
- [ ] Gradings are reproducible from the stored model artifact.

**Stop condition:** if advisor approval rate is below 80% on the sample review, do not advance. Revisit features.

### Milestone 3 — Web player

**Goal:** a user can open any piece in the corpus in the browser, see proper notation, hear it, and practice it.

**Deliverables:**
- Notation rendering of any piece from the corpus.
- Optional tab view toggled alongside notation.
- Playback with play/pause/seek.
- A/B loop selection over a measure range.
- Tempo slider (50%–150% of original, no pitch shift required at this stage).
- Responsive layout that works on a laptop and on a tablet in landscape.

**Validation checks:**
- [ ] Any 10 randomly chosen pieces render without visible glitches.
- [ ] Playback matches notation (no obvious desync).
- [ ] Loop and tempo controls function as advertised.
- [ ] Page loads to interactive in under 3 seconds on a standard broadband connection.
- [ ] Advisor confirms the rendered notation looks correct (margins, stems, accidentals) on 10 sample pieces.
- [ ] Tab view, when toggled, is correct for at least 10 sample pieces.

### Milestone 4 — Discovery and recommendation feed

**Goal:** a user lands on the site, indicates their level, and sees pieces appropriate for them.

**Deliverables:**
- Onboarding flow: either direct level selection (with examples per level) or a short placement quiz. Advisor designs the questions if a quiz is used.
- Feed view: shows pieces at the user's level and one grade above, with composer, title, estimated length, and a preview thumbnail.
- Search and filter (by composer, period, length, grade).
- "Try this piece" action that opens the player.

**Validation checks:**
- [ ] A new user can go from landing page to playing a level-appropriate piece in under 90 seconds.
- [ ] Feed shows at least 20 pieces for the central grade range (3–6).
- [ ] Filters work and combine correctly.
- [ ] Advisor reviews feeds at three different declared levels and confirms each looks pedagogically reasonable.
- [ ] No "wall of Asturias" effect: feed shows variety across composers and periods.

### Milestone 5 — Accounts and tracking

**Goal:** users have an identity, a library, and their behavior feeds back into the recommendation surface.

**Deliverables:**
- Account creation (email + password minimum; OAuth optional).
- Per-piece status: not seen, playing, completed, too hard, not for me.
- Personal library view filtered by status.
- Recommendation feed adjusts based on status signals (e.g., "too hard" pushes future recommendations toward the lower end of the user's level).
- Privacy: clear statement of what is stored and why.

**Validation checks:**
- [ ] User can sign up, sign in, sign out, and delete their account.
- [ ] Status changes persist across sessions.
- [ ] Marking pieces "too hard" measurably changes the next feed load.
- [ ] No personal data is stored beyond what is needed; this is documented in a public privacy note.
- [ ] Account deletion actually deletes — verified by inspection.

### Milestone 6 — Closed beta

**Goal:** real classical guitarists use the platform and tell us what is wrong.

**Deliverables:**
- 15–30 invited users, mix of self-taught and teacher-taught, mix of levels.
- Feedback channel (form, email, or lightweight in-app).
- Bug triage process; weekly review of incoming reports.
- Two-week minimum beta duration; longer if issues are significant.

**Validation checks:**
- [ ] At least 20 users have completed onboarding and opened at least three pieces each.
- [ ] At least 10 users have returned to the site on a separate day.
- [ ] Qualitative feedback gathered and summarized.
- [ ] No critical bugs open (crashes, broken playback, wrong grades on most pieces).
- [ ] Advisor signs off on public launch.

**Stop condition:** if the advisor declines to sign off, do not launch. Address the issues raised and repeat the closed beta.

### Milestone 7 — Public launch

**Goal:** the project is open to anyone, documented well enough for outside contributors, and stable enough not to embarrass the team.

**Deliverables:**
- Public sign-up enabled.
- Documentation: README, user-facing help, contributor guide, architecture overview.
- Issue templates and a public roadmap.
- A short blog post or launch note explaining what the project is and is not.
- Backup and uptime monitoring in place.

**Validation checks:**
- [ ] A new contributor can set up the project locally from documentation alone, without asking questions.
- [ ] At least one external contributor has opened a PR (need not be merged; the bar is "the project is approachable enough that someone tried").
- [ ] Monitoring alerts work (verified by deliberately triggering one).
- [ ] Database backups exist and have been test-restored once.

---

## 8. Definition of done for the MVP

The MVP is complete when, and only when, all of the following are true:

- [ ] All seven milestones' validation checks pass.
- [ ] A new user can land on the site, choose a level, find a piece, play it through with loop and tempo controls, mark it "playing," and return the next day to find it in their library.
- [ ] The musical advisor has signed off in writing on grading quality, notation rendering, and overall pedagogical soundness.
- [ ] The repository is public, the license is in place, and a contributor guide exists.
- [ ] The project has at least 20 active users from the closed beta who have used it more than once.

Anything beyond this is post-MVP.

---

## 9. Post-MVP roadmap (not for the MVP agent to action)

Held here so the team can resist scope creep with a clear answer of "later, not never":

- OMR pipeline to unlock IMSLP's PDF-only repertoire.
- Pitch-preserving slowdown for serious practice.
- Fingering annotations (user-added first; suggested second).
- Expansion to fingerstyle and VGM with separate graders.
- Federated or contributed-score model (community uploads, moderation, licensing).
- Mobile native apps.
- Teacher accounts and assignment flows.

---

## 10. Failure modes the agent should watch for

If any of these is happening, stop and escalate to the human team:

- **Scope creep into a non-goal (§4).** Treat any pull toward these as a red flag.
- **Building without advisor input on pedagogically loaded decisions.** Grading, level placement, and notation correctness all qualify.
- **Premature optimization.** No caching, sharding, or microservices before there are users.
- **Drift from MusicXML.** Any proposal to store scores in a custom format must be rejected.
- **A milestone taking more than 2× its initial estimate.** Surface this; consider cutting scope rather than extending time.

---

*End of specification. Treat this document as the contract. When in doubt, re-read §2 (intent), §4 (non-goals), and §6 (principles) before acting.*
