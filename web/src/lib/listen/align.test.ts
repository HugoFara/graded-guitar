import { describe, it, expect } from "vitest";
import { buildReference, type BarSpan, type NoteEvent } from "./reference";
import { TempoMap } from "./tempo";
import { synthesizePerformance, type Perturbation } from "./synth";
import { viterbiAlign, OnlineFollower, decimateFrames } from "./align";
import { FEATURE_DIM } from "./chroma";

const TPQ = 960;
const BEATS_PER_BAR = 4;
const BAR_TICKS = TPQ * BEATS_PER_BAR;
const BARS = 16;

// A sustaining bass note under a moving upper line — the texture most
// of the corpus actually has. A single-line fixture would make every
// frame a bare pitch class and overstate how distinguishable real
// reference frames are.
function buildTestReference() {
  const notes: NoteEvent[] = [];
  const bars: BarSpan[] = [];
  for (let b = 0; b < BARS; b++) {
    bars.push({ startTick: b * BAR_TICKS, durationTicks: BAR_TICKS });
    notes.push({
      startTick: b * BAR_TICKS,
      endTick: (b + 1) * BAR_TICKS,
      midi: 40 + ((b * 5) % 12),
    });
    for (let q = 0; q < BEATS_PER_BAR; q++) {
      const t = b * BAR_TICKS + q * TPQ;
      notes.push({ startTick: t, endTick: t + TPQ, midi: 60 + ((b * 3 + q * 2) % 12) });
    }
  }
  const tempo = new TempoMap(TPQ, [{ tick: 0, bpm: 120 }]);
  return buildReference(notes, bars, tempo);
}

// Bar error at every live frame the player was actually sounding.
// Silent frames are excluded: the aligner has no positional evidence
// there and is not scored on guessing.
function barErrors(
  ref: ReturnType<typeof buildTestReference>,
  path: Int32Array,
  truth: Int32Array,
): number[] {
  const out: number[] = [];
  for (let t = 0; t < truth.length; t++) {
    if (truth[t] < 0) continue;
    const got = ref.barOfFrame[path[t]];
    const want = ref.barOfFrame[truth[t]];
    if (got < 0 || want < 0) continue;
    out.push(Math.abs(got - want));
  }
  return out;
}

function quantile(values: number[], q: number): number {
  if (!values.length) return NaN;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))];
}

// Longest run of a constant reference position in the recovered path —
// where the aligner thinks the player stalled.
function longestHold(path: Int32Array): { refFrame: number; length: number } {
  let best = { refFrame: path[0] ?? 0, length: 0 };
  let runStart = 0;
  for (let t = 1; t <= path.length; t++) {
    if (t === path.length || path[t] !== path[runStart]) {
      const length = t - runStart;
      if (length > best.length) best = { refFrame: path[runStart], length };
      runStart = t;
    }
  }
  return best;
}

// Largest backward move in the recovered path — where the aligner
// thinks the player went back and started again.
function largestBackJump(path: Int32Array): { at: number; from: number; to: number; size: number } {
  let best = { at: 0, from: 0, to: 0, size: 0 };
  for (let t = 1; t < path.length; t++) {
    const size = path[t - 1] - path[t];
    if (size > best.size) best = { at: t, from: path[t - 1], to: path[t], size };
  }
  return best;
}

describe("reference construction", () => {
  const ref = buildTestReference();

  it("covers the whole score at the declared frame rate", () => {
    // 16 bars of 4 beats at 120bpm = 32 seconds.
    expect(ref.durationMs).toBeCloseTo(32000, -1);
    expect(ref.frameCount).toBe(Math.ceil(32000 / 50));
    expect(ref.barCount).toBe(BARS);
  });

  it("normalizes every sounding frame", () => {
    let sounding = 0;
    for (let f = 0; f < ref.frameCount; f++) {
      let ss = 0;
      for (let c = 0; c < FEATURE_DIM; c++) {
        ss += ref.frames[f * FEATURE_DIM + c] ** 2;
      }
      if (ss > 0) {
        sounding++;
        expect(Math.sqrt(ss)).toBeCloseTo(1, 5);
      }
    }
    expect(sounding).toBe(ref.frameCount);
  });

  it("assigns frames to bars monotonically", () => {
    let last = -1;
    for (let f = 0; f < ref.frameCount; f++) {
      const b = ref.barOfFrame[f];
      if (b < 0) continue;
      expect(b).toBeGreaterThanOrEqual(last);
      last = b;
    }
    expect(last).toBe(BARS - 1);
  });
});

describe("viterbi alignment — spec M8 stop condition", () => {
  const ref = buildTestReference();

  it("tracks a clean performance", () => {
    const { live, truth } = synthesizePerformance(ref, []);
    const { path } = viterbiAlign(ref, live);
    const errors = barErrors(ref, path, truth);
    expect(Math.max(...errors)).toBeLessThanOrEqual(1);
    expect(quantile(errors, 0.95)).toBe(0);
  });

  it("localizes an injected hesitation to within one bar", () => {
    // Stall for 3 seconds in the middle of bar 8.
    const atRefFrame = ref.barFirstFrame[8] + 10;
    const perturbations: Perturbation[] = [
      { kind: "hesitate", atRefFrame, frames: 60 },
    ];
    const { live, truth } = synthesizePerformance(ref, perturbations);
    const { path } = viterbiAlign(ref, live);

    expect(Math.max(...barErrors(ref, path, truth))).toBeLessThanOrEqual(1);

    const hold = longestHold(path);
    expect(hold.length).toBeGreaterThan(30);
    expect(Math.abs(ref.barOfFrame[hold.refFrame] - 8)).toBeLessThanOrEqual(1);
  });

  it("follows a tempo change without losing the bar", () => {
    // Bars 4 through 10 played at half the written tempo.
    const perturbations: Perturbation[] = [
      {
        kind: "tempo",
        fromRefFrame: ref.barFirstFrame[4],
        toRefFrame: ref.barFirstFrame[10],
        ratio: 0.5,
      },
    ];
    const { live, truth } = synthesizePerformance(ref, perturbations);
    const { path } = viterbiAlign(ref, live);
    expect(Math.max(...barErrors(ref, path, truth))).toBeLessThanOrEqual(1);
  });

  it("recovers a restart", () => {
    // Break off in bar 9 and start again from bar 4.
    const atRefFrame = ref.barFirstFrame[9];
    const backToRefFrame = ref.barFirstFrame[4];
    const perturbations: Perturbation[] = [
      { kind: "silence", atRefFrame, frames: 20 },
      { kind: "restart", atRefFrame, backToRefFrame },
    ];
    const { live, truth } = synthesizePerformance(ref, perturbations);
    const { path } = viterbiAlign(ref, live);

    expect(Math.max(...barErrors(ref, path, truth))).toBeLessThanOrEqual(1);

    const jump = largestBackJump(path);
    expect(Math.abs(ref.barOfFrame[jump.from] - 9)).toBeLessThanOrEqual(1);
    expect(Math.abs(ref.barOfFrame[jump.to] - 4)).toBeLessThanOrEqual(1);
  });

  it("handles all three perturbations in one take", () => {
    const perturbations: Perturbation[] = [
      { kind: "hesitate", atRefFrame: ref.barFirstFrame[3] + 5, frames: 40 },
      {
        kind: "tempo",
        fromRefFrame: ref.barFirstFrame[6],
        toRefFrame: ref.barFirstFrame[9],
        ratio: 0.6,
      },
      { kind: "silence", atRefFrame: ref.barFirstFrame[12], frames: 25 },
      {
        kind: "restart",
        atRefFrame: ref.barFirstFrame[12],
        backToRefFrame: ref.barFirstFrame[10],
      },
    ];
    const { live, truth } = synthesizePerformance(ref, perturbations);
    const { path } = viterbiAlign(ref, live);
    const errors = barErrors(ref, path, truth);
    expect(quantile(errors, 0.99)).toBeLessThanOrEqual(1);
  });

  it("degrades gracefully under heavier noise", () => {
    const { live, truth } = synthesizePerformance(ref, [], { noise: 0.25, seed: 7 });
    const { path } = viterbiAlign(ref, live);
    expect(quantile(barErrors(ref, path, truth), 0.95)).toBeLessThanOrEqual(1);
  });

  it("returns empty for an empty take", () => {
    const result = viterbiAlign(ref, {
      frames: new Float32Array(0),
      frameCount: 0,
      silent: new Uint8Array(0),
      frameRate: ref.frameRate,
    });
    expect(result.path.length).toBe(0);
  });
});

describe("online follower", () => {
  const ref = buildTestReference();

  it("stays within a bar of the truth on a clean run", () => {
    const { live, truth } = synthesizePerformance(ref, []);
    const follower = new OnlineFollower(ref);
    const path = new Int32Array(live.frameCount);
    for (let t = 0; t < live.frameCount; t++) {
      path[t] = follower.step(live.frames, t * FEATURE_DIM, live.silent[t] === 1);
    }
    // The live cursor is allowed to be worse than the offline pass —
    // it only ever sees the past. One bar is the spec M8 target.
    expect(quantile(barErrors(ref, path, truth), 0.9)).toBeLessThanOrEqual(1);
  });

  it("reports low confidence before it has evidence", () => {
    const follower = new OnlineFollower(ref);
    expect(follower.confidence).toBe(0);
    const { live } = synthesizePerformance(ref, []);
    for (let t = 0; t < 20; t++) {
      follower.step(live.frames, t * FEATURE_DIM, live.silent[t] === 1);
    }
    expect(follower.confidence).toBeGreaterThan(0);
    expect(follower.confidence).toBeLessThanOrEqual(1);
  });
});

describe("decimateFrames", () => {
  const ref = buildTestReference();

  it("halves the frame count and keeps rows normalized", () => {
    const { live } = synthesizePerformance(ref, []);
    const half = decimateFrames(live);
    expect(half.frameCount).toBe(Math.ceil(live.frameCount / 2));
    expect(half.frameRate).toBe(live.frameRate / 2);
    for (let t = 0; t < half.frameCount; t++) {
      if (half.silent[t]) continue;
      let ss = 0;
      for (let c = 0; c < FEATURE_DIM; c++) ss += half.frames[t * FEATURE_DIM + c] ** 2;
      expect(Math.sqrt(ss)).toBeCloseTo(1, 5);
    }
  });
});
