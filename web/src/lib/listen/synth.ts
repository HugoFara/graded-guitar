// Synthetic performances with known ground truth.
//
// Spec §7 M8's stop condition is stated against this generator: if the
// aligner cannot localize an injected hesitation, tempo change and
// restart to within one bar of where they were injected, it is
// measuring itself rather than the player, and its output must not
// reach the M2 label set.
//
// Not test-only. It is the harness the milestone is evaluated with, and
// it is the only way to check alignment against truth we actually know
// — a real take's ground truth has to be hand-annotated bar by bar.

import { CHROMA_BINS } from "./chroma";
import type { LiveFrames } from "./align";
import type { Reference } from "./reference";

export type Perturbation =
  // Player stalls on one position for `frames` live frames.
  | { kind: "hesitate"; atRefFrame: number; frames: number }
  // Player plays [fromRefFrame, toRefFrame) at `ratio` times the
  // written tempo. ratio < 1 is slower, > 1 is faster.
  | { kind: "tempo"; fromRefFrame: number; toRefFrame: number; ratio: number }
  // Player breaks off and starts again from an earlier position.
  | { kind: "restart"; atRefFrame: number; backToRefFrame: number }
  // Player stops making sound for `frames` live frames.
  | { kind: "silence"; atRefFrame: number; frames: number };

export type SynthOptions = {
  // Per-bin uniform noise added before renormalizing, as a fraction of
  // the frame's own scale. Real captures carry room tone, string buzz
  // and nail attack; a follower tuned against noiseless input is tuned
  // against a signal it will never see.
  noise: number;
  seed: number;
};

export const DEFAULT_SYNTH_OPTIONS: SynthOptions = { noise: 0.05, seed: 1 };

// mulberry32 — small, fast, and deterministic across runs so a failing
// alignment test fails the same way twice.
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export type SynthResult = {
  live: LiveFrames;
  // Reference frame each live frame truly came from, or -1 for frames
  // the player was silent through. Comparisons must skip the -1s: the
  // aligner has no positional evidence there and should not be scored
  // on guessing.
  truth: Int32Array;
};

// Guards against a restart perturbation that jumps backwards forever.
const MAX_LIVE_FRAMES = 200_000;

export function synthesizePerformance(
  ref: Reference,
  perturbations: Perturbation[] = [],
  options: Partial<SynthOptions> = {},
): SynthResult {
  const opts = { ...DEFAULT_SYNTH_OPTIONS, ...options };
  const rand = mulberry32(opts.seed);

  const tempos = perturbations.filter(
    (p): p is Extract<Perturbation, { kind: "tempo" }> => p.kind === "tempo",
  );
  const points = perturbations.filter((p) => p.kind !== "tempo");
  const fired = new Set<number>();

  const truthList: number[] = [];
  let pos = 0;

  while (pos < ref.frameCount && truthList.length < MAX_LIVE_FRAMES) {
    const i = Math.floor(pos);

    let jumped = false;
    for (let pi = 0; pi < points.length; pi++) {
      if (fired.has(pi)) continue;
      const p = points[pi];
      if (p.atRefFrame !== i) continue;
      fired.add(pi);
      if (p.kind === "hesitate") {
        for (let k = 0; k < p.frames; k++) truthList.push(i);
      } else if (p.kind === "silence") {
        for (let k = 0; k < p.frames; k++) truthList.push(-1);
      } else if (p.kind === "restart") {
        pos = p.backToRefFrame;
        jumped = true;
        break;
      }
    }
    if (jumped) continue;

    const region = tempos.find((t) => i >= t.fromRefFrame && i < t.toRefFrame);
    const ratio = region && region.ratio > 0 ? region.ratio : 1;

    truthList.push(i);
    pos += ratio;
  }

  const truth = Int32Array.from(truthList);
  const frameCount = truth.length;
  const frames = new Float32Array(frameCount * CHROMA_BINS);
  const silent = new Uint8Array(frameCount);

  for (let t = 0; t < frameCount; t++) {
    const src = truth[t];
    if (src < 0) {
      silent[t] = 1;
      continue;
    }
    let ss = 0;
    for (let c = 0; c < CHROMA_BINS; c++) {
      const v = Math.max(
        0,
        ref.frames[src * CHROMA_BINS + c] + (rand() - 0.5) * 2 * opts.noise,
      );
      frames[t * CHROMA_BINS + c] = v;
      ss += v * v;
    }
    // A reference frame with no notes sounding is all zeros; noise can
    // leave it non-zero but meaningless, so mark it silent to match what
    // the capture gate would have done.
    if (ss <= 0) {
      silent[t] = 1;
      continue;
    }
    const inv = 1 / Math.sqrt(ss);
    for (let c = 0; c < CHROMA_BINS; c++) frames[t * CHROMA_BINS + c] *= inv;
  }

  return {
    live: { frames, frameCount, silent, frameRate: ref.frameRate },
    truth,
  };
}
