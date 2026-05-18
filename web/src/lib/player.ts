import * as alphaTab from "@coderline/alphatab";

export type PlayerHandles = {
  api: alphaTab.AlphaTabApi;
  destroy: () => void;
};

export type PlayerCallbacks = {
  onPositionChanged?: (currentTickPos: number, totalTicks: number, currentTime: number, endTime: number) => void;
  onPlayerStateChanged?: (state: number) => void;
  onScoreLoaded?: (score: alphaTab.model.Score) => void;
  onError?: (err: unknown) => void;
};

export function mountPlayer(
  element: HTMLElement,
  musicXmlUrl: string,
  cb: PlayerCallbacks,
): PlayerHandles {
  const settings: alphaTab.Settings = new alphaTab.Settings();
  settings.core.engine = "svg";
  settings.player.enablePlayer = true;
  settings.player.enableCursor = true;
  settings.player.enableUserInteraction = true;
  settings.player.scrollMode = alphaTab.ScrollMode.OffScreen;
  settings.notation.elements.set(alphaTab.NotationElement.GuitarTuning, false);

  const api = new alphaTab.AlphaTabApi(element, settings);

  if (cb.onScoreLoaded) api.scoreLoaded.on(cb.onScoreLoaded);
  if (cb.onPositionChanged) {
    api.playerPositionChanged.on((e) => {
      cb.onPositionChanged!(e.currentTick, e.endTick, e.currentTime, e.endTime);
    });
  }
  if (cb.onPlayerStateChanged) {
    api.playerStateChanged.on((e) => cb.onPlayerStateChanged!(e.state));
  }
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
