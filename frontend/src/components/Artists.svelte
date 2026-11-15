<script lang="ts">
  import { api, cached } from '../lib/api';
  import { menu } from '../lib/contextMenu.svelte';
  import { artistMenu } from '../lib/menus';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { Artist } from '../lib/types';
  import FavoritesToggle from './FavoritesToggle.svelte';
  import SkeletonList from './SkeletonList.svelte';

  let { fav = false }: { fav?: boolean } = $props();

  let artists = $state<Artist[]>(cached.artists() ?? []);
  let loaded = $state(cached.artists() !== undefined);
  const arrive = cached.artists() === undefined;
  let filter = $state('');

  store.run(async () => {
    artists = await api.artists();
    loaded = true;
  });

  const normalize = (s: string) => s.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
  const visible = $derived(
    artists.filter((a) => (!fav || a.starred) && (!filter || normalize(a.name).includes(normalize(filter)))),
  );
</script>

<section class:arrive>
  <h2>{t('artists.title')}</h2>
  <div class="filters">
    <input type="search" placeholder={t('artists.filter')} aria-label={t('artists.filter')} bind:value={filter} />
    <FavoritesToggle active={fav} />
  </div>
  {#if !loaded}
    <SkeletonList count={14} sub={false} />
  {/if}
  {#if loaded && visible.length === 0}
    <p class="muted">{fav ? t('favorites.noArtists') : t('artists.empty')}</p>
  {/if}
  <ul class="rows">
    {#each visible as artist (artist.id)}
      <li>
        <a href={`#/artist/${encodeURIComponent(artist.id)}`} use:menu={() => artistMenu(artist)}>
          <span>{artist.name}</span>
          <span class="muted">{t('album.count', { count: artist.album_count })}</span>
        </a>
      </li>
    {/each}
  </ul>
</section>

<style>
  .filters {
    display: flex;
    gap: 8px;
    align-items: center;
    margin-bottom: 12px;
  }
  input {
    flex: 1;
    min-width: 0;
  }
  ul {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  a {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 8px;
    border-radius: 6px;
    color: inherit;
    text-decoration: none;
  }
  a:hover {
    background: var(--surface-2);
  }
  a span:first-child {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .muted {
    flex: none;
  }
  /* Rows off screen are not laid out until they come near (long lists on phones);
     the estimated height keeps the page's total height, and Back's position, right. */
  ul.rows > li {
    content-visibility: auto;
    contain-intrinsic-size: auto 41px;
  }
</style>
