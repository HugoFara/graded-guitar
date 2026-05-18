<script lang="ts">
  import { isDummySource, type ResolvedGrade } from "../lib/manifest";

  type Props = { resolved: ResolvedGrade };
  let { resolved }: Props = $props();

  const labelFor = (r: ResolvedGrade): string => {
    if (r.kind === "none") return "—";
    if (r.kind === "curator") return `G${r.grade}`;
    return `G${r.grade}${isDummySource(r.source) ? " (placeholder)" : " (estimated)"}`;
  };

  const titleFor = (r: ResolvedGrade): string => {
    if (r.kind === "none") return "No grade assigned";
    return `${r.kind} grade · source: ${r.source}`;
  };
</script>

<span
  class="badge"
  class:curator={resolved.kind === "curator"}
  class:model={resolved.kind === "model" && !(resolved.kind === "model" && isDummySource(resolved.source))}
  class:dummy={resolved.kind === "model" && isDummySource(resolved.source)}
  class:none={resolved.kind === "none"}
  title={titleFor(resolved)}
>
  {labelFor(resolved)}
</span>

<style>
  .badge {
    display: inline-block;
    padding: 0.15em 0.5em;
    font-size: 0.85em;
    border-radius: 3px;
    border: 1px solid var(--border);
    white-space: nowrap;
  }
  .curator {
    background: #dcfce7;
    border-color: #16a34a;
    color: #14532d;
  }
  .model {
    background: #dbeafe;
    border-color: #2563eb;
    color: #1e3a8a;
  }
  .dummy {
    background: var(--warn-bg);
    border-color: #d97706;
    color: var(--warn-fg);
  }
  .none {
    color: var(--muted);
  }
</style>
