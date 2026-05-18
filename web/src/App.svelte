<script lang="ts">
  import { onMount } from "svelte";
  import Router from "svelte-spa-router";
  import CorpusList from "./routes/CorpusList.svelte";
  import PieceDetail from "./routes/PieceDetail.svelte";
  import Onboard from "./routes/Onboard.svelte";
  import Feed from "./routes/Feed.svelte";
  import Landing from "./routes/Landing.svelte";
  import Profile from "./routes/Profile.svelte";
  import Library from "./routes/Library.svelte";
  import Privacy from "./routes/Privacy.svelte";
  import { getActiveProfileSync } from "./lib/storage/profile";

  const routes = {
    "/": Landing,
    "/browse": CorpusList,
    "/onboard": Onboard,
    "/feed": Feed,
    "/library": Library,
    "/profile": Profile,
    "/privacy": Privacy,
    "/piece/:cid": PieceDetail,
  };

  let activeName = $state<string | null>(null);
  let activeLevel = $state<number | null>(null);

  // Header chip — reads the active profile on every navigation so it
  // reflects updates from /onboard or /profile without a manual reload.
  function refreshChip() {
    const active = getActiveProfileSync();
    activeName = active?.display_name ?? null;
    activeLevel = active?.level ?? null;
  }

  onMount(() => {
    refreshChip();
    window.addEventListener("hashchange", refreshChip);
    return () => window.removeEventListener("hashchange", refreshChip);
  });
</script>

<header class="container">
  <div class="row">
    <h1><a href="#/">graded-guitar</a></h1>
    <nav>
      {#if activeName != null}
        <a href="#/profile" class="level-chip" title="manage profiles">
          {activeName}{#if activeLevel != null}<span class="lvl"> · L{activeLevel}</span>{/if}
        </a>
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

<footer class="container site-footer">
  <p>
    <strong>Local-only profiles.</strong>
    Your library lives in this browser — there is no server, no
    account in the usual sense. If the project gains traction we may
    offer hosted infrastructure later (opt-in). Details in the
    <a href="#/privacy">privacy note</a>.
  </p>
</footer>

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
  .level-chip .lvl {
    color: var(--muted);
  }
  .site-footer {
    margin-top: 3rem;
    padding: 1rem 0;
    border-top: 1px solid var(--border);
    font-size: 0.85em;
    color: var(--muted);
  }
  .site-footer p {
    margin: 0;
  }
</style>
