import { describe, it, expect } from "vitest";
import {
  CHROMA_BINS,
  MIDI_LOW,
  MIDI_HIGH,
  midiToFreq,
  harmonicOffsets,
  chromaFromPitches,
  createChromaMapping,
  chromaFromSpectrum,
  l2Normalize,
  cosineDistanceAt,
  SILENCE_FLOOR_DB,
} from "./chroma";

const SAMPLE_RATE = 48000;
const FFT_SIZE = 16384;

function silentSpectrum(): Float32Array {
  return new Float32Array(FFT_SIZE / 2).fill(-120);
}

function binOf(freq: number): number {
  return Math.round(freq / (SAMPLE_RATE / FFT_SIZE));
}

describe("pitch geometry", () => {
  it("anchors A4 at 440 Hz", () => {
    expect(midiToFreq(69)).toBeCloseTo(440, 6);
    expect(midiToFreq(81)).toBeCloseTo(880, 6);
    // Guitar's low E.
    expect(midiToFreq(MIDI_LOW)).toBeCloseTo(82.41, 2);
  });

  it("places partials on the pitch classes a plucked string excites", () => {
    const h = harmonicOffsets();
    expect(h.map((x) => x.offset)).toEqual([0, 0, 7, 0, 4, 7]);
    // Weights fall as 1/h.
    expect(h[0].weight).toBe(1);
    expect(h[1].weight).toBeCloseTo(0.5, 6);
  });
});

describe("chromaFromPitches", () => {
  it("smears a single note onto its fundamental, fifth and third", () => {
    // MIDI 60 is C. Fifth above is G (7), major third is E (4).
    const c = chromaFromPitches([60]);
    expect(c[0]).toBeGreaterThan(c[7]);
    expect(c[7]).toBeGreaterThan(c[4]);
    // Everything else stays empty.
    for (let i = 0; i < CHROMA_BINS; i++) {
      if (i === 0 || i === 4 || i === 7) continue;
      expect(c[i]).toBe(0);
    }
  });

  it("is octave-blind", () => {
    const low = Array.from(chromaFromPitches([48]));
    const high = Array.from(chromaFromPitches([72]));
    expect(low).toEqual(high);
  });

  it("accumulates a chord, reinforcing classes the partials agree on", () => {
    const single = Array.from(chromaFromPitches([60]));
    const chord = Array.from(chromaFromPitches([60, 64, 67]));

    // C major. Neither E nor G puts a partial on C, so the root gets no
    // reinforcement from the chord tones above it.
    expect(chord[0]).toBe(single[0]);
    // G does get reinforced: it is C's 3rd and 6th partial as well as
    // its own fundamental, which is why it ends up the strongest class
    // in the vector rather than the root.
    expect(chord[7]).toBeGreaterThan(chord[0]);
    // E picks up C's 5th partial on top of its own fundamental.
    expect(chord[4]).toBeGreaterThan(single[4]);
    expect(chord[4]).toBeLessThan(chord[7]);
  });

  it("reuses the output buffer without leaking the previous frame", () => {
    const buf = new Float32Array(CHROMA_BINS);
    chromaFromPitches([60], buf);
    chromaFromPitches([62], buf);
    expect(buf[0]).toBe(0);
    expect(buf[2]).toBeGreaterThan(0);
  });
});

describe("createChromaMapping", () => {
  const mapping = createChromaMapping(SAMPLE_RATE, FFT_SIZE);

  it("covers the whole analysis band", () => {
    expect(mapping.pitchClass.length).toBe(MIDI_HIGH - MIDI_LOW + 1);
  });

  it("gives every pitch at least one bin, including the low register", () => {
    for (let i = 0; i < mapping.binStart.length; i++) {
      expect(mapping.binEnd[i]).toBeGreaterThan(mapping.binStart[i]);
    }
  });

  it("brackets each pitch's nominal frequency", () => {
    for (let i = 0; i < mapping.binStart.length; i++) {
      const midi = MIDI_LOW + i;
      const nominal = binOf(midiToFreq(midi));
      expect(mapping.binStart[i]).toBeLessThanOrEqual(nominal);
      expect(mapping.binEnd[i]).toBeGreaterThan(nominal - 1);
    }
  });
});

describe("chromaFromSpectrum", () => {
  const mapping = createChromaMapping(SAMPLE_RATE, FFT_SIZE);

  it("puts a 440 Hz peak on pitch class A", () => {
    const spectrum = silentSpectrum();
    spectrum[binOf(440)] = -20;
    const { chroma, energy } = chromaFromSpectrum(spectrum, mapping);
    expect(energy).toBeGreaterThan(0);
    let argmax = 0;
    for (let i = 1; i < CHROMA_BINS; i++) if (chroma[i] > chroma[argmax]) argmax = i;
    expect(argmax).toBe(9);
  });

  it("reports no energy for a silent frame", () => {
    const { energy } = chromaFromSpectrum(silentSpectrum(), mapping);
    expect(energy).toBe(0);
  });

  it("ignores bins at or below the silence floor", () => {
    const spectrum = silentSpectrum().fill(SILENCE_FLOOR_DB);
    const { energy } = chromaFromSpectrum(spectrum, mapping);
    expect(energy).toBe(0);
  });

  it("survives non-finite bins", () => {
    const spectrum = silentSpectrum();
    spectrum[binOf(440)] = -Infinity;
    spectrum[binOf(523.25)] = -25;
    const { chroma, energy } = chromaFromSpectrum(spectrum, mapping);
    expect(Number.isFinite(energy)).toBe(true);
    for (let i = 0; i < CHROMA_BINS; i++) expect(Number.isFinite(chroma[i])).toBe(true);
  });

  it("agrees with the symbolic side on which class dominates", () => {
    // An observed A with its first partials should peak where the
    // reference model says a plucked A peaks.
    const spectrum = silentSpectrum();
    for (let h = 1; h <= 4; h++) {
      spectrum[binOf(440 * h)] = -20 - 6 * Math.log2(h);
    }
    const { chroma } = chromaFromSpectrum(spectrum, mapping);
    const reference = chromaFromPitches([69]);
    let observedArgmax = 0;
    let referenceArgmax = 0;
    for (let i = 1; i < CHROMA_BINS; i++) {
      if (chroma[i] > chroma[observedArgmax]) observedArgmax = i;
      if (reference[i] > reference[referenceArgmax]) referenceArgmax = i;
    }
    expect(observedArgmax).toBe(referenceArgmax);
  });
});

describe("l2Normalize and cosineDistanceAt", () => {
  it("normalizes to unit length", () => {
    const v = Float32Array.from([3, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]);
    l2Normalize(v);
    expect(Math.hypot(...v)).toBeCloseTo(1, 6);
  });

  it("leaves a zero vector alone rather than producing NaN", () => {
    const v = new Float32Array(CHROMA_BINS);
    l2Normalize(v);
    for (const x of v) expect(x).toBe(0);
  });

  it("scores identical frames at zero distance", () => {
    const a = l2Normalize(chromaFromPitches([60]));
    expect(cosineDistanceAt(a, 0, a, 0)).toBeCloseTo(0, 6);
  });

  it("scores a tritone apart as more distant than a fifth apart", () => {
    const c = l2Normalize(chromaFromPitches([60]));
    const g = l2Normalize(chromaFromPitches([67]));
    const fSharp = l2Normalize(chromaFromPitches([66]));
    expect(cosineDistanceAt(c, 0, fSharp, 0)).toBeGreaterThan(
      cosineDistanceAt(c, 0, g, 0),
    );
  });

  it("reads frames at an offset in a flat backing array", () => {
    const flat = new Float32Array(CHROMA_BINS * 2);
    flat.set(l2Normalize(chromaFromPitches([60])), 0);
    flat.set(l2Normalize(chromaFromPitches([60])), CHROMA_BINS);
    expect(cosineDistanceAt(flat, 0, flat, CHROMA_BINS)).toBeCloseTo(0, 6);
  });
});
