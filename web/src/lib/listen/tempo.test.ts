import { describe, it, expect } from "vitest";
import { TempoMap } from "./tempo";

const TPQ = 960;

describe("TempoMap", () => {
  it("converts at a constant tempo", () => {
    const map = new TempoMap(TPQ, [{ tick: 0, bpm: 120 }]);
    // 120bpm: a quarter note is 500ms.
    expect(map.tickToMs(0)).toBe(0);
    expect(map.tickToMs(TPQ)).toBeCloseTo(500, 6);
    expect(map.tickToMs(4 * TPQ)).toBeCloseTo(2000, 6);
  });

  it("round-trips ticks through milliseconds", () => {
    const map = new TempoMap(TPQ, [{ tick: 0, bpm: 92 }]);
    for (const tick of [0, 137, TPQ, 5 * TPQ, 12345]) {
      expect(map.msToTick(map.tickToMs(tick))).toBeCloseTo(tick, 6);
    }
  });

  it("applies a mid-score tempo change", () => {
    const map = new TempoMap(TPQ, [
      { tick: 0, bpm: 120 },
      { tick: 4 * TPQ, bpm: 60 },
    ]);
    expect(map.tickToMs(4 * TPQ)).toBeCloseTo(2000, 6);
    // At 60bpm a quarter takes 1000ms, so the next bar takes twice as
    // long as the first.
    expect(map.tickToMs(8 * TPQ)).toBeCloseTo(6000, 6);
    expect(map.msToTick(6000)).toBeCloseTo(8 * TPQ, 6);
  });

  it("round-trips across a tempo change", () => {
    const map = new TempoMap(TPQ, [
      { tick: 0, bpm: 144 },
      { tick: 3 * TPQ, bpm: 72 },
      { tick: 9 * TPQ, bpm: 100 },
    ]);
    for (const tick of [0, TPQ, 3 * TPQ, 5 * TPQ, 9 * TPQ, 20 * TPQ]) {
      expect(map.msToTick(map.tickToMs(tick))).toBeCloseTo(tick, 4);
    }
  });

  it("sorts unordered changes", () => {
    const ordered = new TempoMap(TPQ, [
      { tick: 0, bpm: 120 },
      { tick: 4 * TPQ, bpm: 60 },
    ]);
    const shuffled = new TempoMap(TPQ, [
      { tick: 4 * TPQ, bpm: 60 },
      { tick: 0, bpm: 120 },
    ]);
    expect(shuffled.tickToMs(8 * TPQ)).toBeCloseTo(ordered.tickToMs(8 * TPQ), 6);
  });

  it("falls back when the score declares no tempo at tick 0", () => {
    const map = new TempoMap(TPQ, [{ tick: 4 * TPQ, bpm: 60 }], 120);
    expect(map.tickToMs(TPQ)).toBeCloseTo(500, 6);
  });

  it("lets the later of two changes on the same tick win", () => {
    const map = new TempoMap(TPQ, [
      { tick: 0, bpm: 120 },
      { tick: 2 * TPQ, bpm: 60 },
      { tick: 2 * TPQ, bpm: 240 },
    ]);
    // 240bpm: a quarter is 250ms, so the bar after the change is short.
    expect(map.tickToMs(3 * TPQ) - map.tickToMs(2 * TPQ)).toBeCloseTo(250, 6);
  });

  it("drops nonsense tempi rather than emitting Infinity", () => {
    const map = new TempoMap(TPQ, [
      { tick: 0, bpm: 120 },
      { tick: 2 * TPQ, bpm: 0 },
      { tick: 3 * TPQ, bpm: NaN },
      { tick: 4 * TPQ, bpm: -60 },
    ]);
    expect(Number.isFinite(map.tickToMs(8 * TPQ))).toBe(true);
    expect(map.tickToMs(8 * TPQ)).toBeCloseTo(4000, 6);
  });

  it("clamps negative inputs to the start of the score", () => {
    const map = new TempoMap(TPQ, [{ tick: 0, bpm: 120 }]);
    expect(map.tickToMs(-100)).toBe(0);
    expect(map.msToTick(-100)).toBe(0);
  });

  it("defaults a nonsense ticks-per-quarter to the MIDI standard", () => {
    const map = new TempoMap(0, [{ tick: 0, bpm: 120 }]);
    expect(map.ticksPerQuarter).toBe(960);
  });
});
