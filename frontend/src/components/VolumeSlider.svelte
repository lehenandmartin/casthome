<script lang="ts">
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import { currentVolume, setVolumeSoon, stepVolume, volumeAvailable } from '../lib/volume.svelte';
  import Icon from './Icon.svelte';

  const p = $derived(store.player);
  const available = $derived(volumeAvailable());
  const volume = $derived(currentVolume());
</script>

{#if available}
  <!-- Touch screens: − and + around the slider, one step each (a slider is
       hard to set precisely with a finger). Mouse: the speaker icon. -->
  <div class="volume">
    <span class="icon"><Icon name={volume === 0 || p?.muted ? 'volumeMute' : 'volume'} size={18} /></span>
    <button
      class="icon-btn step"
      aria-label={t('player.volumeDown')}
      title={t('player.volumeDown')}
      disabled={volume <= 0}
      onclick={() => stepVolume(-1)}><Icon name="minus" size={18} /></button
    >
    <input
      type="range"
      min="0"
      max="1"
      step="0.01"
      value={volume}
      style:--fill={`${volume * 100}%`}
      aria-label={t('player.volume')}
      aria-valuetext={`${Math.round(volume * 100)} %`}
      oninput={(e) => setVolumeSoon(Number((e.target as HTMLInputElement).value))}
    />
    <button
      class="icon-btn step"
      aria-label={t('player.volumeUp')}
      title={t('player.volumeUp')}
      disabled={volume >= 1}
      onclick={() => stepVolume(1)}><Icon name="plus" size={18} /></button
    >
  </div>
{/if}

<style>
  .volume {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--muted);
    width: 100%;
  }
  .icon {
    display: grid;
    flex: none;
  }
  .step {
    display: none;
    flex: none;
    color: var(--text);
  }
  @media (hover: none) and (pointer: coarse) {
    .volume {
      gap: 0;
    }
    .icon {
      display: none;
    }
    .step {
      display: inline-grid;
      width: 40px;
      height: 44px;
    }
  }
</style>
