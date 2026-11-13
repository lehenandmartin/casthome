<script lang="ts">
  import { api } from '../lib/api';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { SearchResult } from '../lib/types';
  import AlbumGrid from './AlbumGrid.svelte';
  import SongList from './SongList.svelte';

  let starred = $state<SearchResult | null>(null);

  store.run(async () => {
    starred = await api.starred();
  });

  const empty = $derived(
    starred !== null && starred.artists.length + starred.albums.length + starred.songs.length === 0,
  );
</script>

<section>
  <h2>{t('favorites.title')}</h2>
  {#if empty}
    <p class="muted">{t('favorites.empty')}</p>
  {/if}

  {#if starred && starred.artists.length > 0}
    <h3>{t('search.artists')}</h3>
    <ul class="artists">
      {#each starred.artists as artist (artist.id)}
        <li><a href={`#/artist/${encodeURIComponent(artist.id)}`}>{artist.name}</a></li>
      {/each}
    </ul>
  {/if}

  {#if starred && starred.albums.length > 0}
    <h3>{t('search.albums')}</h3>
    <AlbumGrid albums={starred.albums} />
  {/if}

  {#if starred && starred.songs.length > 0}
    <h3>{t('search.songs')}</h3>
    <SongList
      songs={starred.songs}
      onplay={(i) => store.run(() => api.playSongs(starred!.songs.map((s) => s.id), i))}
    />
  {/if}
</section>

<style>
  h3 {
    margin: 20px 0 8px;
  }
  .artists {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .artists a {
    display: block;
    padding: 6px 12px;
    border-radius: 999px;
    background: var(--surface-2);
    color: inherit;
    text-decoration: none;
  }
</style>
