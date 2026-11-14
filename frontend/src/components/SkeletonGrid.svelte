<script lang="ts">
  // Placeholder for AlbumGrid (square covers) or ArtistGrid (round pictures).
  import { observeColumns } from '../lib/grid';

  let {
    count = 8,
    round = false,
    rows,
  }: {
    count?: number;
    round?: boolean;
    /** Fill this many full rows for the current width, instead of `count`. */
    rows?: number;
  } = $props();

  let grid = $state<HTMLElement | null>(null);
  let columns = $state(0);
  $effect(() => {
    if (rows && grid) return observeColumns(grid, (n) => (columns = n));
  });
  const shown = $derived(rows && columns > 0 ? rows * columns : count);
</script>

<ul class="grid" class:round aria-hidden="true" bind:this={grid}>
  {#each { length: shown } as _, i (i)}
    <li>
      <span class="skeleton cover" class:round></span>
      <span class="skeleton text title"></span>
      {#if !round}<span class="skeleton text sub"></span>{/if}
    </li>
  {/each}
</ul>

<style>
  .grid {
    list-style: none;
    padding: 0;
    margin: 0 0 16px;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 16px;
  }
  /* Same columns as ArtistGrid. */
  .grid.round {
    grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
    gap: 16px 12px;
  }
  @media (min-width: 720px) {
    .grid.round {
      grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
      gap: 16px;
    }
  }
  li {
    display: grid;
    gap: 6px;
  }
  .round li {
    justify-items: center;
  }
  .cover {
    width: 100%;
    aspect-ratio: 1;
    border-radius: 8px;
  }
  .cover.round {
    border-radius: 50%;
  }
  .title {
    width: 75%;
  }
  .sub {
    width: 45%;
  }
</style>
