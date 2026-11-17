<script lang="ts">
  import { modal } from '../lib/modal';
  import { fadeOut, sheetOut } from '../lib/motion';
  import { api } from '../lib/api';
  import { deviceIcon } from '../lib/devices';
  import { t } from '../lib/i18n';
  import type { IconName } from '../lib/icons';
  import { store } from '../lib/store.svelte';
  import Icon from './Icon.svelte';
  import VolumeSlider from './VolumeSlider.svelte';

  interface Choice {
    uuid: string;
    name: string;
    detail: string;
    icon: IconName;
  }

  let busy = $state<string | null>(null);

  const p = $derived(store.player);
  const activeUuid = $derived(p?.device_uuid ?? null);
  const playing = $derived(p?.status === 'playing' || p?.status === 'buffering' || p?.status === 'loading');

  const typeLabel = (type: string, model: string) =>
    type === 'group' ? t('devices.group') : type === 'audio' ? model || t('devices.speaker') : model || t('devices.tv');

  const thisBrowser = $derived<Choice>({
    uuid: store.browserUuid,
    name: t('devices.thisBrowser'),
    detail: t('devices.thisBrowserDetail', { name: store.browserName }),
    icon: deviceIcon('browser'),
  });
  // Another tab (e.g. your laptop) currently playing.
  const otherBrowser = $derived<Choice | null>(
    p?.device_type === 'browser' && activeUuid && activeUuid !== store.browserUuid
      ? { uuid: activeUuid, name: p.device_name ?? t('devices.otherBrowser'), detail: t('devices.otherBrowser'), icon: deviceIcon('browser') }
      : null,
  );
  const groups = $derived(store.devices.filter((d) => d.cast_type === 'group'));
  const singles = $derived(store.devices.filter((d) => d.cast_type !== 'group'));
  const toChoice = (d: (typeof store.devices)[number]): Choice => ({
    uuid: d.uuid,
    name: d.name,
    detail: typeLabel(d.cast_type, d.model),
    icon: deviceIcon(d.cast_type),
  });

  async function choose(uuid: string) {
    if (busy) return;
    if (uuid === activeUuid && p?.connected) {
      close();
      return;
    }
    busy = uuid;
    await store.run(async () => {
      await api.selectDevice(uuid);
      close();
    });
    busy = null;
  }

  function close() {
    store.devicePickerOpen = false;
  }

  async function disconnect() {
    if (busy) return;
    busy = store.browserUuid;
    await store.run(async () => {
      await api.selectDevice(store.browserUuid);
      close();
    });
    busy = null;
  }
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && close()} />

{#snippet row(choice: Choice)}
  {@const active = choice.uuid === activeUuid}
  <li class:active>
    <button class="choice" disabled={busy !== null && busy !== choice.uuid} onclick={() => choose(choice.uuid)}>
      <span class="icon"><Icon name={choice.icon} size={22} /></span>
      <span class="text">
        <span class="name ellipsis">{choice.name}</span>
        <span class="detail ellipsis">
          {#if active && busy !== choice.uuid && choice.uuid !== store.browserUuid}<span class="live-dot" class:lost={!p?.connected}></span>{/if}
          {#if busy === choice.uuid}
            {t('devices.connecting')}
          {:else if active && !p?.connected}
            {t('devices.disconnected')}
          {:else if active && playing}
            {t('devices.playing')}
          {:else if active}
            {t('devices.connected')}
          {:else}
            {choice.detail}
          {/if}
        </span>
      </span>
      {#if busy === choice.uuid}
        <span class="spinner" aria-hidden="true"></span>
      {:else if active}
        <span class="check"><Icon name="check" size={20} /></span>
      {/if}
    </button>
    {#if active && p?.connected}
      <div class="vol"><VolumeSlider /></div>
    {/if}
    {#if active && choice.uuid !== store.browserUuid}
      <!-- Ends the session on the speaker (it goes back to idle) and carries on
           in this browser. -->
      <button class="disconnect" disabled={busy !== null} onclick={disconnect}>
        <Icon name="logout" size={18} />{t('devices.disconnect')}
      </button>
    {/if}
  </li>
{/snippet}

<div class="sheet-backdrop" role="presentation" onclick={close} out:fadeOut|global></div>
<div class="sheet" use:modal out:sheetOut|global role="dialog" aria-modal="true" aria-labelledby="device-title">
  <div class="head">
    <h3 id="device-title">{t('devices.title')}</h3>
    <button class="icon-btn" aria-label={t('playlist.cancel')} onclick={close}><Icon name="close" size={20} /></button>
  </div>

  <ul role="list">
    {@render row(thisBrowser)}
    {#if otherBrowser}{@render row(otherBrowser)}{/if}
  </ul>

  {#if groups.length > 0}
    <p class="section">{t('devices.groups')}</p>
    <ul role="list">
      {#each groups as device (device.uuid)}{@render row(toChoice(device))}{/each}
    </ul>
  {/if}

  <p class="section">{t('devices.castDevices')}</p>
  {#if singles.length === 0}
    <p class="searching muted"><span class="spinner small" aria-hidden="true"></span>{t('devices.none')}</p>
  {:else}
    <ul role="list">
      {#each singles as device (device.uuid)}{@render row(toChoice(device))}{/each}
    </ul>
  {/if}
</div>

<style>
  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  h3 {
    margin: 0;
    font-size: var(--text-lg);
  }
  .section {
    margin: 16px 4px 4px;
    font-size: var(--text-xs);
    font-weight: 500;
    color: var(--muted);
  }
  ul {
    list-style: none;
    margin: 8px 0 0;
    padding: 0;
    display: grid;
    gap: 2px;
  }
  li {
    border-radius: 12px;
  }
  li.active {
    background: var(--surface-2);
  }
  .choice {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 12px;
    text-align: left;
    background: none;
    border-radius: 12px;
    padding: 12px 12px;
    min-height: 60px;
  }
  .choice:hover:not(:disabled) {
    background: var(--surface-2);
  }
  .active .choice:hover {
    background: none;
  }
  .icon {
    display: grid;
    place-items: center;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: var(--surface-2);
    color: var(--muted);
    flex: none;
  }
  .active .icon {
    background: var(--surface-3);
    color: var(--text);
  }
  .text {
    flex: 1;
    min-width: 0;
    display: grid;
  }
  .name {
    font-weight: 600;
  }
  .detail .live-dot {
    margin-right: 6px;
    vertical-align: 1px;
  }
  .detail {
    font-size: var(--text-sm);
    color: var(--muted);
  }
  .check {
    color: var(--accent);
  }
  .vol {
    padding: 0 16px 12px 64px;
  }
  .disconnect {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0 12px 12px 64px;
    padding: 6px 16px;
    min-height: 34px;
    font-size: var(--text-sm);
    background: var(--surface);
    color: var(--danger);
  }
  .searching {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 8px 4px;
  }
  .spinner {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: 2px solid var(--surface-3);
    border-top-color: var(--accent);
    animation: spin 0.8s linear infinite;
    flex: none;
  }
  .spinner.small {
    width: 14px;
    height: 14px;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
