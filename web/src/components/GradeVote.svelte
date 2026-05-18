<script lang="ts">
  // Grade-disagreement vote — three buttons (easier / right / harder)
  // that record the user's opinion of the visible grade. Independent
  // of status (a vote is an opinion; a status is a commitment). See
  // ADR 0013, follow-up #2.
  //
  // The control hides itself when there's no grade to vote on: a
  // disagreement vote against a "no grade" badge has no meaning.
  import { onMount } from "svelte";
  import { getActiveProfileSync } from "../lib/storage/profile";
  import type { GradeSnapshot } from "../lib/storage/status";
  import {
    getVote,
    setVote,
    type GradeVote,
  } from "../lib/storage/votes";

  type Props = { cid: string; gradeSnapshot?: GradeSnapshot };
  let { cid, gradeSnapshot }: Props = $props();

  let current = $state<GradeVote | null>(null);
  let profileId = $state<string | null>(null);

  onMount(async () => {
    const p = getActiveProfileSync();
    if (!p) return;
    profileId = p.id;
    current = await getVote(p.id, cid);
  });

  async function vote(next: GradeVote) {
    if (!profileId) return;
    // Toggle off if the user clicks the active vote again — same UX
    // rule as StatusSelector.
    const target = next === current ? null : next;
    current = target;
    await setVote(profileId, cid, target, gradeSnapshot);
  }

  const BUTTONS: { value: GradeVote; label: string; hint: string }[] = [
    { value: "easier", label: "Easier", hint: "I think this is graded too high" },
    { value: "right", label: "About right", hint: "the grade looks correct" },
    { value: "harder", label: "Harder", hint: "I think this is graded too low" },
  ];
</script>

{#if gradeSnapshot}
  <div class="vote" role="group" aria-label="grade disagreement vote">
    <span class="prompt">Grade feels:</span>
    {#each BUTTONS as b}
      <button
        type="button"
        class:active={current === b.value}
        onclick={() => vote(b.value)}
        title={b.hint}
        aria-pressed={current === b.value}
        data-vote={b.value}
      >
        {b.label}
      </button>
    {/each}
  </div>
{/if}

<style>
  .vote {
    display: inline-flex;
    gap: 0.3rem;
    flex-wrap: wrap;
    align-items: center;
    font-size: 0.85em;
  }
  .prompt {
    color: var(--muted);
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
