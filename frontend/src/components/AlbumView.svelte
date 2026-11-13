<script lang="ts">
  import { api, coverUrl } from '../lib/api';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { Album } from '../lib/types';

  let { id }: { id: string } = $props();
  let album = $state<Album | null>(null);

  $effect(() => {
    album = null;
    const albumId = id;
    store.run(async () => {
      album = await api.album(albumId);
    });
  });

  const currentId = $derived(store.player?.current?.id);
</script>

{#if album}
  <section>
    <header>
      {#if album.cover_art}<img src={coverUrl(album.cover_art, 600)} alt="" />{/if}
      <div>
        <h2>{album.name}</h2>
        <p class="muted">{album.artist}{album.year ? ` · ${album.year}` : ''}</p>
        <p class="muted">{t('album.tracks', { count: album.song_count })} · {formatTime(album.duration)}</p>
        <div class="actions">
          <button class="primary" onclick={() => store.run(() => api.playAlbum(album!.id))}>{t('album.play')}</button>
          <button onclick={() => store.run(() => api.queueAlbum(album!.id, 'next'))}>{t('album.playNext')}</button>
          <button onclick={() => store.run(() => api.queueAlbum(album!.id, 'end'))}>{t('album.addToQueue')}</button>
        </div>
      </div>
    </header>
    <ol class="tracks">
      {#each album.songs ?? [] as song, i (song.id)}
        <li class:current={song.id === currentId}>
          <button class="row" onclick={() => store.run(() => api.playAlbum(album!.id, i))}>
            <span class="num muted">{song.track ?? i + 1}</span>
            <span class="title">{song.title}</span>
            <span class="muted">{formatTime(song.duration)}</span>
          </button>
        </li>
      {/each}
    </ol>
  </section>
{/if}

<style>
  header {
    display: grid;
    gap: 16px;
    margin-bottom: 16px;
  }
  @media (min-width: 640px) {
    header {
      grid-template-columns: 220px 1fr;
      align-items: end;
    }
  }
  img {
    width: 100%;
    max-width: 320px;
    aspect-ratio: 1;
    object-fit: cover;
    border-radius: 8px;
  }
  h2 {
    margin: 0 0 4px;
  }
  p {
    margin: 0 0 4px;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
  }
  .tracks {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .row {
    width: 100%;
    display: grid;
    grid-template-columns: 2.5em 1fr auto;
    gap: 8px;
    text-align: left;
    background: none;
    border: 0;
    border-radius: 6px;
    padding: 10px 8px;
  }
  .row:hover {
    background: var(--surface-2);
  }
  .title {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .current .title {
    color: var(--accent);
    font-weight: 600;
  }
</style>
