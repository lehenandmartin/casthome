<script lang="ts">
  import { coverUrl } from '../lib/api';
  import { menu } from '../lib/contextMenu.svelte';
  import { fullRows, observeColumns } from '../lib/grid';
  import { albumMenu } from '../lib/menus';
  import type { Album } from '../lib/types';

  let {
    albums,
    showArtist = true,
    rowsOnly = false,
  }: {
    albums: Album[];
    showArtist?: boolean;
    /** Show only full rows for the current width (all of them if less than a row). */
    rowsOnly?: boolean;
  } = $props();

  let grid = $state<HTMLElement | null>(null);
  let columns = $state(0);
  $effect(() => {
    if (rowsOnly && grid) return observeColumns(grid, (n) => (columns = n));
  });
  const shown = $derived(rowsOnly ? fullRows(albums, columns) : albums);
</script>

<ul class="grid" role="list" bind:this={grid}>
  {#each shown as album (album.id)}
    <li>
      <a href={`#/album/${encodeURIComponent(album.id)}`} use:menu={() => albumMenu(album)}>
        {#if album.cover_art}
          <img src={coverUrl(album.cover_art)} alt="" loading="lazy" />
        {:else}
          <div class="cover-placeholder"></div>
        {/if}
        <strong>{album.name}</strong>
        <span class="muted" class:figures={!showArtist}>{showArtist ? album.artist : (album.year ?? '')}</span>
      </a>
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
  a {
    display: grid;
    gap: 4px;
    color: inherit;
    text-decoration: none;
    min-width: 0;
  }
  img,
  .cover-placeholder {
    width: 100%;
    aspect-ratio: 1;
    object-fit: cover;
    border-radius: 8px;
    background: var(--surface-2);
  }
  strong,
  span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
