<script lang="ts">
  import { api, coverUrl } from '../lib/api';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { Album } from '../lib/types';
  import SongList from './SongList.svelte';

  let { id }: { id: string } = $props();
  let album = $state<Album | null>(null);

  $effect(() => {
    album = null;
    const albumId = id;
    store.run(async () => {
      album = await api.album(albumId);
    });
  });
</script>

{#if album}
  <section>
    <header>
      {#if album.cover_art}<img src={coverUrl(album.cover_art, 600)} alt="" />{/if}
      <div>
        <h2>{album.name}</h2>
        <p class="muted"><a href={`#/artist/${encodeURIComponent(album.artist_id ?? '')}`}>{album.artist}</a>{album.year ? ` · ${album.year}` : ''}</p>
        <p class="muted">{t('album.tracks', { count: album.song_count })} · {formatTime(album.duration)}</p>
        <div class="actions">
          <button class="primary" onclick={() => store.run(() => api.playAlbum(album!.id))}>{t('album.play')}</button>
          <button onclick={() => store.run(() => api.queueAlbum(album!.id, 'next'))}>{t('album.playNext')}</button>
          <button onclick={() => store.run(() => api.queueAlbum(album!.id, 'end'))}>{t('album.addToQueue')}</button>
        </div>
      </div>
    </header>
    <SongList songs={album.songs ?? []} numbered showAlbum={false} onplay={(i) => store.run(() => api.playAlbum(album!.id, i))} />
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
  a {
    color: inherit;
  }
</style>
