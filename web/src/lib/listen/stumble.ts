// Turns an alignment path into the per-bar record that is the point of
// the whole milestone: where the player hesitated, slowed, stopped, or
// went back and started again.
//
// Reads only the offline Viterbi path (ADR 0018). Measurements never
// come from the live follower, whose tracking errors are shaped exactly
// like the player errors we are trying to measure.

import type { Alignment, LiveFrames } from "./align";
import type { Reference } from "./reference";

export type BarPerformance = {
  // 0-based bar index, matching Reference.barOfFrame.
  bar: number;
  reached: boolean;
  // Separate entries into this bar. More than one means the player came
  // back to it — the strongest per-bar difficulty signal we collect.
  attempts: number;
  // Live frames spent in this bar across all attempts, and in the final
  // attempt alone.
  liveFrames: number;
  lastAttemptFrames: number;
  // Reference frames the bar occupies, i.e. its written duration.
  expectedFrames: number;
  // expectedFrames / lastAttemptFrames. 1 is written tempo, below 1 is
  // slower than written. Computed from the last attempt because that is
  // the one that answers "can they play it now"; earlier attempts are
  // counted separately as `attempts`.
  tempoRatio: number;
  // Longest run of frames the path did not advance — the player behind
  // the score, whether stalled or picking a chord apart.
  longestHoldFrames: number;
  silentFrames: number;
  // Backward jumps leaving from / landing in this bar.
  restartsFrom: number;
  restartsTo: number;
  // Mean chroma distance over frames with evidence. High values mean
  // the aligner was matching this bar poorly, so its other numbers
  // deserve less weight. NaN when the bar was never sounded.
  meanCost: number;
};

export type TakeAnalysis = {
  bars: BarPerformance[];
  barCount: number;
  reachedBars: number;
  furthestBar: number;
  // reachedBars / barCount.
  completion: number;
  // True when the player got to the final bar. When false, any
  // difficulty derived from this take is a LOWER BOUND, not an
  // estimate — see the censoring rule in spec §7 M8.
  completed: boolean;
  medianTempoRatio: number;
  totalRestarts: number;
  totalHoldFrames: number;
  durationMs: number;
  meanCost: number;
};

export type StumbleOptions = {
  // Minimum constant-path run counted as a hold rather than transition
  // jitter. The transition prior allows a stationary step at 15%
  // weight, so short holds are normal even in clean playing.
  minHoldFrames: number;
  // Minimum backward move counted as a restart rather than alignment
  // noise, in reference frames.
  minRestartFrames: number;
};

export const DEFAULT_STUMBLE_OPTIONS: StumbleOptions = {
  minHoldFrames: 8,
  minRestartFrames: 20,
};

function median(values: number[]): number {
  const usable = values.filter((v) => Number.isFinite(v)).sort((a, b) => a - b);
  if (!usable.length) return NaN;
  const mid = usable.length >> 1;
  return usable.length % 2 ? usable[mid] : (usable[mid - 1] + usable[mid]) / 2;
}

export function analyzeTake(
  ref: Reference,
  live: LiveFrames,
  alignment: Alignment,
  options: Partial<StumbleOptions> = {},
): TakeAnalysis {
  const opts = { ...DEFAULT_STUMBLE_OPTIONS, ...options };
  const { path, frameCost } = alignment;
  const barCount = ref.barCount;

  const bars: BarPerformance[] = [];
  const expectedFrames = new Int32Array(barCount);
  for (let f = 0; f < ref.frameCount; f++) {
    const b = ref.barOfFrame[f];
    if (b >= 0) expectedFrames[b]++;
  }
  for (let b = 0; b < barCount; b++) {
    bars.push({
      bar: b,
      reached: false,
      attempts: 0,
      liveFrames: 0,
      lastAttemptFrames: 0,
      expectedFrames: expectedFrames[b],
      tempoRatio: NaN,
      longestHoldFrames: 0,
      silentFrames: 0,
      restartsFrom: 0,
      restartsTo: 0,
      meanCost: NaN,
    });
  }

  const costSum = new Float64Array(barCount);
  const costCount = new Int32Array(barCount);

  let prevBar = -1;
  let holdRun = 0;
  let furthestBar = -1;

  for (let t = 0; t < path.length; t++) {
    const bar = ref.barOfFrame[path[t]];
    if (bar < 0) {
      prevBar = -1;
      holdRun = 0;
      continue;
    }
    const rec = bars[bar];

    if (bar !== prevBar) {
      rec.attempts++;
      rec.reached = true;
      rec.lastAttemptFrames = 0;
      // A backward move of any size crosses bars; only count it as a
      // restart when it is big enough not to be alignment jitter around
      // a barline.
      if (t > 0) {
        const back = path[t - 1] - path[t];
        if (back >= opts.minRestartFrames) {
          const fromBar = ref.barOfFrame[path[t - 1]];
          if (fromBar >= 0) bars[fromBar].restartsFrom++;
          rec.restartsTo++;
        }
      }
    }
    prevBar = bar;

    rec.liveFrames++;
    rec.lastAttemptFrames++;
    if (live.silent[t]) rec.silentFrames++;
    if (bar > furthestBar) furthestBar = bar;

    if (t > 0 && path[t] === path[t - 1]) {
      holdRun++;
      if (holdRun >= opts.minHoldFrames && holdRun > rec.longestHoldFrames) {
        rec.longestHoldFrames = holdRun;
      }
    } else {
      holdRun = 0;
    }

    const cost = frameCost[t];
    if (Number.isFinite(cost)) {
      costSum[bar] += cost;
      costCount[bar]++;
    }
  }

  for (const rec of bars) {
    if (rec.lastAttemptFrames > 0 && rec.expectedFrames > 0) {
      rec.tempoRatio = rec.expectedFrames / rec.lastAttemptFrames;
    }
    if (costCount[rec.bar] > 0) {
      rec.meanCost = costSum[rec.bar] / costCount[rec.bar];
    }
  }

  const reachedBars = bars.filter((b) => b.reached).length;
  const totalCostCount = costCount.reduce((s, v) => s + v, 0);
  const totalCostSum = costSum.reduce((s, v) => s + v, 0);

  return {
    bars,
    barCount,
    reachedBars,
    furthestBar,
    completion: barCount > 0 ? reachedBars / barCount : 0,
    completed: barCount > 0 && furthestBar >= barCount - 1,
    medianTempoRatio: median(bars.map((b) => b.tempoRatio)),
    totalRestarts: bars.reduce((s, b) => s + b.restartsTo, 0),
    totalHoldFrames: bars.reduce((s, b) => s + b.longestHoldFrames, 0),
    durationMs: (path.length / live.frameRate) * 1000,
    meanCost: totalCostCount > 0 ? totalCostSum / totalCostCount : NaN,
  };
}

// The bars a player struggled with most, worst first. This is what the
// practice view shows and what a future difficulty model consumes.
//
// The score deliberately mixes evidence of *effort* (playing under
// tempo, holding, going back) rather than evidence of *error*: we do
// not detect wrong notes, and per spec §4 as amended we are not trying
// to. A bar that took three attempts and came out at half speed is hard
// whether or not every note in it was right.
export function hardestBars(
  analysis: TakeAnalysis,
  limit = 5,
): { bar: number; score: number; reason: string }[] {
  const scored = analysis.bars
    .filter((b) => b.reached && b.expectedFrames > 0)
    .map((b) => {
      const slowdown = Number.isFinite(b.tempoRatio)
        ? Math.max(0, 1 / Math.max(b.tempoRatio, 0.05) - 1)
        : 0;
      const hold = b.longestHoldFrames / Math.max(b.expectedFrames, 1);
      const retry = Math.max(0, b.attempts - 1);
      const score = slowdown + hold + retry;

      const reasons: string[] = [];
      if (retry > 0) reasons.push(`${b.attempts} attempts`);
      if (slowdown > 0.15) {
        reasons.push(`${Math.round((1 / b.tempoRatio) * 100)}% of written time`);
      }
      if (hold > 0.15) reasons.push("held");
      return {
        bar: b.bar,
        score,
        reason: reasons.length ? reasons.join(", ") : "clean",
      };
    })
    .filter((b) => b.score > 0)
    .sort((a, b) => b.score - a.score);

  return scored.slice(0, limit);
}
