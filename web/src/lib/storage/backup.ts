// Per-profile JSON backup — the wire format we'll use to migrate from
// local-only storage to a hosted backend later. Keep this stable; if
// you need to evolve the shape, bump `version` and write a migrator.
// See decisions/0012-m5-local-accounts.md.
import {
  createProfile,
  type Profile,
} from "./profile";
import {
  exportStatuses,
  importStatuses,
  type StatusExport,
} from "./status";

// v2 carries status records that may include the grade snapshot
// fields (grade_at_record / grade_source_at_record) — see status.ts.
// v1 backups are still accepted; their records simply have no
// snapshot. The envelope version tracks the backup payload as a
// whole; the statuses sub-payload has its own version.
export type ProfileBackup = {
  version: 1 | 2;
  exported_at: string;
  profile: {
    display_name: string;
    level: number | null;
    created_at: string;
  };
  statuses: StatusExport;
};

export async function exportProfile(p: Profile): Promise<ProfileBackup> {
  return {
    version: 2,
    exported_at: new Date().toISOString(),
    profile: {
      display_name: p.display_name,
      level: p.level,
      created_at: p.created_at,
    },
    statuses: await exportStatuses(p.id),
  };
}

// Importing creates a NEW profile (never overwrites an existing one)
// so users can't accidentally clobber their current library by loading
// an old backup. Caller can rename / activate afterward.
export async function importProfile(
  payload: ProfileBackup,
): Promise<{ profile: Profile; imported: number; skipped: number }> {
  if (!payload || (payload.version !== 1 && payload.version !== 2)) {
    throw new Error("unsupported backup version");
  }
  const profile = await createProfile({
    display_name: payload.profile.display_name || "Imported",
    level: payload.profile.level ?? null,
  });
  const result = await importStatuses(profile.id, payload.statuses);
  return { profile, ...result };
}

export function backupFilename(p: Profile): string {
  const slug = p.display_name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const date = new Date().toISOString().slice(0, 10);
  return `graded-guitar-${slug || "profile"}-${date}.json`;
}
