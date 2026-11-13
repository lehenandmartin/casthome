<script lang="ts">
  import { api } from '../lib/api';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { Playlist } from '../lib/types';

  let { songIds, onclose }: { songIds: string[]; onclose: () => void } = $props();
  let playlists = $state<Playlist[]>([]);
  let name = $state('');
  let busy = $state(false);

  store.run(async () => {
    playlists = await api.playlists();
  });

  async function addTo(playlist: Playlist) {
    busy = true;
    await store.run(async () => {
      await api.updatePlaylist(playlist.id, { add_song_ids: songIds });
      store.notify('playlist_added', { name: playlist.name }, 'info');
      onclose();
    });
    busy = false;
  }

  async function create(event: SubmitEvent) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    busy = true;
    await store.run(async () => {
      await api.createPlaylist(trimmed, songIds);
      store.notify('playlist_added', { name: trimmed }, 'info');
      onclose();
    });
    busy = false;
  }
</script>

<div class="sheet-backdrop" role="presentation" onclick={onclose}></div>
<div class="sheet" role="dialog" aria-modal="true" aria-label={t('playlist.pickTitle')}>
  <h3>{t('playlist.pickTitle')}</h3>
  <form onsubmit={create}>
    <input type="text" bind:value={name} placeholder={t('playlists.namePlaceholder')} aria-label={t('playlists.new')} />
    <button class="primary" type="submit" disabled={busy || !name.trim()}>{t('playlists.create')}</button>
  </form>
  <ul>
    {#each playlists as playlist (playlist.id)}
      <li>
        <button disabled={busy} onclick={() => addTo(playlist)}>
          <span>{playlist.name}</span>
          <span class="muted">{t('playlists.tracks', { count: playlist.song_count })}</span>
        </button>
      </li>
    {/each}
  </ul>
</div>

<style>
  h3 {
    margin: 0 0 12px;
  }
  form {
    display: flex;
    gap: 8px;
    margin-bottom: 8px;
  }
  form input {
    flex: 1;
    min-width: 0;
  }
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  li button {
    width: 100%;
    display: flex;
    justify-content: space-between;
    gap: 12px;
    text-align: left;
    background: none;
    border: 0;
    padding: 10px 8px;
    border-radius: 8px;
  }
  li button:hover {
    background: var(--surface-2);
  }
</style>
