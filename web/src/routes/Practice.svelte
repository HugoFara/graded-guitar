<script lang="ts">
  import { onMount, onDestroy, tick as svelteTick } from "svelte";
  import * as alphaTab from "@coderline/alphatab";
  import {
    loadManifest,
    pieceById,
    resolveGrade,
    musicxmlUrl,
    type Piece,
  } from "../lib/manifest";
  import { mountPlayer, type PlayerHandles } from "../lib/player";
  import { referenceFromScore, tickAtFrame } from "../lib/listen/score";
  import type { Reference } from "../lib/listen/reference";
  import {
    OnlineFollower,
    viterbiAlign,
    decimateFrames,
    VITERBI_CELL_BUDGET,
    type LiveFrames,
  } from "../lib/listen/align";
  import {
    analyzeTake,
    hardestBars,
    type TakeAnalysis,
  } from "../lib/listen/stumble";
  import {
    startCapture,
    MicrophoneUnavailableError,
    type CaptureSession,
  } from "../lib/listen/capture";
  import { addTake, summarizeTake } from "../lib/storage/takes";
  import { getActiveProfileSync } from "../lib/storage/profile";
  import GradeBadge from "../components/GradeBadge.svelte";

  type Props = { params?: { cid: string } };
  let { params }: Props = $props();

  type Phase = "loading" | "ready" | "recording" | "analyzing" | "done";

  let piece = $state<Piece | null>(null);
  let error = $state<string | null>(null);
  let micError = $state<string | null>(null);
  let phase = $state<Phase>("loading");
  let containerEl: HTMLDivElement | undefined = $state();

  let handles: PlayerHandles | null = null;
  let score: alphaTab.model.Score | null = null;
  // Reactive because the bar count is read in the template; the other
  // engine handles below are not.
  let reference = $state<Reference | null>(null);
  let follower: OnlineFollower | null = null;
  let session: CaptureSession | null = null;

  let currentBar = $state(-1);
  let confidence = $state(0);
  let elapsedMs = $state(0);
  let elapsedTimer: ReturnType<typeof setInterval> | null = null;

  let analysis = $state<TakeAnalysis | null>(null);
  let hardest = $state<{ bar: number; score: number; reason: string }[]>([]);
  let saved = $state(false);

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
    handles = mountPlayer(containerEl, musicxmlUrl(piece), {
      onScoreLoaded: (loaded) => {
        score = loaded;
        reference = referenceFromScore(loaded);
        phase = "ready";
      },
      onError: (e) => {
        error = e instanceof Error ? e.message : String(e);
      },
    });
  });

  onDestroy(() => {
    if (session) session.stop();
    if (elapsedTimer) clearInterval(elapsedTimer);
    handles?.destroy();
  });

  async function startRecording() {
    if (!reference || phase === "recording") return;
    micError = null;
    analysis = null;
    hardest = [];
    saved = false;
    follower = new OnlineFollower(reference);

    try {
      session = await startCapture((frame) => {
        if (!reference || !follower) return;
        const position = follower.step(frame.chroma, 0, frame.silent);
        currentBar = reference.barOfFrame[position];
        confidence = follower.confidence;
        // Drive alphaTab's own cursor as well as our bar strip, so the
        // player can read position off the notation they are looking at
        // rather than a number below it.
        if (handles) handles.api.tickPosition = tickAtFrame(reference, position);
      });
    } catch (e) {
      micError =
        e instanceof MicrophoneUnavailableError ? e.message : String(e);
      return;
    }

    phase = "recording";
    const startedAt = performance.now();
    elapsedTimer = setInterval(() => {
      elapsedMs = performance.now() - startedAt;
    }, 200);
  }

  // Both sides of the alignment have to stay at the same frame rate, or
  // the transition prior (which expects roughly one reference frame per
  // live frame at written tempo) is calibrated against the wrong thing.
  // So an over-budget take halves the reference and the take together.
  function fitToBudget(ref: Reference, live: LiveFrames): {
    ref: Reference;
    live: LiveFrames;
  } {
    let r = ref;
    let l = live;
    while (score && r.frameCount * l.frameCount > VITERBI_CELL_BUDGET) {
      r = referenceFromScore(score, r.frameRate / 2);
      l = decimateFrames(l);
    }
    return { ref: r, live: l };
  }

  async function stopRecording() {
    if (!session || !reference) return;
    const captureRatio = session.captureRatio;
    const live = session.stop();
    session = null;
    if (elapsedTimer) {
      clearInterval(elapsedTimer);
      elapsedTimer = null;
    }

    phase = "analyzing";
    // Let the "analyzing" state paint before the Viterbi pass takes the
    // main thread; on a long take it holds it for a second or more.
    await svelteTick();
    await new Promise((r) => setTimeout(r, 0));

    try {
      const fitted = fitToBudget(reference, live);
      const alignment = viterbiAlign(fitted.ref, fitted.live);
      const result = analyzeTake(fitted.ref, fitted.live, alignment);
      analysis = result;
      hardest = hardestBars(result, 5);

      const profile = getActiveProfileSync();
      if (profile && piece) {
        const grade = resolveGrade(piece);
        await addTake(
          profile.id,
          piece.candidate_id,
          summarizeTake(result, {
            captureRatio,
            snapshot:
              grade.kind === "none"
                ? undefined
                : { grade: grade.grade, source: grade.source },
          }),
        );
        saved = true;
      }
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
    phase = "done";
  }

  function formatTime(ms: number): string {
    const s = Math.floor(ms / 1000);
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  }

  // Difficulty shading for the bar strip. Uses the same evidence-of-
  // effort signals as hardestBars: retries, holds, and playing under
  // the written tempo.
  function barHeat(bar: TakeAnalysis["bars"][number]): number {
    if (!bar.reached) return -1;
    const slowdown = Number.isFinite(bar.tempoRatio)
      ? Math.max(0, 1 / Math.max(bar.tempoRatio, 0.05) - 1)
      : 0;
    const hold = bar.longestHoldFrames / Math.max(bar.expectedFrames, 1);
    const retry = Math.max(0, bar.attempts - 1);
    return Math.min(1, (slowdown + hold + retry) / 2);
  }
</script>

<section>
  <p>
    <a href={piece ? `#/piece/${encodeURIComponent(piece.candidate_id)}` : "#/"}
      >← back to the piece</a
    >
  </p>

  {#if error}
    <p class="error">Error: {error}</p>
  {:else if !piece}
    <p>Loading piece…</p>
  {:else}
    {@const grade = resolveGrade(piece)}
    <header>
      <h2>Practice: {piece.metadata.title}</h2>
      <p class="meta">
        <span>{piece.metadata.composer}</span>
        <GradeBadge resolved={grade} />
      </p>
    </header>

    <div class="mic-note">
      <strong>Your audio never leaves this browser.</strong> The microphone
      is used to work out where you are in the score. What gets kept is a
      12-number-per-frame summary of pitch content — the recording itself
      is never stored and never sent anywhere. See the
      <a href="#/privacy">privacy note</a>.
    </div>

    {#if micError}
      <p class="error">{micError}</p>
    {/if}

    <div class="transport">
      {#if phase === "loading"}
        <span class="status">Preparing score…</span>
      {:else if phase === "recording"}
        <button class="stop" onclick={stopRecording}>Stop and analyze</button>
        <span class="status recording">
          ● Recording {formatTime(elapsedMs)}
        </span>
        <span class="status">
          Bar {currentBar >= 0 ? currentBar + 1 : "—"}
          {#if reference}<span class="muted"> of {reference.barCount}</span>{/if}
        </span>
        <span class="status" title="how sure the follower is of your position">
          Tracking: {confidence > 0.5 ? "locked" : confidence > 0.15 ? "searching" : "lost"}
        </span>
      {:else if phase === "analyzing"}
        <span class="status">Aligning your take against the score…</span>
      {:else}
        <button class="start" onclick={startRecording}>
          {phase === "done" ? "Record another take" : "Start listening"}
        </button>
        <span class="status muted">
          Play the piece through. Stop, hesitate or start over as much as you
          need — that is the part we are measuring.
        </span>
      {/if}
    </div>

    {#if analysis}
      {@const a = analysis}
      <div class="results">
        <div class="summary">
          <div class="stat">
            <span class="value">{Math.round(a.completion * 100)}%</span>
            <span class="label">of the piece reached</span>
          </div>
          <div class="stat">
            <span class="value">
              {a.medianTempoRatio ? Math.round(a.medianTempoRatio * 100) : "—"}%
            </span>
            <span class="label">of written tempo</span>
          </div>
          <div class="stat">
            <span class="value">{a.totalRestarts}</span>
            <span class="label">restarts</span>
          </div>
          <div class="stat">
            <span class="value">{formatTime(a.durationMs)}</span>
            <span class="label">take length</span>
          </div>
        </div>

        {#if !a.completed}
          <p class="bound-note">
            You stopped at bar {a.furthestBar + 1} of {a.barCount}. This take
            tells us the piece is <em>at least</em> this hard for you — it is
            recorded as a lower bound, not as a difficulty estimate.
          </p>
        {/if}

        <h3>Where it got hard</h3>
        <div class="bar-strip" role="img" aria-label="per-bar difficulty">
          {#each a.bars as bar (bar.bar)}
            {@const heat = barHeat(bar)}
            <span
              class="bar-cell"
              class:unreached={heat < 0}
              style={heat >= 0
                ? `background: color-mix(in srgb, var(--accent) ${Math.round(heat * 100)}%, var(--card-bg))`
                : ""}
              title={`Bar ${bar.bar + 1}${
                bar.reached
                  ? ` — ${bar.attempts} attempt${bar.attempts === 1 ? "" : "s"}`
                  : " — not reached"
              }`}
            ></span>
          {/each}
        </div>

        {#if hardest.length}
          <ul class="hardest">
            {#each hardest as h (h.bar)}
              <li><strong>Bar {h.bar + 1}</strong> — {h.reason}</li>
            {/each}
          </ul>
        {:else}
          <p class="muted">
            No bar stood out — you played this at a steady tempo throughout.
          </p>
        {/if}

        <p class="saved muted">
          {#if saved}
            Take saved to your library. It stays in this browser.
          {:else}
            Not saved — no active profile. <a href="#/onboard">Set your level</a
            > to keep practice history.
          {/if}
        </p>
      </div>
    {/if}

    <div bind:this={containerEl} class="alphatab" data-cid={piece.candidate_id}></div>
  {/if}
</section>

<style>
  header h2 {
    margin: 0.3em 0 0.2em;
  }
  .meta {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    color: var(--muted);
    flex-wrap: wrap;
  }
  .mic-note {
    margin: 1rem 0;
    padding: 0.6rem 0.8rem;
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 4px;
    background: var(--card-bg);
    font-size: 0.85em;
  }
  .transport {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    flex-wrap: wrap;
    margin: 1rem 0;
    padding: 0.6rem;
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 4px;
  }
  .transport button {
    font-size: 1em;
    padding: 0.4rem 1rem;
  }
  .status {
    font-size: 0.85em;
  }
  .muted {
    color: var(--muted);
  }
  .status.recording {
    color: #b91c1c;
    font-variant-numeric: tabular-nums;
  }
  .results {
    margin: 1rem 0;
    padding: 0.8rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--card-bg);
  }
  .results h3 {
    margin: 1rem 0 0.5rem;
    font-size: 1em;
  }
  .summary {
    display: flex;
    gap: 1.5rem;
    flex-wrap: wrap;
  }
  .stat {
    display: flex;
    flex-direction: column;
  }
  .stat .value {
    font-size: 1.4em;
    font-variant-numeric: tabular-nums;
  }
  .stat .label {
    font-size: 0.8em;
    color: var(--muted);
  }
  .bound-note {
    margin: 0.8rem 0 0;
    padding: 0.5rem 0.7rem;
    border-left: 3px solid var(--muted);
    font-size: 0.9em;
  }
  .bar-strip {
    display: flex;
    flex-wrap: wrap;
    gap: 2px;
  }
  .bar-cell {
    width: 12px;
    height: 22px;
    border: 1px solid var(--border);
    border-radius: 2px;
  }
  .bar-cell.unreached {
    background: transparent;
    opacity: 0.4;
  }
  .hardest {
    margin: 0.8rem 0 0;
    padding-left: 1.2rem;
    font-size: 0.9em;
  }
  .saved {
    margin: 0.8rem 0 0;
    font-size: 0.85em;
  }
  .alphatab {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 1rem;
    min-height: 200px;
    position: relative;
    overflow-x: auto;
  }
  .error {
    color: #b91c1c;
  }
</style>
