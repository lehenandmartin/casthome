<script lang="ts">
  // Top of the queue: title, track count and time left, shuffle, and a menu
  // to save the queue as a playlist or clear it.
  import { api } from '../lib/api';
  import { dialogs } from '../lib/dialog.svelte';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import Icon from './Icon.svelte';

  let { embedded = false, count, remaining }: { embedded?: boolean; count: number; remaining: number } = $props();

  const p = $derived(store.player);
  let menuOpen = $state(false);

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

  async function clearAll() {
    menuOpen = false;
    const ok = await dialogs.confirm({
      title: t('queue.clearAll'),
      message: t('queue.clearConfirm'),
      confirmLabel: t('queue.clearAll'),
      danger: true,
    });
    if (ok) await store.run(api.clearQueue);
  }
</script>

<svelte:window onclick={() => (menuOpen = false)} />

<header class="page-head" class:embedded>
  <div>
    {#if !embedded}<h2>{t('queue.title')}</h2>{/if}
    {#if count > 0}
      <p class="muted">{t('queue.summary', { count, time: formatTime(remaining) })}</p>
    {/if}
  </div>
  {#if count > 0}
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
            <button role="menuitem" class="danger" onclick={clearAll}><Icon name="trash" size={18} />{t('queue.clearAll')}</button>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</header>

<style>
  .page-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }
  .page-head.embedded {
    align-items: center;
  }
  .page-head.embedded p {
    margin: 0;
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
</style>
