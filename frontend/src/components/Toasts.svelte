<script lang="ts">
  import { t, tCode } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
</script>

<div class="toasts" aria-live="polite">
  {#if store.auth === 'signed-in' && store.offlineNotice}
    <div class="toast warning">{t('connection.offline')}</div>
  {/if}
  {#each store.notifications as n (n.id)}
    <button class="toast {n.level}" onclick={() => store.dismiss(n.id)}>{tCode(n.code, n.params)}</button>
  {/each}
</div>

<style>
  .toasts {
    position: fixed;
    top: calc(8px + env(safe-area-inset-top));
    left: 16px;
    right: 16px;
    z-index: 70;
    display: grid;
    gap: 8px;
    justify-items: center;
    pointer-events: none;
  }
  .toast {
    pointer-events: auto;
    max-width: 480px;
    padding: 10px 14px;
    border-radius: 8px;
    border: 0;
    background: var(--surface-2);
    color: var(--text);
    box-shadow: 0 4px 16px rgb(0 0 0 / 0.25);
    text-align: left;
  }
  .error {
    background: var(--danger);
    color: #fff;
  }
</style>
