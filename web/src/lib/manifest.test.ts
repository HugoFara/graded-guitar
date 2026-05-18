import { describe, expect, it } from "vitest";
import {
  applyFilters,
  buildFeed,
  gradeAsInt,
  isDummySource,
  listComposers,
  resolveGrade,
  type Filters,
  type Piece,
} from "./manifest";
import { parseTransposeSemitones } from "./player";

const make = (over: Partial<Piece> & { cid: string }): Piece => ({
  candidate_id: over.cid,
  source: over.source ?? "github",
  file_url: "",
  normalized_path: "",
  format: "musicxml",
  license: "unknown",
  parts: 1,
  metadata: {
    title: over.metadata?.title ?? "Untitled",
    composer: over.metadata?.composer ?? "Anon",
    ...over.metadata,
  },
  grade: over.grade,
  grade_source: over.grade_source,
  model_grade: over.model_grade,
  model_grade_source: over.model_grade_source,
  duration_seconds: over.duration_seconds,
  era: over.era,
});

const baseFilters = (over: Partial<Filters> = {}): Filters => ({
  query: "",
  minGrade: null,
  maxGrade: null,
  source: "all",
  composer: "",
  era: "all",
  maxDurationSeconds: null,
  ...over,
});

describe("resolveGrade", () => {
  it("prefers curator grade over model grade", () => {
    const p = make({
      cid: "a",
      grade: "5",
      grade_source: "delcamp",
      model_grade: "7",
      model_grade_source: "dummy-v0",
    });
    const r = resolveGrade(p);
    expect(r.kind).toBe("curator");
    if (r.kind === "curator") {
      expect(r.grade).toBe("5");
      expect(r.source).toBe("delcamp");
    }
  });

  it("falls back to model grade when curator absent", () => {
    const p = make({ cid: "b", model_grade: "3", model_grade_source: "dummy-v0" });
    const r = resolveGrade(p);
    expect(r.kind).toBe("model");
    if (r.kind === "model") expect(r.source).toBe("dummy-v0");
  });

  it("returns none when neither grade is set", () => {
    const p = make({ cid: "c" });
    expect(resolveGrade(p).kind).toBe("none");
  });
});

describe("isDummySource", () => {
  it("detects dummy-* prefixes", () => {
    expect(isDummySource("dummy-v0")).toBe(true);
    expect(isDummySource("dummy-advisor-v0")).toBe(true);
    expect(isDummySource("m2-v1@abc123")).toBe(false);
    expect(isDummySource("delcamp")).toBe(false);
  });
});

describe("gradeAsInt", () => {
  it("parses well-formed integers", () => {
    expect(gradeAsInt("3")).toBe(3);
    expect(gradeAsInt("10")).toBe(10);
  });
  it("returns null for invalid input", () => {
    expect(gradeAsInt(undefined)).toBeNull();
    expect(gradeAsInt("")).toBeNull();
    expect(gradeAsInt("abc")).toBeNull();
  });
});

describe("parseTransposeSemitones", () => {
  it("reads the guitar 8va-bassa convention", () => {
    const xml = `<transpose>
      <diatonic>0</diatonic>
      <chromatic>0</chromatic>
      <octave-change>-1</octave-change>
    </transpose>`;
    expect(parseTransposeSemitones(xml)).toBe(-12);
  });

  it("combines chromatic + octave-change", () => {
    const xml = `<transpose>
      <chromatic>2</chromatic>
      <octave-change>-1</octave-change>
    </transpose>`;
    expect(parseTransposeSemitones(xml)).toBe(-10);
  });

  it("returns 0 when the file has no transpose declaration", () => {
    expect(parseTransposeSemitones("<score-partwise>no transpose here</score-partwise>")).toBe(0);
  });

  it("ignores missing chromatic or octave-change children", () => {
    expect(parseTransposeSemitones("<transpose></transpose>")).toBe(0);
    expect(parseTransposeSemitones("<transpose><chromatic>3</chromatic></transpose>")).toBe(3);
  });

  it("uses the first transpose declaration on multi-part files", () => {
    const xml = `
      <transpose><octave-change>-1</octave-change></transpose>
      <transpose><octave-change>-2</octave-change></transpose>
    `;
    expect(parseTransposeSemitones(xml)).toBe(-12);
  });
});

describe("applyFilters", () => {
  const pieces = [
    make({ cid: "a", grade: "3", grade_source: "delcamp", metadata: { title: "Adelita", composer: "Tárrega" } }),
    make({ cid: "b", model_grade: "5", model_grade_source: "dummy-v0", metadata: { title: "Etude", composer: "Sor" } }),
    make({ cid: "c", grade: "7", grade_source: "delcamp", metadata: { title: "Capricho", composer: "Tárrega" } }),
    make({ cid: "d", metadata: { title: "Unknown", composer: "Anon" } }),
  ];

  it("returns all by default", () => {
    expect(applyFilters(pieces, baseFilters())).toHaveLength(4);
  });

  it("filters by text query against title+composer", () => {
    const out = applyFilters(pieces, baseFilters({ query: "tárrega" }));
    expect(out.map((p) => p.candidate_id).sort()).toEqual(["a", "c"]);
  });

  it("filters by min grade", () => {
    const out = applyFilters(pieces, baseFilters({ minGrade: 5 }));
    expect(out.map((p) => p.candidate_id).sort()).toEqual(["b", "c"]);
  });

  it("filters by max grade", () => {
    const out = applyFilters(pieces, baseFilters({ maxGrade: 5 }));
    expect(out.map((p) => p.candidate_id).sort()).toEqual(["a", "b"]);
  });

  it("source=curator hides model-only pieces", () => {
    const out = applyFilters(pieces, baseFilters({ source: "curator" }));
    expect(out.map((p) => p.candidate_id).sort()).toEqual(["a", "c"]);
  });

  it("source=model hides curator-only pieces", () => {
    const out = applyFilters(pieces, baseFilters({ source: "model" }));
    expect(out.map((p) => p.candidate_id).sort()).toEqual(["b"]);
  });

  it("min/max grade excludes ungraded pieces", () => {
    const out = applyFilters(pieces, baseFilters({ minGrade: 1, maxGrade: 10 }));
    expect(out.map((p) => p.candidate_id).sort()).toEqual(["a", "b", "c"]);
  });

  it("filters by era when set", () => {
    const erased = [
      make({ cid: "x", era: "renaissance", metadata: { title: "T", composer: "Dowland" } }),
      make({ cid: "y", era: "classical", metadata: { title: "T", composer: "Sor" } }),
    ];
    const out = applyFilters(erased, baseFilters({ era: "renaissance" }));
    expect(out.map((p) => p.candidate_id)).toEqual(["x"]);
  });

  it("filters by composer substring", () => {
    const out = applyFilters(pieces, baseFilters({ composer: "sor" }));
    expect(out.map((p) => p.candidate_id)).toEqual(["b"]);
  });

  it("max duration excludes longer pieces and those with no duration", () => {
    const timed = [
      make({ cid: "short", duration_seconds: 60 }),
      make({ cid: "long", duration_seconds: 600 }),
      make({ cid: "unknown" }),
    ];
    const out = applyFilters(timed, baseFilters({ maxDurationSeconds: 120 }));
    expect(out.map((p) => p.candidate_id)).toEqual(["short"]);
  });

  it("combines composer + era + grade filters", () => {
    const mixed = [
      make({ cid: "1", grade: "5", grade_source: "delcamp", era: "renaissance", metadata: { title: "T", composer: "Dowland" } }),
      make({ cid: "2", grade: "5", grade_source: "delcamp", era: "classical", metadata: { title: "T", composer: "Sor" } }),
      make({ cid: "3", grade: "7", grade_source: "delcamp", era: "renaissance", metadata: { title: "T", composer: "Dowland" } }),
    ];
    const out = applyFilters(
      mixed,
      baseFilters({ era: "renaissance", composer: "Dowland", minGrade: 1, maxGrade: 6 }),
    );
    expect(out.map((p) => p.candidate_id)).toEqual(["1"]);
  });
});

describe("listComposers", () => {
  it("returns unique composers with counts, sorted alphabetically", () => {
    const pieces = [
      make({ cid: "a", metadata: { title: "T1", composer: "Sor", composer_normalized: "Sor" } }),
      make({ cid: "b", metadata: { title: "T2", composer: "Sor", composer_normalized: "Sor" } }),
      make({ cid: "c", metadata: { title: "T3", composer: "Tárrega", composer_normalized: "Tárrega" } }),
    ];
    expect(listComposers(pieces)).toEqual([
      { composer: "Sor", count: 2 },
      { composer: "Tárrega", count: 1 },
    ]);
  });
});

describe("buildFeed", () => {
  const piece = (cid: string, composer: string, title: string, grade: string) =>
    make({
      cid,
      grade,
      grade_source: "delcamp",
      metadata: { title, composer, composer_normalized: composer },
    });

  it("includes level and level+1, excludes others", () => {
    const pieces = [
      piece("a", "X", "T1", "3"),
      piece("b", "X", "T2", "4"),
      piece("c", "X", "T3", "5"),
      piece("d", "X", "T4", "2"),
    ];
    const out = buildFeed(pieces, 3);
    expect(out.map((p) => p.candidate_id).sort()).toEqual(["a", "b"]);
  });

  it("round-robins across composers so one doesn't dominate the head", () => {
    const pieces = [
      piece("a1", "A", "T1", "5"),
      piece("a2", "A", "T2", "5"),
      piece("a3", "A", "T3", "5"),
      piece("b1", "B", "T1", "5"),
      piece("c1", "C", "T1", "5"),
    ];
    const out = buildFeed(pieces, 5, { cap: 4 });
    // First pass: one from each (A is biggest so first)
    expect(out.slice(0, 3).map((p) => p.metadata.composer).sort()).toEqual([
      "A",
      "B",
      "C",
    ]);
  });

  it("respects the cap", () => {
    const pieces = Array.from({ length: 50 }, (_, i) =>
      piece(`p${i}`, `C${i % 5}`, `T${i}`, "4"),
    );
    expect(buildFeed(pieces, 4, { cap: 10 })).toHaveLength(10);
  });

  it("excludes pieces marked too_hard or not_for_me", () => {
    const pieces = [
      piece("a", "X", "T1", "5"),
      piece("b", "X", "T2", "5"),
      piece("c", "X", "T3", "5"),
    ];
    const out = buildFeed(pieces, 5, {
      statuses: { a: "too_hard", b: "not_for_me" },
    });
    expect(out.map((p) => p.candidate_id)).toEqual(["c"]);
  });

  it("sinks completed pieces to the bottom of their bucket", () => {
    const pieces = [
      piece("a", "X", "Apple", "5"),
      piece("b", "X", "Banana", "5"),
      piece("c", "X", "Cherry", "5"),
    ];
    const out = buildFeed(pieces, 5, { statuses: { a: "completed" } });
    expect(out.map((p) => p.metadata.title)).toEqual(["Banana", "Cherry", "Apple"]);
  });

  it("downranks composers with 2+ too_hard pieces", () => {
    const pieces = [
      piece("x1", "X", "T1", "5"),
      piece("x2", "X", "T2", "5"),
      piece("x3", "X", "T3", "5"),
      piece("x4", "X", "T4", "5"),
      piece("y1", "Y", "T1", "5"),
      piece("y2", "Y", "T2", "5"),
    ];
    // X has 2 too_hard marks → bucket sinks below Y's even though X
    // still has more remaining pieces.
    const out = buildFeed(pieces, 5, {
      statuses: { x1: "too_hard", x2: "too_hard" },
      cap: 4,
    });
    // First pick should be from Y (regular bucket), not from X
    // (downranked bucket).
    expect(out[0].metadata.composer).toBe("Y");
  });

  it("a single too_hard does not downrank the composer (only 2+)", () => {
    const pieces = [
      piece("x1", "X", "T1", "5"),
      piece("x2", "X", "T2", "5"),
      piece("x3", "X", "T3", "5"),
      piece("y1", "Y", "T1", "5"),
    ];
    const out = buildFeed(pieces, 5, { statuses: { x1: "too_hard" } });
    // X is still bigger and not downranked, so first pick from X.
    expect(out[0].metadata.composer).toBe("X");
  });

  it("returns empty array for level with no pieces", () => {
    const pieces = [piece("a", "X", "T", "3")];
    expect(buildFeed(pieces, 9)).toEqual([]);
  });

  it("sorts pieces within a composer bucket by title", () => {
    const pieces = [
      piece("a", "X", "Zebra", "5"),
      piece("b", "X", "Apple", "5"),
      piece("c", "X", "Mango", "5"),
    ];
    const out = buildFeed(pieces, 5);
    expect(out.map((p) => p.metadata.title)).toEqual(["Apple", "Mango", "Zebra"]);
  });

  it("caps any one composer at perComposerCap when variety allows", () => {
    // Horetzky-style skew: one composer dominates the bucket, plus
    // enough other composers that the cap doesn't have to relax to
    // fill the feed.
    const pieces = [
      ...Array.from({ length: 30 }, (_, i) =>
        piece(`h${i}`, "Horetzky", `T${i}`, "5"),
      ),
      ...Array.from({ length: 15 }, (_, i) =>
        piece(`o${i}`, `Other${i}`, `T${i}`, "5"),
      ),
    ];
    // 16 composers × 3 perComposerCap = 48 >= cap=20, so the cap
    // applies as-is rather than relaxing.
    const out = buildFeed(pieces, 5, { cap: 20, perComposerCap: 3 });
    const counts = new Map<string, number>();
    for (const p of out) {
      const c = p.metadata.composer;
      counts.set(c, (counts.get(c) ?? 0) + 1);
    }
    expect(counts.get("Horetzky")).toBe(3);
  });

  it("relaxes perComposerCap when there isn't enough variety", () => {
    // Only 2 composers, cap=10, perComposerCap=3 by default. If we
    // applied the literal 3-per-composer cap we'd only fill 6 slots
    // — but the user asked for 10. The cap should relax.
    const pieces = [
      ...Array.from({ length: 8 }, (_, i) => piece(`a${i}`, "A", `T${i}`, "5")),
      ...Array.from({ length: 8 }, (_, i) => piece(`b${i}`, "B", `T${i}`, "5")),
    ];
    const out = buildFeed(pieces, 5, { cap: 10 });
    expect(out).toHaveLength(10);
  });
});
