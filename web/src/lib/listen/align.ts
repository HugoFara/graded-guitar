// Score alignment as hidden-state inference over reference position.
//
// Why not DTW: DTW paths are monotonic, and "the player went back to
// bar 5 and started again" is not a monotonic path. No amount of band
// tuning expresses a restart. Restarts, repeated practice loops and
// skipped passages are the *point* of the stumble map, so the model has
// to be able to represent them.
//
// The model is a discrete HMM over reference frame index:
//
//   - emission: chroma cosine distance between the reference frame and
//     the live frame, scaled into a log-likelihood;
//   - transition: advance 0..3 reference frames per live frame, which
//     covers holding (hesitation) through playing at 3x written tempo;
//   - plus a small uniform jump-anywhere probability, which is the term
//     that makes restarts representable at all.
//
// One model, two decodings (ADR 0018):
//
//   - OnlineFollower — forward filtering, drives the live cursor.
//   - viterbiAlign   — offline, drives every recorded measurement.
//
// All measurements come from the offline pass. A live follower that
// loses its place produces a trace indistinguishable from a player who
// stumbled, and it loses its place in exactly the hard passages where
// the grading signal matters most.

import { FEATURE_DIM, cosineDistanceAt, normalizeFeature } from "./chroma";
import type { Reference } from "./reference";

export type LiveFrames = {
  // frameCount * FEATURE_DIM, row-major, each row band-normalized.
  frames: Float32Array;
  frameCount: number;
  // 1 where the frame fell below the capture energy gate. Silent frames
  // emit a flat likelihood rather than matching whatever reference
  // frame happens to be quiet — see emission handling below.
  silent: Uint8Array;
  frameRate: number;
};

export type AlignOptions = {
  // Emission temperature. Cosine distance is in [0, 1]; dividing by
  // sigma turns it into a log-likelihood. Smaller = sharper = trusts
  // the audio more and the transition prior less.
  sigma: number;
  // Per-step transition weights for advancing d = 0..3 reference frames
  // per live frame. d=1 is playing at written tempo, d=0 is holding,
  // d>=2 is rushing. Normalized internally.
  stepWeights: number[];
  // Probability mass on "jump to an arbitrary reference position".
  // Small: a genuine restart produces sustained evidence and overcomes
  // this prior within a few frames, whereas a single noisy frame should
  // not be able to teleport the cursor.
  jumpProb: number;
};

export const DEFAULT_ALIGN_OPTIONS: AlignOptions = {
  sigma: 0.12,
  stepWeights: [0.15, 0.6, 0.2, 0.05],
  jumpProb: 1e-5,
};

const NEG_INF = -Infinity;

function logAddExp(a: number, b: number): number {
  if (a === NEG_INF) return b;
  if (b === NEG_INF) return a;
  const hi = a > b ? a : b;
  const lo = a > b ? b : a;
  return hi + Math.log1p(Math.exp(lo - hi));
}

function normalizedLogWeights(weights: number[]): Float64Array {
  const safe = weights.map((w) => (Number.isFinite(w) && w > 0 ? w : 0));
  const total = safe.reduce((s, w) => s + w, 0);
  const out = new Float64Array(safe.length);
  for (let i = 0; i < safe.length; i++) {
    out[i] = total > 0 && safe[i] > 0 ? Math.log(safe[i] / total) : NEG_INF;
  }
  return out;
}

// Start-of-take prior. Players usually begin at the beginning, but not
// always — picking up mid-piece is ordinary practice behaviour. Mass is
// concentrated on the opening with a uniform floor everywhere else, so
// starting at bar 30 costs a little evidence rather than being ruled
// out.
function buildLogPrior(frameCount: number, frameRate: number): Float64Array {
  const prior = new Float64Array(frameCount);
  const head = Math.min(frameCount, Math.max(1, Math.round(frameRate * 0.5)));
  const headMass = 0.9;
  const tailCount = frameCount - head;
  const floor = tailCount > 0 ? (1 - headMass) / tailCount : 0;
  for (let i = 0; i < frameCount; i++) {
    const p = i < head ? headMass / head : floor;
    prior[i] = p > 0 ? Math.log(p) : NEG_INF;
  }
  return prior;
}

// Writes the emission log-likelihood of every reference state for one
// live frame. A silent live frame yields a flat vector: silence carries
// no positional information, and letting it match quiet reference
// frames is how a follower drifts through rests.
function fillEmission(
  out: Float64Array,
  ref: Reference,
  live: LiveFrames,
  t: number,
  sigma: number,
): void {
  if (live.silent[t]) {
    out.fill(0);
    return;
  }
  const liveOffset = t * FEATURE_DIM;
  for (let i = 0; i < ref.frameCount; i++) {
    out[i] = -cosineDistanceAt(ref.frames, i * FEATURE_DIM, live.frames, liveOffset) / sigma;
  }
}

// ---------------------------------------------------------------------
// Online: forward filtering for the live cursor.
// ---------------------------------------------------------------------

export class OnlineFollower {
  private readonly ref: Reference;
  private readonly opts: AlignOptions;
  private readonly logStep: Float64Array;
  private readonly logJump: number;
  private readonly logStay: number;
  private alpha: Float64Array;
  private next: Float64Array;
  private emission: Float64Array;
  private started = false;

  // MAP reference frame after the most recent step. Raw argmax — this
  // is the honest estimate, and it jitters when the posterior is
  // diffuse.
  position = 0;
  // Hysteresis-smoothed position, for driving the cursor.
  //
  // On repetitive material the posterior spreads over many bars and the
  // raw argmax teleports frame to frame, which reads to a player as
  // "it lost me" even when the distribution is broadly right. A distant
  // jump therefore has to be supported for JUMP_HOLD_FRAMES in a row
  // before the cursor follows it; until then the cursor keeps advancing
  // at written tempo. Genuine restarts produce sustained evidence and
  // still land, about half a second late.
  //
  // This smooths the *display* only. Measurements come from the offline
  // Viterbi pass and never see this value.
  displayPosition = 0;
  // Posterior mass on the MAP state, in [0, 1]. Low values mean the
  // follower is unsure — the UI dims the cursor rather than lying about
  // a position it does not have.
  confidence = 0;

  constructor(ref: Reference, opts: Partial<AlignOptions> = {}) {
    this.ref = ref;
    this.opts = { ...DEFAULT_ALIGN_OPTIONS, ...opts };
    this.logStep = normalizedLogWeights(this.opts.stepWeights);
    const jump = Math.min(Math.max(this.opts.jumpProb, 0), 0.5);
    this.logJump = jump > 0 ? Math.log(jump) : NEG_INF;
    this.logStay = Math.log(1 - jump);
    this.alpha = buildLogPrior(ref.frameCount, ref.frameRate);
    this.next = new Float64Array(ref.frameCount);
    this.emission = new Float64Array(ref.frameCount);
  }

  reset(): void {
    this.alpha = buildLogPrior(this.ref.frameCount, this.ref.frameRate);
    this.started = false;
    this.position = 0;
    this.displayPosition = 0;
    this.confidence = 0;
    this.pendingJumpTarget = -1;
    this.pendingJumpFrames = 0;
  }

  // Consumes one live frame and returns the MAP reference frame index.
  step(chroma: Float32Array, offset: number, silent: boolean): number {
    const n = this.ref.frameCount;
    const live: LiveFrames = {
      frames: chroma,
      frameCount: 1,
      silent: Uint8Array.of(silent ? 1 : 0),
      frameRate: this.ref.frameRate,
    };
    // fillEmission indexes live frames by t*FEATURE_DIM; hand it a view
    // starting at the caller's offset so the single-frame case does not
    // need its own code path.
    fillEmission(
      this.emission,
      this.ref,
      { ...live, frames: chroma.subarray(offset, offset + FEATURE_DIM) },
      0,
      this.opts.sigma,
    );

    if (!this.started) {
      for (let i = 0; i < n; i++) this.alpha[i] += this.emission[i];
      this.started = true;
    } else {
      // Total mass, for the uniform jump term.
      let total = NEG_INF;
      for (let i = 0; i < n; i++) total = logAddExp(total, this.alpha[i]);
      const jumpTerm = this.logJump + total - Math.log(n);

      for (let j = 0; j < n; j++) {
        let acc = NEG_INF;
        for (let d = 0; d < this.logStep.length; d++) {
          const from = j - d;
          if (from < 0) break;
          const w = this.logStep[d];
          if (w === NEG_INF) continue;
          acc = logAddExp(acc, this.alpha[from] + w);
        }
        this.next[j] = logAddExp(this.logStay + acc, jumpTerm) + this.emission[j];
      }
      const tmp = this.alpha;
      this.alpha = this.next;
      this.next = tmp;
    }

    // Renormalize to keep the vector away from underflow, and read off
    // the MAP state and its posterior mass in the same pass.
    let max = NEG_INF;
    let argmax = 0;
    for (let i = 0; i < n; i++) {
      if (this.alpha[i] > max) {
        max = this.alpha[i];
        argmax = i;
      }
    }
    let sum = 0;
    let nearby = 0;
    // Posterior mass within a bar of the MAP state, not on the MAP state
    // itself.
    //
    // Single-state mass is the wrong quantity here and reads as failure
    // when nothing has failed: over several thousand reference frames, a
    // posterior correctly concentrated on a 20-frame neighbourhood still
    // puts only a few percent on any one frame. Measured on a synthetic
    // take the follower tracked perfectly for all 640 frames, the old
    // metric had a median of 0.28 and showed "locked" on under 10% of
    // them. What the player needs to know is whether the follower knows
    // the bar, so that is what we report.
    const window = Math.round(this.ref.frameCount / Math.max(this.ref.barCount, 1));
    for (let i = 0; i < n; i++) {
      this.alpha[i] -= max;
      const p = Math.exp(this.alpha[i]);
      sum += p;
      if (Math.abs(i - argmax) <= window) nearby += p;
    }
    this.position = argmax;
    this.confidence = sum > 0 ? nearby / sum : 0;
    this.updateDisplay(argmax, window);
    return argmax;
  }

  // Frames a distant MAP has to persist before the cursor follows it.
  // At 20 Hz this is half a second — long enough to reject single-frame
  // excursions on ambiguous material, short enough that a real restart
  // does not feel broken.
  private static readonly JUMP_HOLD_FRAMES = 10;
  private pendingJumpTarget = -1;
  private pendingJumpFrames = 0;

  private updateDisplay(argmax: number, window: number): void {
    const near = Math.abs(argmax - this.displayPosition) <= Math.max(window, 4);
    if (near) {
      this.displayPosition = argmax;
      this.pendingJumpFrames = 0;
      this.pendingJumpTarget = -1;
      return;
    }
    // Distant MAP: only follow it once it has held roughly still for
    // long enough to be a real move rather than posterior jitter.
    if (
      this.pendingJumpTarget >= 0 &&
      Math.abs(argmax - this.pendingJumpTarget) <= Math.max(window, 4)
    ) {
      this.pendingJumpFrames++;
    } else {
      this.pendingJumpTarget = argmax;
      this.pendingJumpFrames = 1;
    }
    if (this.pendingJumpFrames >= OnlineFollower.JUMP_HOLD_FRAMES) {
      this.displayPosition = argmax;
      this.pendingJumpFrames = 0;
      this.pendingJumpTarget = -1;
    } else if (this.displayPosition < this.ref.frameCount - 1) {
      // Coast forward at written tempo rather than freezing, so the
      // cursor keeps moving with the player while the evidence settles.
      this.displayPosition++;
    }
  }
}

// ---------------------------------------------------------------------
// Offline: Viterbi, the measurement path.
// ---------------------------------------------------------------------

export type Alignment = {
  // Reference frame index chosen for each live frame.
  path: Int32Array;
  // Cosine distance at each chosen (reference, live) pair. Silent live
  // frames carry NaN — they were not matched on evidence.
  frameCost: Float32Array;
  logProb: number;
};

// Backpointer encoding: 0..3 is "advanced d frames from j-d", JUMP means
// "arrived from the best state of the previous step". The jump source is
// the argmax over all states, which is the same for every j at a given
// t, so it costs one entry per live frame rather than one per cell.
const JUMP = 255;

// Backpointers dominate memory: one byte per (live frame x reference
// frame). A five-minute piece played straight through is ~36 MB, which
// is fine; a take three times the length of the score is not. Callers
// over budget should decimate with `decimateFrames` before aligning.
export const VITERBI_CELL_BUDGET = 120_000_000;

export function viterbiAlign(
  ref: Reference,
  live: LiveFrames,
  opts: Partial<AlignOptions> = {},
): Alignment {
  const o = { ...DEFAULT_ALIGN_OPTIONS, ...opts };
  const n = ref.frameCount;
  const t = live.frameCount;

  if (n === 0 || t === 0) {
    return { path: new Int32Array(0), frameCost: new Float32Array(0), logProb: NEG_INF };
  }
  const cells = n * t;
  if (cells > VITERBI_CELL_BUDGET) {
    throw new RangeError(
      `alignment too large: ${n} reference x ${t} live frames = ${cells} cells ` +
        `exceeds budget ${VITERBI_CELL_BUDGET}; decimate before aligning`,
    );
  }

  const logStep = normalizedLogWeights(o.stepWeights);
  const jump = Math.min(Math.max(o.jumpProb, 0), 0.5);
  const logJump = jump > 0 ? Math.log(jump) : NEG_INF;
  const logStay = Math.log(1 - jump);

  const back = new Uint8Array(cells);
  const jumpSource = new Int32Array(t);
  const emission = new Float64Array(n);
  // Annotated rather than inferred: the two buffers are swapped each
  // step, and inference pins one of them to a narrower ArrayBuffer type
  // that the swap then violates.
  let delta: Float64Array = buildLogPrior(n, ref.frameRate);
  let next: Float64Array = new Float64Array(n);

  fillEmission(emission, ref, live, 0, o.sigma);
  for (let i = 0; i < n; i++) delta[i] += emission[i];

  for (let step = 1; step < t; step++) {
    fillEmission(emission, ref, live, step, o.sigma);

    // Best jump-in predecessor is the argmax over all states, shared by
    // every destination.
    let bestPrev = NEG_INF;
    let bestPrevIdx = 0;
    for (let i = 0; i < n; i++) {
      if (delta[i] > bestPrev) {
        bestPrev = delta[i];
        bestPrevIdx = i;
      }
    }
    jumpSource[step] = bestPrevIdx;
    const jumpScore = logJump + bestPrev - Math.log(n);
    const rowOffset = step * n;

    for (let j = 0; j < n; j++) {
      let best = NEG_INF;
      let bestD = 0;
      for (let d = 0; d < logStep.length; d++) {
        const from = j - d;
        if (from < 0) break;
        const w = logStep[d];
        if (w === NEG_INF) continue;
        const score = delta[from] + w;
        if (score > best) {
          best = score;
          bestD = d;
        }
      }
      const local = best === NEG_INF ? NEG_INF : logStay + best;
      if (jumpScore > local) {
        next[j] = jumpScore + emission[j];
        back[rowOffset + j] = JUMP;
      } else {
        next[j] = local + emission[j];
        back[rowOffset + j] = bestD;
      }
    }

    // Renormalize by the running max so long takes do not underflow.
    let max = NEG_INF;
    for (let j = 0; j < n; j++) if (next[j] > max) max = next[j];
    if (max > NEG_INF) for (let j = 0; j < n; j++) next[j] -= max;

    const tmp = delta;
    delta = next;
    next = tmp;
  }

  let endBest = NEG_INF;
  let endIdx = 0;
  for (let i = 0; i < n; i++) {
    if (delta[i] > endBest) {
      endBest = delta[i];
      endIdx = i;
    }
  }

  const path = new Int32Array(t);
  let cur = endIdx;
  for (let step = t - 1; step >= 0; step--) {
    path[step] = cur;
    if (step === 0) break;
    const bp = back[step * n + cur];
    cur = bp === JUMP ? jumpSource[step] : cur - bp;
    if (cur < 0) cur = 0;
  }

  const frameCost = new Float32Array(t);
  for (let step = 0; step < t; step++) {
    frameCost[step] = live.silent[step]
      ? NaN
      : cosineDistanceAt(
          ref.frames,
          path[step] * FEATURE_DIM,
          live.frames,
          step * FEATURE_DIM,
        );
  }

  return { path, frameCost, logProb: endBest };
}

// Halves the frame rate by averaging adjacent frames, for takes that
// blow the Viterbi cell budget. Averaging then renormalizing is the
// right operation on chroma: the vector is an energy distribution, so
// the mean of two frames is the distribution over the merged window.
export function decimateFrames(live: LiveFrames): LiveFrames {
  const outCount = Math.ceil(live.frameCount / 2);
  const frames = new Float32Array(outCount * FEATURE_DIM);
  const silent = new Uint8Array(outCount);

  for (let i = 0; i < outCount; i++) {
    const a = 2 * i;
    const b = Math.min(a + 1, live.frameCount - 1);
    for (let c = 0; c < FEATURE_DIM; c++) {
      frames[i * FEATURE_DIM + c] =
        (live.frames[a * FEATURE_DIM + c] + live.frames[b * FEATURE_DIM + c]) / 2;
    }
    normalizeFeature(frames.subarray(i * FEATURE_DIM, (i + 1) * FEATURE_DIM));
    // A merged frame counts as silent only if both halves were: a note
    // attack landing in either half is positional evidence.
    silent[i] = live.silent[a] && live.silent[b] ? 1 : 0;
  }

  return { frames, frameCount: outCount, silent, frameRate: live.frameRate / 2 };
}
