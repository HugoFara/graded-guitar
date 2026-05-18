# M6 Closed-beta invite

Template for inviting beta testers to graded-guitar. Per spec §7 M6
the goal is **15–30 invited users, mix of self-taught and
teacher-taught, mix of levels**. Per ADR 0013 the beta is framed
explicitly as a grading-signal collector.

The two templates below are starting points. **Edit the body** before
sending — they're a baseline, not a script. Track every send in
`docs/outreach/beta-log.md` (one row per invite) so we know who got
which framing and who hasn't been reminded.

---

## Template A — Cold (someone you don't know, asked by a friend, etc.)

> Subject: a tiny ask — try a classical-guitar repertoire site (10 min)?
>
> Hi {name},
>
> I'm building [graded-guitar](https://hugofara.github.io/graded-guitar/),
> a free, open-source site that helps classical guitarists find sheet
> music matched to their level. Every piece is auto-graded by
> difficulty, you set your level, and the feed only shows you pieces
> you can actually play.
>
> It's in pre-alpha and the grader is honestly a placeholder right
> now — that's exactly why I'm reaching out. The feature I most need
> beta testers for is the "this grade feels wrong: easier / right /
> harder" vote on every piece. The more real guitarists tell me when
> the grader is off, the faster it stops being a placeholder.
>
> Ten minutes is enough to be useful: open the site, set your level
> in onboarding, click through five pieces, vote on the grade on each
> one. If you have more time, mark some as "playing" or "too hard"
> and that's even more signal. Everything stays in your browser
> unless you hit "Share signals" on the profile page, which sends me
> the data and which is strictly opt-in.
>
> No account, no email, no tracking. You can read the
> [privacy note](https://hugofara.github.io/graded-guitar/#/privacy)
> for the full story.
>
> Open to feedback, complaints, bug reports, "this is dumb because
> X" — all of it.
>
> Thanks,
> Hugo

## Template B — Warm (someone you know, in the project's orbit)

> Subject: pre-alpha beta — graded-guitar
>
> Hey {name},
>
> Quick favour: I have something usable enough to test. It's the
> classical-guitar repertoire site I've been building —
> [graded-guitar](https://hugofara.github.io/graded-guitar/).
> Public-domain pieces, auto-graded, feed matched to your level.
>
> Two things I'd love your input on:
>
> 1. **Do the grades feel right?** Every piece has an "easier /
>    right / harder" vote. The grader is `dummy-v0` right now (full
>    disclosure, that's in a banner at the top) and your votes are
>    how I find out where it's wrong.
> 2. **Does the feed surface anything good?** I'd want to know if
>    you actually find something worth practicing in the first five
>    pieces it shows you.
>
> If you want to send me your library so the data goes into the
> grader improvement, the profile page has a "Share signals…"
> button that downloads your library as JSON and pops a draft email
> for you to attach it. Strictly opt-in.
>
> File any bugs / awkward UI / outright bad ideas through this
> issue template:
> https://github.com/HugoFara/graded-guitar/issues/new?template=beta-feedback.yml
> — or just reply to this email.
>
> Thanks,
> Hugo

---

## What to capture about each invitee (before sending)

A minimum row in `docs/outreach/beta-log.md`:

| date | name / handle | how I know them | self-taught vs. teacher-taught | rough level | template | sent? | replied? |
|------|---------------|-----------------|--------------------------------|-------------|----------|-------|----------|

Spec §7 M6 calls for a **mix of self-taught and teacher-taught, mix
of levels**. If the log skews one way after the first 10 invites,
shift the next batch.

## Beta open-letter (landing footer banner)

When the count of confirmed beta users crosses 5, swap the pre-alpha
banner copy in `web/src/App.svelte` to something like:

> Pre-alpha. We're running a closed beta with ~15-30 classical
> guitarists. The grader is still placeholder; your votes are what
> retire it. See [the closed-beta note](…) for details.
