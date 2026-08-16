// Builds the reference side of the alignment: the chroma sequence the
// score predicts, sampled uniformly in time at the follower's frame
// rate, plus the tick and bar each frame belongs to.
//
// Deliberately free of any alphaTab import. The score adapter lives in
// `score.ts`; keeping this module over plain data means the whole
// alignment core is testable with hand-written fixtures and no
// rendering engine. See decisions/0018-microphone-score-following.md.

import {
  CHROMA_BINS,
  chromaFromPitches,
  l2Normalize,
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
  // frameCount * CHROMA_BINS, row-major, each row L2-normalized.
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

  const frames = new Float32Array(frameCount * CHROMA_BINS);
  const frameTick = new Float64Array(frameCount);
  const barOfFrame = new Int32Array(frameCount);
  const scratch = new Float32Array(CHROMA_BINS);

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
    l2Normalize(scratch);
    frames.set(scratch, f * CHROMA_BINS);
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
