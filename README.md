# graded-guitar

A free, open-source web platform where classical guitarists discover sheet music matched to their playing level. Every score in the library is automatically graded by difficulty, so a player declares (or is placed at) a level and receives a feed of pieces they can actually play.

> The repo is currently **private**; see [`decisions/0004-deferrals.md`](./decisions/0004-deferrals.md) for why and when it goes public.

> **Status:** Milestone 0 — Foundation. Pre-alpha. No usable application yet.

See [`project-spec.md`](./project-spec.md) for the full, authoritative specification. Everything in this repo is governed by that document.

---

## Quickstart

This is currently a documentation-and-data repository. There is no application to run yet.

```bash
git clone git@github.com:HugoFara/graded-guitar.git
cd graded-guitar
./scripts/check.sh   # runs the same checks CI runs
```

That's it. When the data ingest pipeline (Milestone 1) lands, this section will gain a real "install and run" path.

## What's in here today

| Path                  | Purpose                                                          |
| --------------------- | ---------------------------------------------------------------- |
| `project-spec.md`     | Authoritative product spec. Read this first.                     |
| `decisions/`          | Architecture Decision Records. One file per meaningful decision. |
| `syllabi/`            | Structured grade-list data for RCM, Trinity, ABRSM.              |
| `docs/ADVISOR.md`     | Template for the musical advisor agreement (spec §5).            |
| `scripts/check.sh`    | Repository self-check; also runs in CI.                          |
| `.github/workflows/`  | CI configuration.                                                |

## How this project is built

We follow the milestones in [`project-spec.md`](./project-spec.md) in order. Each milestone has explicit validation checks; we do not advance until they pass. When we make a meaningful technical choice, we record it in [`decisions/`](./decisions/).

If you disagree with a decision, open an issue or a PR against the relevant ADR. Do not silently diverge.

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md). The short version: this project values pedagogical correctness above technical elegance — see spec §5 and §6 — and we are intentionally narrow in scope (classical guitar only, no editing, no OMR, no audio listening; see spec §4).

## License

MIT. See [`LICENSE`](./LICENSE) and [`decisions/0001-license-mit.md`](./decisions/0001-license-mit.md) for rationale.
