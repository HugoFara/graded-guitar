<script lang="ts">
  import { onMount } from "svelte";
  import {
    loadManifest,
    resolveGrade,
    formatDuration,
    type Manifest,
    type Piece,
  } from "../lib/manifest";
  import { getActiveProfileSync } from "../lib/storage/profile";
  import {
    loadAllStatuses,
    STATUS_VALUES,
    type PieceStatus,
  } from "../lib/storage/status";
  import GradeBadge from "../components/GradeBadge.svelte";
  import StatusChip from "../components/StatusChip.svelte";

  let manifest = $state<Manifest | null>(null);
  let statuses = $state<Record<string, PieceStatus>>({});
  let error = $state<string | null>(null);
  let activeFilter = $state<PieceStatus | "all">("playing");
  let profileName = $state<string>("");

  onMount(async () => {
    try {
      manifest = await loadManifest();
      const active = getActiveProfileSync();
      if (active) {
        profileName = active.display_name;
        statuses = await loadAllStatuses(active.id);
      }
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  });

  function encodeCid(cid: string): string {
    return encodeURIComponent(cid);
  }

  const byCid = $derived.by(() => {
    const out = new Map<string, Piece>();
    for (const p of manifest?.pieces ?? []) out.set(p.candidate_id, p);
    return out;
  });

  const counts = $derived.by(() => {
    const c: Record<PieceStatus, number> = {
      not_seen: 0,
      playing: 0,
      completed: 0,
      too_hard: 0,
      not_for_me: 0,
    };
    for (const s of Object.values(statuses)) c[s]++;
    return c;
  });

  const visible = $derived.by(() => {
    const out: { piece: Piece; status: PieceStatus; updatedKey: string }[] = [];
    for (const [cid, status] of Object.entries(statuses)) {
      if (status === "not_seen") continue;
      if (activeFilter !== "all" && status !== activeFilter) continue;
      const piece = byCid.get(cid);
      if (!piece) continue;
      out.push({ piece, status, updatedKey: cid });
    }
    out.sort((a, b) => a.piece.metadata.title.localeCompare(b.piece.metadata.title));
    return out;
  });

  // Statuses to show as tabs — drop the implicit "not_seen" default,
  // and add an "all" pseudo-status to see the whole library.
  const TABS: { value: PieceStatus | "all"; label: string }[] = [
    { value: "playing", label: "Playing" },
    { value: "completed", label: "Completed" },
    { value: "too_hard", label: "Too hard" },
    { value: "not_for_me", label: "Skipped" },
    { value: "all", label: "All" },
  ];

  // Keep the linter happy that STATUS_VALUES import is intentional:
  // it documents the exhaustive enum, and a future tab could be added
  // by reading it directly.
  void STATUS_VALUES;
</script>

<section class="library">
  <header class="lib-header">
    <h2>Your library</h2>
    <p class="meta">
      {#if profileName}
        Saved on this browser under <strong>{profileName}</strong>.
      {/if}
      Mark pieces from any
      <a href="#/piece/{encodeCid('')}" onclick={(e) => { e.preventDefault(); }}
        title="Open a piece to set its status">piece detail</a>
      page. <a href="#/feed">Back to feed</a>.
    </p>
  </header>

  {#if error}
    <p class="error">Failed to load: {error}</p>
  {:else if !manifest}
    <p>Loading…</p>
  {:else}
    <div class="tabs" role="tablist" aria-label="library status">
      {#each TABS as t}
        {@const n = t.value === "all"
          ? counts.playing + counts.completed + counts.too_hard + counts.not_for_me
          : counts[t.value]}
        <button
          type="button"
          role="tab"
          class:active={activeFilter === t.value}
          aria-selected={activeFilter === t.value}
          onclick={() => (activeFilter = t.value)}
        >
          {t.label} <span class="count">{n}</span>
        </button>
      {/each}
    </div>

    {#if visible.length === 0}
      <p class="empty">
        Nothing here yet. Open a piece and mark it as
        <em>{activeFilter === "all" ? "playing / completed / etc." : activeFilter.replace("_", " ")}</em>
        to see it in your library.
      </p>
    {:else}
      <ul class="rows" data-library-loaded="true">
        {#each visible as { piece, status } (piece.candidate_id)}
          {@const grade = resolveGrade(piece)}
          <li>
            <a href="#/piece/{encodeCid(piece.candidate_id)}" class="row">
              <div class="row-main">
                <span class="title">{piece.metadata.title}</span>
                <span class="composer">{piece.metadata.composer}</span>
              </div>
              <div class="row-meta">
                <GradeBadge resolved={grade} />
                {#if piece.duration_seconds}
                  <span class="duration">~{formatDuration(piece.duration_seconds)}</span>
                {/if}
                <StatusChip {status} />
              </div>
            </a>
          </li>
        {/each}
      </ul>
    {/if}
  {/if}
</section>

<style>
  .library {
    max-width: 60rem;
    margin: 1rem auto;
  }
  .lib-header h2 {
    margin: 0.3em 0 0.2em;
  }
  .meta {
    color: var(--muted);
  }
  .tabs {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
    margin: 0.75rem 0;
  }
  .tabs button {
    padding: 0.4rem 0.75rem;
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 999px;
    cursor: pointer;
    font-size: 0.9em;
    color: inherit;
  }
  .tabs button:hover {
    border-color: var(--accent);
  }
  .tabs button.active {
    background: var(--accent);
    color: white;
    border-color: var(--accent);
  }
  .tabs .count {
    opacity: 0.8;
    margin-left: 0.3rem;
  }
  .rows {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }
  .row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 0.7rem;
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: inherit;
    text-decoration: none;
  }
  .row:hover {
    border-color: var(--accent);
  }
  .row-main {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }
  .title {
    font-weight: 500;
  }
  .composer {
    font-size: 0.85em;
    color: var(--muted);
  }
  .row-meta {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  .duration {
    font-size: 0.85em;
    color: var(--muted);
    font-variant-numeric: tabular-nums;
  }
  .empty {
    color: var(--muted);
  }
  .error {
    color: #b91c1c;
  }
</style>
