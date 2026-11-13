<script lang="ts">
  import { api, coverUrl } from '../lib/api';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { Album } from '../lib/types';

  const PAGE = 40;
  let albums = $state<Album[]>([]);
  let loading = $state(false);
  let done = $state(false);

  async function loadMore() {
    loading = true;
    await store.run(async () => {
      const page = await api.albums('newest', PAGE, albums.length);
      albums = [...albums, ...page];
      done = page.length < PAGE;
    });
    loading = false;
  }

  loadMore();
</script>

<section>
  <h2>{t('albums.newest')}</h2>
  {#if !loading && albums.length === 0}
    <p class="muted">{t('albums.empty')}</p>
  {/if}
  <ul class="grid">
    {#each albums as album (album.id)}
      <li>
        <a href={`#/album/${encodeURIComponent(album.id)}`}>
          {#if album.cover_art}
            <img src={coverUrl(album.cover_art)} alt="" loading="lazy" />
          {:else}
            <div class="cover-placeholder"></div>
          {/if}
          <strong>{album.name}</strong>
          <span class="muted">{album.artist}</span>
        </a>
      </li>
    {/each}
  </ul>
  {#if !done && albums.length > 0}
    <button onclick={loadMore} disabled={loading}>{t('albums.loadMore')}</button>
  {/if}
</section>

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
