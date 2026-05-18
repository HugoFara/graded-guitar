# 0011 — M3 web player stack

- **Status:** Accepted
- **Date:** 2026-05-18 (proposed) · 2026-05-18 (accepted, after scope review)

## Context

ADR [0003](./0003-stack-deferred.md) explicitly deferred the M3 stack
choice to "the start of the milestone that first needs it." M3 is the
web player (spec §7 M3). The deliverables are:

- Notation rendering of any piece in the corpus.
- Optional tab view alongside notation.
- Playback (play/pause/seek).
- A/B measure-range loop.
- Tempo slider 50%–150%.
- Responsive layout (laptop + tablet landscape).
- Time-to-interactive <3 s on broadband.

Plus, from ADR [0010](./0010-m2-close-with-dummy-labels.md), the player
must surface `model_grade_source` so a user can tell a `dummy-v0` grade
from a real one — visible attribution is part of the trust story.

ADR 0003 already named the load-bearing decision: **the notation
library choice cascades into everything else.** OSMD and Verovio are
notation-only; alphaTab covers notation + tab + playback + loop +
tempo in one library and maps to every M3 deliverable directly. That
narrows the conversation to "alphaTab vs. (OSMD+Tone.js+VexFlow+…)."

## Decision

Three picks. Each is independently revisable; alphaTab is the
load-bearing one.

### 1. Notation + tab + playback library: **alphaTab**

alphaTab (MPL-2.0, https://alphatab.net) provides:
- MusicXML / GuitarPro / alphaTex input.
- SVG/HTML5 notation rendering with built-in tab view.
- Browser playback via Web Audio API (`alphaTab.Synthesizer`).
- Measure-range looping + tempo control as first-class API surface.
- Cursor following + scrolling out of the box.

Alternatives considered:

- **OpenSheetMusicDisplay** (BSD-3): solid MusicXML renderer, no tab,
  no playback. Pairing it with Tone.js for audio + VexFlow for tab +
  a custom MIDI converter is three libraries against alphaTab's one.
- **Verovio** (LGPL-3): MEI-first; MusicXML import works but is not
  the primary path. No playback. Same composition cost as OSMD.
- **VexFlow** (MIT): low-level rendering primitive, not a complete
  notation viewer.

alphaTab's downside is that it's the heaviest of the three (~600 KB
gzipped including the bravura soundfont split). The <3 s TTI target
holds if the soundfont is lazy-loaded (alphaTab supports this) — the
notation renders before audio is ready, which matches the M3 user
journey (open piece → read → optionally press play).

### 2. Application framework: **Svelte 5 + Vite (no SvelteKit)**

The site is a small SPA with one piece-detail route and a corpus list
view. There is no backend at M3 — `corpus/manifest.json` ships as a
static asset, and the player reads it directly. SSR / API routes are
M5+ concerns.

That makes the right framework one with:
- Static build output, no Node runtime to deploy.
- Tiny runtime budget (the page is already paying ~600 KB to alphaTab).
- Good `alphaTab` interop (alphaTab is plain JS; framework friction
  shouldn't add work).

**Svelte 5 + Vite** fits:
- Build output is plain HTML+JS, deployable to GitHub Pages.
- Runtime is ~5–10 KB for the apps we'll need.
- Svelte 5 runes are explicit enough to read without prior knowledge.
- Vite gives fast HMR; first-party Svelte plugin.

Alternatives considered:

- **SvelteKit / Next.js / Astro:** all bring SSR or routing tooling
  we don't need yet. Adopting them pre-emptively is the failure mode
  spec §10 names ("premature optimization"). Adopt at the milestone
  that first uses SSR (recommendation feed in M4 may, but doesn't
  require it).
- **Vanilla TypeScript + a router:** smaller, but the two routes
  we need now will be twenty by M5 and rolling our own router is
  the kind of "boring infra we don't enjoy maintaining" that
  Svelte 5 already solves.

### 3. Deployment: **GitHub Pages from a CI job**

Already on GitHub, already running Actions. The site is static at M3.
A workflow that builds with Vite and pushes the `dist/` to the
`gh-pages` branch is ~20 lines.

Cloudflare Pages / Vercel / Netlify are equally fine; the deciding
factor is "least new infra to learn." The decision is reversible
when a real backend lands (M5).

### Repo layout

```
web/                  (new top-level)
  ├── package.json
  ├── vite.config.ts
  ├── public/         (static assets)
  ├── src/
  │   ├── App.svelte
  │   ├── routes/     (piece detail, corpus list)
  │   ├── lib/        (manifest loader, alphaTab wrapper)
  │   └── main.ts
  └── README.md
```

The Python pipeline keeps `scripts/`, `corpus/`, `decisions/`. The
web app reads `corpus/manifest.json` and the normalized MusicXML
files; build-time the relevant subset gets copied into `web/public/`
to ship as static assets. Manifest grows ~~900 KB today and will
plateau under 2 MB by M2 close — fine to ship inline.

## Consequences

- **Three new development dependencies** when M3 starts: `alphatab`,
  `svelte@5`, `vite`. All MIT/MPL-compatible with the repo's MIT
  license.
- **The corpus shape stops being open-ended.** M3 reads
  `manifest.json` directly, so any future change to that schema
  (`model_grade_source` rename, new fields) has to update the web
  app in the same PR. Worth pinning a schema doc inside
  `corpus/README.md` when M3 starts.
- **Audio/font assets must be hostable on GitHub Pages.** alphaTab's
  default soundfont is ~30 MB uncompressed; we'll either bundle a
  smaller classical-guitar SF2 or lazy-load on first playback. Sound
  quality is M3-bound but not M3-blocking.
- **Spec §7 M3 has an advisor-gated validation step** ("Advisor
  confirms the rendered notation looks correct on 10 sample
  pieces"). This stack picks the renderer the advisor will be asked
  to bless; if they reject alphaTab's output on, e.g., classical
  guitar slur conventions, M3 is back at this ADR.
- **No mobile native scope.** Spec §4 excludes mobile native; the
  responsive web app is the mobile story.

## Open items for M3 kickoff

- ~~Confirm the alphaTab soundfont strategy (default vs custom SF2).~~
  Decision at v0.1: use alphaTab's default lazy-loaded soundfont; revisit
  if classical-guitar timbre is a blocker during the advisor render
  review. The notation renders before audio loads, so TTI is unaffected.
- ~~Schema-doc `corpus/manifest.json`'s read surface.~~ Added to
  [`corpus/README.md`](../corpus/README.md) under "Web read surface" —
  the player consumes a fixed subset of fields and that subset is now
  documented.
- ~~Corpus-list dummy display rule.~~ v0.1 shows the piece with a
  yellow "(placeholder)" badge for any `model_grade_source` starting
  with `dummy-`, blue "(estimated)" for non-dummy models, and green for
  curator grades. A `source` filter ("all / curator only / model only")
  lets a level-conscious user hide placeholder grades.

## v0.1 implementation notes (2026-05-18)

Landed alongside this ADR's acceptance:

- `web/` top-level Svelte 5 + Vite project with `package.json`,
  `vite.config.ts`, `tsconfig.json`.
- Routes: `/` (corpus list with grade/source filter) and
  `/piece/:cid` (alphaTab player with play/pause/stop, tempo slider
  50–150%, A/B loop, tab toggle).
- `web/scripts/copy-corpus.mjs` — `prebuild`/`predev` step that mirrors
  `corpus/manifest.json` and `corpus/normalized/` into `web/public/`.
  Output is gitignored (matches `corpus/normalized/` policy).
- `.github/workflows/web.yml` — typecheck + test + build on every push
  touching `web/` or `corpus/manifest.json`; deploy step gated behind
  `workflow_dispatch` until the repo flips public (ADR 0004).

Spec §7 M3 validation gates **not yet satisfied** by this PR:

- 10 random pieces render glitch-free (mechanical check; pending).
- Playback matches notation (mechanical check; pending).
- TTI <3 s on broadband (measurement; pending bundle profile).
- Advisor sign-off on notation correctness on 10 sample pieces (human;
  awaits advisor engagement).
- Tab view correctness on 10 sample pieces (human; awaits advisor).
