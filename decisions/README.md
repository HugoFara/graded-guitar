# Decision Log

This folder holds Architecture Decision Records (ADRs). One file per meaningful choice. Numbered sequentially. Once accepted, an ADR is immutable — supersede it with a new file rather than editing.

## Format

Each ADR is a short markdown file:

```
NNNN-kebab-case-title.md
```

Use [`template.md`](./template.md) as the starting point. Sections:

- **Status** — Proposed / Accepted / Superseded by #NNNN.
- **Context** — what forced the decision.
- **Decision** — what we chose.
- **Consequences** — what this commits us to, and what it costs.

## When to write one

Open an ADR when introducing a new dependency, a new file format, a new service, a new architectural pattern, or any choice future-you would Google to remember the reasoning for. If you'd want to argue about it later, write it down now.

## Index

- [0001 — License: MIT](./0001-license-mit.md)
- [0002 — Syllabi: RCM, Trinity, ABRSM](./0002-syllabi-sources.md)
- [0003 — Stack: deferred to Milestone 1](./0003-stack-deferred.md)
- [0004 — Deliberate deferrals: repo visibility, advisor, syllabi data](./0004-deferrals.md)
- [0005 — M1 ingest pipeline architecture](./0005-ingest-pipeline.md)
- [0006 — GitHub as primary discovery source](./0006-github-as-source.md)
- [0007 — Mutopia as a secondary source via patched python-ly](./0007-mutopia-source.md)
- [0008 — Guitar Loot as a third source with curator-assigned grades](./0008-guitarloot-source.md)
- [0009 — M2 grading-model inputs and approach (scoping)](./0009-m2-grading-inputs.md)
- [0012 — M5 accounts: local-only profiles, async storage interface](./0012-m5-local-accounts.md)
- [0013 — M6 framing: closed beta as the grading-signal path](./0013-m6-beta-as-grader.md)
- [0014 — Corpus diversification: the realistic frontier without OMR](./0014-corpus-diversification-frontier.md)
