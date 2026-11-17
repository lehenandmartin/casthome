<script lang="ts">
  // A grid of artists (round pictures), like AlbumGrid for albums.
  import { coverUrl } from '../lib/api';
  import { menu } from '../lib/contextMenu.svelte';
  import { fullRows, observeColumns } from '../lib/grid';
  import { artistMenu } from '../lib/menus';
  import type { Artist } from '../lib/types';
  import Icon from './Icon.svelte';

  let {
    artists,
    rowsOnly = false,
  }: {
    artists: Artist[];
    /** Show only full rows for the current width (all of them if less than a row). */
    rowsOnly?: boolean;
  } = $props();

  let grid = $state<HTMLElement | null>(null);
  let columns = $state(0);
  $effect(() => {
    if (rowsOnly && grid) return observeColumns(grid, (n) => (columns = n));
  });
  const shown = $derived(rowsOnly ? fullRows(artists, columns) : artists);
</script>

<ul class="grid" role="list" bind:this={grid}>
  {#each shown as artist (artist.id)}
    <li>
      <a href={`#/artist/${encodeURIComponent(artist.id)}`} use:menu={() => artistMenu(artist)}>
        {#if artist.cover_art}
          <img src={coverUrl(artist.cover_art)} alt="" loading="lazy" />
        {:else}
          <span class="placeholder"><Icon name="artist" size={36} /></span>
        {/if}
        <strong>{artist.name}</strong>
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
    /* Three columns on a phone: two would make huge pictures. */
    grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
    gap: 16px 12px;
  }
  @media (min-width: 720px) {
    .grid {
      grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
      gap: 16px;
    }
  }
  a {
    display: grid;
    gap: 6px;
    justify-items: center;
    text-align: center;
    color: inherit;
    text-decoration: none;
    min-width: 0;
  }
  img,
  .placeholder {
    width: 100%;
    aspect-ratio: 1;
    object-fit: cover;
    border-radius: 50%;
    background: var(--surface-2);
  }
  .placeholder {
    display: grid;
    place-items: center;
    color: var(--muted);
  }
  strong {
    max-width: 100%;
    font-size: var(--text-sm);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
