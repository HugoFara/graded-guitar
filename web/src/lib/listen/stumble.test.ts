import { describe, it, expect } from "vitest";
import { buildReference, type BarSpan, type NoteEvent } from "./reference";
import { TempoMap } from "./tempo";
import { synthesizePerformance, type Perturbation } from "./synth";
import { viterbiAlign } from "./align";
import { analyzeTake, hardestBars } from "./stumble";

const TPQ = 960;
const BAR_TICKS = TPQ * 4;
const BARS = 16;

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
    for (let q = 0; q < 4; q++) {
      const t = b * BAR_TICKS + q * TPQ;
      notes.push({ startTick: t, endTick: t + TPQ, midi: 60 + ((b * 3 + q * 2) % 12) });
    }
  }
  return buildReference(notes, bars, new TempoMap(TPQ, [{ tick: 0, bpm: 120 }]));
}

function analyze(ref: ReturnType<typeof buildTestReference>, perts: Perturbation[]) {
  const { live } = synthesizePerformance(ref, perts);
  return analyzeTake(ref, live, viterbiAlign(ref, live), {});
}

describe("analyzeTake", () => {
  const ref = buildTestReference();

  it("reports a clean run-through as complete and at written tempo", () => {
    const a = analyze(ref, []);
    expect(a.completed).toBe(true);
    expect(a.completion).toBe(1);
    expect(a.reachedBars).toBe(BARS);
    expect(a.furthestBar).toBe(BARS - 1);
    expect(a.medianTempoRatio).toBeCloseTo(1, 1);
    expect(a.totalRestarts).toBe(0);
    expect(a.bars.every((b) => b.attempts === 1)).toBe(true);
  });

  it("attributes a hesitation to the bar it happened in", () => {
    const a = analyze(ref, [
      { kind: "hesitate", atRefFrame: ref.barFirstFrame[8] + 10, frames: 60 },
    ]);
    const held = a.bars.reduce((best, b) =>
      b.longestHoldFrames > best.longestHoldFrames ? b : best,
    );
    expect(Math.abs(held.bar - 8)).toBeLessThanOrEqual(1);
    expect(held.longestHoldFrames).toBeGreaterThan(30);
    // The bar took much longer than written, so it reads as slow.
    expect(held.tempoRatio).toBeLessThan(0.8);
  });

  it("reports slow bars below a tempo ratio of one", () => {
    const a = analyze(ref, [
      {
        kind: "tempo",
        fromRefFrame: ref.barFirstFrame[4],
        toRefFrame: ref.barFirstFrame[10],
        ratio: 0.5,
      },
    ]);
    for (let b = 5; b < 9; b++) {
      expect(a.bars[b].tempoRatio).toBeLessThan(0.75);
    }
    expect(a.bars[1].tempoRatio).toBeCloseTo(1, 1);
    expect(a.bars[14].tempoRatio).toBeCloseTo(1, 1);
  });

  it("counts a restart as a second attempt on the bars replayed", () => {
    const a = analyze(ref, [
      { kind: "silence", atRefFrame: ref.barFirstFrame[9], frames: 20 },
      {
        kind: "restart",
        atRefFrame: ref.barFirstFrame[9],
        backToRefFrame: ref.barFirstFrame[4],
      },
    ]);
    expect(a.totalRestarts).toBeGreaterThanOrEqual(1);
    // Bars 4..8 were played twice; bars 0..3 once.
    expect(a.bars[6].attempts).toBe(2);
    expect(a.bars[1].attempts).toBe(1);
    // The tempo ratio uses the final attempt only, so replaying a bar
    // must not make it look like it took twice as long.
    expect(a.bars[6].tempoRatio).toBeCloseTo(1, 1);
  });

  it("marks an abandoned take as not completed", () => {
    // Truncate the take partway: align only the first half of the live
    // frames, as if the player stopped.
    const { live } = synthesizePerformance(ref, []);
    const half = Math.floor(live.frameCount / 2);
    const truncated = {
      frames: live.frames.slice(0, half * 12),
      frameCount: half,
      silent: live.silent.slice(0, half),
      frameRate: live.frameRate,
    };
    const a = analyzeTake(ref, truncated, viterbiAlign(ref, truncated), {});
    expect(a.completed).toBe(false);
    expect(a.completion).toBeLessThan(1);
    expect(a.furthestBar).toBeLessThan(BARS - 1);
  });

  it("leaves unreached bars without a tempo ratio rather than guessing", () => {
    const { live } = synthesizePerformance(ref, []);
    const half = Math.floor(live.frameCount / 2);
    const truncated = {
      frames: live.frames.slice(0, half * 12),
      frameCount: half,
      silent: live.silent.slice(0, half),
      frameRate: live.frameRate,
    };
    const a = analyzeTake(ref, truncated, viterbiAlign(ref, truncated), {});
    const unreached = a.bars.filter((b) => !b.reached);
    expect(unreached.length).toBeGreaterThan(0);
    for (const b of unreached) {
      expect(Number.isNaN(b.tempoRatio)).toBe(true);
      expect(b.attempts).toBe(0);
    }
  });

  it("records expected duration for every bar, played or not", () => {
    const a = analyze(ref, []);
    for (const b of a.bars) expect(b.expectedFrames).toBeGreaterThan(0);
  });
});

describe("hardestBars", () => {
  const ref = buildTestReference();

  it("ranks the stalled bar first and explains why", () => {
    const a = analyze(ref, [
      { kind: "hesitate", atRefFrame: ref.barFirstFrame[11] + 8, frames: 70 },
    ]);
    const hardest = hardestBars(a, 3);
    expect(hardest.length).toBeGreaterThan(0);
    expect(Math.abs(hardest[0].bar - 11)).toBeLessThanOrEqual(1);
    expect(hardest[0].reason).not.toBe("clean");
  });

  it("ranks a replayed bar above an untouched one", () => {
    const a = analyze(ref, [
      { kind: "silence", atRefFrame: ref.barFirstFrame[12], frames: 20 },
      {
        kind: "restart",
        atRefFrame: ref.barFirstFrame[12],
        backToRefFrame: ref.barFirstFrame[10],
      },
    ]);
    const hardest = hardestBars(a, 5);
    const bars = hardest.map((h) => h.bar);
    expect(bars.some((b) => b >= 10 && b <= 12)).toBe(true);
    expect(hardest.some((h) => h.reason.includes("attempts"))).toBe(true);
  });

  it("returns nothing for a clean take", () => {
    expect(hardestBars(analyze(ref, []), 5).length).toBe(0);
  });

  it("respects the limit", () => {
    const a = analyze(ref, [
      { kind: "hesitate", atRefFrame: ref.barFirstFrame[2] + 4, frames: 40 },
      { kind: "hesitate", atRefFrame: ref.barFirstFrame[5] + 4, frames: 40 },
      { kind: "hesitate", atRefFrame: ref.barFirstFrame[9] + 4, frames: 40 },
    ]);
    expect(hardestBars(a, 2).length).toBeLessThanOrEqual(2);
  });
});
