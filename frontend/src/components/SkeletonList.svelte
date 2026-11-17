<script lang="ts">
  // Placeholder rows for track and item lists, at the height of the real rows.
  let { count = 8, thumb = false, sub = true }: { count?: number; thumb?: boolean; sub?: boolean } = $props();
  // Varied widths, so the placeholder reads as text rather than a grid.
  const widths = [62, 48, 70, 40, 56, 66, 44, 58];
</script>

<ol class="rows" aria-hidden="true">
  {#each { length: count } as _, i (i)}
    <li>
      {#if thumb}<span class="skeleton thumb"></span>{/if}
      <span class="text">
        <span class="skeleton text" style:width={`${widths[i % widths.length]}%`}></span>
        {#if sub}<span class="skeleton text small" style:width={`${widths[(i + 3) % widths.length] - 15}%`}></span>{/if}
      </span>
    </li>
  {/each}
</ol>

<style>
  .rows {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  li {
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 58px;
    padding: 0 8px;
  }
  .thumb {
    width: 44px;
    height: 44px;
    flex: none;
  }
  .text {
    flex: 1;
    display: grid;
    gap: 8px;
  }
  .small {
    height: 0.75em;
  }
</style>
