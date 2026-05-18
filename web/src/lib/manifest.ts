export type Piece = {
  candidate_id: string;
  source: string;
  file_url: string;
  page_url?: string;
  normalized_path: string;
  format: string;
  license: string;
  license_spdx?: string;
  parts: number;
  metadata: {
    title: string;
    composer: string;
    composer_normalized?: string;
    key_fifths?: string;
    opus?: string;
  };
  grade?: string;
  grade_source?: string;
  model_grade?: string;
  model_grade_source?: string;
  duration_seconds?: number;
  era?: Era;
};

export type Era =
  | "renaissance"
  | "baroque"
  | "classical"
  | "romantic"
  | "modern"
  | "traditional"
  | "unknown";

export const ERAS: Era[] = [
  "renaissance",
  "baroque",
  "classical",
  "romantic",
  "modern",
  "traditional",
  "unknown",
];

export type Manifest = {
  pieces: Piece[];
};

let cached: Promise<Manifest> | null = null;

export function loadManifest(): Promise<Manifest> {
  if (!cached) {
    cached = fetch(`${import.meta.env.BASE_URL}manifest.json`).then((r) => {
      if (!r.ok) throw new Error(`manifest.json: ${r.status}`);
      return r.json();
    });
  }
  return cached;
}

export type ResolvedGrade =
  | { kind: "curator"; grade: string; source: string }
  | { kind: "model"; grade: string; source: string }
  | { kind: "none" };

export function resolveGrade(p: Piece): ResolvedGrade {
  if (p.grade) {
    return { kind: "curator", grade: p.grade, source: p.grade_source ?? "curator" };
  }
  if (p.model_grade) {
    return {
      kind: "model",
      grade: p.model_grade,
      source: p.model_grade_source ?? "model",
    };
  }
  return { kind: "none" };
}

export function isDummySource(source: string): boolean {
  return source.startsWith("dummy-");
}

// Mirrors web/scripts/copy-corpus.mjs `safeName()`: files with `#` in
// their name break Vite preview's SPA fallback (it treats %23 as a
// fragment), so the copy step renames `#` → `--` and we do the same
// when resolving URLs.
function safeFilename(name: string): string {
  return name.replaceAll("#", "--");
}

export function musicxmlUrl(p: Piece): string {
  const base = (import.meta.env.BASE_URL ?? "/").replace(/\/$/, "");
  const filename = safeFilename(p.normalized_path.replace(/^corpus\/normalized\//, ""));
  return `${base}/musicxml/${encodeURIComponent(filename)}`;
}

export function pieceById(manifest: Manifest, cid: string): Piece | undefined {
  return manifest.pieces.find((p) => p.candidate_id === cid);
}

export function formatDuration(seconds: number | undefined): string {
  if (seconds == null || !Number.isFinite(seconds) || seconds <= 0) return "—";
  const total = Math.round(seconds);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function gradeAsInt(g: string | undefined): number | null {
  if (!g) return null;
  const n = parseInt(g, 10);
  return Number.isFinite(n) ? n : null;
}

export type Filters = {
  query: string;
  minGrade: number | null;
  maxGrade: number | null;
  source: "all" | "curator" | "model";
  composer: string;
  era: Era | "all";
  maxDurationSeconds: number | null;
};

// Per-piece status from the M5 status store, treated as a string here
// to avoid a module cycle. Valid values match storage/status.ts; an
// unknown string is treated the same as "not_seen".
export type FeedStatuses = Record<string, string>;

export type FeedOptions = {
  statuses?: FeedStatuses;
  cap?: number;
  // Hard ceiling on how many pieces any one composer can contribute
  // to the feed. Defends against the "wall of Horetzky" effect — one
  // composer with 120 pieces dominating a feed even after round-robin
  // when smaller buckets exhaust. Defaults to 3.
  //
  // The cap relaxes automatically when there isn't enough variety to
  // fill `cap` at the requested per-composer ceiling — otherwise a
  // bucket with only 2 composers and cap=20 would underfill to 6.
  perComposerCap?: number;
};

// Composers with this many "too_hard" pieces by the user get pushed
// to the bottom of the bucket order. Below the threshold we trust a
// single "too_hard" might be specific to that piece, not the composer.
const TOO_HARD_COMPOSER_THRESHOLD = 2;

// Build the M4 feed for a declared level: pieces at the target grade
// and one above, round-robined across composer buckets so a prolific
// composer (Horetzky alone has 120 pieces) doesn't dominate the page.
// M5 status signals layered on top:
//   - too_hard / not_for_me on a piece → exclude
//   - too_hard on N≥2 pieces by the same composer → bucket pushed to
//     the bottom of the round-robin order
//   - completed → still shown but sorted to the bottom of its bucket
//   - playing → no effect on the feed; library view uses it instead
// Within each bucket pieces are otherwise sorted by title for
// determinism. See decisions/0012-m5-local-accounts.md.
export function buildFeed(
  pieces: Piece[],
  level: number,
  opts: FeedOptions = {},
): Piece[] {
  const statuses = opts.statuses ?? {};
  const cap = opts.cap ?? 30;
  const targets = new Set([level, level + 1]);
  const matching = pieces.filter((p) => {
    const s = statuses[p.candidate_id];
    if (s === "too_hard" || s === "not_for_me") return false;
    const r = resolveGrade(p);
    if (r.kind === "none") return false;
    const g = gradeAsInt(r.grade);
    return g != null && targets.has(g);
  });

  const buckets = new Map<string, Piece[]>();
  for (const p of matching) {
    const composer =
      p.metadata.composer_normalized || p.metadata.composer || "?";
    if (!buckets.has(composer)) buckets.set(composer, []);
    buckets.get(composer)!.push(p);
  }
  for (const list of buckets.values()) {
    list.sort((a, b) => {
      // Completed pieces sink to the bottom of their bucket so fresh
      // suggestions surface first; ties break on title.
      const ca = statuses[a.candidate_id] === "completed" ? 1 : 0;
      const cb = statuses[b.candidate_id] === "completed" ? 1 : 0;
      if (ca !== cb) return ca - cb;
      return a.metadata.title.localeCompare(b.metadata.title);
    });
  }

  // Composer order: bucket priority is "regular" first, then "downranked"
  // (= ≥2 too_hard pieces from this composer). Within each tier, the
  // bigger bucket goes first so popular composers anchor the top.
  const tooHardByComposer = new Map<string, number>();
  for (const p of pieces) {
    if (statuses[p.candidate_id] !== "too_hard") continue;
    const composer =
      p.metadata.composer_normalized || p.metadata.composer || "?";
    tooHardByComposer.set(composer, (tooHardByComposer.get(composer) ?? 0) + 1);
  }
  const composers = [...buckets.keys()].sort((a, b) => {
    const aDown = (tooHardByComposer.get(a) ?? 0) >= TOO_HARD_COMPOSER_THRESHOLD;
    const bDown = (tooHardByComposer.get(b) ?? 0) >= TOO_HARD_COMPOSER_THRESHOLD;
    if (aDown !== bDown) return aDown ? 1 : -1;
    return buckets.get(b)!.length - buckets.get(a)!.length;
  });

  const perCap = Math.max(
    opts.perComposerCap ?? 3,
    Math.ceil(cap / Math.max(composers.length, 1)),
  );
  const out: Piece[] = [];
  let pass = 0;
  while (out.length < cap) {
    let added = 0;
    for (const c of composers) {
      const list = buckets.get(c)!;
      if (pass < list.length && pass < perCap) {
        out.push(list[pass]);
        added++;
        if (out.length >= cap) break;
      }
    }
    if (added === 0) break;
    pass++;
  }
  return out;
}

export function applyFilters(pieces: Piece[], f: Filters): Piece[] {
  const q = f.query.trim().toLowerCase();
  const composerNeedle = f.composer.trim().toLowerCase();
  return pieces.filter((p) => {
    if (q) {
      const hay = `${p.metadata.title} ${p.metadata.composer}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    if (composerNeedle) {
      const composer = (
        p.metadata.composer_normalized || p.metadata.composer
      ).toLowerCase();
      if (!composer.includes(composerNeedle)) return false;
    }
    if (f.era !== "all" && p.era !== f.era) return false;
    if (
      f.maxDurationSeconds != null &&
      (p.duration_seconds == null || p.duration_seconds > f.maxDurationSeconds)
    ) {
      return false;
    }
    const r = resolveGrade(p);
    if (f.source === "curator" && r.kind !== "curator") return false;
    if (f.source === "model" && r.kind !== "model") return false;
    if (f.minGrade != null || f.maxGrade != null) {
      const g = r.kind === "none" ? null : gradeAsInt(r.grade);
      if (g == null) return false;
      if (f.minGrade != null && g < f.minGrade) return false;
      if (f.maxGrade != null && g > f.maxGrade) return false;
    }
    return true;
  });
}

// Composer list for the autocomplete: every distinct
// composer_normalized (with a fallback to composer) plus how many
// pieces each appears in. Caller usually wants alpha order; we leave
// counts in so the UI can rank popular composers if it wants.
export function listComposers(
  pieces: Piece[],
): { composer: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const p of pieces) {
    const c = p.metadata.composer_normalized || p.metadata.composer || "?";
    counts.set(c, (counts.get(c) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([composer, count]) => ({ composer, count }))
    .sort((a, b) => a.composer.localeCompare(b.composer));
}
