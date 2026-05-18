// Per-piece status store — M5 spec §7 enum, persisted per profile.
// `not_seen` is the implicit default; it's not written to disk, so
// `getStatus()` returns `"not_seen"` for any unset cid. That keeps the
// storage size proportional to interactions, not corpus size. See
// decisions/0012-m5-local-accounts.md.
import { statusKey } from "./keys";

export const STATUS_VALUES = [
  "not_seen",
  "playing",
  "completed",
  "too_hard",
  "not_for_me",
] as const;

export type PieceStatus = (typeof STATUS_VALUES)[number];

export function isPieceStatus(s: unknown): s is PieceStatus {
  return typeof s === "string" && (STATUS_VALUES as readonly string[]).includes(s);
}

// A status event captured against the grade context that was visible
// to the user at write time. `grade_at_record` is the resolved grade
// string as displayed (e.g. "5"); `grade_source_at_record` is the
// provenance — "delcamp-eric-crouch" for curator grades, "dummy-v0"
// for the placeholder model, etc. These let us replay or discard
// historical signals when the grader changes — without them, a year's
// worth of `too_hard` feedback recorded against a placeholder grader
// becomes silent noise. See decisions/0013-m6-beta-as-grader.md.
export type StatusRecord = {
  status: PieceStatus;
  updated_at: string;
  grade_at_record?: string;
  grade_source_at_record?: string;
};

export type GradeSnapshot = {
  grade?: string;
  source?: string;
};

type StatusMap = Record<string, StatusRecord>;

function hasStorage(): boolean {
  return typeof localStorage !== "undefined";
}

function readMap(profileId: string): StatusMap {
  if (!hasStorage()) return {};
  const raw = localStorage.getItem(statusKey(profileId));
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return {};
    }
    const out: StatusMap = {};
    for (const [cid, rec] of Object.entries(parsed as Record<string, unknown>)) {
      if (!rec || typeof rec !== "object") continue;
      const r = rec as Record<string, unknown>;
      if (!isPieceStatus(r.status)) continue;
      if (typeof r.updated_at !== "string") continue;
      const entry: StatusRecord = { status: r.status, updated_at: r.updated_at };
      if (typeof r.grade_at_record === "string") {
        entry.grade_at_record = r.grade_at_record;
      }
      if (typeof r.grade_source_at_record === "string") {
        entry.grade_source_at_record = r.grade_source_at_record;
      }
      out[cid] = entry;
    }
    return out;
  } catch {
    return {};
  }
}

function writeMap(profileId: string, map: StatusMap): void {
  if (!hasStorage()) return;
  localStorage.setItem(statusKey(profileId), JSON.stringify(map));
}

export async function getStatus(
  profileId: string,
  cid: string,
): Promise<PieceStatus> {
  return readMap(profileId)[cid]?.status ?? "not_seen";
}

// Setting a piece back to "not_seen" deletes its record so the storage
// stays tight. Any other value persists with a fresh timestamp.
//
// `snapshot` captures the grade context the user saw when they made
// this judgment — see StatusRecord. Production call sites must pass
// it; we keep it optional so unit tests and migrations don't have to
// fabricate a manifest lookup.
export async function setStatus(
  profileId: string,
  cid: string,
  status: PieceStatus,
  snapshot?: GradeSnapshot,
): Promise<void> {
  const map = readMap(profileId);
  if (status === "not_seen") {
    if (cid in map) {
      delete map[cid];
      writeMap(profileId, map);
    }
    return;
  }
  const rec: StatusRecord = {
    status,
    updated_at: new Date().toISOString(),
  };
  if (snapshot?.grade) rec.grade_at_record = snapshot.grade;
  if (snapshot?.source) rec.grade_source_at_record = snapshot.source;
  map[cid] = rec;
  writeMap(profileId, map);
}

export async function listByStatus(
  profileId: string,
  status: PieceStatus,
): Promise<{ cid: string; updated_at: string }[]> {
  const map = readMap(profileId);
  const out: { cid: string; updated_at: string }[] = [];
  for (const [cid, rec] of Object.entries(map)) {
    if (rec.status === status) out.push({ cid, updated_at: rec.updated_at });
  }
  // Most-recent first — the library view wants the freshest activity
  // at the top, and the feed feedback heuristic doesn't care about order.
  out.sort((a, b) => b.updated_at.localeCompare(a.updated_at));
  return out;
}

// Bulk read for the feed heuristic, which needs every status at once
// to compute composer/grade penalties. Returns a flat Record so call
// sites can do O(1) lookups by cid.
export async function loadAllStatuses(
  profileId: string,
): Promise<Record<string, PieceStatus>> {
  const map = readMap(profileId);
  const out: Record<string, PieceStatus> = {};
  for (const [cid, rec] of Object.entries(map)) {
    out[cid] = rec.status;
  }
  return out;
}

export async function clearAllStatuses(profileId: string): Promise<void> {
  if (!hasStorage()) return;
  localStorage.removeItem(statusKey(profileId));
}

// Export/import payload — JSON-friendly snapshot of one profile's
// status records. The shape is the wire format for the eventual
// server migration; don't reshape it without writing a migrator.
//
// v2 adds optional grade_at_record / grade_source_at_record fields on
// each record. v1 imports are accepted (snapshot fields are simply
// absent on the imported entries).
export type StatusExport = {
  version: 1 | 2;
  records: StatusMap;
};

export async function exportStatuses(profileId: string): Promise<StatusExport> {
  return { version: 2, records: readMap(profileId) };
}

// Merge strategy: incoming record wins iff its updated_at is newer.
// Tied or missing timestamps fall back to "keep what's here." This
// makes idempotent re-imports safe and gives the future server-merge
// a tractable rule.
export async function importStatuses(
  profileId: string,
  payload: StatusExport,
): Promise<{ imported: number; skipped: number }> {
  if (!payload || (payload.version !== 1 && payload.version !== 2) || !payload.records) {
    throw new Error("unsupported status export version");
  }
  const current = readMap(profileId);
  let imported = 0;
  let skipped = 0;
  for (const [cid, rec] of Object.entries(payload.records)) {
    if (!isPieceStatus(rec?.status) || typeof rec?.updated_at !== "string") {
      skipped++;
      continue;
    }
    const here = current[cid];
    if (!here || rec.updated_at > here.updated_at) {
      const next: StatusRecord = { status: rec.status, updated_at: rec.updated_at };
      if (typeof rec.grade_at_record === "string") {
        next.grade_at_record = rec.grade_at_record;
      }
      if (typeof rec.grade_source_at_record === "string") {
        next.grade_source_at_record = rec.grade_source_at_record;
      }
      current[cid] = next;
      imported++;
    } else {
      skipped++;
    }
  }
  writeMap(profileId, current);
  return { imported, skipped };
}
