# Syllabi

Structured grade-list data for the three examining boards used as ground truth for the grading model (see [ADR 0002](../decisions/0002-syllabi-sources.md), spec Milestone 2).

| File              | Board                          | Grade range     | Source                                       |
| ----------------- | ------------------------------ | --------------- | -------------------------------------------- |
| `rcm.json`        | Royal Conservatory of Music    | 1–10            | https://www.rcmusic.com/learning/examinations |
| `trinity.json`    | Trinity College London         | Initial, 1–8    | https://www.trinitycollege.com/qualifications/music/guitar |
| `abrsm.json`      | ABRSM                          | Initial, 1–8    | https://www.abrsm.org/en/our-exams/classical-guitar-exams |

Each file conforms to [`schema.json`](./schema.json). CI validates this on every PR.

## Populating the data

The stubs in this directory have correct metadata (`syllabus`, `edition`, `source`, `grades`) and an **empty `pieces` array**. The next task is to extract the piece-grade tuples from each board's current syllabus PDF or web page and populate the array.

This is intentionally left for a human pass rather than auto-generated, because:

- Syllabi change between editions. We need to fix the edition we're working from and record the extraction date.
- Spec §5 makes pedagogical correctness a release blocker. A typo'd grade is worse than no grade.
- The musical advisor should validate the extracted list (spec Milestone 1 validation: advisor spot-checks; the same applies here a fortiori).

Once each `pieces` array has data, the syllabus file should also be reviewed by the advisor before being used to train the model (spec Milestone 2).

## Field guide

- `grade` — must be a string from the parent `grades` array. Strings (not numbers) because Trinity and ABRSM include `"Initial"`.
- `list` — RCM and ABRSM split each grade into lists (A/B/C…). Trinity has a single list per grade. Leave blank when not applicable.
- `opus` — free-form ("Op. 35 No. 17", "BWV 996/iv"). Useful for disambiguating IMSLP matches downstream.
- `imslp_url` — optional. Filled in opportunistically during ingest (Milestone 1).
