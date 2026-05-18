// Declared playing level. Stored on the active profile (M5); see
// decisions/0012-m5-local-accounts.md. The sync API here exists for
// hot paths in components (header chip, feed mount); canonical reads
// and writes go through the profile store.
import { getActiveProfileSync, setActiveLevelSync } from "./storage/profile";

export const MIN_LEVEL = 1;
export const MAX_LEVEL = 10;

export function loadLevel(): number | null {
  return getActiveProfileSync()?.level ?? null;
}

export function saveLevel(level: number): void {
  if (!Number.isFinite(level) || level < MIN_LEVEL || level > MAX_LEVEL) return;
  setActiveLevelSync(Math.round(level));
}

export function clearLevel(): void {
  setActiveLevelSync(null);
}
