# ClassClef outreach — draft

Draft of an outreach email to the operator of
[classclef.com](https://www.classclef.com/) (the site's "contact" link
goes to `classclef@gmail.com`). Goal: get explicit permission to
ingest the site's classical-guitar MusicXML/GuitarPro files into the
graded-guitar corpus, mirroring the permission the GAPS dataset
authors (arXiv:2408.08653) obtained in 2024.

Per ADR 0013 (M6 framing) and ADR 0015 (OMR feasibility spike) this
is the second of two parallel corpus-expansion paths. PDMX delivered
+307 pieces; ClassClef's ~5,900-piece catalogue would, if even a
fraction is ingestible, be the largest single-source addition the
corpus has seen.

**Status:** draft only. Do NOT send until the operator (Hugo) has
reviewed and edited the body / signature.

---

## Recipient

- **To:** classclef@gmail.com
- **Subject:** Permission to mirror ClassClef classical-guitar
  MusicXML in an open-source discovery platform

## Body (draft)

> Hi,
>
> My name is Hugo Farajallah. I'm building
> [graded-guitar](https://github.com/HugoFara/graded-guitar), an
> open-source classical-guitar repertoire discovery platform — every
> piece is automatically graded by difficulty so self-taught players
> can find pieces matched to their level. The repo is MIT-licensed
> and currently in late pre-alpha; a local-only beta is live at
> hugofara.github.io/graded-guitar/.
>
> The corpus today is about 1,100 public-domain MusicXML files
> stitched together from Guitar Loot, the Mutopia Project, the PDMX
> dataset (NeurIPS 2024), and a handful of GitHub repositories. It is
> heavily Renaissance / Baroque-leaning because that's where free
> MusicXML happens to be available — Romantic and 20th-century
> pedagogical repertoire is thin.
>
> ClassClef is by far the most complete public-facing classical-guitar
> archive I've come across, and the work to assemble it is striking.
> I'd love to discuss whether you'd be willing to let me mirror a
> subset of the site's MusicXML or GuitarPro files into the
> graded-guitar corpus, with proper attribution. A few specifics so
> you can judge:
>
> - **Attribution.** Every piece sourced from ClassClef would carry a
>   visible "Source: classclef.com" line on its detail page in the
>   web app, linking back to your original page. The same would be
>   recorded in the corpus manifest (`source_url`) for any downstream
>   use.
> - **License terms.** I'm happy to work within whatever terms suit
>   you — including a non-commercial restriction if that's what you'd
>   prefer. Files from your site would carry their own license tag in
>   the manifest separate from the MIT license that covers our code.
> - **Format.** The platform consumes MusicXML / MXL natively. If
>   you only license redistribution of the MusicXML form (and not
>   the GuitarPro source), that works for us — we use MuseScore CLI
>   to convert if needed, with a manual review step on a sample.
> - **Scale of mirroring.** Initially I'd target a few hundred pieces
>   chosen to fill known gaps in the existing corpus (e.g., Tárrega,
>   Albéniz, Villa-Lobos, Brouwer, Barrios, Castelnuovo-Tedesco
>   transcriptions where licensing permits). Not the entire site.
> - **Right to withdraw.** If at any point you'd like a piece — or
>   all of them — removed, I'd remove them within a week and document
>   the takedown. The corpus is regenerable from scratch via a
>   reproducible pipeline.
> - **Precedent.** The authors of the GAPS dataset (Yang & Riley,
>   ISMIR 2024) wrote that they "obtained permission from the website
>   owner of classclef.com." I'd be grateful for the same kind of
>   arrangement, scoped to graded-guitar's discovery use case.
>
> The platform is, and will remain, free at the point of use; the
> MIT license covers our code, not the corpus content.
>
> Two practical questions:
>
> 1. Would you be open in principle? If so, is there a license
>    framing you'd prefer (CC-BY-NC, CC-BY, a custom statement, …)?
> 2. Is there a subset you'd specifically want included (or
>    excluded)?
>
> Happy to send a one-page summary of the project, or a screencast
> of the platform, whichever helps.
>
> Thanks for your time, and for the archive — it's a remarkable
> resource.
>
> Best,
> Hugo Farajallah
> github@hugofara.net
> github.com/HugoFara/graded-guitar

## Edit notes (for Hugo before sending)

- Replace "I" / "my" if you want to phrase this as project-owned
  rather than individual.
- The PDMX reference is fresh (2024-2025) and tells the operator we
  have an alternative source — not a threat, but it removes any
  implicit "we need you or nothing." Drop if you'd rather not signal
  alternatives.
- If you want to attach the platform URL with seeded ClassClef
  attribution already in place, deploy a dummy "would look like this"
  piece detail page first, screenshot it, and link. Adds zero
  ambiguity about what attribution we mean.
- "Within a week" for takedowns is the standard small-project SLA;
  raise to "within 48 hours" if you want to be more deferential, or
  leave as-is.
- The closing line about "remarkable resource" is sincere and worth
  keeping; don't drop it for brevity.

## After sending

If a response arrives:

- **Yes, with conditions** → write an ADR documenting the agreed
  terms before any ingest. Mirror their preferred license tag into
  every ClassClef-sourced manifest entry. Add a "Sources" footer
  on the detail page that includes the agreed attribution.
- **No** → log it here as a closed thread and move on. Do not
  re-approach for at least 6 months.
- **No reply after 4 weeks** → one follow-up, then close as
  no-response.

If/when the agreement lands, the next steps are:

1. Write `scripts/m1_discover_classclef.py` (HTML walk pattern, see
   `m1_discover_guitarloot.py` for the template).
2. Hand-pick or batch-export the target subset (probably ~500
   pieces from named composers, capped to ~50 per composer to keep
   variety).
3. Run the ingest, validate, regenerate manifest + report, deploy.
