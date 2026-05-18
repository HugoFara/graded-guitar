<script lang="ts">
  import { onMount } from "svelte";
  import {
    loadManifest,
    applyFilters,
    listComposers,
    resolveGrade,
    formatDuration,
    ERAS,
    type Manifest,
    type Filters,
  } from "../lib/manifest";
  import GradeBadge from "../components/GradeBadge.svelte";

  let manifest = $state<Manifest | null>(null);
  let error = $state<string | null>(null);

  let filters = $state<Filters>({
    query: "",
    minGrade: null,
    maxGrade: null,
    source: "all",
    composer: "",
    era: "all",
    maxDurationSeconds: null,
  });

  let maxMinutesInput = $state<string>("");

  let limit = $state(100);

  onMount(async () => {
    try {
      manifest = await loadManifest();
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  });

  const composerList = $derived(
    manifest ? listComposers(manifest.pieces) : [],
  );

  // Sync the user-typed "max minutes" → maxDurationSeconds (60×)
  $effect(() => {
    const trimmed = maxMinutesInput.trim();
    if (!trimmed) {
      filters.maxDurationSeconds = null;
      return;
    }
    const n = parseFloat(trimmed);
    filters.maxDurationSeconds = Number.isFinite(n) && n > 0 ? n * 60 : null;
  });

  const filtered = $derived(
    manifest ? applyFilters(manifest.pieces, filters) : [],
  );

  const sorted = $derived(
    [...filtered].sort((a, b) => {
      const composerCmp = a.metadata.composer.localeCompare(b.metadata.composer);
      if (composerCmp !== 0) return composerCmp;
      return a.metadata.title.localeCompare(b.metadata.title);
    }),
  );

  const visible = $derived(sorted.slice(0, limit));

  function encodeCid(cid: string): string {
    return encodeURIComponent(cid);
  }

  function parseGrade(v: string): number | null {
    const n = parseInt(v, 10);
    return Number.isFinite(n) ? n : null;
  }
</script>

<section>
  {#if error}
    <p class="error">Failed to load manifest: {error}</p>
  {:else if !manifest}
    <p>Loading corpus…</p>
  {:else}
    <div class="toolbar">
      <input
        type="search"
        placeholder="Search title or composer…"
        bind:value={filters.query}
      />
      <label>
        Composer
        <input
          type="search"
          list="composer-list"
          placeholder="any"
          bind:value={filters.composer}
        />
        <datalist id="composer-list">
          {#each composerList as c}
            <option value={c.composer}>{c.count}</option>
          {/each}
        </datalist>
      </label>
      <label>
        Era
        <select bind:value={filters.era}>
          <option value="all">any</option>
          {#each ERAS as era}
            <option value={era}>{era}</option>
          {/each}
        </select>
      </label>
      <label>
        Min grade
        <select
          value={filters.minGrade ?? ""}
          onchange={(e) => (filters.minGrade = parseGrade((e.target as HTMLSelectElement).value))}
        >
          <option value="">any</option>
          {#each [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] as g}
            <option value={g}>{g}</option>
          {/each}
        </select>
      </label>
      <label>
        Max grade
        <select
          value={filters.maxGrade ?? ""}
          onchange={(e) => (filters.maxGrade = parseGrade((e.target as HTMLSelectElement).value))}
        >
          <option value="">any</option>
          {#each [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] as g}
            <option value={g}>{g}</option>
          {/each}
        </select>
      </label>
      <label>
        Max length (min)
        <input
          type="number"
          min="0"
          step="1"
          placeholder="any"
          bind:value={maxMinutesInput}
        />
      </label>
      <label>
        Source
        <select bind:value={filters.source}>
          <option value="all">all</option>
          <option value="curator">curator only</option>
          <option value="model">model only</option>
        </select>
      </label>
      <span class="count">
        {filtered.length} match{filtered.length === 1 ? "" : "es"}
        ({manifest.pieces.length} total)
      </span>
    </div>

    <ul class="pieces" data-corpus-loaded="true" data-corpus-count={manifest.pieces.length}>
      {#each visible as p (p.candidate_id)}
        {@const grade = resolveGrade(p)}
        <li>
          <a href="#/piece/{encodeCid(p.candidate_id)}" class="piece">
            <span class="title">{p.metadata.title}</span>
            <span class="composer">{p.metadata.composer}</span>
            <span class="duration">
              {#if p.duration_seconds}~{formatDuration(p.duration_seconds)}{/if}
            </span>
            <GradeBadge resolved={grade} />
          </a>
        </li>
      {/each}
    </ul>

    {#if filtered.length > limit}
      <div class="more">
        Showing {limit} of {filtered.length}.
        <button onclick={() => (limit += 100)}>Show 100 more</button>
      </div>
    {/if}
  {/if}
</section>

<style>
  .toolbar {
    display: flex;
    gap: 0.75rem;
    align-items: flex-end;
    flex-wrap: wrap;
    margin-bottom: 1rem;
  }
  .toolbar label {
    display: flex;
    flex-direction: column;
    font-size: 0.8em;
    color: var(--muted);
  }
  .toolbar input[type="number"] {
    width: 6em;
  }
  .toolbar input[list],
  .toolbar input[type="search"] {
    min-width: 12rem;
  }
  .count {
    margin-left: auto;
    color: var(--muted);
    font-size: 0.9em;
  }
  .pieces {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .pieces li {
    border-bottom: 1px solid var(--border);
  }
  .piece {
    display: grid;
    grid-template-columns: 2fr 1.2fr auto auto;
    gap: 1rem;
    align-items: center;
    padding: 0.6rem 0.3rem;
    color: inherit;
    text-decoration: none;
  }
  .piece:hover {
    background: #f3f4f6;
  }
  .title {
    font-weight: 500;
  }
  .composer {
    color: var(--muted);
    font-size: 0.9em;
  }
  .duration {
    color: var(--muted);
    font-size: 0.85em;
    font-variant-numeric: tabular-nums;
    min-width: 3em;
    text-align: right;
  }
  .more {
    margin-top: 1rem;
    text-align: center;
    color: var(--muted);
  }
  .error {
    color: #b91c1c;
  }
  @media (max-width: 600px) {
    .piece {
      grid-template-columns: 1fr auto;
    }
    .composer,
    .duration {
      grid-column: 1 / -1;
    }
  }
</style>
