// Profile store — M5 client-only "account" model. Profiles live in
// localStorage; every public function returns a Promise so the swap to
// a network-backed implementation later is implementation-only, not
// caller-only. See decisions/0012-m5-local-accounts.md.
import { MAX_LEVEL, MIN_LEVEL } from "../level";
import { KEY_ACTIVE_PROFILE, KEY_LEGACY_LEVEL, KEY_PROFILES } from "./keys";

export type Profile = {
  id: string;
  display_name: string;
  created_at: string;
  level: number | null;
};

export type ProfileInput = {
  display_name: string;
  level?: number | null;
};

function hasStorage(): boolean {
  return typeof localStorage !== "undefined";
}

function readProfiles(): Profile[] {
  if (!hasStorage()) return [];
  const raw = localStorage.getItem(KEY_PROFILES);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isProfile);
  } catch {
    return [];
  }
}

function writeProfiles(profiles: Profile[]): void {
  if (!hasStorage()) return;
  localStorage.setItem(KEY_PROFILES, JSON.stringify(profiles));
}

function isProfile(x: unknown): x is Profile {
  if (!x || typeof x !== "object") return false;
  const o = x as Record<string, unknown>;
  return (
    typeof o.id === "string" &&
    typeof o.display_name === "string" &&
    typeof o.created_at === "string" &&
    (o.level == null || typeof o.level === "number")
  );
}

function clampLevel(level: number | null | undefined): number | null {
  if (level == null) return null;
  if (!Number.isFinite(level)) return null;
  const n = Math.round(level);
  if (n < MIN_LEVEL || n > MAX_LEVEL) return null;
  return n;
}

// Generate a short, sortable, opaque id. We don't need cryptographic
// quality — collisions are vanishingly unlikely for a single browser's
// profile list and we never round-trip these ids to a server.
function newId(): string {
  const ts = Date.now().toString(36);
  const rand = Math.random().toString(36).slice(2, 8);
  return `p_${ts}_${rand}`;
}

// One-time migration: if the legacy M4 `gradedGuitar.level` key exists
// and no profiles do yet, create a default profile that absorbs it.
// Idempotent — safe to call on every load.
function ensureMigrated(): Profile[] {
  if (!hasStorage()) return [];
  let profiles = readProfiles();
  if (profiles.length > 0) return profiles;

  const legacy = localStorage.getItem(KEY_LEGACY_LEVEL);
  const legacyLevel = legacy != null ? clampLevel(parseInt(legacy, 10)) : null;

  const defaultProfile: Profile = {
    id: newId(),
    display_name: "You",
    created_at: new Date().toISOString(),
    level: legacyLevel,
  };
  profiles = [defaultProfile];
  writeProfiles(profiles);
  localStorage.setItem(KEY_ACTIVE_PROFILE, defaultProfile.id);
  if (legacy != null) localStorage.removeItem(KEY_LEGACY_LEVEL);
  return profiles;
}

export async function listProfiles(): Promise<Profile[]> {
  return ensureMigrated();
}

export async function getActiveProfile(): Promise<Profile | null> {
  const profiles = ensureMigrated();
  if (profiles.length === 0) return null;
  if (!hasStorage()) return profiles[0] ?? null;
  const activeId = localStorage.getItem(KEY_ACTIVE_PROFILE);
  const found = activeId ? profiles.find((p) => p.id === activeId) : null;
  return found ?? profiles[0] ?? null;
}

export async function setActiveProfile(id: string): Promise<void> {
  if (!hasStorage()) return;
  const profiles = ensureMigrated();
  if (!profiles.some((p) => p.id === id)) {
    throw new Error(`profile not found: ${id}`);
  }
  localStorage.setItem(KEY_ACTIVE_PROFILE, id);
}

export async function createProfile(input: ProfileInput): Promise<Profile> {
  const name = input.display_name.trim();
  if (!name) throw new Error("display_name required");
  const profiles = ensureMigrated();
  const profile: Profile = {
    id: newId(),
    display_name: name,
    created_at: new Date().toISOString(),
    level: clampLevel(input.level ?? null),
  };
  profiles.push(profile);
  writeProfiles(profiles);
  return profile;
}

export async function updateProfile(
  id: string,
  patch: Partial<ProfileInput>,
): Promise<Profile> {
  const profiles = ensureMigrated();
  const i = profiles.findIndex((p) => p.id === id);
  if (i < 0) throw new Error(`profile not found: ${id}`);
  const next: Profile = { ...profiles[i] };
  if (patch.display_name != null) {
    const name = patch.display_name.trim();
    if (!name) throw new Error("display_name required");
    next.display_name = name;
  }
  if (patch.level !== undefined) {
    next.level = clampLevel(patch.level);
  }
  profiles[i] = next;
  writeProfiles(profiles);
  return next;
}

// Deletes the profile and its status records. If the deleted profile
// was active, the active pointer moves to the first remaining profile
// (or clears, if none remain). Status data lives under a separate key
// (see ./status.ts); this module only handles its own data, plus the
// active pointer because that's a foreign key into this table.
export async function deleteProfile(id: string): Promise<void> {
  if (!hasStorage()) return;
  const profiles = ensureMigrated();
  const remaining = profiles.filter((p) => p.id !== id);
  if (remaining.length === profiles.length) return;
  writeProfiles(remaining);
  const activeId = localStorage.getItem(KEY_ACTIVE_PROFILE);
  if (activeId === id) {
    if (remaining.length > 0) {
      localStorage.setItem(KEY_ACTIVE_PROFILE, remaining[0].id);
    } else {
      localStorage.removeItem(KEY_ACTIVE_PROFILE);
    }
  }
}

// Sync helpers for components that read the active profile on every
// render (header chip, feed mount). These are safe because the
// localStorage backing is sync; they exist alongside the async API so
// the future server-backed implementation can keep the async surface
// while sync callers move to $effect/Svelte stores. Internal use only.
export function getActiveProfileSync(): Profile | null {
  if (!hasStorage()) return null;
  const profiles = ensureMigrated();
  if (profiles.length === 0) return null;
  const activeId = localStorage.getItem(KEY_ACTIVE_PROFILE);
  return (activeId ? profiles.find((p) => p.id === activeId) : null) ?? profiles[0];
}

export function setActiveLevelSync(level: number | null): void {
  if (!hasStorage()) return;
  const active = getActiveProfileSync();
  if (!active) return;
  const profiles = readProfiles();
  const i = profiles.findIndex((p) => p.id === active.id);
  if (i < 0) return;
  profiles[i] = { ...profiles[i], level: clampLevel(level) };
  writeProfiles(profiles);
}
