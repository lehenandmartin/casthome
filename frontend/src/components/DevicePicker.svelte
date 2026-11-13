<script lang="ts">
  import { api } from '../lib/api';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';

  let { onclose }: { onclose: () => void } = $props();
  let busy = $state<string | null>(null);

  async function choose(uuid: string) {
    busy = uuid;
    await store.run(() => api.selectDevice(uuid));
    busy = null;
    onclose();
  }
</script>

<div class="backdrop" role="presentation" onclick={onclose}></div>
<div class="sheet" role="dialog" aria-modal="true" aria-label={t('devices.title')}>
  <h3>{t('devices.title')}</h3>
  {#if store.devices.length === 0}
    <p class="muted">{t('devices.none')}</p>
  {/if}
  <ul>
    {#each store.devices as device (device.uuid)}
      <li>
        <button
          class:selected={device.uuid === store.player?.device_uuid}
          disabled={busy !== null}
          onclick={() => choose(device.uuid)}
        >
          <span>{device.name}</span>
          <span class="muted">
            {device.cast_type === 'group' ? t('devices.group') : device.model}
            {#if busy === device.uuid}· {t('player.loading')}{/if}
          </span>
        </button>
      </li>
    {/each}
  </ul>
</div>

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgb(0 0 0 / 0.4);
    z-index: 20;
  }
  .sheet {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 21;
    max-height: 70dvh;
    overflow: auto;
    background: var(--surface);
    border-radius: 16px 16px 0 0;
    padding: 16px 16px calc(16px + env(safe-area-inset-bottom));
  }
  @media (min-width: 640px) {
    .sheet {
      left: auto;
      right: 16px;
      bottom: 96px;
      width: 360px;
      border-radius: 12px;
      box-shadow: 0 8px 32px rgb(0 0 0 / 0.3);
    }
  }
  h3 {
    margin: 0 0 8px;
  }
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  li button {
    width: 100%;
    display: grid;
    text-align: left;
    gap: 2px;
    background: none;
    border: 0;
    padding: 10px 8px;
    border-radius: 8px;
  }
  li button:hover {
    background: var(--surface-2);
  }
  .selected span:first-child {
    color: var(--accent);
    font-weight: 600;
  }
</style>
