<script lang="ts">
  import { onMount } from "svelte";
  import { push } from "svelte-spa-router";
  import { loadLevel } from "../lib/level";

  onMount(() => {
    const level = loadLevel();
    push(level != null ? "/feed" : "/onboard");
  });
</script>

<p>Loading…</p>
