<script lang="ts">
  // Status selector for piece detail. Loads & writes through the
  // status store for the active profile. M5 spec §7 — exactly the
  // five values from decisions/0012-m5-local-accounts.md.
  import { onMount } from "svelte";
  import { getActiveProfileSync } from "../lib/storage/profile";
  import {
    getStatus,
    setStatus,
    type GradeSnapshot,
    type PieceStatus,
  } from "../lib/storage/status";

  // `gradeSnapshot` is what the user sees on the page when they
  // judge the piece. It's persisted alongside the status so we can
  // audit / replay / discard signals once the grader changes (today
  // most grades are from dummy-v0). See ADR 0013.
  type Props = { cid: string; gradeSnapshot?: GradeSnapshot };
  let { cid, gradeSnapshot }: Props = $props();

  let current = $state<PieceStatus>("not_seen");
  let profileId = $state<string | null>(null);

  onMount(async () => {
    const p = getActiveProfileSync();
    if (!p) return;
    profileId = p.id;
    current = await getStatus(p.id, cid);
  });

  async function set(next: PieceStatus) {
    if (!profileId) return;
    // Toggle off if user clicks the active state again
    const target = next === current ? "not_seen" : next;
    current = target;
    await setStatus(profileId, cid, target, gradeSnapshot);
  }

  const BUTTONS: { value: PieceStatus; label: string; hint: string }[] = [
    { value: "playing", label: "Playing", hint: "I'm working on this" },
    { value: "completed", label: "Completed", hint: "I can play this" },
    { value: "too_hard", label: "Too hard", hint: "above my level right now" },
    { value: "not_for_me", label: "Not for me", hint: "skip this in the feed" },
  ];
</script>

<div class="status" role="group" aria-label="piece status">
  {#each BUTTONS as b}
    <button
      type="button"
      class:active={current === b.value}
      onclick={() => set(b.value)}
      title={b.hint}
      aria-pressed={current === b.value}
    >
      {b.label}
    </button>
  {/each}
</div>

<style>
  .status {
    display: inline-flex;
    gap: 0.3rem;
    flex-wrap: wrap;
    align-items: center;
  }
  button {
    font-size: 0.85em;
    padding: 0.3rem 0.6rem;
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 999px;
    cursor: pointer;
    color: inherit;
  }
  button:hover {
    border-color: var(--accent);
  }
  button.active {
    background: var(--accent);
    color: white;
    border-color: var(--accent);
  }
</style>
