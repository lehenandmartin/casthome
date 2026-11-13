<script lang="ts">
  import { icons, type IconName } from '../lib/icons';

  let { name, size = 22, label }: { name: IconName; size?: number; label?: string } = $props();
  const icon = $derived(icons[name] as { d: string; fill?: boolean; width?: number });
</script>

<svg
  width={size}
  height={size}
  viewBox="0 0 24 24"
  fill={icon.fill ? 'currentColor' : 'none'}
  stroke={icon.fill ? 'none' : 'currentColor'}
  stroke-width={icon.width ?? 2}
  stroke-linecap="round"
  stroke-linejoin="round"
  role={label ? 'img' : undefined}
  aria-label={label}
  aria-hidden={label ? undefined : 'true'}
>
  <path d={icon.d} />
</svg>

<style>
  svg {
    display: block;
    flex: none;
  }
</style>
