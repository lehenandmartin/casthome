<script lang="ts">
  import { dragHandle, dragHandleZone, type DndEvent } from 'svelte-dnd-action';
  import { flip } from 'svelte/animate';
  import { api, coverUrl } from '../lib/api';
  import { dialogs } from '../lib/dialog.svelte';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { QueueItem } from '../lib/types';
  import Icon from './Icon.svelte';

  // svelte-dnd-action keys items by `id`; the song id is kept as `song_id`.
  type Row = Omit<QueueItem, 'id'> & { id: number; song_id: string };
  const FLIP_MS = 150;

  const items = $derived(store.queue.items);
  const index = $derived(store.queue.index);
  const current = $derived(index !== null ? (items[index] ?? null) : null);
  const firstUpcoming = $derived(index === null ? 0 : index + 1);
  const history = $derived(index === null ? [] : items.slice(0, index));
  const p = $derived(store.player);
  const playing = $derived(p?.status === 'playing');

  // Local copy of the upcoming tracks so they can be reordered while dragging;
  // resynced from the server on every queue update.
  let upcoming = $state<Row[]>([]);
  let dragging = $state(false);
  let showHistory = $state(false);
  let menuOpen = $state(false);

  $effect(() => {
    const rows = items.slice(firstUpcoming).map((item) => ({ ...item, song_id: item.id, id: item.uid }));
    if (!dragging) upcoming = rows;
  });

  const remaining = $derived.by(() => {
    const rest = items.slice(firstUpcoming).reduce((sum, item) => sum + (item.duration || 0), 0);
    const currentLeft = current ? Math.max(0, (p?.duration ?? current.duration) - store.position) : 0;
    return rest + currentLeft;
  });

  function consider(e: CustomEvent<DndEvent<Row>>) {
    dragging = true;
    upcoming = e.detail.items;
  }

  async function finalize(e: CustomEvent<DndEvent<Row>>) {
    upcoming = e.detail.items;
    dragging = false;
    const uid = Number(e.detail.info.id);
    const to = firstUpcoming + upcoming.findIndex((r) => r.uid === uid);
    const from = items.findIndex((r) => r.uid === uid);
    if (to < firstUpcoming || to === from) return;
    await store.run(() => api.moveItem(uid, to));
  }

  async function saveAsPlaylist() {
    menuOpen = false;
    const name = await dialogs.prompt({
      title: t('queue.saveAsPlaylist'),
      placeholder: t('playlists.namePlaceholder'),
      confirmLabel: t('playlist.save'),
    });
    if (!name) return;
    await store.run(async () => {
      await api.createPlaylist(name, [], true);
      store.notify('playlist_saved', {}, 'info');
    });
  }

  async function clear() {
    menuOpen = false;
    const ok = await dialogs.confirm({
      title: t('queue.clear'),
      message: t('queue.clearConfirm'),
      confirmLabel: t('queue.clear'),
      danger: true,
    });
    if (ok) await store.run(api.clearQueue);
  }
</script>

<svelte:window onclick={() => (menuOpen = false)} />

<section>
  <header class="page-head">
    <div>
      <h2>{t('queue.title')}</h2>
      {#if items.length > 0}
        <p class="muted">{t('queue.summary', { count: items.length, time: formatTime(remaining) })}</p>
      {/if}
    </div>
    {#if items.length > 0}
      <div class="head-actions">
        <button
          class="chip"
          class:on={p?.shuffle}
          aria-pressed={p?.shuffle ?? false}
          onclick={() => store.run(() => api.setMode({ shuffle: !p?.shuffle }))}
        >
          <Icon name="shuffle" size={16} />{t('player.shuffle')}
        </button>
        <div class="menu-wrap">
          <button
            class="icon-btn"
            aria-label={t('song.more')}
            aria-expanded={menuOpen}
            onclick={(e) => {
              e.stopPropagation();
              menuOpen = !menuOpen;
            }}><Icon name="moreVertical" size={20} /></button
          >
          {#if menuOpen}
            <div class="menu" role="menu">
              <button role="menuitem" onclick={saveAsPlaylist}><Icon name="save" size={18} />{t('queue.saveAsPlaylist')}</button>
              <button role="menuitem" class="danger" onclick={clear}><Icon name="trash" size={18} />{t('queue.clear')}</button>
            </div>
          {/if}
        </div>
      </div>
    {/if}
  </header>

  {#if items.length === 0}
    <div class="empty">
      <Icon name="queue" size={44} />
      <p>{t('queue.empty')}</p>
      <a class="button primary" href="#/">{t('queue.browse')}</a>
    </div>
  {/if}

  {#if current}
    <p class="section">{t('queue.nowPlaying')}</p>
    <button class="current" onclick={() => store.openNowPlaying()}>
      {#if current.cover_art}
        <img src={coverUrl(current.cover_art, 128)} alt="" />
      {:else}
        <span class="thumb big"><Icon name="disc" size={24} /></span>
      {/if}
      <span class="text">
        <span class="title ellipsis">{current.title}</span>
        <span class="muted ellipsis">{current.artist}{current.album ? ` · ${current.album}` : ''}</span>
      </span>
      {#if playing}
        <span class="eq" aria-hidden="true"><i></i><i></i><i></i></span>
      {:else}
        <span class="muted">{formatTime(current.duration)}</span>
      {/if}
    </button>
  {/if}

  {#if upcoming.length > 0}
    <p class="section">{t('queue.upNext')} <span class="count">{upcoming.length}</span></p>
    <ol
      class="list"
      use:dragHandleZone={{ items: upcoming, flipDurationMs: FLIP_MS, dropTargetStyle: {} }}
      onconsider={consider}
      onfinalize={finalize}
    >
      {#each upcoming as item (item.id)}
        <li animate:flip={{ duration: FLIP_MS }}>
          <span class="handle" use:dragHandle aria-label={t('queue.drag')} title={t('queue.drag')}>
            <Icon name="grip" size={18} />
          </span>
          <button class="row" onclick={() => store.run(() => api.jump(item.uid))}>
            {#if item.cover_art}
              <img src={coverUrl(item.cover_art, 96)} alt="" loading="lazy" />
            {:else}
              <span class="thumb"><Icon name="disc" size={18} /></span>
            {/if}
            <span class="text">
              <span class="ellipsis">{item.title}</span>
              <span class="muted ellipsis">{item.artist}</span>
            </span>
            <span class="muted time">{formatTime(item.duration)}</span>
          </button>
          <button
            class="icon-btn remove"
            aria-label={t('queue.remove')}
            title={t('queue.remove')}
            onclick={() => store.run(() => api.removeItem(item.uid))}><Icon name="close" size={18} /></button
          >
        </li>
      {/each}
    </ol>
  {:else if current}
    <p class="muted end">{t('queue.nothingNext')}</p>
  {/if}

  {#if history.length > 0}
    <button class="section toggle" aria-expanded={showHistory} onclick={() => (showHistory = !showHistory)}>
      {t('queue.history')} <span class="count">{history.length}</span>
      <Icon name={showHistory ? 'chevronDown' : 'chevronRight'} size={16} />
    </button>
    {#if showHistory}
      <ol class="list history">
        {#each history as item (item.uid)}
          <li>
            <button class="row" onclick={() => store.run(() => api.jump(item.uid))}>
              {#if item.cover_art}
                <img src={coverUrl(item.cover_art, 96)} alt="" loading="lazy" />
              {:else}
                <span class="thumb"><Icon name="disc" size={18} /></span>
              {/if}
              <span class="text">
                <span class="ellipsis">{item.title}</span>
                <span class="muted ellipsis">{item.artist}</span>
              </span>
              <span class="muted time">{formatTime(item.duration)}</span>
            </button>
            <button
              class="icon-btn remove"
              aria-label={t('queue.remove')}
              title={t('queue.remove')}
              onclick={() => store.run(() => api.removeItem(item.uid))}><Icon name="close" size={18} /></button
            >
          </li>
        {/each}
      </ol>
    {/if}
  {/if}
</section>

<style>
  .page-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }
  .page-head h2 {
    margin-bottom: 0;
  }
  .page-head p {
    margin: 2px 0 0;
  }
  .head-actions {
    display: flex;
    align-items: center;
    gap: 4px;
    padding-top: 4px;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.9rem;
    padding: 6px 12px;
    min-height: 34px;
  }
  .chip.on {
    background: var(--accent-soft);
    color: var(--accent);
  }
  .menu-wrap {
    position: relative;
  }
  .menu {
    position: absolute;
    right: 0;
    top: 100%;
    z-index: 15;
    display: grid;
    min-width: 210px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    box-shadow: var(--shadow);
    padding: 6px;
  }
  .menu button {
    display: flex;
    align-items: center;
    gap: 10px;
    background: none;
    border-radius: 8px;
    text-align: left;
    padding: 10px 12px;
  }
  .menu button:hover {
    background: var(--surface-2);
  }
  .danger {
    color: var(--danger);
  }
  .section {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 22px 0 8px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--muted);
  }
  .count {
    font-weight: 600;
    letter-spacing: 0;
    padding: 1px 8px;
    border-radius: 999px;
    background: var(--surface-2);
  }
  .toggle {
    background: none;
    padding: 0;
    min-height: 0;
    border-radius: 0;
  }
  .empty {
    display: grid;
    justify-items: center;
    gap: 8px;
    padding: 48px 16px;
    text-align: center;
    color: var(--muted);
  }
  .button {
    display: inline-block;
    padding: 9px 18px;
    border-radius: 999px;
    text-decoration: none;
    font-weight: 600;
  }
  .button.primary {
    background: var(--accent);
    color: var(--on-accent);
  }
  .current {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 14px;
    text-align: left;
    padding: 10px;
    border-radius: var(--radius);
    background: var(--accent-soft);
    min-height: 0;
  }
  .current img,
  .thumb.big {
    width: 56px;
    height: 56px;
  }
  .current .title {
    font-weight: 700;
    color: var(--accent);
  }
  .list {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .list li {
    display: flex;
    align-items: center;
    border-radius: 10px;
    background: var(--bg);
  }
  .list li:hover {
    background: var(--surface-2);
  }
  .history li {
    opacity: 0.65;
  }
  .history .row {
    padding-left: 10px;
  }
  .handle {
    flex: none;
    width: 34px;
    height: 48px;
    display: grid;
    place-items: center;
    color: var(--muted);
    cursor: grab;
    touch-action: none;
  }
  .row {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 12px;
    text-align: left;
    background: none;
    padding: 6px 4px;
    border-radius: 10px;
    min-height: 0;
  }
  img,
  .thumb {
    width: 44px;
    height: 44px;
    border-radius: 6px;
    object-fit: cover;
    background: var(--surface-2);
    color: var(--muted);
    display: grid;
    place-items: center;
    flex: none;
  }
  .text {
    flex: 1;
    display: grid;
    min-width: 0;
  }
  .time {
    font-variant-numeric: tabular-nums;
  }
  .remove {
    color: var(--muted);
    flex: none;
  }
  .end {
    margin: 12px 4px;
  }
  .eq {
    display: inline-flex;
    align-items: flex-end;
    gap: 2px;
    height: 16px;
    color: var(--accent);
    flex: none;
  }
  .eq i {
    width: 3px;
    background: currentColor;
    border-radius: 1px;
    animation: eq 0.9s ease-in-out infinite;
  }
  .eq i:nth-child(2) {
    animation-delay: -0.3s;
  }
  .eq i:nth-child(3) {
    animation-delay: -0.6s;
  }
  @keyframes eq {
    0%,
    100% {
      height: 4px;
    }
    50% {
      height: 16px;
    }
  }
</style>
