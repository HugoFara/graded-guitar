# web/

M3 web player for graded-guitar. Svelte 5 + Vite + alphaTab.

See [`../decisions/0011-m3-stack.md`](../decisions/0011-m3-stack.md) for
the stack rationale.

## What's here

- Routes
  - `/` — corpus list. Filter by grade range, by source (curator /
    model / all), and by free-text on title or composer.
  - `/piece/:cid` — alphaTab player with play/pause/stop, tempo slider
    (50–150%), A/B loop, and a tab-view toggle.
- `src/lib/manifest.ts` — typed loader for `corpus/manifest.json` and
  the grade-resolution rules (curator preferred, model fallback,
  `dummy-*` flagged as "placeholder").
- `src/lib/player.ts` — thin alphaTab wrapper.

## Running

```bash
pnpm install
pnpm dev          # http://localhost:5173
```

`predev` mirrors the corpus into `public/` first — both
`public/manifest.json` and `public/musicxml/` are gitignored.

## Testing

```bash
pnpm test         # vitest, unit tests on manifest filtering
pnpm check        # svelte-check / typecheck
pnpm build        # production build into dist/
pnpm test:e2e     # Playwright render smoke + TTI on 10 random pieces
pnpm report:e2e   # regenerate ../corpus/m3_render_check.md
```

First-time setup for e2e tests needs the Chromium binary:

```bash
pnpm exec playwright install chromium
```

## Deployment

A `workflow_dispatch`-gated job in
[`.github/workflows/web.yml`](../.github/workflows/web.yml) builds and
deploys to GitHub Pages. The deploy step only fires when the workflow
is manually triggered with `deploy=true`, and the repo has to be
public (see ADR 0004). Until then, builds run on push to confirm the
project still compiles.
