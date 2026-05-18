# 0012 — M5 accounts: local-only profiles, async storage interface

- **Status:** Accepted
- **Date:** 2026-05-18

## Context

Spec §7 M5 ("Accounts and tracking") asks for:

1. Account creation (email + password minimum).
2. Per-piece status: `not_seen | playing | completed | too_hard | not_for_me`.
3. Personal library view filtered by status.
4. Recommendation feed that adjusts based on status signals.
5. A public privacy statement.

Four of the five deliverables are pure client-side: status, library,
feed feedback, and privacy. The one that genuinely needs a server is
the first — identity. Today the project has no backend; M0–M4 ship as
a static site to GitHub Pages.

We could:

- **(a) Wait for a backend.** Block M5 on picking and standing up a host
  (Supabase, Pocketbase, Fly + Postgres, …). Spec §7 M5 doesn't pin a
  choice; making one now risks regretting it after closed beta
  (§7 M6) tells us what the real load looks like.
- **(b) Scaffold the shape now, store everything in the browser.**
  Treat "account" as **local profile**. The storage layer is shaped as
  an async interface (every call returns a `Promise`) so that swapping
  to a real backend later is a same-shape implementation change,
  not a UI rewrite.

(b) lets us close 4/5 deliverables with real, testable behavior — and
defers the host/auth decision until we know more. The cost is that
profiles aren't portable across devices or browsers, and there's no
recovery from clearing site data. We accept that tradeoff for M5 and
make it visible to users.

## Decision

1. **No real authentication at M5.** "Account" → "local profile."
   Multiple profiles can coexist in one browser; switching profiles
   means changing the active profile id. No password storage. No
   email collected (we use a free-form display name instead — there
   is nowhere to send mail).

2. **Async storage interface.** All persistence goes through
   `src/lib/storage/*.ts` modules whose public API returns
   `Promise<T>`. The current implementation is synchronous localStorage
   under the hood; the async wrappers are deliberate so call sites
   don't change when a network-backed implementation lands.

3. **Storage layout (localStorage keys):**

   - `gradedGuitar.profiles` — JSON array of profiles.
     Each: `{ id, display_name, created_at, level }`.
   - `gradedGuitar.activeProfileId` — string id of the active profile.
   - `gradedGuitar.status.<profileId>` — JSON object,
     `{ [cid]: { status, updated_at } }`.

   The existing `gradedGuitar.level` key (M4) is migrated into the
   default profile on first run, then removed.

4. **Status enum is exactly the spec's five values.** No additions, no
   renames. Persisted as snake_case strings.

5. **Feed feedback heuristic:**

   - `too_hard` or `not_for_me` on a piece → hide that piece from the
     feed entirely.
   - `too_hard` on N≥2 pieces by the same composer → drop that
     composer's bucket-priority in the round-robin (effectively pushes
     their remaining pieces down, doesn't hide them).
   - `completed` doesn't hide a piece (you may want to revisit it) but
     it down-weights repeat surfacing.
   - `playing` is neutral on the feed; it's the signal the library
     view uses to surface "what you're working on."

   The heuristic is intentionally simple — there's no learning model;
   we want behavior that's debuggable by reading one function. When
   M6 beta feedback arrives we'll know if it needs to grow up.

6. **UI honesty.** The landing page carries a banner that says,
   plainly, that accounts live in this browser only and that the
   project may move to hosted infrastructure later. The privacy note
   at `/privacy` says the same thing in full sentences. We don't want
   users to discover this after they've recorded a year of progress.

7. **Export / import.** Each profile can be exported to a JSON file
   and imported back. This is the migration path: when a real
   backend lands, the import endpoint on the server consumes the
   same JSON shape. It also doubles as a user-controlled backup
   today.

## Consequences

**Commits us to:**

- An async storage interface from day one. Even though localStorage
  is synchronous, every call site uses `await`. This is the entire
  point of the scaffold; deviating defeats it.
- A snake_case status enum frozen at the M5 close. Renames after
  beta data is recorded would require a migration script.
- Surfacing the "local-only" caveat in the UI — not just docs.

**Costs:**

- Two storage layouts to maintain when the backend lands: the local
  one (for offline / unauthenticated users, if we keep that) and the
  remote one. The export/import path is the bridge.
- The "delete account" gate is honest but trivial: it clears
  localStorage keys. When a real backend exists, it has to actually
  delete server-side rows.
- No cross-device sync. A user who plays on a laptop and tablet sees
  two independent libraries until they manually export/import (or we
  ship the backend).

**Forecloses:**

- Nothing structurally — every M5 piece is replaceable by a
  network-backed implementation behind the same interface. The
  forecloses are about *not* doing things prematurely:
  - We don't pick an auth provider now.
  - We don't pick a database now.
  - We don't pick a hosting tier now.

**Follow-ups:**

- M6 closed beta will tell us how often "I lost my library" happens
  in practice. If it's common, we promote the backend decision.
- A future ADR will record the backend choice and the migration plan
  from local → remote, using export/import as the wire format.
