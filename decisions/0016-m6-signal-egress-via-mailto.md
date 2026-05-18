# 0016 — M6 signal egress: mailto + attach, no upload endpoint

- **Status:** Accepted
- **Date:** 2026-05-18

## Context

ADR 0013 frames M6 as a grading-signal collector. The closed beta
yields `(user_self_declared_level, piece, status, vote)` data that
the M2-successor grader trains/validates against. That data needs to
*leave* the user's device or it is useless to us.

Today, ADR 0012 commits the project to **local-only storage**: no
server, no auth, no upload. The privacy note repeats that promise
verbatim. The question forced by ADR 0013 is: how do we collect
signals without breaking that promise?

Three candidate paths considered:

1. **Build a real upload endpoint.** Stand up a small server (e.g.,
   a Cloudflare Worker writing to R2), add an "Upload" button that
   POSTs the JSON. Requires service infra, secrets, retention
   policy, and a privacy-note rewrite. Out of proportion for ≤30
   beta users.
2. **Use a Google Form / Tally form.** The user pastes JSON into a
   text area. Form host gets the data; users see a third-party
   domain. Free, but routes private library data through a vendor
   we'd then have to add to the privacy note.
3. **mailto: + attach.** The browser downloads the JSON, then opens
   the user's mail client with a prefilled draft. The user attaches
   the file and hits Send. Data goes directly from the user to a
   maintainer email; no third-party service touches it, and the
   user controls the moment of egress.

(1) is right for M7+. (3) is right for ≤30 beta users where two
extra clicks of friction beat the cost of an upload service plus
the additional privacy surface.

## Decision

1. **The "Share signals…" button on `/profile` does a download +
   mailto.** No upload endpoint. The user is the one who clicks
   Send. The mail goes to `hugo.farajallah@unige.ch`.

2. **Strictly opt-in.** The default M6 user never sends anything.
   The privacy note (M5 deliverable §5) is updated to call out the
   share button as the *only* path by which data leaves the
   browser, and to describe exactly what's in the file.

3. **The export envelope (`ProfileBackup`) is the wire format.**
   No anonymization, no field stripping. The user can read the
   downloaded JSON before attaching if they want to know what
   they're sending. Envelope versions: v1 (M5 baseline), v2 (adds
   status grade snapshots per ADR 0013), v3 (adds the vote
   sub-payload). Older envelopes are still accepted on import.

4. **Maintainer-side handling is private and ad-hoc.** Attachments
   land in a private folder (`~/graded-guitar-private/beta-signals/`),
   not the repo. Aggregate stats may appear in M2-successor reports;
   raw files do not get redistributed. See `docs/BETA_TRIAGE.md`.

5. **M7 may revisit.** A real launch with hundreds or thousands of
   users would not survive on mailto+attach. When/if traffic
   demands a hosted endpoint, write the next ADR — do not back-door
   one in.

## Consequences

**Commits us to:**

- A two-click submission friction floor (download, then attach). We
  accept this; M6 is small enough that the friction acts as
  consent confirmation rather than a usability problem.
- An export envelope that is the user-visible wire format. Every
  field in `ProfileBackup` must be safe for the user to read and
  send — no internal-only debug fields.
- The privacy note as a contract: "The only way data leaves your
  browser is the Share signals button you click yourself." If this
  changes, the privacy note changes in the same commit.
- Maintainer-side discipline: signal attachments live outside the
  repo, are not redistributed, and aggregate-only reports.

**Costs:**

- Maintainer ergonomics: incoming signals arrive as email
  attachments, not in a queryable database. Aggregation across
  users requires running a script over a folder of JSONs. That's
  fine at N=30; it would not be fine at N=300.
- No automated retention enforcement. A user can ask us to delete
  their submission; we have to actually find and delete the file.
  Document the request in `docs/BETA_TRIAGE.md` when it happens.

**Forecloses:**

- Sneaking telemetry in later. Once "explicit opt-in only" is in
  the privacy note, any change toward automatic collection has to
  be advertised loudly and is a separate ADR.

**Follow-ups:**

- If/when an upload endpoint is added at M7, supersede this ADR.
- If the export envelope gains internal/debug fields, route them
  to a separate dev-only payload, not the user-visible backup.
