<script lang="ts">
  import Router from "svelte-spa-router";
  import CorpusList from "./routes/CorpusList.svelte";
  import PieceDetail from "./routes/PieceDetail.svelte";

  const routes = {
    "/": CorpusList,
    "/piece/:cid": PieceDetail,
  };
</script>

<header class="container">
  <h1><a href="#/">graded-guitar</a></h1>
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
