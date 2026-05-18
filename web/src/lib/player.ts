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
  // MusicXML reader falls back to program 0 (piano). Force the nylon
  // guitar patch on every track at load time.
  const NYLON_GUITAR_PROGRAM = 24;
  api.scoreLoaded.on((score) => {
    for (const track of score.tracks) {
      track.playbackInfo.program = NYLON_GUITAR_PROGRAM;
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
      return r.arrayBuffer();
    })
    .then((buf) => api.load(new Uint8Array(buf)))
    .catch((e) => cb.onError?.(e));

  return {
    api,
    destroy: () => api.destroy(),
  };
}
