# 0014 — Corpus diversification: the realistic frontier without OMR

- **Status:** Accepted
- **Date:** 2026-05-18

## Context

External review on 2026-05-18 flagged the corpus skew: Guitar Loot
accounts for 53% of accepted pieces and a single arranger (Felix
Horetzky) for 15%. The review's prescription was to "get Guitar Loot
under 40%" by adding sources from a suggested list: Werner Icking
Music Archive, Folkoteca Galega, the CC-licensed MuseScore subset,
contemporary composer sites, Cantorion, Free Scores project.

This ADR records what happened when those leads were probed.

## Findings

A two-hour audit on 2026-05-18:

- **Werner Icking Music Archive (WIMA)** — *defunct*. The site's
  surviving page redirects all music files to IMSLP's
  `Category:WIMA_files`. The M1.1 discovery run (2026-05-17) already
  established that IMSLP's `Category:For guitar` yields zero MusicXML
  files. Adding WIMA gains nothing.
- **OpenScore (musescore.com/openscore)** — gated behind Cloudflare on
  the web front-end. The official OpenScore GitHub org has only
  `Lieder` and `StringQuartets` mirrors; no classical-guitar mirror
  exists.
- **Project Gutenberg sheet-music section** — under 50 MusicXML scores
  total; per-book inspection needed to find any guitar pieces; long
  tail per file. Not worth a dedicated discover script.
- **Hausmusik.ch** — Swiss free-scores archive. No guitar/lute section
  surfaces from the top-level "tree view" or alphabetical index.
- **Folkoteca Galega** — Galician folk music, off-genre for classical
  guitar.
- **Garden of Musical Delights** — Flemish/Dutch traditional music,
  off-genre.
- **GitHub repo + code search** — `gh search code` is already
  saturated for the modern-composer queries we'd want
  (`barrios extension:musicxml` → 0 hits;
  `rodrigo extension:musicxml` → 0 hits;
  `"Classical Guitar" extension:musicxml` → 120 hits, identical to
  the candidate set we already process). The two heaviest-hit repos
  in our current github candidates (`MaxDevv/Music-Thingy`,
  `nskold/Scrape`) are personal-practice and Catholic-liturgical
  collections respectively, not classical-guitar repertoire.

## The frontier without OMR

The 2026 free-MusicXML ecosystem for classical guitar appears to be:

- **Guitar Loot** (~530 raw, 428 accepted) — single arranger, mostly
  Renaissance/Baroque lute repertoire.
- **Mutopia** (332 accepted) — diverse but biased toward what the
  LilyPond community has typeset, which is itself
  Renaissance/Baroque-heavy plus Classical-era pedagogical works
  (Sor, Giuliani, Carcassi, Aguado).
- **GitHub long tail** (41 accepted, ≈300 raw) — heterogeneous
  small-scale uploads, mostly student/practice files.

Total ceiling without OMR or community submissions: roughly
**1,000-1,500 pieces**, with the same Renaissance/Baroque/Classical
distribution we already have. **Modern repertoire (Villa-Lobos,
Barrios, Brouwer, Rodrigo, Castelnuovo-Tedesco, Ponce, Tedesco) is
essentially absent from free MusicXML.** That's not a search problem;
it's that these works are still under copyright in most jurisdictions
and the modern transcriptions that do exist are mostly behind
paywalls or in PDF-only form on IMSLP.

## Decision

1. **Park "Guitar Loot < 40%" as a goal that requires either OMR or
   community submissions.** Until one of those paths opens, the
   target is not achievable through reproducible scraping.

2. **Mark the modern-composer gap as a known shape of the corpus,
   not a bug.** The spec §3 audience (advanced beginner through
   intermediate, Grades 2-7) is mostly served by the Classical-era
   pedagogical repertoire we already have plenty of. Modern
   repertoire is mostly Grade 6+ — important for completeness but
   not for the MVP-user moment.

3. **Treat the corpus shape as material context in two downstream
   surfaces:**
   - Any future advisor outreach (per ADR 0013) should mention that
     the corpus is Renaissance/Baroque-heavy; an advisor who reviews
     50 random pieces will be reviewing mostly Delcamp-style lute
     transcriptions. That's a fact about the sample, not the
     project.
   - The closed-beta invite copy (ADR 0013) should set expectations
     about era coverage. We don't want a tester to land expecting
     Villa-Lobos and find none.

4. **Open one community-submission affordance early.** Defer the
   submission *form* to post-MVP (spec §4 calls user-uploaded scores
   a non-goal at MVP), but the README and `/privacy` page should
   carry a sentence inviting people who type-set classical-guitar
   MusicXML to get in touch. Cost: one paragraph; potential upside:
   one or two contributed pieces a month would compound.

5. **Defer the OMR research spike.** The reviewer flagged this as
   priority #4. After this corpus-frontier audit, OMR moves up in
   credibility — but a real OMR evaluation needs its own session
   and probably its own ADR. Mark it as the next strategic question
   after the M6 closed beta has started generating real signal.

## Consequences

**Commits us to:**

- Honest framing of the corpus in user-facing copy and advisor
  outreach: "Renaissance-and-Baroque-heavy, with growing
  Classical-era pedagogical coverage."
- A short "got classical-guitar MusicXML?" sentence in the README and
  `/privacy` page.
- Not burning more sessions on speculative external-archive probing
  without new intel.

**Costs:**

- Corpus diversity remains a real-but-deferred weakness. If a
  Grade 6+ user with modern-rep interests tries the platform, the
  feed will under-serve them.
- Advisor recruitment is harder when the sample they'd review is
  biased toward one era's repertoire.

**Forecloses:**

- Nothing structurally. The ingest pipeline remains source-pluggable
  (ADR 0005). If a new free-MusicXML archive surfaces, an ADR + a
  discover script is the unchanged path.

**Follow-ups:**

- Add the "got MusicXML? get in touch" sentence to README + `/privacy`.
- After M6 begins, revisit OMR as the credible path to 10K-piece scale.
- If anyone independently discovers an active classical-guitar
  MusicXML archive (e.g. a conservatory open-access program), add it
  here.
