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
    expect(dump.version).toBe(1);
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
});
