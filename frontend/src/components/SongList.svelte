<script lang="ts">
  import { api } from '../lib/api';
  import { contextMenu, menu } from '../lib/contextMenu.svelte';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { songMenu } from '../lib/menus';
  import { startSongDrag } from '../lib/songDrag';
  import { store } from '../lib/store.svelte';
  import type { MenuSpec } from '../lib/contextMenu.svelte';
  import type { Song } from '../lib/types';
  import Icon from './Icon.svelte';
  import StarButton from './StarButton.svelte';
  import SwipeRow from './SwipeRow.svelte';

  let {
    songs,
    onplay,
    onremove,
    numbered = false,
    ranked = false,
    showAlbum = true,
  }: {
    songs: Song[];
    /** Clicking a row: usually "play this list from here". */
    onplay: (index: number) => void;
    /** When set, the menu offers "Remove from playlist". */
    onremove?: (index: number) => void;
    numbered?: boolean;
    /** Number rows 1, 2, 3… (a top list) instead of by track number. */
    ranked?: boolean;
    showAlbum?: boolean;
  } = $props();

  const currentId = $derived(store.player?.current?.id);
  // Desktop, queue panel open: rows can be dragged into the queue.
  const draggable = $derived(store.isDesktop && store.queuePanel);

  // The ⋯ button and a right-click on the row open the same menu.
  function menuFor(index: number): MenuSpec {
    const remove = onremove;
    return songMenu(
      songs[index],
      remove ? [{ label: t('playlist.removeTrack'), icon: 'trash', danger: true, action: () => remove(index) }] : [],
    );
  }

  async function addToQueue(song: Song) {
    await store.run(async () => {
      await api.queueSongs([song.id], 'queue');
      store.notify('added_to_queue', {}, 'info');
    });
  }
</script>


<ol class="songs" role="list">
  {#each songs as song, i (`${song.id}-${i}`)}
    <li
      class:current={song.id === currentId}
      use:menu={() => menuFor(i)}
      draggable={draggable ? 'true' : undefined}
      ondragstart={(e) => startSongDrag(e, song)}
    >
      <SwipeRow right={{ label: t('song.addToQueue'), icon: 'queue', action: () => addToQueue(song) }}>
      <button class="row" onclick={() => onplay(i)}>
        {#if ranked}<span class="num muted figures">{i + 1}</span>
        {:else if numbered}<span class="num muted figures">{song.track ?? i + 1}</span>{/if}
        <span class="text">
          <span class="title">{song.title}</span>
          {#if showAlbum}<span class="muted">{song.artist} · {song.album}</span>{/if}
        </span>
        <span class="muted figures">{formatTime(song.duration)}</span>
      </button>
      <StarButton kind="song" id={song.id} bind:starred={song.starred} />
      <button
        class="more"
        aria-label={t('song.more')}
        aria-haspopup="dialog"
        onclick={(e) => {
          e.stopPropagation();
          contextMenu.open(menuFor(i));
        }}><Icon name="more" size={20} /></button
      >
      </SwipeRow>
    </li>
  {/each}
</ol>

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
  /* Rows off screen are not laid out until they come near (long track lists on
     phones); the estimated height keeps the page's total height right. */
  .songs > li {
    content-visibility: auto;
    contain-intrinsic-size: auto 60px;
  }
</style>
