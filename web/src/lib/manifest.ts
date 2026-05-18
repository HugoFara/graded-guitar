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
};

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
};

export function applyFilters(pieces: Piece[], f: Filters): Piece[] {
  const q = f.query.trim().toLowerCase();
  return pieces.filter((p) => {
    if (q) {
      const hay = `${p.metadata.title} ${p.metadata.composer}`.toLowerCase();
      if (!hay.includes(q)) return false;
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
