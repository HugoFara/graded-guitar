<script lang="ts">
  import { onMount } from "svelte";
  import { push } from "svelte-spa-router";
  import {
    createProfile,
    deleteProfile,
    getActiveProfile,
    listProfiles,
    setActiveProfile,
    updateProfile,
    type Profile,
  } from "../lib/storage/profile";
  import { clearAllStatuses } from "../lib/storage/status";
  import {
    backupFilename,
    exportProfile,
    importProfile,
    type ProfileBackup,
  } from "../lib/storage/backup";
  import { MAX_LEVEL, MIN_LEVEL } from "../lib/level";

  let profiles = $state<Profile[]>([]);
  let activeId = $state<string | null>(null);
  let newName = $state("");
  let newLevel = $state<number | "">("");
  let error = $state<string | null>(null);
  let importInfo = $state<string | null>(null);
  let busy = $state(false);
  let fileInput: HTMLInputElement | undefined = $state();

  async function refresh() {
    profiles = await listProfiles();
    const active = await getActiveProfile();
    activeId = active?.id ?? null;
  }

  onMount(refresh);

  async function activate(id: string) {
    busy = true;
    try {
      await setActiveProfile(id);
      await refresh();
      // Notify the header chip (listens for hashchange already; dispatch
      // a storage event so multi-tab also stays in sync if it matters).
      window.dispatchEvent(new Event("hashchange"));
    } finally {
      busy = false;
    }
  }

  async function create() {
    error = null;
    busy = true;
    try {
      const lvl =
        newLevel === ""
          ? null
          : Number.isFinite(newLevel as number)
            ? (newLevel as number)
            : null;
      const created = await createProfile({ display_name: newName, level: lvl });
      await setActiveProfile(created.id);
      newName = "";
      newLevel = "";
      await refresh();
      window.dispatchEvent(new Event("hashchange"));
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      busy = false;
    }
  }

  async function rename(p: Profile, name: string) {
    if (!name.trim()) return;
    busy = true;
    try {
      await updateProfile(p.id, { display_name: name });
      await refresh();
      window.dispatchEvent(new Event("hashchange"));
    } finally {
      busy = false;
    }
  }

  async function changeLevel(p: Profile, raw: string) {
    const n = raw === "" ? null : parseInt(raw, 10);
    if (n != null && (!Number.isFinite(n) || n < MIN_LEVEL || n > MAX_LEVEL)) {
      return;
    }
    busy = true;
    try {
      await updateProfile(p.id, { level: n });
      await refresh();
      window.dispatchEvent(new Event("hashchange"));
    } finally {
      busy = false;
    }
  }

  async function downloadBackup(p: Profile) {
    busy = true;
    try {
      const dump = await exportProfile(p);
      const blob = new Blob([JSON.stringify(dump, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = backupFilename(p);
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } finally {
      busy = false;
    }
  }

  // "Share signals" path — downloads the same JSON as Export, then
  // opens a draft email pre-filled with attach-this-file instructions.
  // We can't programmatically attach to mailto: from the browser, so
  // we keep it honest: the user downloads, then attaches.
  //
  // This is the only outbound channel for user library data. It must
  // stay strictly opt-in. See the privacy note for what's in the file.
  const SIGNAL_TO = "github@hugofara.net";

  async function shareSignals(p: Profile) {
    await downloadBackup(p);
    const subject = encodeURIComponent("graded-guitar beta — library signals");
    const body = encodeURIComponent(
      [
        "Hi Hugo,",
        "",
        "Sharing my graded-guitar library so you can use my piece statuses",
        "and grade-disagreement votes as input to the grader.",
        "",
        `Profile name: ${p.display_name}`,
        `Declared level: ${p.level ?? "(not set)"}`,
        "",
        "(Attach the file that just downloaded: " + backupFilename(p) + ")",
        "",
        "Anything else worth knowing?",
        "",
        "Thanks,",
      ].join("\n"),
    );
    window.location.href = `mailto:${SIGNAL_TO}?subject=${subject}&body=${body}`;
  }

  async function onImportFile(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    error = null;
    importInfo = null;
    busy = true;
    try {
      const text = await file.text();
      const payload = JSON.parse(text) as ProfileBackup;
      const result = await importProfile(payload);
      await refresh();
      window.dispatchEvent(new Event("hashchange"));
      const voteSuffix = result.votes_imported > 0
        ? `, ${result.votes_imported} grade votes (${result.votes_skipped} skipped)`
        : "";
      importInfo =
        `Imported "${result.profile.display_name}" — ${result.imported} statuses (${result.skipped} skipped)${voteSuffix}.`;
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      busy = false;
      // Allow re-importing the same file later
      if (input) input.value = "";
    }
  }

  async function remove(p: Profile) {
    if (!window.confirm(`Delete profile "${p.display_name}"? This wipes its library on this browser.`)) {
      return;
    }
    busy = true;
    try {
      await deleteProfile(p.id);
      // Also wipe their status records — deleteProfile only handles
      // the profile table; status data lives under its own key.
      await clearAllStatuses(p.id);
      await refresh();
      window.dispatchEvent(new Event("hashchange"));
      if (profiles.length === 0) push("/onboard");
    } finally {
      busy = false;
    }
  }
</script>

<section class="profile">
  <h2>Profiles</h2>
  <p class="lead">
    Profiles live in this browser only. They don't sync across devices.
    See <a href="#/privacy">the privacy note</a> for what's stored.
  </p>

  {#if profiles.length === 0}
    <p class="empty">No profile yet. <a href="#/onboard">Start onboarding</a>.</p>
  {:else}
    <ul class="list">
      {#each profiles as p (p.id)}
        <li class="row" class:active={p.id === activeId}>
          <div class="head">
            <input
              class="name"
              value={p.display_name}
              onchange={(e) => rename(p, (e.target as HTMLInputElement).value)}
              aria-label="display name"
            />
            {#if p.id === activeId}
              <span class="badge">active</span>
            {:else}
              <button type="button" disabled={busy} onclick={() => activate(p.id)}>
                Switch to this
              </button>
            {/if}
          </div>
          <div class="meta">
            <label>
              Level
              <input
                type="number"
                min={MIN_LEVEL}
                max={MAX_LEVEL}
                value={p.level ?? ""}
                onchange={(e) => changeLevel(p, (e.target as HTMLInputElement).value)}
                aria-label="playing level"
              />
            </label>
            <span class="created">created {p.created_at.slice(0, 10)}</span>
            <button type="button" disabled={busy} onclick={() => downloadBackup(p)}>
              Export JSON
            </button>
            <button
              type="button"
              disabled={busy}
              onclick={() => shareSignals(p)}
              title="Send your library to the developers as M6 beta feedback"
            >
              Share signals…
            </button>
            <button class="danger" type="button" disabled={busy} onclick={() => remove(p)}>
              Delete
            </button>
          </div>
        </li>
      {/each}
    </ul>
  {/if}

  <h3>Create another profile</h3>
  <div class="create">
    <input
      placeholder="Display name (e.g. Practice, Lessons, Recital prep)"
      bind:value={newName}
      aria-label="new profile name"
    />
    <input
      type="number"
      min={MIN_LEVEL}
      max={MAX_LEVEL}
      placeholder="Level"
      bind:value={newLevel}
      aria-label="new profile level"
    />
    <button type="button" disabled={busy || !newName.trim()} onclick={create}>
      Create
    </button>
  </div>
  {#if error}
    <p class="error">{error}</p>
  {/if}

  <h3>Share signals with the project</h3>
  <p class="hint">
    During the M6 beta we use real library data to improve the grader.
    <strong>Share signals…</strong> downloads your library as JSON and
    opens a pre-filled email so you can attach it. Strictly opt-in.
    See <a href="#/privacy">the privacy note</a> for what's in the file.
  </p>

  <h3>Import a backup</h3>
  <p class="hint">
    Imports a JSON backup as a new profile. Existing profiles are
    untouched — you can rename or delete them afterward.
  </p>
  <div class="create">
    <input
      bind:this={fileInput}
      type="file"
      accept="application/json,.json"
      disabled={busy}
      onchange={onImportFile}
      aria-label="import profile backup"
    />
  </div>
  {#if importInfo}
    <p class="info">{importInfo}</p>
  {/if}
</section>

<style>
  .profile {
    max-width: 50rem;
    margin: 1rem auto;
  }
  .lead {
    color: var(--muted);
  }
  .list {
    list-style: none;
    padding: 0;
    margin: 1rem 0;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  .row {
    padding: 0.7rem;
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }
  .row.active {
    border-color: var(--accent);
  }
  .head {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .head .name {
    flex: 1;
    font-size: 1em;
    font-weight: 500;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 0.2rem 0.4rem;
  }
  .head .name:hover,
  .head .name:focus {
    border-color: var(--border);
    background: var(--bg, transparent);
  }
  .badge {
    font-size: 0.75em;
    padding: 0.1rem 0.5rem;
    border-radius: 999px;
    background: var(--accent);
    color: white;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .meta {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
    font-size: 0.85em;
    color: var(--muted);
  }
  .meta label {
    display: flex;
    align-items: center;
    gap: 0.3rem;
  }
  .meta input[type="number"] {
    width: 4rem;
  }
  .created {
    font-variant-numeric: tabular-nums;
  }
  .danger {
    margin-left: auto;
    color: #b91c1c;
  }
  .create {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-top: 0.5rem;
  }
  .create input[type="number"] {
    width: 5rem;
  }
  .empty {
    color: var(--muted);
  }
  .error {
    color: #b91c1c;
  }
  .info {
    color: var(--accent);
  }
  .hint {
    color: var(--muted);
    font-size: 0.9em;
  }
</style>
