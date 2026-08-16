// Recorded practice takes — the M8 measurement record.
//
// Storage is keyed per profile, which is what makes the record
// per-(player, piece) rather than per-piece. That is load-bearing, not
// incidental: a bare per-piece average would have to be migrated at
// exactly the moment the data got good, when M6 beta players at
// differing levels start contributing. See ADR 0018.
//
// Derived summaries only. The chroma stream a take is computed from is
// ~1 KB/s and would blow the localStorage budget within a handful of
// takes; the per-bar summary is what any downstream difficulty model
// actually consumes.
import type { GradeSnapshot } from "./status";
import { takesKey } from "./keys";
import type { TakeAnalysis } from "../listen/stumble";

// Short keys, and the reason for them: a 200-bar piece carries a
// summary per bar, and verbose keys tripled the stored size for no
// benefit. Mapping:
//   b = bar index (0-based)   a = attempts
//   t = tempo ratio           h = longest hold, frames
//   r = restarts landing here
export type BarSummary = {
  b: number;
  a: number;
  t: number | null;
  h: number;
  r: number;
};

export type TakeRecord = {
  recorded_at: string;
  duration_ms: number;
  // False means the player did not reach the last bar. Any difficulty
  // derived from this take is then a LOWER BOUND, never a point
  // estimate — the censoring rule in spec §7 M8. Consumers that ignore
  // this flag will bias the top of the grade scale.
  completed: boolean;
  completion: number;
  furthest_bar: number;
  bar_count: number;
  median_tempo_ratio: number | null;
  total_restarts: number;
  // Mean chroma distance over the take. High values mean the alignment
  // itself was poor and the rest of these numbers deserve less weight.
  mean_cost: number | null;
  // Frames produced over frames the wall clock expected. Well below 1
  // means the browser throttled capture and the timing is not
  // trustworthy.
  capture_ratio: number;
  bars: BarSummary[];
  grade_at_record?: string;
  grade_source_at_record?: string;
};

type TakeMap = Record<string, TakeRecord[]>;

// Keeping every take of every piece would grow without bound in a
// store with a ~5 MB ceiling. Ten is enough to see progress on a piece
// while staying well inside budget.
export const MAX_TAKES_PER_PIECE = 10;

function hasStorage(): boolean {
  return typeof localStorage !== "undefined";
}

function finiteOrNull(v: number): number | null {
  return Number.isFinite(v) ? v : null;
}

function round(v: number, places: number): number {
  const f = 10 ** places;
  return Math.round(v * f) / f;
}

// Analysis -> stored record. Rounding here rather than at read time
// keeps the JSON small and makes stored takes comparable across
// versions of the analyzer's floating-point details.
export function summarizeTake(
  analysis: TakeAnalysis,
  meta: { captureRatio: number; snapshot?: GradeSnapshot },
): TakeRecord {
  return {
    recorded_at: new Date().toISOString(),
    duration_ms: Math.round(analysis.durationMs),
    completed: analysis.completed,
    completion: round(analysis.completion, 3),
    furthest_bar: analysis.furthestBar,
    bar_count: analysis.barCount,
    median_tempo_ratio: finiteOrNull(round(analysis.medianTempoRatio, 3)),
    total_restarts: analysis.totalRestarts,
    mean_cost: finiteOrNull(round(analysis.meanCost, 4)),
    capture_ratio: round(meta.captureRatio, 3),
    bars: analysis.bars
      .filter((bar) => bar.reached)
      .map((bar) => ({
        b: bar.bar,
        a: bar.attempts,
        t: finiteOrNull(round(bar.tempoRatio, 3)),
        h: bar.longestHoldFrames,
        r: bar.restartsTo,
      })),
    ...(meta.snapshot?.grade ? { grade_at_record: meta.snapshot.grade } : {}),
    ...(meta.snapshot?.source
      ? { grade_source_at_record: meta.snapshot.source }
      : {}),
  };
}

function isBarSummary(v: unknown): v is BarSummary {
  if (!v || typeof v !== "object") return false;
  const b = v as Record<string, unknown>;
  return (
    typeof b.b === "number" &&
    typeof b.a === "number" &&
    (b.t === null || typeof b.t === "number") &&
    typeof b.h === "number" &&
    typeof b.r === "number"
  );
}

function isTakeRecord(v: unknown): v is TakeRecord {
  if (!v || typeof v !== "object") return false;
  const r = v as Record<string, unknown>;
  return (
    typeof r.recorded_at === "string" &&
    typeof r.completed === "boolean" &&
    typeof r.bar_count === "number" &&
    Array.isArray(r.bars) &&
    r.bars.every(isBarSummary)
  );
}

function readMap(profileId: string): TakeMap {
  if (!hasStorage()) return {};
  const raw = localStorage.getItem(takesKey(profileId));
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    const out: TakeMap = {};
    for (const [cid, list] of Object.entries(parsed as Record<string, unknown>)) {
      if (!Array.isArray(list)) continue;
      const valid = list.filter(isTakeRecord);
      if (valid.length) out[cid] = valid;
    }
    return out;
  } catch {
    return {};
  }
}

function writeMap(profileId: string, map: TakeMap): void {
  if (!hasStorage()) return;
  localStorage.setItem(takesKey(profileId), JSON.stringify(map));
}

export async function addTake(
  profileId: string,
  cid: string,
  take: TakeRecord,
): Promise<void> {
  const map = readMap(profileId);
  const list = map[cid] ?? [];
  list.push(take);
  // Newest first, then truncate — so the cap drops the oldest take
  // rather than refusing to record a new one.
  list.sort((a, b) => b.recorded_at.localeCompare(a.recorded_at));
  map[cid] = list.slice(0, MAX_TAKES_PER_PIECE);
  writeMap(profileId, map);
}

export async function getTakes(
  profileId: string,
  cid: string,
): Promise<TakeRecord[]> {
  return readMap(profileId)[cid] ?? [];
}

export async function loadAllTakes(profileId: string): Promise<TakeMap> {
  return readMap(profileId);
}

export async function clearTakes(profileId: string, cid?: string): Promise<void> {
  if (!hasStorage()) return;
  if (!cid) {
    localStorage.removeItem(takesKey(profileId));
    return;
  }
  const map = readMap(profileId);
  delete map[cid];
  writeMap(profileId, map);
}

// The best evidence we have about a piece from this player: the take
// that got furthest, tie-broken by the most recent. "Furthest" rather
// than "fastest" because an abandoned take tells us less than a
// completed one regardless of how quick the abandoned part was.
export async function bestTake(
  profileId: string,
  cid: string,
): Promise<TakeRecord | null> {
  const takes = await getTakes(profileId, cid);
  if (!takes.length) return null;
  return takes.reduce((best, t) => {
    if (t.completion > best.completion) return t;
    if (t.completion === best.completion && t.recorded_at > best.recorded_at) return t;
    return best;
  });
}

export type TakesExport = {
  version: 1;
  takes: TakeMap;
};

export async function exportTakes(profileId: string): Promise<TakesExport> {
  return { version: 1, takes: readMap(profileId) };
}

// Merge by timestamp: a take is identified by when it was recorded, so
// re-importing the same backup is idempotent and importing two devices'
// backups unions them.
export async function importTakes(
  profileId: string,
  payload: TakesExport,
): Promise<{ imported: number; skipped: number }> {
  if (!payload || payload.version !== 1 || !payload.takes) {
    throw new Error("unsupported takes export version");
  }
  const current = readMap(profileId);
  let imported = 0;
  let skipped = 0;

  for (const [cid, list] of Object.entries(payload.takes)) {
    if (!Array.isArray(list)) continue;
    const existing = current[cid] ?? [];
    const seen = new Set(existing.map((t) => t.recorded_at));
    for (const take of list) {
      if (!isTakeRecord(take) || seen.has(take.recorded_at)) {
        skipped++;
        continue;
      }
      existing.push(take);
      seen.add(take.recorded_at);
      imported++;
    }
    existing.sort((a, b) => b.recorded_at.localeCompare(a.recorded_at));
    current[cid] = existing.slice(0, MAX_TAKES_PER_PIECE);
  }

  writeMap(profileId, current);
  return { imported, skipped };
}
