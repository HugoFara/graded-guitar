<script lang="ts">
  import { onMount } from "svelte";
  import { push } from "svelte-spa-router";
  import {
    loadManifest,
    resolveGrade,
    type Manifest,
    type Piece,
  } from "../lib/manifest";
  import { MIN_LEVEL, MAX_LEVEL, loadLevel, saveLevel } from "../lib/level";

  let manifest = $state<Manifest | null>(null);
  let selected = $state<number>(loadLevel() ?? 5);

  onMount(async () => {
    manifest = await loadManifest().catch(() => null);
  });

  // Examples per grade — pick up to two pieces whose resolved grade
  // equals the level, preferring curator-graded ones. Falls back to
  // model-graded if no curator labels are available for that level.
  const examples = $derived.by(() => {
    const out: Record<number, Piece[]> = {};
    if (!manifest) return out;
    for (let g = MIN_LEVEL; g <= MAX_LEVEL; g++) {
      const matchG = manifest.pieces.filter((p) => {
        const r = resolveGrade(p);
        if (r.kind === "none") return false;
        return parseInt(r.grade, 10) === g;
      });
      const curated = matchG.filter((p) => resolveGrade(p).kind === "curator");
      const pool = curated.length > 0 ? curated : matchG;
      out[g] = pool.slice(0, 2);
    }
    return out;
  });

  function pick(level: number) {
    selected = level;
  }

  function confirm() {
    saveLevel(selected);
    push("/feed");
  }
</script>

<section class="onboard">
  <h2>What level do you play at?</h2>
  <p class="lead">
    Pick a grade roughly aligned with the
    <a href="https://www.delcamp.net/en/cours_de_guitare/cours_de_guitare_classique.html" target="_blank" rel="noopener">Delcamp</a>
    scale (1 = beginner, 10 = advanced concert). You can change this any time.
  </p>

  <div class="grid" role="radiogroup" aria-label="playing level">
    {#each Array(MAX_LEVEL - MIN_LEVEL + 1) as _, i}
      {@const g = MIN_LEVEL + i}
      <button
        type="button"
        class="level"
        class:selected={selected === g}
        aria-pressed={selected === g}
        onclick={() => pick(g)}
      >
        <span class="num">{g}</span>
        <span class="hint">
          {#if g <= 2}
            very early
          {:else if g <= 4}
            beginner
          {:else if g <= 6}
            intermediate
          {:else if g <= 8}
            advanced
          {:else}
            concert
          {/if}
        </span>
        {#if examples[g]?.length}
          <span class="example">
            e.g. {examples[g][0].metadata.title}
          </span>
        {/if}
      </button>
    {/each}
  </div>

  <div class="actions">
    <button class="primary" onclick={confirm}>Show me pieces</button>
    <a href="#/browse" class="skip">Skip — let me browse the full corpus</a>
  </div>
</section>

<style>
  .onboard {
    max-width: 60rem;
    margin: 1rem auto;
  }
  .lead {
    color: var(--muted);
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(8rem, 1fr));
    gap: 0.75rem;
    margin: 1.25rem 0;
  }
  .level {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
    padding: 0.75rem;
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    cursor: pointer;
    text-align: left;
    font: inherit;
    color: inherit;
  }
  .level:hover {
    border-color: var(--accent);
  }
  .level.selected {
    border-color: var(--accent);
    box-shadow: inset 0 0 0 1px var(--accent);
  }
  .num {
    font-size: 1.5em;
    font-weight: 600;
  }
  .hint {
    font-size: 0.85em;
    color: var(--muted);
    text-transform: lowercase;
  }
  .example {
    font-size: 0.75em;
    color: var(--muted);
    font-style: italic;
    /* keep example to one line, ellipsis if too long */
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    width: 100%;
  }
  .actions {
    display: flex;
    align-items: center;
    gap: 1.25rem;
    margin-top: 1.5rem;
  }
  .primary {
    padding: 0.6rem 1.25rem;
    background: var(--accent);
    color: white;
    border: none;
    border-radius: 4px;
    font-weight: 500;
    font-size: 1em;
    cursor: pointer;
  }
  .skip {
    font-size: 0.9em;
  }
</style>
