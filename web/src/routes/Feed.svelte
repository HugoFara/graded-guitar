<script lang="ts">
  import { onMount } from "svelte";
  import { push } from "svelte-spa-router";
  import {
    loadManifest,
    buildFeed,
    resolveGrade,
    formatDuration,
    type Manifest,
  } from "../lib/manifest";
  import { loadLevel } from "../lib/level";
  import GradeBadge from "../components/GradeBadge.svelte";

  let manifest = $state<Manifest | null>(null);
  let error = $state<string | null>(null);
  let level = $state<number | null>(loadLevel());

  onMount(async () => {
    if (level == null) {
      push("/onboard");
      return;
    }
    try {
      manifest = await loadManifest();
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  });

  const feed = $derived(
    manifest && level != null ? buildFeed(manifest.pieces, level, 30) : [],
  );

  function encodeCid(cid: string): string {
    return encodeURIComponent(cid);
  }
</script>

<section class="feed">
  {#if level == null}
    <p>
      Redirecting to <a href="#/onboard">level selection</a>…
    </p>
  {:else if error}
    <p class="error">Failed to load corpus: {error}</p>
  {:else if !manifest}
    <p>Loading feed…</p>
  {:else}
    <header class="feed-header">
      <h2>Pieces for level {level}{level < 10 ? `–${level + 1}` : ""}</h2>
      <p class="meta">
        Showing {feed.length} pieces from grades {level} and {Math.min(level + 1, 10)}, sampled across composers.
        <a href="#/onboard">Change level</a> · <a href="#/browse">browse the full corpus</a>
      </p>
    </header>

    {#if feed.length === 0}
      <p class="empty">
        No pieces at grade {level} or {level + 1} yet. Try a different level or
        <a href="#/browse">browse the full corpus</a>.
      </p>
    {:else}
      <ul class="cards" data-feed-loaded="true">
        {#each feed as p (p.candidate_id)}
          {@const grade = resolveGrade(p)}
          <li>
            <a href="#/piece/{encodeCid(p.candidate_id)}" class="card">
              <div class="card-head">
                <span class="title">{p.metadata.title}</span>
                <GradeBadge resolved={grade} />
              </div>
              <div class="card-meta">
                <span class="composer">{p.metadata.composer}</span>
                {#if p.era && p.era !== "unknown"}
                  <span class="era">{p.era}</span>
                {/if}
                {#if p.duration_seconds}
                  <span class="duration">~{formatDuration(p.duration_seconds)}</span>
                {/if}
              </div>
            </a>
          </li>
        {/each}
      </ul>
    {/if}
  {/if}
</section>

<style>
  .feed-header h2 {
    margin: 0.5em 0 0.2em;
  }
  .meta {
    color: var(--muted);
    font-size: 0.9em;
    margin-top: 0;
  }
  .cards {
    list-style: none;
    padding: 0;
    margin: 1rem 0 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
    gap: 0.75rem;
  }
  .card {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    padding: 0.8rem;
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: inherit;
    text-decoration: none;
    height: 100%;
  }
  .card:hover {
    border-color: var(--accent);
  }
  .card-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.5rem;
  }
  .title {
    font-weight: 500;
  }
  .card-meta {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex-wrap: wrap;
    font-size: 0.85em;
    color: var(--muted);
  }
  .era {
    text-transform: capitalize;
    padding: 0.05em 0.4em;
    border: 1px solid var(--border);
    border-radius: 3px;
    font-size: 0.85em;
  }
  .duration {
    font-variant-numeric: tabular-nums;
  }
  .empty {
    color: var(--muted);
  }
  .error {
    color: #b91c1c;
  }
</style>
