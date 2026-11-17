<script lang="ts">
  import { TRIGGERS, dragHandleZone, setAriaStrings, type DndEvent } from 'svelte-dnd-action';
  import { flip } from 'svelte/animate';
  import { api, coverUrl } from '../lib/api';
  import { menu } from '../lib/contextMenu.svelte';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { currentSongMenu, queueItemMenu } from '../lib/menus';
  import { dropTarget as targetAt, readLayout, type DropTarget, type Zone } from '../lib/queueDrop';
  import { carriesSongs, droppedSongs } from '../lib/songDrag';
  import { store } from '../lib/store.svelte';
  import type { MessageKey } from '../lib/i18n/en';
  import type { QueueItem } from '../lib/types';
  import Icon from './Icon.svelte';
  import QueueHeader from './QueueHeader.svelte';
  import QueueRow from './QueueRow.svelte';

  // svelte-dnd-action keys items by `id`; the song id is kept as `song_id`.
  type Row = Omit<QueueItem, 'id'> & { id: number; song_id: string };
  const FLIP_MS = 150;

  const items = $derived(store.queue.items);
  const index = $derived(store.queue.index);
  const current = $derived(index !== null ? (items[index] ?? null) : null);
  const firstUpcoming = $derived(index === null ? 0 : index + 1);
  // Rows removed by the user disappear at once, before the server confirms.
  let hidden = $state(new Set<number>());
  const history = $derived(index === null ? [] : items.slice(0, index).filter((item) => !hidden.has(item.uid)));
  const p = $derived(store.player);
  const playing = $derived(p?.status === 'playing');

  // Local copies of the two upcoming parts so they can be reordered (and
  // tracks dragged from one to the other); resynced on every queue update.
  //   queuedRows:  "Next in queue" (added by hand, plays first)
  //   contextRows: "Next from: <album/playlist>"
  let queuedRows = $state<Row[]>([]);
  let contextRows = $state<Row[]>([]);
  let dragging = $state(false);
  let showHistory = $state(false);

  $effect(() => {
    const rows = items
      .slice(firstUpcoming)
      .filter((item) => !hidden.has(item.uid))
      .map((item) => ({ ...item, song_id: item.id, id: item.uid }));
    if (!dragging) {
      queuedRows = rows.filter((r) => r.queued);
      contextRows = rows.filter((r) => !r.queued);
    }
  });

  // What screen readers hear while a track is moved with the keyboard, in the
  // interface language (the library's own strings are English only).
  $effect(() => {
    setAriaStrings({
      dragStarted: ({ itemLabel, zoneLabel, position, count }) =>
        t('dnd.started', { item: itemLabel, zone: zoneLabel, position, count }),
      movedToPosition: ({ itemLabel, zoneLabel, position, count }) =>
        t('dnd.moved', { item: itemLabel, zone: zoneLabel, position, count }),
      movedToZoneStart: ({ itemLabel, zoneLabel, position, count }) =>
        t('dnd.moved', { item: itemLabel, zone: zoneLabel, position, count }),
      movedToZoneEnd: ({ itemLabel, zoneLabel, position, count }) =>
        t('dnd.moved', { item: itemLabel, zone: zoneLabel, position, count }),
      dropped: ({ itemLabel, zoneLabel, position }) => t('dnd.dropped', { item: itemLabel, zone: zoneLabel, position }),
      zoneActiveInstruction: t('dnd.instruction'),
      zoneDragDisabledInstruction: t('dnd.disabled'),
    });
  });

  const upcomingCount = $derived(queuedRows.length + contextRows.length);
  const contextTitle = $derived(
    store.queue.radio
      ? t('queue.nextFromRadio', { title: store.queue.context_name ?? '' })
      : store.queue.context_name
        ? t('queue.nextFrom', { name: store.queue.context_name })
        : t('queue.nextFromUnnamed'),
  );
  const radioSource = $derived(
    store.queue.radio && store.queue.radio_source
      ? t(`radio.source.${store.queue.radio_source}` as MessageKey)
      : null,
  );

  const remaining = $derived.by(() => {
    const rest = items.slice(firstUpcoming).reduce((sum, item) => sum + (item.duration || 0), 0);
    const currentLeft = current ? Math.max(0, (p?.duration ?? current.duration) - store.position) : 0;
    return rest + currentLeft;
  });

  // Shown inside the queue sheet/panel (which has its own title).
  let { embedded = false }: { embedded?: boolean } = $props();

  // Tapping the current track shows the player: on mobile, go back to it
  // (closing the sheet) or open it if the queue was opened from a page.
  function openPlayer() {
    if (store.isDesktop) {
      store.openNowPlaying();
      return;
    }
    const wasOverPlayer = store.nowPlayingOpen;
    store.closeQueue();
    if (!wasOverPlayer) setTimeout(() => store.openNowPlaying(), 40);
  }

  // Right-click menu of a row ("Move to Next in queue" for album/playlist rows).
  const rowMenu = (row: Row, zone?: Zone) =>
    queueItemMenu({ ...row, id: row.song_id }, zone === 'context' ? () => toNextInQueue(row.uid) : undefined);

  function remove(uid: number) {
    hidden = new Set([...hidden, uid]);
    store.run(async () => {
      try {
        await api.removeItem(uid);
      } catch (error) {
        // Not removed: show it again.
        hidden = new Set([...hidden].filter((h) => h !== uid));
        throw error;
      }
    });
  }

  // Forget hidden rows once the server's queue no longer has them.
  $effect(() => {
    const present = new Set(items.map((item) => item.uid));
    const kept = [...hidden].filter((uid) => present.has(uid));
    if (kept.length !== hidden.size) hidden = new Set(kept);
  });

  // Swipe right on an album/playlist track: move it to the end of "Next in queue".
  function toNextInQueue(uid: number) {
    const to = firstUpcoming + queuedRows.length;
    store.run(async () => {
      await api.moveItem(uid, Math.min(to, items.length - 1), true);
      store.notify('added_to_queue', {}, 'info');
    });
  }

  function setRows(zone: Zone, rows: Row[]) {
    if (zone === 'queued') queuedRows = rows;
    else contextRows = rows;
  }

  function consider(zone: Zone, e: CustomEvent<DndEvent<Row>>) {
    setRows(zone, e.detail.items);
    // A keyboard drag ends with one more "consider" (dragStopped), after the
    // drop: it is not a drag, or the queue would stop following the server.
    dragging = e.detail.info.trigger !== TRIGGERS.DRAG_STOPPED;
  }

  async function finalize(zone: Zone, e: CustomEvent<DndEvent<Row>>) {
    setRows(zone, e.detail.items);
    dragging = false;
    const uid = Number(e.detail.info.id);
    const at = e.detail.items.findIndex((r) => r.uid === uid);
    if (at < 0) return; // this zone is where the track came from; the other one reports the drop
    const to = firstUpcoming + (zone === 'queued' ? at : queuedRows.length + at);
    const original = items.find((r) => r.uid === uid);
    const from = items.findIndex((r) => r.uid === uid);
    const queued = zone === 'queued';
    if (to === from && original?.queued === queued) return;
    await store.run(() => api.moveItem(uid, to, queued));
  }

  // --- tracks dragged in from a list (desktop) ---------------------------------
  let drop = $state<DropTarget | null>(null);
  let sectionEl: HTMLElement | undefined = $state();

  const dropTarget = (y: number) => targetAt(readLayout(sectionEl), y, queuedRows.length, contextRows.length);

  function dragOver(e: DragEvent) {
    if (!store.isDesktop || !carriesSongs(e)) return;
    e.preventDefault(); // accept the drop
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
    const target = dropTarget(e.clientY);
    if (drop?.zone !== target.zone || drop.offset !== target.offset) drop = target;
  }

  function dragLeave(e: DragEvent) {
    if (!sectionEl?.contains(e.relatedTarget as Node | null)) drop = null;
  }

  function dropSongs(e: DragEvent) {
    const ids = droppedSongs(e);
    const target = drop ?? dropTarget(e.clientY);
    drop = null;
    if (!ids) return;
    e.preventDefault();
    store.run(async () => {
      await api.dropSongs(ids, target.zone, target.offset);
      store.notify('added_to_queue', {}, 'info');
    });
  }
</script>

<svelte:window ondragend={() => (drop = null)} />

<section
  aria-label={t('queue.title')}
  bind:this={sectionEl}
  class:drop-over={drop !== null}
  ondragover={dragOver}
  ondragleave={dragLeave}
  ondrop={dropSongs}
>
  <QueueHeader {embedded} count={items.length} {remaining} />

  {#if items.length === 0}
    <div class="empty">
      <Icon name="queue" size={44} />
      <p>{t('queue.empty')}</p>
      <a class="button primary" href="#/" onclick={() => !store.isDesktop && store.closeQueue()}>{t('queue.browse')}</a>
    </div>
  {/if}

  {#if current}
    <p class="section">{t('queue.nowPlaying')}</p>
    <!-- Drop line under it: first in "Next in queue" (still empty, so not shown). -->
    <button
      class="current now-bar"
      class:drop-after={drop?.zone === 'queued' && queuedRows.length === 0}
      onclick={openPlayer}
      use:menu={() => currentSongMenu(current)}
    >
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
        <span class="muted figures">{formatTime(current.duration)}</span>
      {/if}
    </button>
  {/if}

  {#snippet zone(name: Zone, rows: Row[])}
    <ol
      class="list"
      aria-label={name === 'queued' ? t('queue.nextInQueue') : contextTitle}
      data-zone={name}
      class:drop-hint={(dragging || drop !== null) && rows.length === 0}
      class:drop-end={drop?.zone === name && drop.offset === rows.length && rows.length > 0}
      class:drop-into={drop?.zone === name && rows.length === 0}
      use:dragHandleZone={{ items: rows, type: 'upcoming', flipDurationMs: FLIP_MS, dropTargetStyle: {}, zoneTabIndex: -1 }}
      onconsider={(e) => consider(name, e)}
      onfinalize={(e) => finalize(name, e)}
    >
      {#each rows as item, i (item.id)}
        <li
          aria-label={`${item.title}, ${item.artist}`}
          animate:flip={{ duration: FLIP_MS }}
          use:menu={() => rowMenu(item, name)}
          class:drop-before={drop?.zone === name && drop.offset === i}
        >
          <QueueRow
            {item}
            handle
            onplay={() => store.run(() => api.jump(item.uid))}
            onremove={() => remove(item.uid)}
            onqueue={name === 'context' ? () => toNextInQueue(item.uid) : undefined}
          />
        </li>
      {/each}
    </ol>
  {/snippet}

  {#if queuedRows.length > 0 || (dragging && contextRows.length > 0)}
    <div class="section split">
      <span>{t('queue.nextInQueue')} <span class="count figures">{queuedRows.length}</span></span>
      {#if queuedRows.length > 0}
        <button class="link-btn" aria-label={t('queue.clearQueuedLabel')} onclick={() => store.run(api.clearQueued)}>
          {t('queue.clearQueued')}
        </button>
      {/if}
    </div>
    {@render zone('queued', queuedRows)}
  {/if}

  {#if contextRows.length > 0 || (dragging && queuedRows.length > 0)}
    <p class="section">
      {#if store.queue.radio}<Icon name="radio" size={14} />{/if}
      <span class="ellipsis">{contextTitle}</span> <span class="count figures">{contextRows.length}</span>
    </p>
    {#if store.queue.radio}
      <p class="radio-hint muted">{t('queue.radioHint')}{radioSource ? ` · ${radioSource}` : ''}</p>
    {/if}
    {@render zone('context', contextRows)}
  {/if}

  {#if current && upcomingCount === 0 && !dragging}
    <p class="muted end">{t('queue.nothingNext')}</p>
  {/if}

  {#if history.length > 0}
    <button class="section toggle" aria-expanded={showHistory} onclick={() => (showHistory = !showHistory)}>
      {t('queue.history')} <span class="count figures">{history.length}</span>
      <Icon name={showHistory ? 'chevronDown' : 'chevronRight'} size={16} />
    </button>
    {#if showHistory}
      <ol class="list history" role="list" aria-label={t('queue.history')}>
        {#each history as item (item.uid)}
          <li use:menu={() => queueItemMenu(item)}>
            <QueueRow {item} onplay={() => store.run(() => api.jump(item.uid))} onremove={() => remove(item.uid)} />
          </li>
        {/each}
      </ol>
    {/if}
  {/if}
</section>

<style>
  .section {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 24px 0 8px;
    font-size: var(--text-xs);
    font-weight: 500;
    color: var(--muted);
  }
  .radio-hint {
    margin: -4px 0 8px;
    font-size: var(--text-xs);
  }
  .split {
    justify-content: space-between;
  }
  .link-btn {
    background: none;
    min-height: 0;
    padding: 2px 8px;
    font-size: var(--text-xs);
    font-weight: 600;
    letter-spacing: 0;
    text-transform: none;
    color: var(--accent);
  }
  .drop-hint {
    min-height: 52px;
    border: 2px dashed var(--surface-3);
    border-radius: 10px;
  }
  /* A track dragged in from a list: a line where it will land. */
  .drop-hint.drop-into {
    border-color: var(--accent);
    background: var(--accent-soft);
  }
  li.drop-before {
    box-shadow: inset 0 2px 0 var(--accent);
  }
  .drop-end,
  .current.drop-after {
    box-shadow: inset 0 -2px 0 var(--accent);
  }
  /* An empty queue takes the track anywhere. */
  section.drop-over:has(.empty) {
    outline: 2px dashed var(--accent);
    outline-offset: -6px;
    border-radius: 12px;
  }
  .count {
    font-variant-numeric: tabular-nums;
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
    padding: 8px 16px;
    border-radius: 8px;
    text-decoration: none;
    font-weight: 500;
  }
  .button.primary {
    background: var(--accent);
    color: var(--on-accent);
  }
  .current {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 12px;
    text-align: left;
    padding: 12px;
    border-radius: var(--radius);
    min-height: 0;
  }
  .current img,
  .thumb.big {
    width: 56px;
    height: 56px;
  }
  .current .title {
    font-weight: 500;
  }
  /* Each part of the queue is one block, rounded at its top and bottom only. */
  .list {
    list-style: none;
    margin: 0;
    padding: 0;
    border-radius: 10px;
    overflow: hidden;
    background: var(--bg);
  }
  .list li {
    display: flex;
    align-items: center;
    background: var(--bg);
  }
  .list :global(.swipe) {
    border-radius: 0;
  }
  /* The right-click/long-press highlight, drawn inside (the block clips outside). */
  .list li:global(.context-target) {
    border-radius: 0;
    outline-offset: -2px;
  }
  .list li:hover {
    background: var(--surface-2);
  }
  .history li {
    opacity: 0.65;
  }
  .current img,
  .current .thumb {
    border-radius: 6px;
    object-fit: cover;
    background: var(--surface-2);
    color: var(--muted);
    display: grid;
    place-items: center;
    flex: none;
  }
  .current .text {
    flex: 1;
    display: grid;
    min-width: 0;
  }
  .end {
    margin: 12px 4px;
  }
  .eq {
    display: inline-flex;
    align-items: flex-end;
    gap: 2px;
    height: 16px;
    color: inherit;
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
