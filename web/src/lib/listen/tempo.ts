// Tick <-> millisecond conversion across a score's tempo changes.
//
// The reference is sampled uniformly in *time*, not in ticks. That
// matters: a uniform-tick reference would read a written ritardando as
// the player slowing down, and the whole point of the stumble map is to
// separate what the score asks for from what the player did. Sampling
// in time puts the composer's tempo on the reference side, so the
// aligner's warp measures only the player's departure from it.

export type TempoChange = {
  tick: number;
  bpm: number;
};

type Segment = {
  startTick: number;
  startMs: number;
  msPerTick: number;
};

export class TempoMap {
  readonly ticksPerQuarter: number;
  private readonly segments: Segment[];

  // `changes` need not be sorted and need not include a tick-0 entry;
  // the constructor sorts, and prepends `fallbackBpm` if the score does
  // not declare a tempo at its start. Non-positive or non-finite BPMs
  // are dropped rather than propagating Infinity through every
  // downstream timestamp.
  constructor(
    ticksPerQuarter: number,
    changes: TempoChange[],
    fallbackBpm = 120,
  ) {
    this.ticksPerQuarter = ticksPerQuarter > 0 ? ticksPerQuarter : 960;

    const clean = changes
      .filter((c) => Number.isFinite(c.tick) && c.tick >= 0)
      .filter((c) => Number.isFinite(c.bpm) && c.bpm > 0)
      .sort((a, b) => a.tick - b.tick);

    if (!clean.length || clean[0].tick > 0) {
      clean.unshift({ tick: 0, bpm: fallbackBpm > 0 ? fallbackBpm : 120 });
    }

    this.segments = [];
    let ms = 0;
    for (let i = 0; i < clean.length; i++) {
      const { tick, bpm } = clean[i];
      // Two changes on the same tick: the later one wins, which is what
      // a reader does with a redundant tempo marking.
      if (i > 0 && tick === clean[i - 1].tick) {
        this.segments.pop();
      } else if (i > 0) {
        const prev = this.segments[this.segments.length - 1];
        ms = prev.startMs + (tick - prev.startTick) * prev.msPerTick;
      }
      this.segments.push({
        startTick: tick,
        startMs: ms,
        msPerTick: 60000 / (bpm * this.ticksPerQuarter),
      });
    }
  }

  private segmentForTick(tick: number): Segment {
    let lo = 0;
    let hi = this.segments.length - 1;
    while (lo < hi) {
      const mid = (lo + hi + 1) >> 1;
      if (this.segments[mid].startTick <= tick) lo = mid;
      else hi = mid - 1;
    }
    return this.segments[lo];
  }

  private segmentForMs(ms: number): Segment {
    let lo = 0;
    let hi = this.segments.length - 1;
    while (lo < hi) {
      const mid = (lo + hi + 1) >> 1;
      if (this.segments[mid].startMs <= ms) lo = mid;
      else hi = mid - 1;
    }
    return this.segments[lo];
  }

  tickToMs(tick: number): number {
    const t = tick < 0 ? 0 : tick;
    const seg = this.segmentForTick(t);
    return seg.startMs + (t - seg.startTick) * seg.msPerTick;
  }

  msToTick(ms: number): number {
    const m = ms < 0 ? 0 : ms;
    const seg = this.segmentForMs(m);
    return seg.startTick + (m - seg.startMs) / seg.msPerTick;
  }
}
