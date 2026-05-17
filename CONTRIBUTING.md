# Contributing to Repertoire

Thanks for thinking about contributing. A few things to know before you start.

## Read the spec first

The single source of truth is [`project-spec.md`](./project-spec.md). Anything you propose must be consistent with it. In particular:

- **§4 — Non-goals.** PRs that drift toward these will be closed with a pointer here. The list exists to keep the MVP shippable.
- **§5 — Musical advisor.** Anything that affects pedagogical correctness (grading rubric, level placement, notation correctness) requires advisor sign-off. We will not merge changes in those areas without it.
- **§6 — Working principles.** MusicXML is the canonical format. Reuse the FOSS notation ecosystem; don't rewrite it.

If you think the spec is wrong, open an issue. Don't route around it in a PR.

## How we make decisions

Meaningful technical choices live in [`decisions/`](./decisions/) as short ADRs. If your PR introduces a new dependency, a new file format, a new service, or a new architectural pattern, add an ADR alongside the code. Use [`decisions/template.md`](./decisions/template.md).

## Issues

- **Bug reports:** what you did, what you expected, what happened, the piece (composer + title + IMSLP URL if applicable) if it's score-specific.
- **Feature requests:** check §4 of the spec first. If your idea is on the non-goals list, it belongs in §9 (post-MVP roadmap), not the MVP.
- **Pedagogical issues** (wrong grade, wrong notation, weird recommendation): tag with `pedagogy`; these go to the advisor.

## Pull requests

- Branch off `main`, keep PRs focused, write a real description.
- Update or add an ADR if your change is non-trivial.
- CI must be green.
- For changes that touch user-facing musical output, include a note about whether advisor review is needed.

## Code of conduct

See [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md). Be decent.
