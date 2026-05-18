<script lang="ts">
  import { onMount } from "svelte";
  import { push } from "svelte-spa-router";
  import {
    loadManifest,
    buildFeed,
    resolveGrade,
    gradeAsInt,
    formatDuration,
    type Manifest,
    type Piece,
  } from "../lib/manifest";
  import { loadLevel } from "../lib/level";
  import GradeBadge from "../components/GradeBadge.svelte";
  import StatusChip from "../components/StatusChip.svelte";
  import { getActiveProfileSync } from "../lib/storage/profile";
  import { loadAllStatuses, type PieceStatus } from "../lib/storage/status";

  let manifest = $state<Manifest | null>(null);
  let error = $state<string | null>(null);
  let level = $state<number | null>(loadLevel());
  let statuses = $state<Record<string, PieceStatus>>({});

  onMount(async () => {
    if (level == null) {
      push("/onboard");
      return;
    }
    try {
      manifest = await loadManifest();
      const active = getActiveProfileSync();
      if (active) statuses = await loadAllStatuses(active.id);
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  });

  function statusFor(cid: string): PieceStatus {
    return statuses[cid] ?? "not_seen";
  }

  const feed = $derived(
    manifest && level != null
      ? buildFeed(manifest.pieces, level, { statuses, cap: 30 })
      : [],
  );

  // Split the feed by grade: "at your level" vs "stretch (level+1)".
  // The spec asks the feed to show pieces from level and one above —
  // labelling the boundary makes it clear which is which.
  const atLevel = $derived(
    level == null ? [] : feed.filter((p) => pieceGrade(p) === level),
  );
  const stretch = $derived(
    level == null ? [] : feed.filter((p) => pieceGrade(p) === level + 1),
  );

  function pieceGrade(p: Piece): number | null {
    const r = resolveGrade(p);
    if (r.kind === "none") return null;
    return gradeAsInt(r.grade);
  }

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
      <h2>Pieces for you</h2>
      <p class="meta">
        Showing {feed.length} pieces sampled across composers, at grades {level} and {Math.min(level + 1, 10)}.
        <a href="#/library">your library</a> · <a href="#/onboard">change level</a> · <a href="#/browse">browse the full corpus</a>
      </p>
    </header>

    {#if feed.length === 0}
      <p class="empty">
        No pieces at grade {level} or {level + 1} yet. Try a different level or
        <a href="#/browse">browse the full corpus</a>.
      </p>
    {:else}
      <div data-feed-loaded="true">
        {#if atLevel.length > 0}
          <h3 class="section-head">At your level (grade {level})</h3>
          <ul class="cards" data-feed-section="at-level">
            {#each atLevel as p (p.candidate_id)}
              {@const grade = resolveGrade(p)}
              <li>
                <a href="#/piece/{encodeCid(p.candidate_id)}" class="card">
                  <div class="card-head">
                    <span class="title">{p.metadata.title}</span>
                    <GradeBadge resolved={grade} />
                  </div>
                  <StatusChip status={statusFor(p.candidate_id)} />
                  <div class="card-meta">
                    <span class="composer">{p.metadata.composer}</span>
                    {#if p.era && p.era !== "unknown"}
                      <span class="era">{p.era}</span>
                    {/if}
                    {#if p.duration_seconds}
                      <span class="duration">~{formatDuration(p.duration_seconds)}</span>
                    {/if}
                  </div>
                  <span class="cta">Try this piece →</span>
                </a>
              </li>
            {/each}
          </ul>
        {/if}

        {#if stretch.length > 0}
          <h3 class="section-head">A step up (grade {level + 1})</h3>
          <ul class="cards" data-feed-section="stretch">
            {#each stretch as p (p.candidate_id)}
              {@const grade = resolveGrade(p)}
              <li>
                <a href="#/piece/{encodeCid(p.candidate_id)}" class="card">
                  <div class="card-head">
                    <span class="title">{p.metadata.title}</span>
                    <GradeBadge resolved={grade} />
                  </div>
                  <StatusChip status={statusFor(p.candidate_id)} />
                  <div class="card-meta">
                    <span class="composer">{p.metadata.composer}</span>
                    {#if p.era && p.era !== "unknown"}
                      <span class="era">{p.era}</span>
                    {/if}
                    {#if p.duration_seconds}
                      <span class="duration">~{formatDuration(p.duration_seconds)}</span>
                    {/if}
                  </div>
                  <span class="cta">Try this piece →</span>
                </a>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
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
  .section-head {
    margin: 1.5rem 0 0.5rem;
    font-size: 1em;
    color: var(--muted);
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .cards {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
    gap: 0.75rem;
  }
  .card {
    position: relative;
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
    transition: border-color 0.1s ease;
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
  .cta {
    font-size: 0.85em;
    color: var(--accent);
    margin-top: auto;
    opacity: 0;
    transition: opacity 0.1s ease;
  }
  .card:hover .cta,
  .card:focus-visible .cta {
    opacity: 1;
  }
  .empty {
    color: var(--muted);
  }
  .error {
    color: #b91c1c;
  }
</style>
