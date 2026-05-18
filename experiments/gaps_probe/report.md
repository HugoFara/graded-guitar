# GAPS dataset probe — report

Per ADR 0015: assess whether the GAPS dataset (arXiv:2408.08653,
"GAPS: A Large and Diverse Classical Guitar Dataset and Benchmark
Transcription Model", Yang & Riley et al. 2024 ISMIR) is usable for
the graded-guitar corpus or only as a future advisor-quality
validation set.

- Dataset page: <https://aim-qmul.github.io/GAPS/>
- Zenodo record: <https://zenodo.org/records/13962272>
- Public download: `gaps_v1_no_audio.zip` (7.0 MB; 2.3 GB total when
  including externally-hosted audio via YouTube)

## What's in the no-audio bundle

After unzipping `gaps_v1_no_audio.zip`:

| Asset | Count | Notes |
|---|---:|---|
| MusicXML (`.xml`) | 400 | Scores |
| MIDI (`.mid`) | 301 | Fine-aligned to performance audio |
| Syncpoints (`.json`) | 400 | Score↔audio alignment |
| Metadata CSV | 1 | 53 columns; title, composer, duration, key, etc. |

The paper reports 300 final pieces after rejection; the 400 in the
zip include the extras (74 explicitly rejected during curation +
others kept for reference).

## License — the deciding constraint

The Zenodo record lists the license as **CC BY-NC-SA 4.0** —
Creative Commons Attribution-NonCommercial-ShareAlike 4.0
International.

The dataset companion site adds custom restrictions on top:

> "GAPS may only be used by the individual signing below and by
> members of the research group or organisation of this individual."
>
> "GAPS may be used only for non-commercial research purposes."
>
> "GAPS (or data enabling its reproduction) may not be sold, leased,
> published or distributed to any third party without written
> permission."

**Implications for graded-guitar:**

- The corpus we ship is hosted on GitHub Pages, free at the point of
  use, MIT-licensed, and could be deployed by a third party
  commercially without our involvement. NC explicitly forbids that.
- ShareAlike taints derivative works — adding GAPS data would force
  the whole corpus + any model trained on it to be CC-BY-NC-SA.
  That conflicts with the MIT-licensed code in the same repo.
- The "individual signing below" clause means GAPS is licensed
  per-person, not per-project. Even with permission, we couldn't
  redistribute it through the platform.

**Conclusion: GAPS cannot be part of the public corpus.**

## What GAPS is still useful for

Per ADR 0013, the M2 advisor sign-off needs 50 randomly graded
pieces to be reviewed at the 40/50 plausibility bar. GAPS provides:

- **300 advisor-quality classical-guitar scores**, curated by
  researchers with 10+ years music experience, sourced from
  ClassClef, with alignment-verified performances by 200+ players.
- A held-out validation set of *exactly the genre we care about*,
  which our current corpus (Renaissance/Baroque-heavy) cannot supply
  on its own.
- Performance recordings (via YouTube links in metadata) — useful
  later if we ever want to evaluate audio↔score grading signals.

The non-commercial clause permits use in research, which is what M2
grading-model development is. We can:

- Download GAPS to a developer machine
- Use it as a held-out test set to evaluate dummy-v0 successors
- Cite it in any M2 evaluation report
- Never ship it as corpus content

This is the right framing: **GAPS becomes the M2 evaluation oracle,
not an M1 corpus source.** It is more valuable to us in that role
than it would be as 300 added pieces, because we currently have no
advisor-quality held-out set at all.

## Composer / arranger spread

Sampled from the metadata CSV's `composer` field (which the
ClassClef export populated with "Music by Arr: …" style — the
*arranger* of each performance, not the original composer). 271
entries are blank in that field.

Top recurring arrangers (= performers who recorded the audio):

- Stefan Apke (15 + variants)
- Julian Bream (5 + variants)
- Edson Lopes (4 + variants)
- Andrew Zohn (4)
- Jószef Eötvös (4)
- Andres Segovia (3)
- John Williams (3)
- Marcos Diaz (3)
- Roland Dyens (2)

That's an A-list of 20th-century classical guitarists. The original
composer for each piece would have to be re-extracted from the
MusicXML metadata itself, not the CSV.

## Recommendation

- **Do not ingest GAPS into the public corpus.** License precludes
  it.
- **Keep the local download for M2 work.** Use it as the held-out
  validation set when we replace `dummy-v0` with an advisor-blessed
  grader.
- **Document the relationship in an ADR** at the M2 replacement
  milestone — not now; the data is here, the constraint is logged.
