import { beforeEach, describe, expect, it } from "vitest";
import {
  createProfile,
  deleteProfile,
  getActiveProfile,
  listProfiles,
  setActiveProfile,
  updateProfile,
} from "./profile";
import { KEY_ACTIVE_PROFILE, KEY_LEGACY_LEVEL, KEY_PROFILES } from "./keys";

describe("profile store", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("seeds a default profile on first access", async () => {
    const profiles = await listProfiles();
    expect(profiles).toHaveLength(1);
    expect(profiles[0].display_name).toBe("You");
    expect(profiles[0].level).toBe(null);

    const active = await getActiveProfile();
    expect(active?.id).toBe(profiles[0].id);
  });

  it("migrates the legacy gradedGuitar.level key into the default profile", async () => {
    localStorage.setItem(KEY_LEGACY_LEVEL, "6");
    const profiles = await listProfiles();
    expect(profiles[0].level).toBe(6);
    // Legacy key is consumed
    expect(localStorage.getItem(KEY_LEGACY_LEVEL)).toBe(null);
  });

  it("ignores garbage in the legacy level on migration", async () => {
    localStorage.setItem(KEY_LEGACY_LEVEL, "garbage");
    const profiles = await listProfiles();
    expect(profiles[0].level).toBe(null);
  });

  it("creates additional profiles", async () => {
    await listProfiles();
    const second = await createProfile({ display_name: "Practice", level: 4 });
    expect(second.level).toBe(4);
    const all = await listProfiles();
    expect(all).toHaveLength(2);
  });

  it("rejects blank display_name on create", async () => {
    await expect(createProfile({ display_name: "   " })).rejects.toThrow();
  });

  it("updates display_name and level", async () => {
    const profiles = await listProfiles();
    const updated = await updateProfile(profiles[0].id, {
      display_name: "Hugo",
      level: 7,
    });
    expect(updated.display_name).toBe("Hugo");
    expect(updated.level).toBe(7);
  });

  it("clears level when patched with null", async () => {
    const profiles = await listProfiles();
    await updateProfile(profiles[0].id, { level: 5 });
    const next = await updateProfile(profiles[0].id, { level: null });
    expect(next.level).toBe(null);
  });

  it("switches the active profile", async () => {
    const first = (await listProfiles())[0];
    const second = await createProfile({ display_name: "Other" });
    await setActiveProfile(second.id);
    expect((await getActiveProfile())?.id).toBe(second.id);
    await setActiveProfile(first.id);
    expect((await getActiveProfile())?.id).toBe(first.id);
  });

  it("deletes a profile and reassigns active if needed", async () => {
    const first = (await listProfiles())[0];
    const second = await createProfile({ display_name: "Other" });
    await setActiveProfile(second.id);
    await deleteProfile(second.id);
    const active = await getActiveProfile();
    expect(active?.id).toBe(first.id);
  });

  it("clears active pointer when last profile is deleted", async () => {
    const first = (await listProfiles())[0];
    await deleteProfile(first.id);
    // Calling listProfiles again seeds another default — but the
    // active pointer was cleared between, which is the invariant we
    // care about.
    expect(localStorage.getItem(KEY_ACTIVE_PROFILE)).toBe(null);
    expect(JSON.parse(localStorage.getItem(KEY_PROFILES)!)).toHaveLength(0);
  });

  it("rejects out-of-range level", async () => {
    const profiles = await listProfiles();
    const next = await updateProfile(profiles[0].id, { level: 99 });
    expect(next.level).toBe(null);
  });
});
