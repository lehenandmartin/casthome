<script lang="ts">
  import { api } from '../lib/api';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { Artist } from '../lib/types';

  let artists = $state<Artist[]>([]);
  let loaded = $state(false);
  let filter = $state('');

  store.run(async () => {
    artists = await api.artists();
    loaded = true;
  });

  const normalize = (s: string) => s.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
  const visible = $derived(filter ? artists.filter((a) => normalize(a.name).includes(normalize(filter))) : artists);
</script>

<section>
  <h2>{t('artists.title')}</h2>
  <input type="search" placeholder={t('artists.filter')} aria-label={t('artists.filter')} bind:value={filter} />
  {#if loaded && visible.length === 0}
    <p class="muted">{t('artists.empty')}</p>
  {/if}
  <ul>
    {#each visible as artist (artist.id)}
      <li>
        <a href={`#/artist/${encodeURIComponent(artist.id)}`}>
          <span>{artist.name}</span>
          <span class="muted">{t('album.count', { count: artist.album_count })}</span>
        </a>
      </li>
    {/each}
  </ul>
</section>

<style>
  input {
    width: 100%;
    margin-bottom: 12px;
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
</style>
