<script lang="ts">
  import { api } from '../lib/api';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { AddMode, Song } from '../lib/types';
  import Icon from './Icon.svelte';
  import PlaylistPicker from './PlaylistPicker.svelte';
  import RatingStars from './RatingStars.svelte';
  import StarButton from './StarButton.svelte';

  let {
    songs,
    onplay,
    onremove,
    numbered = false,
    showAlbum = true,
  }: {
    songs: Song[];
    /** Clicking a row: usually "play this list from here". */
    onplay: (index: number) => void;
    /** When set, the menu offers "Remove from playlist". */
    onremove?: (index: number) => void;
    numbered?: boolean;
    showAlbum?: boolean;
  } = $props();

  let menuFor = $state<number | null>(null);
  let pickerFor = $state<string | null>(null);
  const currentId = $derived(store.player?.current?.id);
  const menuSong = $derived(menuFor !== null ? (songs[menuFor] ?? null) : null);

  async function add(song: Song, mode: AddMode) {
    menuFor = null;
    await store.run(async () => {
      await api.queueSongs([song.id], mode);
      if (mode !== 'now') store.notify('added_to_queue', {}, 'info');
    });
  }
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && (menuFor = null)} />

<ol class="songs">
  {#each songs as song, i (`${song.id}-${i}`)}
    <li class:current={song.id === currentId}>
      <button class="row" onclick={() => onplay(i)}>
        {#if numbered}<span class="num muted">{song.track ?? i + 1}</span>{/if}
        <span class="text">
          <span class="title">{song.title}</span>
          {#if showAlbum}<span class="muted">{song.artist} · {song.album}</span>{/if}
        </span>
        <span class="muted">{formatTime(song.duration)}</span>
      </button>
      <StarButton kind="song" id={song.id} bind:starred={song.starred} />
      <button
        class="more"
        aria-label={t('song.more')}
        aria-haspopup="dialog"
        onclick={(e) => {
          e.stopPropagation();
          menuFor = i;
        }}><Icon name="more" size={20} /></button
      >
    </li>
  {/each}
</ol>

<!-- Actions open as a bottom sheet: a dropdown would end up under the player on mobile. -->
{#if menuSong && menuFor !== null}
  {@const index = menuFor}
  <div class="sheet-backdrop" role="presentation" onclick={() => (menuFor = null)}></div>
  <div class="sheet" role="dialog" aria-modal="true" aria-label={t('song.more')}>
    <div class="sheet-head">
      <span class="text">
        <strong class="ellipsis">{menuSong.title}</strong>
        <span class="muted ellipsis">{menuSong.artist}{menuSong.album ? ` · ${menuSong.album}` : ''}</span>
      </span>
      <RatingStars id={menuSong.id} bind:rating={songs[index].user_rating} />
    </div>
    <div class="sheet-actions" role="menu">
      <button role="menuitem" onclick={() => add(menuSong, 'now')}><Icon name="play" size={20} />{t('song.playNow')}</button>
      <button role="menuitem" onclick={() => add(menuSong, 'queue')}><Icon name="queue" size={20} />{t('song.addToQueue')}</button>
      <button
        role="menuitem"
        onclick={() => {
          pickerFor = menuSong.id;
          menuFor = null;
        }}><Icon name="playlist" size={20} />{t('song.addToPlaylist')}</button
      >
      {#if menuSong.album_id}
        <a role="menuitem" href={`#/album/${encodeURIComponent(menuSong.album_id)}`} onclick={() => (menuFor = null)}
          ><Icon name="disc" size={20} />{t('song.goToAlbum')}</a
        >
      {/if}
      {#if menuSong.artist_id}
        <a role="menuitem" href={`#/artist/${encodeURIComponent(menuSong.artist_id)}`} onclick={() => (menuFor = null)}
          ><Icon name="artist" size={20} />{t('song.goToArtist')}</a
        >
      {/if}
      {#if onremove}
        <button
          role="menuitem"
          class="danger"
          onclick={() => {
            menuFor = null;
            onremove(index);
          }}><Icon name="trash" size={20} />{t('playlist.removeTrack')}</button
        >
      {/if}
    </div>
  </div>
{/if}

{#if pickerFor}
  <PlaylistPicker songIds={[pickerFor]} onclose={() => (pickerFor = null)} />
{/if}

<style>
  .songs {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  li {
    display: flex;
    align-items: center;
    border-radius: 6px;
  }
  li:hover {
    background: var(--surface-2);
  }
  .row {
    flex: 1;
    min-width: 0;
    display: flex;
    gap: 10px;
    align-items: center;
    text-align: left;
    background: none;
    border: 0;
    padding: 10px 8px;
  }
  .num {
    width: 2em;
    flex: none;
  }
  .text {
    flex: 1;
    min-width: 0;
    display: grid;
  }
  .text > span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .current .title {
    color: var(--accent);
    font-weight: 600;
  }
  .more {
    display: grid;
    place-items: center;
    background: none;
    width: 40px;
    height: 40px;
    min-height: 0;
    padding: 0;
    color: var(--muted);
    flex: none;
  }
  .sheet-head {
    display: grid;
    gap: 8px;
    padding: 4px 4px 12px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 6px;
  }
  .sheet-head .text {
    display: grid;
    min-width: 0;
  }
  .sheet-actions {
    display: grid;
  }
  .sheet-actions > * {
    display: flex;
    align-items: center;
    gap: 14px;
    background: none;
    border-radius: 10px;
    padding: 12px 8px;
    text-align: left;
    text-decoration: none;
    color: inherit;
    font-size: 1rem;
  }
  .sheet-actions > *:hover {
    background: var(--surface-2);
  }
  .sheet-actions .danger {
    color: var(--danger);
  }
</style>
