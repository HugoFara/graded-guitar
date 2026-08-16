import { describe, it, expect, beforeEach } from "vitest";
import {
  addTake,
  getTakes,
  bestTake,
  clearTakes,
  exportTakes,
  importTakes,
  summarizeTake,
  loadAllTakes,
  MAX_TAKES_PER_PIECE,
  type TakeRecord,
} from "./takes";
import type { BarPerformance, TakeAnalysis } from "../listen/stumble";

const PROFILE = "p1";
const CID = "mutopia:ftp/SorF/O35/sorf_op35_no5";

function bar(overrides: Partial<BarPerformance> & { bar: number }): BarPerformance {
  return {
    reached: true,
    attempts: 1,
    liveFrames: 40,
    lastAttemptFrames: 40,
    expectedFrames: 40,
    tempoRatio: 1,
    longestHoldFrames: 0,
    silentFrames: 0,
    restartsFrom: 0,
    restartsTo: 0,
    meanCost: 0.05,
    ...overrides,
  };
}

function analysis(overrides: Partial<TakeAnalysis> = {}): TakeAnalysis {
  const bars = overrides.bars ?? [bar({ bar: 0 }), bar({ bar: 1 }), bar({ bar: 2 })];
  return {
    bars,
    barCount: bars.length,
    reachedBars: bars.filter((b) => b.reached).length,
    furthestBar: bars.length - 1,
    completion: 1,
    completed: true,
    medianTempoRatio: 1,
    totalRestarts: 0,
    totalHoldFrames: 0,
    durationMs: 12000,
    meanCost: 0.05,
    ...overrides,
  };
}

function record(over: Partial<TakeRecord> = {}): TakeRecord {
  return {
    ...summarizeTake(analysis(), { captureRatio: 1 }),
    ...over,
  };
}

describe("summarizeTake", () => {
  it("keeps the completed flag that drives the censoring rule", () => {
    const done = summarizeTake(analysis(), { captureRatio: 1 });
    expect(done.completed).toBe(true);

    const abandoned = summarizeTake(
      analysis({ completed: false, completion: 0.4, furthestBar: 1 }),
      { captureRatio: 1 },
    );
    expect(abandoned.completed).toBe(false);
    expect(abandoned.completion).toBe(0.4);
  });

  it("stores only bars the player reached", () => {
    const a = analysis({
      bars: [
        bar({ bar: 0 }),
        bar({ bar: 1 }),
        bar({ bar: 2, reached: false, attempts: 0, tempoRatio: NaN }),
      ],
    });
    const rec = summarizeTake(a, { captureRatio: 1 });
    expect(rec.bars.map((b) => b.b)).toEqual([0, 1]);
  });

  it("turns non-finite metrics into null rather than storing NaN", () => {
    // JSON.stringify writes NaN as null anyway; doing it here keeps the
    // in-memory record honest instead of only the serialized one.
    const rec = summarizeTake(
      analysis({ medianTempoRatio: NaN, meanCost: NaN }),
      { captureRatio: 1 },
    );
    expect(rec.median_tempo_ratio).toBe(null);
    expect(rec.mean_cost).toBe(null);
  });

  it("carries the grade snapshot forward, per ADR 0013", () => {
    const rec = summarizeTake(analysis(), {
      captureRatio: 1,
      snapshot: { grade: "5", source: "dummy-v0" },
    });
    expect(rec.grade_at_record).toBe("5");
    expect(rec.grade_source_at_record).toBe("dummy-v0");
  });

  it("records the capture ratio so throttled takes are identifiable", () => {
    const rec = summarizeTake(analysis(), { captureRatio: 0.4321 });
    expect(rec.capture_ratio).toBeCloseTo(0.432, 3);
  });
});

describe("takes store", () => {
  beforeEach(() => localStorage.clear());

  it("returns nothing for an unseen piece", async () => {
    expect(await getTakes(PROFILE, CID)).toEqual([]);
    expect(await bestTake(PROFILE, CID)).toBe(null);
  });

  it("round-trips a take", async () => {
    await addTake(PROFILE, CID, record({ recorded_at: "2026-08-16T10:00:00.000Z" }));
    const takes = await getTakes(PROFILE, CID);
    expect(takes.length).toBe(1);
    expect(takes[0].bar_count).toBe(3);
  });

  it("keeps takes newest first", async () => {
    await addTake(PROFILE, CID, record({ recorded_at: "2026-08-16T10:00:00.000Z" }));
    await addTake(PROFILE, CID, record({ recorded_at: "2026-08-16T12:00:00.000Z" }));
    await addTake(PROFILE, CID, record({ recorded_at: "2026-08-16T11:00:00.000Z" }));
    const takes = await getTakes(PROFILE, CID);
    expect(takes.map((t) => t.recorded_at)).toEqual([
      "2026-08-16T12:00:00.000Z",
      "2026-08-16T11:00:00.000Z",
      "2026-08-16T10:00:00.000Z",
    ]);
  });

  it("caps history by dropping the oldest, not refusing the newest", async () => {
    for (let i = 0; i < MAX_TAKES_PER_PIECE + 4; i++) {
      await addTake(
        PROFILE,
        CID,
        record({ recorded_at: `2026-08-16T${String(i).padStart(2, "0")}:00:00.000Z` }),
      );
    }
    const takes = await getTakes(PROFILE, CID);
    expect(takes.length).toBe(MAX_TAKES_PER_PIECE);
    expect(takes[0].recorded_at).toBe("2026-08-16T13:00:00.000Z");
    expect(takes.at(-1)?.recorded_at).toBe("2026-08-16T04:00:00.000Z");
  });

  it("keeps profiles separate", async () => {
    await addTake(PROFILE, CID, record());
    expect(await getTakes("p2", CID)).toEqual([]);
  });

  it("picks the furthest take as best, not the most recent", async () => {
    await addTake(
      PROFILE,
      CID,
      record({ recorded_at: "2026-08-16T10:00:00.000Z", completion: 1, completed: true }),
    );
    await addTake(
      PROFILE,
      CID,
      record({ recorded_at: "2026-08-16T11:00:00.000Z", completion: 0.3, completed: false }),
    );
    const best = await bestTake(PROFILE, CID);
    expect(best?.completion).toBe(1);
  });

  it("breaks a completion tie by recency", async () => {
    await addTake(PROFILE, CID, record({ recorded_at: "2026-08-16T10:00:00.000Z" }));
    await addTake(PROFILE, CID, record({ recorded_at: "2026-08-16T11:00:00.000Z" }));
    expect((await bestTake(PROFILE, CID))?.recorded_at).toBe("2026-08-16T11:00:00.000Z");
  });

  it("clears one piece or all of them", async () => {
    await addTake(PROFILE, CID, record());
    await addTake(PROFILE, "other", record());
    await clearTakes(PROFILE, CID);
    expect(await getTakes(PROFILE, CID)).toEqual([]);
    expect((await getTakes(PROFILE, "other")).length).toBe(1);
    await clearTakes(PROFILE);
    expect(await loadAllTakes(PROFILE)).toEqual({});
  });

  it("survives corrupt storage", async () => {
    localStorage.setItem("gradedGuitar.takes.p1", "{not json");
    expect(await getTakes(PROFILE, CID)).toEqual([]);
  });

  it("drops malformed records rather than the whole store", async () => {
    localStorage.setItem(
      "gradedGuitar.takes.p1",
      JSON.stringify({
        [CID]: [record({ recorded_at: "2026-08-16T10:00:00.000Z" }), { junk: true }],
      }),
    );
    const takes = await getTakes(PROFILE, CID);
    expect(takes.length).toBe(1);
  });
});

describe("takes export/import", () => {
  beforeEach(() => localStorage.clear());

  it("round-trips", async () => {
    await addTake(PROFILE, CID, record({ recorded_at: "2026-08-16T10:00:00.000Z" }));
    const payload = await exportTakes(PROFILE);
    const result = await importTakes("p2", payload);
    expect(result.imported).toBe(1);
    expect((await getTakes("p2", CID)).length).toBe(1);
  });

  it("is idempotent — re-importing the same backup adds nothing", async () => {
    await addTake(PROFILE, CID, record({ recorded_at: "2026-08-16T10:00:00.000Z" }));
    const payload = await exportTakes(PROFILE);
    await importTakes(PROFILE, payload);
    const second = await importTakes(PROFILE, payload);
    expect(second.imported).toBe(0);
    expect(second.skipped).toBe(1);
    expect((await getTakes(PROFILE, CID)).length).toBe(1);
  });

  it("unions takes recorded on two devices", async () => {
    await addTake(PROFILE, CID, record({ recorded_at: "2026-08-16T10:00:00.000Z" }));
    await addTake("p2", CID, record({ recorded_at: "2026-08-16T15:00:00.000Z" }));
    await importTakes(PROFILE, await exportTakes("p2"));
    expect((await getTakes(PROFILE, CID)).length).toBe(2);
  });

  it("rejects an unknown version", async () => {
    await expect(
      importTakes(PROFILE, { version: 9, takes: {} } as never),
    ).rejects.toThrow(/unsupported/);
  });
});
