import { beforeEach, describe, expect, it } from "vitest";
import {
  backupFilename,
  exportProfile,
  importProfile,
} from "./backup";
import {
  createProfile,
  getActiveProfile,
  listProfiles,
  setActiveProfile,
} from "./profile";
import {
  getStatus,
  setStatus,
} from "./status";
import {
  getVote,
  loadAllVotes,
  setVote,
} from "./votes";

describe("profile backup", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("round-trips a profile and its statuses into a new profile", async () => {
    // Seed default, change its level, add a few statuses
    const original = (await listProfiles())[0];
    const { updateProfile } = await import("./profile");
    await updateProfile(original.id, { display_name: "Hugo", level: 6 });
    await setStatus(original.id, "piece-a", "playing");
    await setStatus(original.id, "piece-b", "completed");

    const refreshed = (await listProfiles()).find((p) => p.id === original.id)!;
    const dump = await exportProfile(refreshed);
    expect(dump.version).toBe(3);
    expect(dump.profile.display_name).toBe("Hugo");
    expect(dump.profile.level).toBe(6);
    expect(Object.keys(dump.statuses.records)).toHaveLength(2);

    const { profile: imported, imported: n } = await importProfile(dump);
    expect(imported.id).not.toBe(original.id); // new profile, not overwrite
    expect(imported.display_name).toBe("Hugo");
    expect(imported.level).toBe(6);
    expect(n).toBe(2);
    expect(await getStatus(imported.id, "piece-a")).toBe("playing");
    expect(await getStatus(imported.id, "piece-b")).toBe("completed");
  });

  it("rejects unknown version", async () => {
    await expect(
      // @ts-expect-error — intentional bad version
      importProfile({ version: 99, exported_at: "", profile: {}, statuses: {} }),
    ).rejects.toThrow();
  });

  it("uses display name slug in the filename", () => {
    const p = {
      id: "p1",
      display_name: "Recital prep!",
      created_at: "2026-01-01T00:00:00Z",
      level: 5,
    };
    expect(backupFilename(p)).toMatch(/^graded-guitar-recital-prep-\d{4}-\d{2}-\d{2}\.json$/);
  });

  it("falls back to 'profile' when display name has no usable chars", () => {
    const p = {
      id: "p1",
      display_name: "!!!",
      created_at: "2026-01-01T00:00:00Z",
      level: null,
    };
    expect(backupFilename(p)).toMatch(/^graded-guitar-profile-\d{4}-\d{2}-\d{2}\.json$/);
  });

  it("does not change the active profile on import", async () => {
    const first = (await listProfiles())[0];
    await setActiveProfile(first.id);
    const second = await createProfile({ display_name: "Other", level: 4 });
    await setStatus(second.id, "x", "playing");
    const dump = await exportProfile(second);
    await setActiveProfile(first.id);
    await importProfile(dump);
    expect((await getActiveProfile())?.id).toBe(first.id);
  });

  it("accepts v1 backups without snapshot fields", async () => {
    const v1: any = {
      version: 1,
      exported_at: "2026-04-01T00:00:00.000Z",
      profile: {
        display_name: "Legacy",
        level: 4,
        created_at: "2026-01-01T00:00:00.000Z",
      },
      statuses: {
        version: 1,
        records: {
          "old-piece": {
            status: "playing",
            updated_at: "2026-03-15T00:00:00.000Z",
          },
        },
      },
    };
    const { profile, imported } = await importProfile(v1);
    expect(imported).toBe(1);
    expect(profile.display_name).toBe("Legacy");
    expect(await getStatus(profile.id, "old-piece")).toBe("playing");
  });

  it("round-trips snapshot fields through a v2 backup", async () => {
    const p = await createProfile({ display_name: "Snap", level: 5 });
    await setStatus(p.id, "x", "too_hard", { grade: "6", source: "dummy-v0" });
    const dump = await exportProfile(p);
    const { profile: restored, imported } = await importProfile(dump);
    expect(imported).toBe(1);
    const restoredDump = await exportProfile(restored);
    const rec = restoredDump.statuses.records["x"];
    expect(rec.grade_at_record).toBe("6");
    expect(rec.grade_source_at_record).toBe("dummy-v0");
  });

  it("round-trips grade-disagreement votes through a v3 backup", async () => {
    const p = await createProfile({ display_name: "Voter", level: 5 });
    await setVote(p.id, "x", "harder", { grade: "5", source: "dummy-v0" });
    await setVote(p.id, "y", "easier", { grade: "8", source: "dummy-v0" });
    const dump = await exportProfile(p);
    expect(dump.version).toBe(3);
    expect(Object.keys(dump.votes!.records)).toHaveLength(2);

    const result = await importProfile(dump);
    expect(result.votes_imported).toBe(2);
    expect(result.votes_skipped).toBe(0);
    expect(await getVote(result.profile.id, "x")).toBe("harder");
    const all = await loadAllVotes(result.profile.id);
    expect(all["x"].grade_at_record).toBe("5");
  });

  it("accepts a v2 backup that has no votes field", async () => {
    const v2: any = {
      version: 2,
      exported_at: "2026-04-01T00:00:00.000Z",
      profile: {
        display_name: "PreVotes",
        level: 4,
        created_at: "2026-01-01T00:00:00.000Z",
      },
      statuses: {
        version: 2,
        records: {
          "old-piece": {
            status: "playing",
            updated_at: "2026-03-15T00:00:00.000Z",
            grade_at_record: "4",
            grade_source_at_record: "dummy-v0",
          },
        },
      },
    };
    const result = await importProfile(v2);
    expect(result.imported).toBe(1);
    expect(result.votes_imported).toBe(0);
    expect(result.votes_skipped).toBe(0);
    expect(await loadAllVotes(result.profile.id)).toEqual({});
  });
});
