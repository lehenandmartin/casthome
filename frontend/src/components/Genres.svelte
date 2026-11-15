<script lang="ts">
  import { api, cached } from '../lib/api';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { Genre } from '../lib/types';

  let genres = $state<Genre[]>(cached.genres() ?? []);
  let loaded = $state(cached.genres() !== undefined);
  const arrive = cached.genres() === undefined;

  store.run(async () => {
    genres = await api.genres();
    loaded = true;
  });
</script>

<section class:arrive>
  <h2>{t('genres.title')}</h2>
  {#if !loaded}
    <ul aria-hidden="true">
      {#each { length: 12 } as _, i (i)}<li><span class="skeleton sk-genre"></span></li>{/each}
    </ul>
  {/if}
  {#if loaded && genres.length === 0}
    <p class="muted">{t('genres.empty')}</p>
  {/if}
  <ul class="rows" role="list">
    {#each genres as genre (genre.name)}
      <li>
        <a href={`#/genre/${encodeURIComponent(genre.name)}`}>
          <span>{genre.name}</span>
          <span class="muted">{t('genre.summary', { albums: genre.album_count, songs: genre.song_count })}</span>
        </a>
      </li>
    {/each}
  </ul>
</section>

<style>
  .sk-genre {
    height: 64px;
    border-radius: 8px;
  }
  ul {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 8px;
  }
  a {
    display: grid;
    gap: 2px;
    padding: 12px;
    border-radius: 8px;
    background: var(--surface);
    border: 1px solid var(--border);
    color: inherit;
    text-decoration: none;
  }
  a:hover {
    background: var(--surface-2);
  }
  /* Rows off screen are not laid out until they come near (long lists on phones);
     the estimated height keeps the page's total height, and Back's position, right. */
  ul.rows > li {
    content-visibility: auto;
    contain-intrinsic-size: auto 68px;
  }
</style>
