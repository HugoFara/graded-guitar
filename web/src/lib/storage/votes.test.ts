import { beforeEach, describe, expect, it } from "vitest";
import {
  clearAllVotes,
  exportVotes,
  getVote,
  importVotes,
  loadAllVotes,
  setVote,
} from "./votes";

const PID = "p_vote";

describe("vote store", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("returns null for an unset cid", async () => {
    expect(await getVote(PID, "missing")).toBeNull();
  });

  it("round-trips a vote", async () => {
    await setVote(PID, "piece-a", "harder");
    expect(await getVote(PID, "piece-a")).toBe("harder");
  });

  it("clearing the vote removes the record", async () => {
    await setVote(PID, "piece-a", "easier");
    await setVote(PID, "piece-a", null);
    expect(await loadAllVotes(PID)).toEqual({});
  });

  it("persists the grade snapshot when supplied", async () => {
    await setVote(PID, "piece-a", "harder", {
      grade: "5",
      source: "dummy-v0",
    });
    const all = await loadAllVotes(PID);
    expect(all["piece-a"].grade_at_record).toBe("5");
    expect(all["piece-a"].grade_source_at_record).toBe("dummy-v0");
  });

  it("isolates votes per profile id", async () => {
    await setVote("p1", "piece-a", "easier");
    await setVote("p2", "piece-a", "harder");
    expect(await getVote("p1", "piece-a")).toBe("easier");
    expect(await getVote("p2", "piece-a")).toBe("harder");
  });

  it("clearAllVotes removes everything for a profile", async () => {
    await setVote(PID, "a", "easier");
    await setVote(PID, "b", "harder");
    await clearAllVotes(PID);
    expect(await loadAllVotes(PID)).toEqual({});
  });

  it("export/import round-trips on a fresh profile", async () => {
    await setVote(PID, "a", "easier", { grade: "3", source: "dummy-v0" });
    await setVote(PID, "b", "right", { grade: "6", source: "delcamp-eric-crouch" });
    const dump = await exportVotes(PID);
    await clearAllVotes(PID);
    const result = await importVotes(PID, dump);
    expect(result.imported).toBe(2);
    expect(result.skipped).toBe(0);
    const all = await loadAllVotes(PID);
    expect(all["a"].vote).toBe("easier");
    expect(all["a"].grade_at_record).toBe("3");
    expect(all["b"].grade_source_at_record).toBe("delcamp-eric-crouch");
  });

  it("import keeps the newer record on conflict", async () => {
    await setVote(PID, "a", "easier");
    const dump = await exportVotes(PID);
    await new Promise((r) => setTimeout(r, 5));
    await setVote(PID, "a", "harder");
    const result = await importVotes(PID, dump);
    expect(result.imported).toBe(0);
    expect(result.skipped).toBe(1);
    expect(await getVote(PID, "a")).toBe("harder");
  });

  it("rejects unknown export versions", async () => {
    await expect(
      importVotes(PID, { version: 99 as unknown as 1, records: {} }),
    ).rejects.toThrow();
  });

  it("skips records with invalid vote values on import", async () => {
    const result = await importVotes(PID, {
      version: 1,
      records: {
        "good": { vote: "easier", updated_at: "2026-01-01T00:00:00.000Z" },
        "bad": {
          vote: "nope" as unknown as "easier",
          updated_at: "2026-01-01T00:00:00.000Z",
        },
      },
    });
    expect(result.imported).toBe(1);
    expect(result.skipped).toBe(1);
  });
});
