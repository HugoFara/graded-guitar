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
import {
  exportVotes,
  importVotes,
  type VoteExport,
} from "./votes";

// Envelope versions:
//   v1 — statuses only, no grade snapshot fields
//   v2 — statuses with optional snapshot fields (ADR 0013)
//   v3 — adds the grade-disagreement votes sub-payload (ADR 0013 follow-up)
// Older imports are still accepted; missing payloads default to empty.
export type ProfileBackup = {
  version: 1 | 2 | 3;
  exported_at: string;
  profile: {
    display_name: string;
    level: number | null;
    created_at: string;
  };
  statuses: StatusExport;
  votes?: VoteExport;
};

export async function exportProfile(p: Profile): Promise<ProfileBackup> {
  return {
    version: 3,
    exported_at: new Date().toISOString(),
    profile: {
      display_name: p.display_name,
      level: p.level,
      created_at: p.created_at,
    },
    statuses: await exportStatuses(p.id),
    votes: await exportVotes(p.id),
  };
}

export type ImportResult = {
  profile: Profile;
  imported: number;
  skipped: number;
  votes_imported: number;
  votes_skipped: number;
};

// Importing creates a NEW profile (never overwrites an existing one)
// so users can't accidentally clobber their current library by loading
// an old backup. Caller can rename / activate afterward.
export async function importProfile(
  payload: ProfileBackup,
): Promise<ImportResult> {
  if (
    !payload
    || (payload.version !== 1 && payload.version !== 2 && payload.version !== 3)
  ) {
    throw new Error("unsupported backup version");
  }
  const profile = await createProfile({
    display_name: payload.profile.display_name || "Imported",
    level: payload.profile.level ?? null,
  });
  const statusResult = await importStatuses(profile.id, payload.statuses);
  let votesImported = 0;
  let votesSkipped = 0;
  if (payload.votes) {
    const voteResult = await importVotes(profile.id, payload.votes);
    votesImported = voteResult.imported;
    votesSkipped = voteResult.skipped;
  }
  return {
    profile,
    imported: statusResult.imported,
    skipped: statusResult.skipped,
    votes_imported: votesImported,
    votes_skipped: votesSkipped,
  };
}

export function backupFilename(p: Profile): string {
  const slug = p.display_name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const date = new Date().toISOString().slice(0, 10);
  return `graded-guitar-${slug || "profile"}-${date}.json`;
}
