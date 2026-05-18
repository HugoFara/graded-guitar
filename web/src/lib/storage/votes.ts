// Per-piece grade-disagreement vote — separate from status (ADR 0013).
// A vote is the user's opinion about whether the shown grade is right.
// Status is the user's commitment to a piece. The two are independent:
// a user can vote "harder" without ever planning to learn the piece.
//
// Storage shape mirrors status.ts: a single record per (profileId, cid)
// keyed in localStorage under `gradedGuitar.votes.{profileId}`. The
// snapshot fields capture the grade context at vote time so signals
// recorded against `dummy-v0` can be replayed or discarded when the
// grader changes — same reasoning as status records.
import type { GradeSnapshot } from "./status";
import { votesKey } from "./keys";

export const VOTE_VALUES = ["easier", "right", "harder"] as const;

export type GradeVote = (typeof VOTE_VALUES)[number];

export function isGradeVote(v: unknown): v is GradeVote {
  return typeof v === "string" && (VOTE_VALUES as readonly string[]).includes(v);
}

export type VoteRecord = {
  vote: GradeVote;
  updated_at: string;
  grade_at_record?: string;
  grade_source_at_record?: string;
};

type VoteMap = Record<string, VoteRecord>;

function hasStorage(): boolean {
  return typeof localStorage !== "undefined";
}

function readMap(profileId: string): VoteMap {
  if (!hasStorage()) return {};
  const raw = localStorage.getItem(votesKey(profileId));
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return {};
    }
    const out: VoteMap = {};
    for (const [cid, rec] of Object.entries(parsed as Record<string, unknown>)) {
      if (!rec || typeof rec !== "object") continue;
      const r = rec as Record<string, unknown>;
      if (!isGradeVote(r.vote)) continue;
      if (typeof r.updated_at !== "string") continue;
      const entry: VoteRecord = { vote: r.vote, updated_at: r.updated_at };
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

function writeMap(profileId: string, map: VoteMap): void {
  if (!hasStorage()) return;
  localStorage.setItem(votesKey(profileId), JSON.stringify(map));
}

export async function getVote(
  profileId: string,
  cid: string,
): Promise<GradeVote | null> {
  return readMap(profileId)[cid]?.vote ?? null;
}

// Pass `null` to clear an existing vote (deletes the record so the
// storage size tracks interactions, not corpus size — same rule as
// status.setStatus).
export async function setVote(
  profileId: string,
  cid: string,
  vote: GradeVote | null,
  snapshot?: GradeSnapshot,
): Promise<void> {
  const map = readMap(profileId);
  if (vote === null) {
    if (cid in map) {
      delete map[cid];
      writeMap(profileId, map);
    }
    return;
  }
  const rec: VoteRecord = {
    vote,
    updated_at: new Date().toISOString(),
  };
  if (snapshot?.grade) rec.grade_at_record = snapshot.grade;
  if (snapshot?.source) rec.grade_source_at_record = snapshot.source;
  map[cid] = rec;
  writeMap(profileId, map);
}

export async function loadAllVotes(
  profileId: string,
): Promise<Record<string, VoteRecord>> {
  return readMap(profileId);
}

export async function clearAllVotes(profileId: string): Promise<void> {
  if (!hasStorage()) return;
  localStorage.removeItem(votesKey(profileId));
}

// Wire format for export/import. v1 is the only version today; the
// envelope is versioned anyway so future shape changes have a hook.
export type VoteExport = {
  version: 1;
  records: VoteMap;
};

export async function exportVotes(profileId: string): Promise<VoteExport> {
  return { version: 1, records: readMap(profileId) };
}

// Merge strategy: incoming record wins iff its updated_at is newer.
// Tied or missing timestamps keep what's already there — same rule as
// status import so the eventual server merge has one law to follow.
export async function importVotes(
  profileId: string,
  payload: VoteExport,
): Promise<{ imported: number; skipped: number }> {
  if (!payload || payload.version !== 1 || !payload.records) {
    throw new Error("unsupported vote export version");
  }
  const current = readMap(profileId);
  let imported = 0;
  let skipped = 0;
  for (const [cid, rec] of Object.entries(payload.records)) {
    if (!isGradeVote(rec?.vote) || typeof rec?.updated_at !== "string") {
      skipped++;
      continue;
    }
    const here = current[cid];
    if (!here || rec.updated_at > here.updated_at) {
      const next: VoteRecord = { vote: rec.vote, updated_at: rec.updated_at };
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
