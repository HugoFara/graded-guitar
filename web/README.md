# web/

M3 web player for graded-guitar. Svelte 5 + Vite + alphaTab.

See [`../decisions/0011-m3-stack.md`](../decisions/0011-m3-stack.md) for
the stack rationale.

## What's here

- Routes
  - `/` — landing. Redirects to `/feed` if a level is stored on the
    active profile, else `/onboard`.
  - `/onboard` — grade picker (M4). Saves the chosen level to the
    active profile and continues to `/feed`.
  - `/feed` — pieces at the user's level and one above (M4). Pieces
    are round-robined across composer buckets so a prolific composer
    doesn't dominate the head of the list. M5 status signals
    (`too_hard`, `not_for_me`, `completed`) re-shape the order.
  - `/library` — your library (M5), tabbed by status: Playing /
    Completed / Too hard / Skipped / All.
  - `/profile` — manage local profiles (M5): switch, rename, change
    level, delete, export/import JSON backups.
  - `/privacy` — public privacy note (M5).
  - `/browse` — corpus list. Filter by free-text, composer (datalist
    autocomplete), era, grade range, max length, and source (curator /
    model / all).
  - `/piece/:cid` — alphaTab player with play/pause/stop, tempo slider
    (50–150%), bar-number loop, tab-view toggle, and the M5 status
    selector.
- `src/lib/manifest.ts` — typed loader for `corpus/manifest.json`,
  grade-resolution rules (curator preferred, model fallback, `dummy-*`
  flagged as "placeholder"), filter logic, and the feed builder.
- `src/lib/level.ts` — playing level (sync wrapper over the active
  profile).
- `src/lib/storage/` — M5 client-only accounts scaffold (see
  [`decisions/0012-m5-local-accounts.md`](../decisions/0012-m5-local-accounts.md)):
  - `profile.ts` — `Profile` CRUD with async API.
  - `status.ts` — per-piece status store (`not_seen | playing |
    completed | too_hard | not_for_me`).
  - `backup.ts` — JSON export/import for the eventual server
    migration.
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

## CI

[`.github/workflows/web.yml`](../.github/workflows/web.yml) runs
**typecheck + unit tests + build** on every push touching `web/` —
that's the fast feedback (~2 min). It does not run Playwright e2e
because the corpus (`corpus/normalized/`, ~110 MB) is gitignored and
the hosted runner has no way to regenerate it without re-fetching from
upstream. Run e2e locally before pushing changes to the player, and
regenerate `corpus/m3_render_check.md` via `pnpm report:e2e`.

`workflow_dispatch` input:

- `run_e2e=true` — only useful on a runner that already has the
  corpus checked out (self-hosted, mostly).

## Deployment

The CI runner has no MusicXML files, so deploys happen from a
developer machine that has the corpus checked out:

```bash
cd web
pnpm deploy:local
```

This builds with the live corpus, writes a `deploy.json` provenance
marker, and force-pushes `dist/` to the `gh-pages` branch via an
orphan commit (no history accumulation). GitHub Pages serves from
that branch; the URL is [hugofara.github.io/graded-guitar/](https://hugofara.github.io/graded-guitar/).

The script refuses to run if `web/public/musicxml/` is empty — that
guard exists so we don't accidentally publish a music-less site from
a fresh clone.
