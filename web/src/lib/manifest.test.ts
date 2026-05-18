import { describe, expect, it } from "vitest";
import {
  applyFilters,
  gradeAsInt,
  isDummySource,
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
});

const baseFilters = (over: Partial<Filters> = {}): Filters => ({
  query: "",
  minGrade: null,
  maxGrade: null,
  source: "all",
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
});
