<script lang="ts">
  import { coverUrl } from '../lib/api';
  import { menu } from '../lib/contextMenu.svelte';
  import { albumMenu } from '../lib/menus';
  import type { Album } from '../lib/types';

  let { albums, showArtist = true }: { albums: Album[]; showArtist?: boolean } = $props();
</script>

<ul class="grid">
  {#each albums as album (album.id)}
    <li>
      <a href={`#/album/${encodeURIComponent(album.id)}`} use:menu={() => albumMenu(album)}>
        {#if album.cover_art}
          <img src={coverUrl(album.cover_art)} alt="" loading="lazy" />
        {:else}
          <div class="cover-placeholder"></div>
        {/if}
        <strong>{album.name}</strong>
        <span class="muted">{showArtist ? album.artist : (album.year ?? '')}</span>
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
