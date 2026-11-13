<script lang="ts">
  import { deviceIcon } from '../lib/devices';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import Icon from './Icon.svelte';

  // compact: icon only (mini player); otherwise icon + device name.
  let { compact = false }: { compact?: boolean } = $props();

  const p = $derived(store.player);
  const casting = $derived(Boolean(p?.device_uuid) && p?.device_type !== 'browser');
  const label = $derived(
    !p?.device_uuid ? t('devices.choose') : store.isThisBrowser ? t('devices.thisBrowser') : (p.device_name ?? t('devices.choose')),
  );
  const warn = $derived(Boolean(p?.device_uuid) && !p?.connected);
</script>

<button
  class="device"
  class:compact
  class:casting
  class:warn
  aria-label={`${t('devices.title')}: ${label}`}
  title={`${t('devices.title')}: ${label}`}
  onclick={(e) => {
    e.stopPropagation();
    store.devicePickerOpen = true;
  }}
>
  <Icon name={p?.device_uuid ? deviceIcon(p.device_type) : 'cast'} size={compact ? 22 : 18} />
  {#if !compact}<span class="ellipsis">{label}</span>{/if}
</button>

<style>
  .device {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    max-width: 100%;
    min-width: 0;
    background: var(--surface-2);
    font-size: 0.9rem;
    padding: 6px 14px;
  }
  .device.casting {
    color: var(--accent);
    background: var(--accent-soft);
  }
  .device.warn {
    color: var(--danger);
  }
  .compact {
    width: 40px;
    height: 40px;
    padding: 0;
    justify-content: center;
    background: none;
  }
  .compact.casting {
    background: none;
  }
</style>
