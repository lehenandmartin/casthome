<script lang="ts">
  import { api, coverUrl } from '../lib/api';
  import { menu } from '../lib/contextMenu.svelte';
  import { playlistMenu } from '../lib/menus';
  import { router } from '../lib/router.svelte';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { Playlist } from '../lib/types';

  let playlists = $state<Playlist[]>([]);
  let loaded = $state(false);
  let name = $state('');

  async function load() {
    await store.run(async () => {
      playlists = await api.playlists();
      loaded = true;
    });
  }

  async function create(event: SubmitEvent) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    await store.run(async () => {
      const playlist = await api.createPlaylist(trimmed);
      name = '';
      router.navigate(`#/playlist/${encodeURIComponent(playlist.id)}`);
    });
  }

  load();
</script>

<section>
  <h2>{t('playlists.title')}</h2>
  <form onsubmit={create}>
    <input type="text" bind:value={name} placeholder={t('playlists.namePlaceholder')} aria-label={t('playlists.new')} />
    <button class="primary" type="submit" disabled={!name.trim()}>{t('playlists.create')}</button>
  </form>
  {#if loaded && playlists.length === 0}
    <p class="muted">{t('playlists.empty')}</p>
  {/if}
  <ul>
    {#each playlists as playlist (playlist.id)}
      <li>
        <a href={`#/playlist/${encodeURIComponent(playlist.id)}`} use:menu={() => playlistMenu(playlist, load)}>
          {#if playlist.cover_art}
            <img src={coverUrl(playlist.cover_art, 96)} alt="" loading="lazy" />
          {:else}
            <span class="thumb"></span>
          {/if}
          <span class="text">
            <span>{playlist.name}</span>
            <span class="muted">
              {t('playlists.tracks', { count: playlist.song_count })} · {formatTime(playlist.duration)}
            </span>
          </span>
        </a>
      </li>
    {/each}
  </ul>
</section>

<style>
  form {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
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
  a {
    display: flex;
    gap: 12px;
    align-items: center;
    padding: 8px;
    border-radius: 6px;
    color: inherit;
    text-decoration: none;
  }
  a:hover {
    background: var(--surface-2);
  }
  img,
  .thumb {
    width: 48px;
    height: 48px;
    border-radius: 4px;
    object-fit: cover;
    background: var(--surface-2);
    flex: none;
  }
  .text {
    display: grid;
    min-width: 0;
  }
  .text > span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
