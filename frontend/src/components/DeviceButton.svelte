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
  <span class="glyph">
    <Icon name={p?.device_uuid ? deviceIcon(p.device_type) : 'cast'} size={compact ? 22 : 18} />
    {#if casting}<span class="live-dot" class:lost={warn}></span>{/if}
  </span>
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
    font-size: var(--text-sm);
    padding: 6px 16px;
  }
  .glyph {
    position: relative;
    display: inline-grid;
    flex: none;
  }
  /* On the speaker's corner, cut out of the button behind it. */
  .glyph .live-dot {
    position: absolute;
    right: -3px;
    top: -2px;
    box-shadow: 0 0 0 2px var(--ring, var(--surface-2));
  }
  .compact .glyph .live-dot {
    --ring: var(--surface);
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
