<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import {
    loadManifest,
    pieceById,
    resolveGrade,
    musicxmlUrl,
    formatDuration,
    type Piece,
  } from "../lib/manifest";
  import * as alphaTab from "@coderline/alphatab";
  import { mountPlayer, type PlayerHandles } from "../lib/player";
  import GradeBadge from "../components/GradeBadge.svelte";
  import StatusSelector from "../components/StatusSelector.svelte";

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

  let totalBars = $state(0);
  let masterBarStarts = $state<number[]>([]);
  let masterBarDurations = $state<number[]>([]);

  let loopStartBar = $state<number | null>(null);
  let loopEndBar = $state<number | null>(null);
  let loopActive = $state(false);

  let currentTimeMs = $state(0);
  let endTimeMs = $state(0);

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
        masterBarStarts = score.masterBars.map((b) => b.start);
        masterBarDurations = score.masterBars.map((b) => b.calculateDuration());
      },
      onRenderFinished: () => {
        renderState = "rendered";
      },
      onPlayerStateChanged: (state) => {
        isPlaying = state === 1;
      },
      onPositionChanged: (_curTick, _totTick, curMs, totMs) => {
        currentTimeMs = curMs;
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

  // Valid range: 1..totalBars, with `from` <= `to`. Returns null if the
  // current inputs don't describe a valid range.
  function loopRangeTicks(): { startTick: number; endTick: number } | null {
    if (loopStartBar == null || loopEndBar == null) return null;
    if (loopStartBar < 1 || loopEndBar < 1) return null;
    if (loopStartBar > totalBars || loopEndBar > totalBars) return null;
    if (loopStartBar > loopEndBar) return null;
    if (!masterBarStarts.length) return null;
    const startTick = masterBarStarts[loopStartBar - 1];
    const lastIdx = loopEndBar - 1;
    const endTick = masterBarStarts[lastIdx] + masterBarDurations[lastIdx];
    return { startTick, endTick };
  }

  function applyLoop() {
    if (!handles) return;
    const range = loopRangeTicks();
    if (!range) return;
    handles.api.playbackRange = range;
    handles.api.tickPosition = range.startTick;
    handles.api.isLooping = true;
    loopActive = true;
  }

  function clearLoop() {
    if (!handles) return;
    handles.api.isLooping = false;
    handles.api.playbackRange = null;
    loopActive = false;
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
        <span class="duration" title="approximate playback duration">~{formatDuration(piece.duration_seconds)}</span>
        <span class="source">source: {piece.source}</span>
        {#if piece.page_url}
          <a href={piece.page_url} target="_blank" rel="noopener">upstream ↗</a>
        {/if}
      </p>
      <div class="status-row">
        <span class="label">Status:</span>
        <StatusSelector cid={piece.candidate_id} />
      </div>
    </header>

    <div class="transport">
      <button onclick={togglePlay}>{isPlaying ? "Pause" : "Play"}</button>
      <button onclick={stop}>Stop</button>
      <span class="time" aria-label="playback time">
        {formatTime(currentTimeMs)} / {formatTime(endTimeMs)}
      </span>
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
      <span class="loop" class:active={loopActive}>
        Loop bars
        <input
          type="number"
          min="1"
          max={totalBars || 1}
          placeholder="from"
          aria-label="loop start bar"
          bind:value={loopStartBar}
        />
        to
        <input
          type="number"
          min="1"
          max={totalBars || 1}
          placeholder="to"
          aria-label="loop end bar"
          bind:value={loopEndBar}
        />
        <button onclick={applyLoop} disabled={loopRangeTicks() == null}>set</button>
        <button onclick={clearLoop} disabled={!loopActive}>clear</button>
        {#if totalBars}
          <span class="bar-hint">of {totalBars}</span>
        {/if}
      </span>
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
  .status-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0.5rem 0;
    flex-wrap: wrap;
  }
  .status-row .label {
    font-size: 0.85em;
    color: var(--muted);
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
  .duration {
    font-size: 0.85em;
    font-variant-numeric: tabular-nums;
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
  .loop input[type="number"] {
    width: 4em;
  }
  .loop.active {
    color: var(--accent);
  }
  .bar-hint {
    color: var(--muted);
  }
  .time {
    font-size: 0.85em;
    color: var(--muted);
    font-variant-numeric: tabular-nums;
  }
  .alphatab {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 1rem;
    min-height: 200px;
    /* alphaTab positions its cursor elements absolutely — anchor them
       to this container. */
    position: relative;
    overflow-x: auto;
  }
  .error {
    color: #b91c1c;
  }
</style>
