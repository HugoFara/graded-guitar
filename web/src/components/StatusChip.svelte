<script lang="ts">
  // Small read-only status indicator for feed/library cards. Renders
  // nothing for "not_seen" so most cards stay uncluttered.
  import type { PieceStatus } from "../lib/storage/status";

  type Props = { status: PieceStatus };
  let { status }: Props = $props();

  const LABELS: Record<PieceStatus, string> = {
    not_seen: "",
    playing: "playing",
    completed: "completed",
    too_hard: "too hard",
    not_for_me: "skipped",
  };
</script>

{#if status !== "not_seen"}
  <span class="chip" data-status={status}>{LABELS[status]}</span>
{/if}

<style>
  .chip {
    font-size: 0.7em;
    padding: 0.1em 0.5em;
    border-radius: 999px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--muted);
    border: 1px solid var(--border);
  }
  .chip[data-status="playing"] {
    color: var(--accent);
    border-color: var(--accent);
  }
  .chip[data-status="completed"] {
    background: var(--accent);
    color: white;
    border-color: var(--accent);
  }
  .chip[data-status="too_hard"],
  .chip[data-status="not_for_me"] {
    color: #b91c1c;
    border-color: #b91c1c;
  }
</style>
