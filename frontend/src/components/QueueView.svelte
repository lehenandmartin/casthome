<script lang="ts">
  import { api, coverUrl } from '../lib/api';
  import { formatTime } from '../lib/format';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
</script>

<section>
  <header>
    <h2>{t('queue.title')}</h2>
    {#if store.queue.items.length > 0}
      <span class="muted">{t('queue.count', { count: store.queue.items.length })}</span>
      <button onclick={() => store.run(api.clearQueue)}>{t('queue.clear')}</button>
    {/if}
  </header>
  {#if store.queue.items.length === 0}
    <p class="muted">{t('queue.empty')}</p>
  {/if}
  <ol>
    {#each store.queue.items as item, i (item.uid)}
      <li class:current={i === store.queue.index}>
        <button class="row" onclick={() => store.run(() => api.jump(i))}>
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
  header button {
    margin-left: auto;
  }
  ol {
    list-style: none;
    padding: 0;
    margin: 8px 0 0;
  }
  .row {
    width: 100%;
    display: grid;
    grid-template-columns: 40px 1fr auto;
    align-items: center;
    gap: 12px;
    text-align: left;
    background: none;
    border: 0;
    padding: 6px 8px;
    border-radius: 6px;
  }
  .row:hover {
    background: var(--surface-2);
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
</style>
