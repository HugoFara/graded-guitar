import { beforeEach, describe, expect, it } from "vitest";
import {
  clearAllStatuses,
  exportStatuses,
  getStatus,
  importStatuses,
  listByStatus,
  loadAllStatuses,
  setStatus,
} from "./status";

const PID = "p_test";

describe("status store", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("returns not_seen for any unset cid", async () => {
    expect(await getStatus(PID, "missing")).toBe("not_seen");
  });

  it("round-trips a status value", async () => {
    await setStatus(PID, "piece-a", "playing");
    expect(await getStatus(PID, "piece-a")).toBe("playing");
  });

  it("setting to not_seen removes the record", async () => {
    await setStatus(PID, "piece-a", "completed");
    await setStatus(PID, "piece-a", "not_seen");
    const all = await loadAllStatuses(PID);
    expect(all).toEqual({});
  });

  it("lists pieces by status, most recent first", async () => {
    await setStatus(PID, "a", "playing");
    // Force ordering — JS dates can collide at ms granularity in tests
    await new Promise((r) => setTimeout(r, 5));
    await setStatus(PID, "b", "playing");
    const out = await listByStatus(PID, "playing");
    expect(out.map((r) => r.cid)).toEqual(["b", "a"]);
  });

  it("listByStatus ignores other statuses", async () => {
    await setStatus(PID, "a", "playing");
    await setStatus(PID, "b", "completed");
    const out = await listByStatus(PID, "completed");
    expect(out.map((r) => r.cid)).toEqual(["b"]);
  });

  it("isolates statuses per profile id", async () => {
    await setStatus("p1", "a", "playing");
    await setStatus("p2", "a", "too_hard");
    expect(await getStatus("p1", "a")).toBe("playing");
    expect(await getStatus("p2", "a")).toBe("too_hard");
  });

  it("clearAllStatuses removes everything for a profile", async () => {
    await setStatus(PID, "a", "playing");
    await setStatus(PID, "b", "completed");
    await clearAllStatuses(PID);
    expect(await loadAllStatuses(PID)).toEqual({});
  });

  it("export/import round-trips on a fresh profile", async () => {
    await setStatus(PID, "a", "playing");
    await setStatus(PID, "b", "too_hard");
    const dump = await exportStatuses(PID);
    await clearAllStatuses(PID);
    const result = await importStatuses(PID, dump);
    expect(result.imported).toBe(2);
    expect(result.skipped).toBe(0);
    expect((await loadAllStatuses(PID))["a"]).toBe("playing");
    expect((await loadAllStatuses(PID))["b"]).toBe("too_hard");
  });

  it("import keeps the newer record on conflict", async () => {
    // Pre-existing record at "now"
    await setStatus(PID, "a", "playing");
    const dump = await exportStatuses(PID);
    // Overwrite locally with a fresher state
    await new Promise((r) => setTimeout(r, 5));
    await setStatus(PID, "a", "completed");
    // Re-importing the older snapshot should be skipped
    const result = await importStatuses(PID, dump);
    expect(result.imported).toBe(0);
    expect(result.skipped).toBe(1);
    expect(await getStatus(PID, "a")).toBe("completed");
  });

  it("rejects unknown export versions", async () => {
    // @ts-expect-error — intentional bad payload
    await expect(importStatuses(PID, { version: 99, records: {} })).rejects.toThrow();
  });

  it("persists grade snapshot when one is supplied", async () => {
    await setStatus(PID, "piece-a", "too_hard", {
      grade: "7",
      source: "dummy-v0",
    });
    const dump = await exportStatuses(PID);
    expect(dump.version).toBe(2);
    const rec = dump.records["piece-a"];
    expect(rec.grade_at_record).toBe("7");
    expect(rec.grade_source_at_record).toBe("dummy-v0");
  });

  it("omits snapshot fields when no snapshot is supplied", async () => {
    await setStatus(PID, "piece-a", "playing");
    const dump = await exportStatuses(PID);
    const rec = dump.records["piece-a"];
    expect(rec.grade_at_record).toBeUndefined();
    expect(rec.grade_source_at_record).toBeUndefined();
  });

  it("clearing back to not_seen drops the snapshot with the record", async () => {
    await setStatus(PID, "piece-a", "too_hard", {
      grade: "7",
      source: "dummy-v0",
    });
    await setStatus(PID, "piece-a", "not_seen");
    const dump = await exportStatuses(PID);
    expect(dump.records["piece-a"]).toBeUndefined();
  });

  it("accepts v1 imports without snapshot fields", async () => {
    const result = await importStatuses(PID, {
      version: 1,
      records: {
        "piece-a": { status: "playing", updated_at: "2026-01-01T00:00:00.000Z" },
      },
    });
    expect(result.imported).toBe(1);
    expect(await getStatus(PID, "piece-a")).toBe("playing");
  });

  it("preserves snapshot fields across import on a v2 envelope", async () => {
    const result = await importStatuses(PID, {
      version: 2,
      records: {
        "piece-a": {
          status: "too_hard",
          updated_at: "2026-01-01T00:00:00.000Z",
          grade_at_record: "5",
          grade_source_at_record: "dummy-v0",
        },
      },
    });
    expect(result.imported).toBe(1);
    const dump = await exportStatuses(PID);
    expect(dump.records["piece-a"].grade_at_record).toBe("5");
    expect(dump.records["piece-a"].grade_source_at_record).toBe("dummy-v0");
  });
});
