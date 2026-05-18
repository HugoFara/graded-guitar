<script lang="ts">
  import { onMount } from "svelte";
  import Router from "svelte-spa-router";
  import CorpusList from "./routes/CorpusList.svelte";
  import PieceDetail from "./routes/PieceDetail.svelte";
  import Onboard from "./routes/Onboard.svelte";
  import Feed from "./routes/Feed.svelte";
  import { loadLevel } from "./lib/level";

  const routes = {
    "/": CorpusList,
    "/browse": CorpusList,
    "/onboard": Onboard,
    "/feed": Feed,
    "/piece/:cid": PieceDetail,
  };

  let level = $state<number | null>(null);

  // Header level chip — reads localStorage on every navigation so it
  // reflects updates from Onboard.svelte without a manual refresh.
  function refreshLevel() {
    level = loadLevel();
  }

  onMount(() => {
    refreshLevel();
    window.addEventListener("hashchange", refreshLevel);
    return () => window.removeEventListener("hashchange", refreshLevel);
  });
</script>

<header class="container">
  <div class="row">
    <h1><a href="#/">graded-guitar</a></h1>
    <nav>
      {#if level != null}
        <a href="#/onboard" class="level-chip">Level {level}</a>
      {:else}
        <a href="#/onboard" class="level-chip set-prompt">Set your level</a>
      {/if}
    </nav>
  </div>
  <p class="warn-banner">
    Pre-alpha. Grade predictions tagged <code>dummy-v0</code> are placeholder labels
    pending advisor sign-off. See
    <a
      href="https://github.com/HugoFara/graded-guitar/blob/main/decisions/0010-m2-close-with-dummy-labels.md"
      >ADR 0010</a
    >.
  </p>
</header>

<main class="container">
  <Router {routes} />
</main>

<style>
  .row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
  }
  nav {
    display: flex;
    align-items: center;
    gap: 1rem;
  }
  .level-chip {
    font-size: 0.9em;
    padding: 0.25rem 0.6rem;
    border: 1px solid var(--border);
    border-radius: 999px;
    text-decoration: none;
    color: inherit;
    background: var(--card-bg);
  }
  .level-chip:hover {
    border-color: var(--accent);
  }
  .level-chip.set-prompt {
    color: var(--accent);
    border-color: var(--accent);
  }
</style>
