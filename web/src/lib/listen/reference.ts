// Builds the reference side of the alignment: the chroma sequence the
// score predicts, sampled uniformly in time at the follower's frame
// rate, plus the tick and bar each frame belongs to.
//
// Deliberately free of any alphaTab import. The score adapter lives in
// `score.ts`; keeping this module over plain data means the whole
// alignment core is testable with hand-written fixtures and no
// rendering engine. See decisions/0018-microphone-score-following.md.

import {
  FEATURE_DIM,
  chromaFromPitches,
  cosineDistanceAt,
  normalizeFeature,
} from "./chroma";
import { TempoMap } from "./tempo";

export type NoteEvent = {
  startTick: number;
  endTick: number;
  midi: number;
};

export type BarSpan = {
  startTick: number;
  durationTicks: number;
};

// Frames per second for both sides of the alignment. 20 Hz is a 50 ms
// grid: fine enough that a bar boundary lands within half a frame at any
// realistic tempo, coarse enough that a five-minute take is 6000 frames
// rather than a matrix we cannot hold.
export const FRAME_RATE = 20;

export type Reference = {
  // frameCount * FEATURE_DIM, row-major, each row band-normalized.
  frames: Float32Array;
  frameCount: number;
  // Score tick at the start of each frame.
  frameTick: Float64Array;
  // 0-based bar index for each frame, or -1 past the end of the score.
  barOfFrame: Int32Array;
  // First frame index belonging to each bar, for bar-level readouts.
  barFirstFrame: Int32Array;
  frameRate: number;
  barCount: number;
  durationMs: number;
  tempo: TempoMap;
};

// How much a piece repeats itself, as seen by the feature: the fraction
// of frame pairs more than half a bar apart that are indistinguishable.
//
// This is the number that explains a wandering cursor. An ostinato
// texture — a static pedal against slow-moving harmony, which is most
// of Asturias — makes the emission term nearly flat, so the aligner is
// running on the transition prior alone and has little to correct
// itself with. Varied writing measures under 5%; an ostinato measures
// tens of percent.
//
// Sampled rather than exhaustive: the exact quantity is O(frames²),
// which is tens of millions of comparisons on a four-minute piece. A
// few hundred samples put it within a point or two, which is all the
// precision a warning needs.
export function estimateAmbiguity(ref: Reference, samples = 300): number {
  if (ref.frameCount < 2 || ref.barCount < 2) return 0;
  const step = Math.max(1, Math.floor(ref.frameCount / samples));
  const framesPerBar = ref.frameCount / ref.barCount;
  let confusable = 0;
  let compared = 0;
  for (let i = 0; i < ref.frameCount; i += step) {
    for (let j = 0; j < ref.frameCount; j += step) {
      if (Math.abs(i - j) < framesPerBar / 2) continue;
      compared++;
      if (
        cosineDistanceAt(ref.frames, i * FEATURE_DIM, ref.frames, j * FEATURE_DIM) < 0.05
      ) {
        confusable++;
      }
    }
  }
  return compared > 0 ? confusable / compared : 0;
}

function barIndexForTick(bars: BarSpan[], tick: number): number {
  if (!bars.length) return -1;
  let lo = 0;
  let hi = bars.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (bars[mid].startTick <= tick) lo = mid;
    else hi = mid - 1;
  }
  const bar = bars[lo];
  if (tick >= bar.startTick + bar.durationTicks && lo === bars.length - 1) {
    return -1;
  }
  return lo;
}

export function buildReference(
  notes: NoteEvent[],
  bars: BarSpan[],
  tempo: TempoMap,
  frameRate: number = FRAME_RATE,
): Reference {
  const usable = notes
    .filter(
      (n) =>
        Number.isFinite(n.startTick) &&
        Number.isFinite(n.endTick) &&
        Number.isFinite(n.midi) &&
        n.endTick > n.startTick,
    )
    .sort((a, b) => a.startTick - b.startTick);

  // The score ends at whichever runs longer, the last barline or the
  // last note's release. Grace notes and ties occasionally overhang the
  // final bar; truncating there would drop the last chord from the
  // reference, which is exactly where a player's final ritardando lives.
  let endTick = 0;
  for (const n of usable) endTick = Math.max(endTick, n.endTick);
  for (const b of bars) {
    endTick = Math.max(endTick, b.startTick + b.durationTicks);
  }

  const durationMs = tempo.tickToMs(endTick);
  const msPerFrame = 1000 / frameRate;
  // The epsilon matters: tick->ms is a chain of floating-point
  // divisions, so a score whose length is an exact multiple of the
  // frame period lands a hair over it and `ceil` invents a trailing
  // all-silent frame at the end of every piece.
  const frameCount = Math.max(1, Math.ceil(durationMs / msPerFrame - 1e-9));

  const frames = new Float32Array(frameCount * FEATURE_DIM);
  const frameTick = new Float64Array(frameCount);
  const barOfFrame = new Int32Array(frameCount);
  const scratch = new Float32Array(FEATURE_DIM);

  // Sweep rather than re-scan: frames advance monotonically in tick, so
  // notes enter the sounding set once and leave once.
  let cursor = 0;
  let active: NoteEvent[] = [];

  for (let f = 0; f < frameCount; f++) {
    const tick = tempo.msToTick(f * msPerFrame);
    frameTick[f] = tick;
    barOfFrame[f] = barIndexForTick(bars, tick);

    while (cursor < usable.length && usable[cursor].startTick <= tick) {
      active.push(usable[cursor]);
      cursor++;
    }
    if (active.length) {
      active = active.filter((n) => n.endTick > tick);
    }

    chromaFromPitches(
      active.map((n) => n.midi),
      scratch,
    );
    normalizeFeature(scratch);
    frames.set(scratch, f * FEATURE_DIM);
  }

  const barFirstFrame = new Int32Array(bars.length).fill(-1);
  for (let f = 0; f < frameCount; f++) {
    const b = barOfFrame[f];
    if (b >= 0 && barFirstFrame[b] === -1) barFirstFrame[b] = f;
  }

  return {
    frames,
    frameCount,
    frameTick,
    barOfFrame,
    barFirstFrame,
    frameRate,
    barCount: bars.length,
    durationMs,
    tempo,
  };
}
