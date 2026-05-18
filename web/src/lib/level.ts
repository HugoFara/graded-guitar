// User's declared playing level, persisted in localStorage. No accounts
// at M4 (spec §7 defers identity to M5) — this is the only personalization
// signal the feed has, so it has to survive page reloads but doesn't
// need to survive a browser change.

const STORAGE_KEY = "gradedGuitar.level";
export const MIN_LEVEL = 1;
export const MAX_LEVEL = 10;

export function loadLevel(): number | null {
  if (typeof localStorage === "undefined") return null;
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  const n = parseInt(raw, 10);
  if (!Number.isFinite(n) || n < MIN_LEVEL || n > MAX_LEVEL) return null;
  return n;
}

export function saveLevel(level: number): void {
  if (typeof localStorage === "undefined") return;
  if (!Number.isFinite(level) || level < MIN_LEVEL || level > MAX_LEVEL) return;
  localStorage.setItem(STORAGE_KEY, String(Math.round(level)));
}

export function clearLevel(): void {
  if (typeof localStorage === "undefined") return;
  localStorage.removeItem(STORAGE_KEY);
}
