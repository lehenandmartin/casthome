<script lang="ts">
  import { api, coverUrl } from '../lib/api';
  import { dialogs } from '../lib/dialog.svelte';
  import { router } from '../lib/router.svelte';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { Playlist } from '../lib/types';
  import SongList from './SongList.svelte';

  let { id }: { id: string } = $props();
  let playlist = $state<Playlist | null>(null);
  let renaming = $state(false);
  let newName = $state('');

  async function load(playlistId: string) {
    await store.run(async () => {
      playlist = await api.playlist(playlistId);
    });
  }

  $effect(() => {
    playlist = null;
    load(id);
  });

  async function rename(event: SubmitEvent) {
    event.preventDefault();
    const name = newName.trim();
    if (!playlist || !name) return;
    const playlistId = playlist.id;
    await store.run(async () => {
      await api.updatePlaylist(playlistId, { name });
      if (playlist) playlist.name = name;
      renaming = false;
    });
  }

  async function remove(index: number) {
    if (!playlist) return;
    const playlistId = playlist.id;
    await store.run(async () => {
      await api.updatePlaylist(playlistId, { remove_indexes: [index] });
      await load(playlistId);
    });
  }

  async function destroy() {
    if (!playlist) return;
    const ok = await dialogs.confirm({
      title: t('playlist.delete'),
      message: t('playlist.deleteConfirm', { name: playlist.name }),
      confirmLabel: t('playlist.delete'),
      danger: true,
    });
    if (!ok || !playlist) return;
    const playlistId = playlist.id;
    await store.run(async () => {
      await api.deletePlaylist(playlistId);
      router.navigate('#/playlists', { replace: true });
    });
  }

  async function queue(mode: 'next' | 'end') {
    if (!playlist) return;
    const playlistId = playlist.id;
    await store.run(async () => {
      await api.queuePlaylist(playlistId, mode);
      store.notify('added_to_queue', {}, 'info');
    });
  }
</script>

{#if playlist}
  <section>
    <header>
      {#if playlist.cover_art}<img src={coverUrl(playlist.cover_art, 600)} alt="" />{/if}
      <div>
        {#if renaming}
          <form onsubmit={rename}>
            <!-- svelte-ignore a11y_autofocus -->
            <input type="text" bind:value={newName} aria-label={t('playlist.rename')} autofocus />
            <button class="primary" type="submit" disabled={!newName.trim()}>{t('playlist.save')}</button>
            <button type="button" onclick={() => (renaming = false)}>{t('playlist.cancel')}</button>
          </form>
        {:else}
          <h2>{playlist.name}</h2>
        {/if}
        <p class="muted">{t('playlists.tracks', { count: playlist.song_count })} · {formatTime(playlist.duration)}</p>
        <div class="actions">
          <button
            class="primary"
            disabled={!playlist.songs?.length}
            onclick={() => store.run(() => api.playPlaylist(playlist!.id))}>{t('playlist.play')}</button
          >
          <button disabled={!playlist.songs?.length} onclick={() => queue('next')}>{t('album.playNext')}</button>
          <button disabled={!playlist.songs?.length} onclick={() => queue('end')}>{t('album.addToQueue')}</button>
          <button
            onclick={() => {
              newName = playlist!.name;
              renaming = true;
            }}>{t('playlist.rename')}</button
          >
          <button class="danger" onclick={destroy}>{t('playlist.delete')}</button>
        </div>
      </div>
    </header>
    {#if !playlist.songs?.length}
      <p class="muted">{t('playlist.empty')}</p>
    {:else}
      <SongList
        songs={playlist.songs}
        onplay={(i) => store.run(() => api.playPlaylist(playlist!.id, i))}
        onremove={remove}
      />
    {/if}
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
  form {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 8px;
  }
  form input {
    flex: 1;
    min-width: 160px;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
  }
  .danger {
    color: var(--danger);
  }
</style>
