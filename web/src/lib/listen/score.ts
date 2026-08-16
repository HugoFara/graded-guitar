// alphaTab score -> alignment reference.
//
// The only module in `listen/` that imports alphaTab. Everything
// downstream works on plain note/bar/tempo data so the alignment core
// stays testable without a rendering engine.

import * as alphaTab from "@coderline/alphatab";
import {
  buildReference,
  FRAME_RATE,
  type BarSpan,
  type NoteEvent,
  type Reference,
} from "./reference";
import { TempoMap, type TempoChange } from "./tempo";

// alphaTab's internal MIDI resolution. Not exposed on the public type
// surface, so `ticksPerQuarterOf` derives it from the score's own bar
// arithmetic and falls back to this.
export const DEFAULT_TICKS_PER_QUARTER = 960;

// Derived rather than assumed: a bar's tick duration and its time
// signature determine the resolution, so the score checks itself.
export function ticksPerQuarterOf(score: alphaTab.model.Score): number {
  for (const mb of score.masterBars) {
    const duration = mb.calculateDuration();
    const num = mb.timeSignatureNumerator;
    const den = mb.timeSignatureDenominator;
    if (duration > 0 && num > 0 && den > 0) {
      const tpq = (duration * den) / (num * 4);
      if (Number.isFinite(tpq) && tpq > 0) return tpq;
    }
  }
  return DEFAULT_TICKS_PER_QUARTER;
}

export function barsFromScore(score: alphaTab.model.Score): BarSpan[] {
  return score.masterBars.map((mb) => ({
    startTick: mb.start,
    durationTicks: mb.calculateDuration(),
  }));
}

// Every sounding note across every track. The microphone hears the
// whole texture, so the reference has to contain it — restricting to
// one track would leave the bass voice unexplained and drag the
// alignment toward whichever frames happen to be sparse.
//
// Transposition is deliberately ignored. Classical guitar parts carry
// <octave-change>-1</octave-change> (see lib/player.ts), and chroma is
// octave-blind, so an octave transposition cannot change the reference.
// A chromatic transposition would, but guitar notation does not use one.
export function notesFromScore(score: alphaTab.model.Score): NoteEvent[] {
  const notes: NoteEvent[] = [];
  for (const track of score.tracks) {
    for (const staff of track.staves) {
      for (const bar of staff.bars) {
        for (const voice of bar.voices) {
          for (const beat of voice.beats) {
            if (beat.isRest) continue;
            const startTick = beat.absolutePlaybackStart;
            const endTick = startTick + beat.playbackDuration;
            if (!(endTick > startTick)) continue;
            for (const note of beat.notes) {
              // Dead (muted) notes are percussive clicks with no pitch
              // to match. Ghost notes are barely sounded and would add
              // reference energy the microphone will not hear.
              if (note.isDead || note.isGhost) continue;
              // Tie destinations are kept: they are the sustained part
              // of a held note, and dropping them would leave the
              // reference silent exactly where the note is still ringing.
              notes.push({ startTick, endTick, midi: note.realValue });
            }
          }
        }
      }
    }
  }
  return notes;
}

export function tempoMapFromScore(score: alphaTab.model.Score): TempoMap {
  const tpq = ticksPerQuarterOf(score);
  const changes: TempoChange[] = [{ tick: 0, bpm: score.tempo }];

  for (const mb of score.masterBars) {
    const automations = mb.tempoAutomations ?? [];
    for (const automation of automations) {
      if (automation.type !== alphaTab.model.AutomationType.Tempo) continue;
      // ratioPosition is the fraction of the way through the bar.
      const tick = mb.start + automation.ratioPosition * mb.calculateDuration();
      changes.push({ tick, bpm: automation.value });
    }
  }

  return new TempoMap(tpq, changes, score.tempo);
}

export function referenceFromScore(
  score: alphaTab.model.Score,
  frameRate: number = FRAME_RATE,
): Reference {
  return buildReference(
    notesFromScore(score),
    barsFromScore(score),
    tempoMapFromScore(score),
    frameRate,
  );
}

// Reference frame -> score tick, for driving alphaTab's cursor from the
// follower's position.
export function tickAtFrame(ref: Reference, frame: number): number {
  if (ref.frameCount === 0) return 0;
  const clamped = Math.min(Math.max(frame, 0), ref.frameCount - 1);
  return ref.frameTick[clamped];
}
