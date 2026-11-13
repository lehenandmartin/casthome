<script lang="ts">
  import { dragHandle, dragHandleZone, type DndEvent } from 'svelte-dnd-action';
  import { flip } from 'svelte/animate';
  import { api, coverUrl } from '../lib/api';
  import { dialogs } from '../lib/dialog.svelte';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { QueueItem } from '../lib/types';

  // svelte-dnd-action keys items by `id`; the song id is kept as `song_id`.
  type Row = Omit<QueueItem, 'id'> & { id: number; song_id: string };
  const FLIP_MS = 150;

  // Local copy so the list can be reordered while dragging; resynced from the
  // server on every queue update (which also confirms or reverts the move).
  let rows = $state<Row[]>([]);
  let dragging = $state(false);

  $effect(() => {
    const items = store.queue.items;
    if (!dragging) rows = items.map((item) => ({ ...item, song_id: item.id, id: item.uid }));
  });

  const currentUid = $derived(store.queue.index !== null ? store.queue.items[store.queue.index]?.uid : undefined);

  function consider(e: CustomEvent<DndEvent<Row>>) {
    dragging = true;
    rows = e.detail.items;
  }

  async function saveAsPlaylist() {
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

  async function finalize(e: CustomEvent<DndEvent<Row>>) {
    rows = e.detail.items;
    dragging = false;
    const uid = Number(e.detail.info.id);
    const to = rows.findIndex((r) => r.uid === uid);
    const from = store.queue.items.findIndex((r) => r.uid === uid);
    if (to < 0 || to === from) return;
    await store.run(() => api.moveItem(uid, to));
  }
</script>

<section>
  <header>
    <h2>{t('queue.title')}</h2>
    {#if rows.length > 0}
      <span class="muted">{t('queue.count', { count: rows.length })}</span>
      <button onclick={saveAsPlaylist}>{t('queue.saveAsPlaylist')}</button>
      <button onclick={() => store.run(api.clearQueue)}>{t('queue.clear')}</button>
    {/if}
  </header>
  {#if rows.length === 0}
    <p class="muted">{t('queue.empty')}</p>
  {/if}
  <ol
    use:dragHandleZone={{ items: rows, flipDurationMs: FLIP_MS, dropTargetStyle: {} }}
    onconsider={consider}
    onfinalize={finalize}
  >
    {#each rows as item (item.id)}
      <li class:current={item.uid === currentUid} animate:flip={{ duration: FLIP_MS }}>
        <span class="handle" use:dragHandle aria-label={t('queue.drag')} title={t('queue.drag')}>⠿</span>
        <button class="row" onclick={() => store.run(() => api.jump(item.uid))}>
          {#if item.cover_art}
            <img src={coverUrl(item.cover_art, 96)} alt="" loading="lazy" />
          {:else}
            <span class="thumb"></span>
          {/if}
          <span class="text">
            <span class="title">{item.title}</span>
            <span class="muted">{item.artist}</span>
          </span>
          <span class="muted">{formatTime(item.duration)}</span>
        </button>
        <button
          class="remove"
          aria-label={t('queue.remove')}
          title={t('queue.remove')}
          onclick={() => store.run(() => api.removeItem(item.uid))}>✕</button
        >
      </li>
    {/each}
  </ol>
</section>

<style>
  header {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }
  header button:first-of-type {
    margin-left: auto;
  }
  ol {
    list-style: none;
    padding: 0;
    margin: 8px 0 0;
  }
  li {
    display: flex;
    align-items: center;
    border-radius: 6px;
    background: var(--bg);
  }
  li:hover {
    background: var(--surface-2);
  }
  .handle {
    flex: none;
    width: 36px;
    height: 44px;
    display: grid;
    place-items: center;
    color: var(--muted);
    cursor: grab;
    touch-action: none;
    font-size: 18px;
  }
  .row {
    flex: 1;
    min-width: 0;
    display: grid;
    grid-template-columns: 40px 1fr auto;
    align-items: center;
    gap: 12px;
    text-align: left;
    background: none;
    border: 0;
    padding: 6px 4px;
  }
  img,
  .thumb {
    width: 40px;
    height: 40px;
    border-radius: 4px;
    object-fit: cover;
    background: var(--surface-2);
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
  .current .title {
    color: var(--accent);
    font-weight: 600;
  }
  .remove {
    flex: none;
    width: 40px;
    height: 40px;
    background: none;
    border: 0;
    color: var(--muted);
  }
</style>
