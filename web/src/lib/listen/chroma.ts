// Chroma (12-bin pitch-class energy) features for score following.
// See decisions/0018-microphone-score-following.md for why chroma and
// not pitch detection: classical guitar is routinely 3-4 voices on one
// staff, monophonic f0 trackers return one pitch per frame and fail on
// every chord, and polyphonic transcription is an open research problem
// we are not taking on as a dependency.
//
// Chroma never has to decide how many notes are sounding. It folds all
// spectral energy into 12 pitch classes and lets the aligner work on
// the shape. We pay for that with octave blindness, which alignment
// does not need.

export const CHROMA_BINS = 12;

// Guitar's low E is MIDI 40. The top of the standard classical range is
// around MIDI 88, but partials of those notes carry real energy well
// above it and folding them in makes the observed vector match the
// harmonic reference model better — so the analysis band runs higher
// than the playable range on purpose.
export const MIDI_LOW = 40;
export const MIDI_HIGH = 96;

// Partials modelled per note when building the *reference* side. A
// plucked nylon string is nothing like a sine: energy lands on the
// fundamental's pitch class plus the fifth (3rd partial) and major
// third (5th partial) above it. Matching a harmonically-smeared
// observation against a one-hot symbolic reference is the single most
// common way this class of aligner is built wrong.
export const HARMONIC_COUNT = 6;

export function midiToFreq(midi: number): number {
  return 440 * Math.pow(2, (midi - 69) / 12);
}

// Pitch-class offset and weight of each modelled partial, relative to
// the fundamental. Partial h sits 12*log2(h) semitones above the
// fundamental; we round to the nearest semitone because chroma is a
// semitone-resolution representation. Weight falls as 1/h, the usual
// first-order approximation for a plucked string.
//
//   h=1 -> +0  (unison)      h=4 -> +0  (two octaves)
//   h=2 -> +0  (octave)      h=5 -> +4  (major third)
//   h=3 -> +7  (fifth)       h=6 -> +7  (fifth)
export function harmonicOffsets(
  count: number = HARMONIC_COUNT,
): { offset: number; weight: number }[] {
  const out: { offset: number; weight: number }[] = [];
  for (let h = 1; h <= count; h++) {
    out.push({
      offset: Math.round(12 * Math.log2(h)) % CHROMA_BINS,
      weight: 1 / h,
    });
  }
  return out;
}

const HARMONICS = harmonicOffsets();

// Symbolic -> chroma. Used to build the reference from the score. The
// harmonic model above is applied here so both sides of the comparison
// carry the same smearing.
export function chromaFromPitches(
  midiPitches: Iterable<number>,
  out: Float32Array = new Float32Array(CHROMA_BINS),
): Float32Array {
  out.fill(0);
  for (const midi of midiPitches) {
    const base = ((Math.round(midi) % CHROMA_BINS) + CHROMA_BINS) % CHROMA_BINS;
    for (const { offset, weight } of HARMONICS) {
      out[(base + offset) % CHROMA_BINS] += weight;
    }
  }
  return out;
}

// Precomputed spectrum-bin -> pitch-class mapping. Depends only on the
// analyser geometry, so it is built once per capture session rather
// than per frame: at 20 Hz over a five-minute take this loop would
// otherwise run 6000 times for no reason.
export type ChromaMapping = {
  sampleRate: number;
  fftSize: number;
  // Half-open [start, end) spectrum-bin range for each analysed pitch.
  binStart: Int32Array;
  binEnd: Int32Array;
  pitchClass: Int8Array;
};

export function createChromaMapping(
  sampleRate: number,
  fftSize: number,
): ChromaMapping {
  const pitchCount = MIDI_HIGH - MIDI_LOW + 1;
  const binStart = new Int32Array(pitchCount);
  const binEnd = new Int32Array(pitchCount);
  const pitchClass = new Int8Array(pitchCount);
  // getFloatFrequencyData fills fftSize/2 bins, each sampleRate/fftSize
  // wide.
  const binCount = fftSize / 2;
  const hz = sampleRate / fftSize;

  for (let i = 0; i < pitchCount; i++) {
    const midi = MIDI_LOW + i;
    // Half-semitone either side of the nominal pitch: the band that
    // belongs to this note and no other.
    const lo = midiToFreq(midi - 0.5);
    const hi = midiToFreq(midi + 0.5);
    let s = Math.ceil(lo / hz);
    let e = Math.ceil(hi / hz);
    if (s < 0) s = 0;
    if (e > binCount) e = binCount;
    // At the bottom of the guitar range a semitone is only ~5 Hz wide,
    // so a coarse FFT can leave a pitch with no bins of its own. Claim
    // the single nearest bin rather than dropping the pitch silently —
    // dropping it would punch a hole in the low register, which is
    // where the bass voice lives.
    if (e <= s) {
      s = Math.min(binCount - 1, Math.max(0, Math.round(midiToFreq(midi) / hz)));
      e = s + 1;
    }
    binStart[i] = s;
    binEnd[i] = e;
    pitchClass[i] = midi % CHROMA_BINS;
  }

  return { sampleRate, fftSize, binStart, binEnd, pitchClass };
}

// Below this level a bin is treated as silence and contributes nothing.
// AnalyserNode reports roughly -100 dB for a quiet room and -30 to -50
// for a plucked note, so -85 sits under the noise floor without
// clipping real signal.
export const SILENCE_FLOOR_DB = -85;

// Observed spectrum -> chroma. `spectrumDb` is an AnalyserNode
// getFloatFrequencyData buffer (decibels, one value per bin).
//
// Returns the *unnormalized* vector plus its total energy. The caller
// normalizes and applies its own silence gate — a frame of near-silence
// still has a well-defined chroma direction after normalization, and
// treating that direction as meaningful is how a follower drifts during
// rests. Keeping energy separate makes that gate explicit.
export function chromaFromSpectrum(
  spectrumDb: Float32Array,
  mapping: ChromaMapping,
  out: Float32Array = new Float32Array(CHROMA_BINS),
): { chroma: Float32Array; energy: number } {
  out.fill(0);
  let energy = 0;
  const { binStart, binEnd, pitchClass } = mapping;

  for (let i = 0; i < pitchClass.length; i++) {
    const end = binEnd[i];
    let sum = 0;
    for (let b = binStart[i]; b < end; b++) {
      const db = spectrumDb[b];
      if (db <= SILENCE_FLOOR_DB || !Number.isFinite(db)) continue;
      // dB -> linear amplitude. Squaring to get power made the loudest
      // partial dominate the vector so heavily that chords collapsed
      // toward their strongest note; amplitude keeps the shape.
      sum += Math.pow(10, db / 20);
    }
    out[pitchClass[i]] += sum;
    energy += sum;
  }

  return { chroma: out, energy };
}

// L2-normalize in place. A zero vector is left as zeros rather than
// producing NaN — silent frames are legitimate and the aligner handles
// them via the energy gate, not via the chroma direction.
export function l2Normalize(v: Float32Array): Float32Array {
  let ss = 0;
  for (let i = 0; i < v.length; i++) ss += v[i] * v[i];
  if (ss <= 0) return v;
  const inv = 1 / Math.sqrt(ss);
  for (let i = 0; i < v.length; i++) v[i] *= inv;
  return v;
}

// Cosine distance between two L2-normalized chroma vectors, read from
// flat backing arrays at the given frame offsets. Chroma is
// non-negative so the dot product is in [0, 1] and the distance is too.
//
// Takes offsets rather than subarrays because this is the aligner's
// innermost loop — one call per (reference frame, live frame) pair —
// and allocating a view per call dominated the profile.
export function cosineDistanceAt(
  a: Float32Array,
  aOffset: number,
  b: Float32Array,
  bOffset: number,
): number {
  let dot = 0;
  for (let i = 0; i < CHROMA_BINS; i++) {
    dot += a[aOffset + i] * b[bOffset + i];
  }
  return 1 - dot;
}
