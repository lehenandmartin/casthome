<script lang="ts">
  import { api } from '../lib/api';
  import { menu } from '../lib/contextMenu.svelte';
  import { artistMenu } from '../lib/menus';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { SearchResult } from '../lib/types';
  import AlbumGrid from './AlbumGrid.svelte';
  import SongList from './SongList.svelte';

  // Kept in the URL (#/search?q=...) so Back returns to the results.
  const initial = new URLSearchParams(location.hash.split('?')[1] ?? '').get('q') ?? '';
  let query = $state(initial);
  let result = $state<SearchResult | null>(null);
  let searched = $state('');
  let timer: ReturnType<typeof setTimeout> | undefined;

  async function run(q: string) {
    const trimmed = q.trim();
    history.replaceState(null, '', trimmed ? `#/search?q=${encodeURIComponent(trimmed)}` : '#/search');
    if (!trimmed) {
      result = null;
      searched = '';
      return;
    }
    await store.run(async () => {
      const r = await api.search(trimmed);
      if (query.trim() === trimmed) {
        result = r;
        searched = trimmed;
      }
    });
  }

  $effect(() => {
    const q = query;
    clearTimeout(timer);
    timer = setTimeout(() => run(q), 300);
    return () => clearTimeout(timer);
  });

  const empty = $derived(
    result !== null && result.artists.length + result.albums.length + result.songs.length === 0,
  );
</script>

<section>
  <!-- svelte-ignore a11y_autofocus -->
  <input
    type="search"
    placeholder={t('search.placeholder')}
    aria-label={t('search.title')}
    bind:value={query}
    autofocus
  />

  {#if empty}
    <p class="muted">{t('search.noResults', { query: searched })}</p>
  {/if}

  {#if result && result.artists.length > 0}
    <h3>{t('search.artists')}</h3>
    <ul class="artists">
      {#each result.artists as artist (artist.id)}
        <li><a href={`#/artist/${encodeURIComponent(artist.id)}`} use:menu={() => artistMenu(artist)}>{artist.name}</a></li>
      {/each}
    </ul>
  {/if}

  {#if result && result.albums.length > 0}
    <h3>{t('search.albums')}</h3>
    <AlbumGrid albums={result.albums} />
  {/if}

  {#if result && result.songs.length > 0}
    <h3>{t('search.songs')}</h3>
    <SongList
      songs={result.songs}
      onplay={(i) => store.run(() => api.playSongs(result!.songs.map((s) => s.id), i))}
    />
  {/if}
</section>

<style>
  input {
    width: 100%;
    font-size: 1.05rem;
  }
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
