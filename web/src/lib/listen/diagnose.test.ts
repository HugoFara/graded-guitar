// Diagnostic sweep, not a pass/fail suite. Run with:
//   npx vitest run src/lib/listen/diagnose.test.ts --reporter=basic
// It prints tables; the assertions are loose deliberately.
//
// This is the harness that found why the follower lost the player on
// Asturias: chroma self-ambiguity, not tempo. Keep it runnable — the
// next time tracking degrades on some piece, the first question is
// again "how distinguishable are this reference's own frames?"

import { describe, it, expect } from "vitest";
import { buildReference, type BarSpan, type NoteEvent } from "./reference";
import { TempoMap } from "./tempo";
import { synthesizePerformance } from "./synth";
import { viterbiAlign, OnlineFollower } from "./align";
import { FEATURE_DIM, cosineDistanceAt } from "./chroma";

const TPQ = 960;
const BAR_TICKS = TPQ * 4;

// Varied fixture: the one the passing tests use.
function variedReference(bars = 16) {
  const notes: NoteEvent[] = [];
  const spans: BarSpan[] = [];
  for (let b = 0; b < bars; b++) {
    spans.push({ startTick: b * BAR_TICKS, durationTicks: BAR_TICKS });
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
  return buildReference(notes, spans, new TempoMap(TPQ, [{ tick: 0, bpm: 120 }]));
}

// Asturias-shaped: a relentless ostinato. A high pedal alternating with
// a melody that moves once every bar or two, all in one key, over a
// sustained bass. Chroma-wise this is near-identical for bars on end —
// the adversarial case for any alignment that only knows pitch content.
function ostinatoReference(bars = 16) {
  const notes: NoteEvent[] = [];
  const spans: BarSpan[] = [];
  const melody = [59, 59, 59, 59, 60, 60, 59, 59, 57, 57, 59, 59, 59, 59, 59, 59];
  for (let b = 0; b < bars; b++) {
    spans.push({ startTick: b * BAR_TICKS, durationTicks: BAR_TICKS });
    for (let s = 0; s < 16; s++) {
      const t = b * BAR_TICKS + s * (TPQ / 4);
      notes.push({ startTick: t, endTick: t + TPQ / 4, midi: s % 2 === 0 ? 71 : melody[b] });
    }
    notes.push({ startTick: b * BAR_TICKS, endTick: (b + 1) * BAR_TICKS, midi: 40 });
  }
  return buildReference(notes, spans, new TempoMap(TPQ, [{ tick: 0, bpm: 120 }]));
}

function barErrors(
  ref: ReturnType<typeof variedReference>,
  path: Int32Array,
  truth: Int32Array,
): number[] {
  const out: number[] = [];
  for (let t = 0; t < truth.length; t++) {
    if (truth[t] < 0) continue;
    const got = ref.barOfFrame[path[t]];
    const want = ref.barOfFrame[truth[t]];
    if (got < 0 || want < 0) continue;
    out.push(Math.abs(got - want));
  }
  return out;
}

function pct(values: number[], q: number): number {
  if (!values.length) return NaN;
  const s = [...values].sort((a, b) => a - b);
  return s[Math.min(s.length - 1, Math.floor(q * s.length))];
}

// Fraction of frame pairs more than half a bar apart that are
// indistinguishable. High = the piece looks the same everywhere = the
// emission term carries almost no positional information and the
// aligner is running on the transition prior alone.
function selfAmbiguity(ref: ReturnType<typeof variedReference>): number {
  const step = Math.max(1, Math.floor(ref.frameCount / 300));
  const framesPerBar = ref.frameCount / ref.barCount;
  let confusable = 0;
  let compared = 0;
  for (let i = 0; i < ref.frameCount; i += step) {
    for (let j = 0; j < ref.frameCount; j += step) {
      if (Math.abs(i - j) < framesPerBar / 2) continue;
      compared++;
      if (cosineDistanceAt(ref.frames, i * FEATURE_DIM, ref.frames, j * FEATURE_DIM) < 0.05) {
        confusable++;
      }
    }
  }
  return compared > 0 ? confusable / compared : 0;
}

describe("diagnosis: what breaks the follower", () => {
  it("measures self-ambiguity of a varied piece vs an ostinato", () => {
    const varied = selfAmbiguity(variedReference());
    const ostinato = selfAmbiguity(ostinatoReference());
    console.log("\n=== reference self-ambiguity (confusable frame pairs) ===");
    console.log(`  varied fixture : ${(varied * 100).toFixed(1)}%`);
    console.log(`  Asturias-shaped: ${(ostinato * 100).toFixed(1)}%`);
    // Single-band chroma scored 79.5% on the ostinato. The register
    // split has to keep it well under that or it was not worth the
    // widened feature.
    expect(ostinato).toBeLessThan(0.5);
  });

  it("sweeps playing tempo against both decodings", () => {
    for (const [name, ref] of [
      ["varied", variedReference()],
      ["ostinato", ostinatoReference()],
    ] as const) {
      console.log(`\n=== ${name}: bar error by playing tempo ===`);
      console.log("  ratio | offline p50/p95 | raw MAP p50/p95 | cursor p50/p95");
      for (const ratio of [1.0, 0.7, 0.5, 0.35]) {
        const { live, truth } = synthesizePerformance(
          ref,
          [{ kind: "tempo", fromRefFrame: 0, toRefFrame: ref.frameCount, ratio }],
          { noise: 0.12, seed: 3 },
        );
        const offline = barErrors(ref, viterbiAlign(ref, live).path, truth);

        const follower = new OnlineFollower(ref);
        const rawPath = new Int32Array(live.frameCount);
        const shownPath = new Int32Array(live.frameCount);
        for (let t = 0; t < live.frameCount; t++) {
          rawPath[t] = follower.step(live.frames, t * FEATURE_DIM, live.silent[t] === 1);
          shownPath[t] = follower.displayPosition;
        }
        const online = barErrors(ref, rawPath, truth);
        const shown = barErrors(ref, shownPath, truth);

        console.log(
          `  ${ratio.toFixed(2)}  |    ${pct(offline, 0.5)} / ${pct(offline, 0.95)}      |   ${pct(online, 0.5)} / ${pct(online, 0.95)}   |   ${pct(shown, 0.5)} / ${pct(shown, 0.95)}`,
        );
      }
    }
  });

  it("reports what the confidence readout shows when tracking is fine", () => {
    const ref = variedReference();
    const { live, truth } = synthesizePerformance(ref, [], { noise: 0.12, seed: 5 });
    const follower = new OnlineFollower(ref);
    const samples: { conf: number; err: number }[] = [];
    for (let t = 0; t < live.frameCount; t++) {
      const p = follower.step(live.frames, t * FEATURE_DIM, live.silent[t] === 1);
      if (truth[t] >= 0) {
        samples.push({ conf: follower.confidence, err: Math.abs(p - truth[t]) });
      }
    }
    const tracking = samples.filter((s) => s.err <= 10);
    const confs = tracking.map((s) => s.conf);
    const lockedPct = (confs.filter((c) => c > 0.5).length / confs.length) * 100;
    console.log("\n=== confidence while actually tracking (frame error <= 10) ===");
    console.log(`  frames tracking well: ${tracking.length}/${samples.length}`);
    console.log(
      `  confidence p05/p50/p95: ${pct(confs, 0.05).toFixed(3)} / ${pct(confs, 0.5).toFixed(3)} / ${pct(confs, 0.95).toFixed(3)}`,
    );
    console.log(`  UI shows "locked" (>0.5) on ${lockedPct.toFixed(1)}% of well-tracked frames`);
    console.log(
      `  UI shows "lost"   (<0.15) on ${((confs.filter((c) => c < 0.15).length / confs.length) * 100).toFixed(1)}% of well-tracked frames`,
    );
    // The single-state metric read "locked" on 9.8% of frames it was
    // tracking perfectly. A readout that calls a good run a bad one is
    // worse than no readout.
    expect(lockedPct).toBeGreaterThan(80);
  });
});
