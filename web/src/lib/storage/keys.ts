// Storage keys for the M5 client-side scaffold. Centralized so the
// future backend migration can grep for "gradedGuitar." and find every
// place that needs to be reshaped. See decisions/0012-m5-local-accounts.md.
export const KEY_PROFILES = "gradedGuitar.profiles";
export const KEY_ACTIVE_PROFILE = "gradedGuitar.activeProfileId";
export const KEY_STATUS_PREFIX = "gradedGuitar.status.";
export const KEY_VOTES_PREFIX = "gradedGuitar.votes.";
// M8 practice takes (ADR 0018). Per-profile, which is what keeps the
// measurement record per-(player, piece).
export const KEY_TAKES_PREFIX = "gradedGuitar.takes.";
// Legacy M4 key; profileStore migrates this into the default profile.
export const KEY_LEGACY_LEVEL = "gradedGuitar.level";

export function statusKey(profileId: string): string {
  return `${KEY_STATUS_PREFIX}${profileId}`;
}

export function votesKey(profileId: string): string {
  return `${KEY_VOTES_PREFIX}${profileId}`;
}

export function takesKey(profileId: string): string {
  return `${KEY_TAKES_PREFIX}${profileId}`;
}
