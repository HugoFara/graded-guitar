import * as alphaTab from "@coderline/alphatab";

export type PlayerHandles = {
  api: alphaTab.AlphaTabApi;
  destroy: () => void;
};

export type PlayerCallbacks = {
  onPositionChanged?: (currentTickPos: number, totalTicks: number, currentTime: number, endTime: number) => void;
  onPlayerStateChanged?: (state: number) => void;
  onScoreLoaded?: (score: alphaTab.model.Score) => void;
  onRenderFinished?: () => void;
  onError?: (err: unknown) => void;
};

// MusicXML's <transpose> element tells a reader: "written pitch is N
// semitones higher than sounding pitch." Classical guitar parts almost
// always carry <octave-change>-1</octave-change> because guitar music
// is notated in treble clef but sounds 8va bassa. alphaTab honors the
// transpose for rendering but plays the MIDI at written pitch — so we
// extract the offset ourselves and apply it to playback after load.
//
// Per spec, <transpose> can live at part/measure level; in our corpus
// every file has a single global transpose declaration, so we take the
// first occurrence and apply it to every track. Multi-instrument scores
// are not part of the M3 corpus.
export function parseTransposeSemitones(xmlText: string): number {
  const block = xmlText.match(/<transpose\b[^>]*>([\s\S]*?)<\/transpose>/);
  if (!block) return 0;
  const chromatic = parseInt(
    block[1].match(/<chromatic>(-?\d+)<\/chromatic>/)?.[1] ?? "0",
    10,
  );
  const octave = parseInt(
    block[1].match(/<octave-change>(-?\d+)<\/octave-change>/)?.[1] ?? "0",
    10,
  );
  const safe = (n: number) => (Number.isFinite(n) ? n : 0);
  return safe(chromatic) + 12 * safe(octave);
}

export function mountPlayer(
  element: HTMLElement,
  musicXmlUrl: string,
  cb: PlayerCallbacks,
): PlayerHandles {
  const base = (import.meta.env.BASE_URL ?? "/").replace(/\/$/, "");
  const settings: alphaTab.Settings = new alphaTab.Settings();
  settings.core.engine = "svg";
  // The alphatab-vite plugin copies fonts/soundfont to publicDir (→ dist/),
  // not the asset bundle dir, so alphaTab's auto-detected paths (relative to
  // its worker's import.meta.url under /assets/) miss them. Override.
  settings.core.fontDirectory = `${base}/font/`;
  // alphaTab dims secondary voices to 40% by default; for classical guitar
  // music voice 2 is the bass line, not a hint — render at full opacity.
  settings.display.resources.secondaryGlyphColor = new alphaTab.model.Color(0, 0, 0, 255);
  settings.player.enablePlayer = true;
  settings.player.enableCursor = true;
  settings.player.enableUserInteraction = true;
  settings.player.scrollMode = alphaTab.ScrollMode.OffScreen;
  settings.player.soundFont = `${base}/soundfont/sonivox.sf2`;
  settings.notation.elements.set(alphaTab.NotationElement.GuitarTuning, false);

  const api = new alphaTab.AlphaTabApi(element, settings);

  // Guitarloot MusicXML declares "Acoustic Guitar (nylon)" via
  // <instrument-sound> but never sets <midi-program>, so alphaTab's
  // MusicXML reader leaves the track at program 0 (piano). Setting
  // `playbackInfo.program` after scoreLoaded is too late — the MIDI
  // file is already generated. Inject a program-change event at tick 0
  // on every track once the MIDI file is built.
  const NYLON_GUITAR_PROGRAM = 24;
  api.scoreLoaded.on((score) => {
    for (const track of score.tracks) {
      track.playbackInfo.program = NYLON_GUITAR_PROGRAM;
    }
  });
  api.midiLoad.on((midi) => {
    const tracks = api.tracks ?? [];
    for (let i = 0; i < tracks.length; i++) {
      const ch = tracks[i].playbackInfo.primaryChannel;
      midi.addEvent(
        new alphaTab.midi.ProgramChangeEvent(i, 0, ch, NYLON_GUITAR_PROGRAM),
      );
    }
  });

  if (cb.onScoreLoaded) api.scoreLoaded.on(cb.onScoreLoaded);
  if (cb.onPositionChanged) {
    api.playerPositionChanged.on((e) => {
      cb.onPositionChanged!(e.currentTick, e.endTick, e.currentTime, e.endTime);
    });
  }
  if (cb.onPlayerStateChanged) {
    api.playerStateChanged.on((e) => cb.onPlayerStateChanged!(e.state));
  }
  if (cb.onRenderFinished) api.renderFinished.on(cb.onRenderFinished);
  if (cb.onError) api.error.on(cb.onError);

  fetch(musicXmlUrl)
    .then((r) => {
      if (!r.ok) throw new Error(`${musicXmlUrl}: ${r.status}`);
      return r.text();
    })
    .then((xmlText) => {
      const transposeSemis = parseTransposeSemitones(xmlText);
      if (transposeSemis !== 0) {
        api.scoreLoaded.on((score) => {
          api.changeTrackTranspositionPitch(score.tracks, transposeSemis);
        });
      }
      api.load(new TextEncoder().encode(xmlText));
    })
    .catch((e) => cb.onError?.(e));

  return {
    api,
    destroy: () => api.destroy(),
  };
}
