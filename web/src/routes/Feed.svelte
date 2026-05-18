<script lang="ts">
  // Placeholder until M4 step 4 ships the real feed view. Lets the
  // Onboard "show me pieces" button land on a real route.
  import { loadLevel } from "../lib/level";

  const level = loadLevel();
</script>

<section>
  <h2>Your feed</h2>
  {#if level == null}
    <p>
      No level set yet. <a href="#/onboard">Choose your level</a> to see a
      tailored feed.
    </p>
  {:else}
    <p>
      Level {level} selected. The full feed view ships in M4 step 4. For now,
      <a href="#/browse">browse the full corpus</a>.
    </p>
  {/if}
</section>
