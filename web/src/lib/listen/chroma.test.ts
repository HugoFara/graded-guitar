import { describe, it, expect } from "vitest";
import {
  CHROMA_BINS,
  FEATURE_DIM,
  BAND_COUNT,
  BAND_SPLIT_MIDI,
  MIDI_LOW,
  MIDI_HIGH,
  bandOf,
  midiToFreq,
  harmonicOffsets,
  harmonicPartials,
  chromaFromPitches,
  createChromaMapping,
  chromaFromSpectrum,
  l2Normalize,
  normalizeFeature,
  cosineDistanceAt,
  SILENCE_FLOOR_DB,
} from "./chroma";

const SAMPLE_RATE = 48000;
const FFT_SIZE = 16384;

// Feature layout: band 0 (below the split) occupies indices 0..11,
// band 1 (at or above) occupies 12..23.
const BASS = 0;
const TREBLE = CHROMA_BINS;

function silentSpectrum(): Float32Array {
  return new Float32Array(FFT_SIZE / 2).fill(-120);
}

function binOf(freq: number): number {
  return Math.round(freq / (SAMPLE_RATE / FFT_SIZE));
}

function argmax(v: Float32Array | number[]): number {
  let best = 0;
  for (let i = 1; i < v.length; i++) if (v[i] > v[best]) best = i;
  return best;
}

describe("feature layout", () => {
  it("is two bands of twelve", () => {
    expect(BAND_COUNT).toBe(2);
    expect(FEATURE_DIM).toBe(CHROMA_BINS * BAND_COUNT);
  });

  it("splits the register at E4", () => {
    expect(BAND_SPLIT_MIDI).toBe(64);
    expect(bandOf(63)).toBe(0);
    expect(bandOf(64)).toBe(1);
    expect(bandOf(MIDI_LOW)).toBe(0);
    expect(bandOf(MIDI_HIGH)).toBe(1);
  });
});

describe("pitch geometry", () => {
  it("anchors A4 at 440 Hz", () => {
    expect(midiToFreq(69)).toBeCloseTo(440, 6);
    expect(midiToFreq(81)).toBeCloseTo(880, 6);
    // Guitar's low E.
    expect(midiToFreq(MIDI_LOW)).toBeCloseTo(82.41, 2);
  });

  it("places partials on the pitch classes a plucked string excites", () => {
    expect(harmonicOffsets().map((x) => x.offset)).toEqual([0, 0, 7, 0, 4, 7]);
  });

  it("keeps partials unreduced so their own register is known", () => {
    // Octave, octave+fifth, two octaves, +major third, +fifth.
    expect(harmonicPartials().map((x) => x.semitones)).toEqual([0, 12, 19, 24, 28, 31]);
    expect(harmonicPartials()[0].weight).toBe(1);
    expect(harmonicPartials()[1].weight).toBeCloseTo(0.5, 6);
  });
});

describe("chromaFromPitches", () => {
  it("files each partial in the register it actually sounds in", () => {
    // C4 (MIDI 60) is below the split, but only its fundamental is —
    // the octave and everything above it ring in the treble band, which
    // is where the microphone will find them.
    const c = chromaFromPitches([60]);
    expect(c[BASS + 0]).toBeCloseTo(1, 6); // fundamental, bass band
    expect(c[TREBLE + 0]).toBeCloseTo(0.75, 6); // 2nd + 4th partials
    expect(c[TREBLE + 7]).toBeCloseTo(0.5, 6); // 3rd + 6th, a fifth up
    expect(c[TREBLE + 4]).toBeCloseTo(0.2, 6); // 5th, a major third up
  });

  it("separates registers instead of folding them together", () => {
    // This is the whole reason the feature is 24-dim. A single chroma
    // scored these identical, which is what made ostinato textures
    // unalignable.
    const low = Array.from(chromaFromPitches([48]));
    const high = Array.from(chromaFromPitches([72]));
    expect(low).not.toEqual(high);
    // The low C puts real energy in the bass band; the high one does not.
    expect(low[BASS + 0]).toBeGreaterThan(1);
    expect(high.slice(0, CHROMA_BINS).every((v) => v === 0)).toBe(true);
  });

  it("still folds octaves within a band", () => {
    // E4 and E5 are both above the split, so every partial of each lands
    // in the treble band and they become indistinguishable — chroma's
    // octave-blindness, now scoped to a register.
    expect(Array.from(chromaFromPitches([64]))).toEqual(
      Array.from(chromaFromPitches([76])),
    );
  });

  it("accumulates a chord, reinforcing classes the partials agree on", () => {
    const single = Array.from(chromaFromPitches([60]));
    const chord = Array.from(chromaFromPitches([60, 64, 67]));
    // C major. Neither E nor G puts a partial on the bass C, so the
    // root gets no reinforcement from the chord tones above it.
    expect(chord[BASS + 0]).toBe(single[BASS + 0]);
    // G is reinforced: it is C's 3rd and 6th partial as well as its own
    // fundamental.
    expect(chord[TREBLE + 7]).toBeGreaterThan(single[TREBLE + 7]);
    // E picks up C's 5th partial on top of its own fundamental.
    expect(chord[TREBLE + 4]).toBeGreaterThan(single[TREBLE + 4]);
  });

  it("reuses the output buffer without leaking the previous frame", () => {
    const buf = new Float32Array(FEATURE_DIM);
    chromaFromPitches([60], buf);
    chromaFromPitches([62], buf);
    expect(buf[BASS + 0]).toBe(0);
    expect(buf[BASS + 2]).toBeGreaterThan(0);
  });
});

describe("createChromaMapping", () => {
  const mapping = createChromaMapping(SAMPLE_RATE, FFT_SIZE);

  it("covers the whole analysis band", () => {
    expect(mapping.pitchClass.length).toBe(MIDI_HIGH - MIDI_LOW + 1);
    expect(mapping.featureIndex.length).toBe(MIDI_HIGH - MIDI_LOW + 1);
  });

  it("gives every pitch at least one bin, including the low register", () => {
    for (let i = 0; i < mapping.binStart.length; i++) {
      expect(mapping.binEnd[i]).toBeGreaterThan(mapping.binStart[i]);
    }
  });

  it("brackets each pitch's nominal frequency", () => {
    for (let i = 0; i < mapping.binStart.length; i++) {
      const nominal = binOf(midiToFreq(MIDI_LOW + i));
      expect(mapping.binStart[i]).toBeLessThanOrEqual(nominal);
      expect(mapping.binEnd[i]).toBeGreaterThan(nominal - 1);
    }
  });

  it("routes each pitch to its band's slot", () => {
    for (let i = 0; i < mapping.featureIndex.length; i++) {
      const midi = MIDI_LOW + i;
      expect(mapping.featureIndex[i]).toBe(bandOf(midi) * CHROMA_BINS + (midi % CHROMA_BINS));
    }
  });
});

describe("chromaFromSpectrum", () => {
  const mapping = createChromaMapping(SAMPLE_RATE, FFT_SIZE);

  it("puts a 440 Hz peak on treble A", () => {
    const spectrum = silentSpectrum();
    spectrum[binOf(440)] = -20;
    const { chroma, energy } = chromaFromSpectrum(spectrum, mapping);
    expect(energy).toBeGreaterThan(0);
    // A4 is above the split, so it belongs to the treble band.
    expect(argmax(chroma)).toBe(TREBLE + 9);
  });

  it("puts a low E peak on bass E", () => {
    const spectrum = silentSpectrum();
    spectrum[binOf(midiToFreq(MIDI_LOW))] = -20;
    const { chroma } = chromaFromSpectrum(spectrum, mapping);
    expect(argmax(chroma)).toBe(BASS + 4);
  });

  it("reports no energy for a silent frame", () => {
    expect(chromaFromSpectrum(silentSpectrum(), mapping).energy).toBe(0);
  });

  it("ignores bins at or below the silence floor", () => {
    const spectrum = silentSpectrum().fill(SILENCE_FLOOR_DB);
    expect(chromaFromSpectrum(spectrum, mapping).energy).toBe(0);
  });

  it("survives non-finite bins", () => {
    const spectrum = silentSpectrum();
    spectrum[binOf(440)] = -Infinity;
    spectrum[binOf(523.25)] = -25;
    const { chroma, energy } = chromaFromSpectrum(spectrum, mapping);
    expect(Number.isFinite(energy)).toBe(true);
    for (let i = 0; i < FEATURE_DIM; i++) expect(Number.isFinite(chroma[i])).toBe(true);
  });

  it("agrees with the symbolic side on which slot dominates", () => {
    // An observed A with its first partials should peak where the
    // reference model says a plucked A peaks. If these two disagree the
    // aligner is comparing incompatible descriptions of the same sound.
    const spectrum = silentSpectrum();
    for (let h = 1; h <= 4; h++) {
      spectrum[binOf(440 * h)] = -20 - 6 * Math.log2(h);
    }
    const { chroma } = chromaFromSpectrum(spectrum, mapping);
    expect(argmax(chroma)).toBe(argmax(chromaFromPitches([69])));
  });
});

describe("normalizeFeature", () => {
  it("gives the whole vector unit length", () => {
    const v = chromaFromPitches([60, 67]);
    normalizeFeature(v);
    let ss = 0;
    for (const x of v) ss += x * x;
    expect(Math.sqrt(ss)).toBeCloseTo(1, 5);
  });

  it("stops a loud band from swamping a quiet one", () => {
    // A quiet bass note under a loud treble figure. Per-band
    // normalization is what keeps the bass line contributing at all —
    // without it the treble dominates and we are back to a single band.
    const v = new Float32Array(FEATURE_DIM);
    v[BASS + 0] = 0.01;
    v[TREBLE + 7] = 10;
    normalizeFeature(v);
    expect(v[BASS + 0]).toBeCloseTo(v[TREBLE + 7], 5);
  });

  it("leaves an empty band at zero without producing NaN", () => {
    const v = new Float32Array(FEATURE_DIM);
    v[TREBLE + 3] = 2;
    normalizeFeature(v);
    expect(v[TREBLE + 3]).toBeCloseTo(1, 5);
    for (let i = 0; i < CHROMA_BINS; i++) expect(v[i]).toBe(0);
  });

  it("leaves an all-zero vector alone", () => {
    const v = new Float32Array(FEATURE_DIM);
    normalizeFeature(v);
    for (const x of v) expect(x).toBe(0);
  });
});

describe("l2Normalize and cosineDistanceAt", () => {
  it("normalizes to unit length", () => {
    const v = Float32Array.from([3, 4, ...new Array(FEATURE_DIM - 2).fill(0)]);
    l2Normalize(v);
    expect(Math.hypot(...v)).toBeCloseTo(1, 6);
  });

  it("normalizes a slice in place, leaving the rest untouched", () => {
    const v = Float32Array.from([3, 4, ...new Array(FEATURE_DIM - 2).fill(0)]);
    v[TREBLE] = 7;
    l2Normalize(v, 0, CHROMA_BINS);
    expect(Math.hypot(v[0], v[1])).toBeCloseTo(1, 6);
    expect(v[TREBLE]).toBe(7);
  });

  it("leaves a zero vector alone rather than producing NaN", () => {
    const v = new Float32Array(FEATURE_DIM);
    l2Normalize(v);
    for (const x of v) expect(x).toBe(0);
  });

  it("scores identical frames at zero distance", () => {
    const a = normalizeFeature(chromaFromPitches([60]));
    expect(cosineDistanceAt(a, 0, a, 0)).toBeCloseTo(0, 6);
  });

  it("can tell two registers of the same pitch class apart", () => {
    const c4 = normalizeFeature(chromaFromPitches([60]));
    const c6 = normalizeFeature(chromaFromPitches([84]));
    const same = cosineDistanceAt(c4, 0, c4, 0);
    const acrossRegister = cosineDistanceAt(c4, 0, c6, 0);
    // Single-band chroma scored these identical — the octave-blindness
    // that made ostinato figures unalignable. They now separate.
    expect(acrossRegister).toBeGreaterThan(same + 0.1);
    // But they stay closer to each other than to an unrelated pitch
    // class: they are still the same note, and a shared upper partial
    // is real evidence, not noise.
    const d4 = normalizeFeature(chromaFromPitches([62]));
    expect(acrossRegister).toBeLessThan(cosineDistanceAt(c4, 0, d4, 0));
  });

  it("reads frames at an offset in a flat backing array", () => {
    const flat = new Float32Array(FEATURE_DIM * 2);
    flat.set(normalizeFeature(chromaFromPitches([60])), 0);
    flat.set(normalizeFeature(chromaFromPitches([60])), FEATURE_DIM);
    expect(cosineDistanceAt(flat, 0, flat, FEATURE_DIM)).toBeCloseTo(0, 6);
  });
});
