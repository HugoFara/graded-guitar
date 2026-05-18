<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import {
    loadManifest,
    pieceById,
    resolveGrade,
    musicxmlUrl,
    type Piece,
  } from "../lib/manifest";
  import * as alphaTab from "@coderline/alphatab";
  import { mountPlayer, type PlayerHandles } from "../lib/player";
  import GradeBadge from "../components/GradeBadge.svelte";

  type Props = { params?: { cid: string } };
  let { params }: Props = $props();

  let piece = $state<Piece | null>(null);
  let error = $state<string | null>(null);
  let containerEl: HTMLDivElement | undefined = $state();
  let handles: PlayerHandles | null = null;

  let isPlaying = $state(false);
  let tempo = $state(100);
  let showTab = $state(true);
  let renderState = $state<"loading" | "rendered" | "error">("loading");

  let loopStart = $state<number | null>(null);
  let loopEnd = $state<number | null>(null);
  let totalBars = $state<number>(0);

  let positionTick = $state(0);
  let endTick = $state(0);
  let currentTimeMs = $state(0);
  let endTimeMs = $state(0);
  let seeking = $state(false);

  onMount(async () => {
    if (!params?.cid) {
      error = "missing piece id";
      return;
    }
    try {
      const manifest = await loadManifest();
      const found = pieceById(manifest, decodeURIComponent(params.cid));
      if (!found) {
        error = `not found: ${params.cid}`;
        return;
      }
      piece = found;
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  });

  $effect(() => {
    if (!piece || !containerEl || handles) return;
    const url = musicxmlUrl(piece);
    handles = mountPlayer(containerEl, url, {
      onScoreLoaded: (score) => {
        totalBars = score.masterBars.length;
      },
      onRenderFinished: () => {
        renderState = "rendered";
      },
      onPlayerStateChanged: (state) => {
        isPlaying = state === 1;
      },
      onPositionChanged: (curTick, totTick, curMs, totMs) => {
        if (!seeking) {
          positionTick = curTick;
          currentTimeMs = curMs;
        }
        endTick = totTick;
        endTimeMs = totMs;
      },
      onError: (e) => {
        error = e instanceof Error ? e.message : String(e);
        renderState = "error";
      },
    });
  });

  onDestroy(() => handles?.destroy());

  function togglePlay() {
    if (!handles) return;
    if (isPlaying) handles.api.pause();
    else handles.api.play();
  }

  function stop() {
    handles?.api.stop();
  }

  function applyTempo(v: number) {
    if (!handles) return;
    tempo = v;
    handles.api.playbackSpeed = v / 100;
  }

  function toggleTab() {
    if (!handles) return;
    showTab = !showTab;
    handles.api.settings.display.staveProfile = showTab
      ? alphaTab.StaveProfile.ScoreTab
      : alphaTab.StaveProfile.Score;
    handles.api.updateSettings();
    handles.api.render();
  }

  function setLoopStart() {
    if (!handles) return;
    loopStart = handles.api.tickPosition;
  }

  function setLoopEnd() {
    if (!handles) return;
    loopEnd = handles.api.tickPosition;
    applyLoop();
  }

  function clearLoop() {
    if (!handles) return;
    loopStart = null;
    loopEnd = null;
    handles.api.isLooping = false;
  }

  function applyLoop() {
    if (!handles || loopStart == null || loopEnd == null) return;
    if (loopEnd <= loopStart) return;
    handles.api.tickPosition = loopStart;
    handles.api.isLooping = true;
  }

  function onSeekInput(v: number) {
    seeking = true;
    positionTick = v;
  }

  function onSeekCommit(v: number) {
    if (!handles) return;
    handles.api.tickPosition = v;
    positionTick = v;
    seeking = false;
  }

  function formatTime(ms: number): string {
    if (!Number.isFinite(ms) || ms < 0) return "0:00";
    const s = Math.floor(ms / 1000);
    const m = Math.floor(s / 60);
    return `${m}:${String(s % 60).padStart(2, "0")}`;
  }
</script>

<section>
  <p><a href="#/">← back to corpus</a></p>

  {#if error}
    <p class="error">Error: {error}</p>
  {:else if !piece}
    <p>Loading piece…</p>
  {:else}
    {@const grade = resolveGrade(piece)}
    <header class="piece-header">
      <h2>{piece.metadata.title}</h2>
      <p class="meta">
        <span>{piece.metadata.composer}</span>
        <GradeBadge resolved={grade} />
        <span class="source">source: {piece.source}</span>
        {#if piece.page_url}
          <a href={piece.page_url} target="_blank" rel="noopener">upstream ↗</a>
        {/if}
      </p>
    </header>

    <div class="transport">
      <button onclick={togglePlay}>{isPlaying ? "Pause" : "Play"}</button>
      <button onclick={stop}>Stop</button>
      <label>
        Tempo {tempo}%
        <input
          type="range"
          min="50"
          max="150"
          step="5"
          value={tempo}
          oninput={(e) => applyTempo(parseInt((e.target as HTMLInputElement).value, 10))}
        />
      </label>
      <button onclick={toggleTab}>{showTab ? "Hide tab" : "Show tab"}</button>
      <span class="loop">
        Loop:
        <button onclick={setLoopStart}>set A</button>
        <button onclick={setLoopEnd}>set B</button>
        <button onclick={clearLoop} disabled={loopStart == null}>clear</button>
        {#if loopStart != null && loopEnd != null}
          <span class="loop-range">A→B set</span>
        {/if}
      </span>
    </div>

    <div class="progress">
      <span class="time">{formatTime(currentTimeMs)}</span>
      <input
        type="range"
        class="progress-bar"
        min="0"
        max={Math.max(endTick, 1)}
        step="1"
        value={positionTick}
        disabled={endTick === 0}
        oninput={(e) => onSeekInput(parseInt((e.target as HTMLInputElement).value, 10))}
        onchange={(e) => onSeekCommit(parseInt((e.target as HTMLInputElement).value, 10))}
      />
      <span class="time">{formatTime(endTimeMs)}</span>
    </div>

    <div
      bind:this={containerEl}
      class="alphatab"
      data-render-state={renderState}
      data-cid={piece.candidate_id}
    ></div>
  {/if}
</section>

<style>
  .piece-header h2 {
    margin: 0.3em 0 0.2em;
  }
  .meta {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    color: var(--muted);
    flex-wrap: wrap;
  }
  .source {
    font-size: 0.85em;
  }
  .transport {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin: 1rem 0;
    padding: 0.6rem;
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 4px;
  }
  .transport label {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.85em;
  }
  .loop {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.85em;
  }
  .loop-range {
    color: var(--accent);
    font-weight: 500;
  }
  .progress {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin: 0 0 1rem;
    padding: 0.4rem 0.6rem;
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 4px;
  }
  .progress-bar {
    flex: 1;
    margin: 0;
  }
  .time {
    font-size: 0.85em;
    color: var(--muted);
    font-variant-numeric: tabular-nums;
    min-width: 3.2em;
    text-align: center;
  }
  .alphatab {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 1rem;
    min-height: 200px;
  }
  .error {
    color: #b91c1c;
  }
</style>
