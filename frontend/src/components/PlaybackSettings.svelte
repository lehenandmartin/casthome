<script lang="ts">
  // Settings → Playback: streaming quality, preloading, Cast addresses.
  import { ApiError, api } from '../lib/api';
  import { t, tCode } from '../lib/i18n';
  import { display } from '../lib/display.svelte';
  import { store } from '../lib/store.svelte';
  import type { PlaybackOptions, StreamFormat } from '../lib/types';

  let {
    initial,
    locked,
    onsaved,
  }: {
    initial: PlaybackOptions;
    locked: (keyof PlaybackOptions)[];
    onsaved: () => void;
  } = $props();

  const FORMATS: StreamFormat[] = ['raw', 'mp3', 'aac', 'opus'];
  const BITRATES = [0, 320, 256, 192, 160, 128, 96];

  // svelte-ignore state_referenced_locally
  let format = $state<StreamFormat>(initial.stream_format);
  // svelte-ignore state_referenced_locally
  let bitrate = $state(initial.max_bitrate);
  // svelte-ignore state_referenced_locally
  let preload = $state(initial.preload_next);
  // svelte-ignore state_referenced_locally
  let hosts = $state(initial.known_hosts.join(', '));
  // svelte-ignore state_referenced_locally
  let scrobble = $state(initial.scrobble);
  // svelte-ignore state_referenced_locally
  let showRatings = $state(initial.show_ratings);
  let busy = $state(false);
  let error = $state<string | null>(null);

  const isLocked = (field: keyof PlaybackOptions) => locked.includes(field);
  const hostList = $derived(
    hosts
      .split(/[\s,;]+/)
      .map((h) => h.trim())
      .filter(Boolean),
  );
  const dirty = $derived(
    format !== initial.stream_format ||
      bitrate !== initial.max_bitrate ||
      preload !== initial.preload_next ||
      scrobble !== initial.scrobble ||
      showRatings !== initial.show_ratings ||
      hostList.join(',') !== initial.known_hosts.join(','),
  );

  async function save(event: SubmitEvent) {
    event.preventDefault();
    busy = true;
    error = null;
    try {
      await api.updatePlayback({
        stream_format: format,
        max_bitrate: bitrate,
        preload_next: preload,
        known_hosts: hostList,
        scrobble,
        show_ratings: showRatings,
      });
      hosts = hostList.join(', ');
      display.ratings = isLocked('show_ratings') ? initial.show_ratings : showRatings;
      store.notify('settings_saved', {}, 'info');
      onsaved();
    } catch (err) {
      error = err instanceof ApiError ? tCode(err.code, err.params) : tCode('unknown');
    } finally {
      busy = false;
    }
  }
</script>

<form class="card form" onsubmit={save}>
  <div class="row">
    <label>
      <span>{t('playback.format')}</span>
      <select bind:value={format} disabled={isLocked('stream_format')}>
        {#each FORMATS as f (f)}<option value={f}>{t(`playback.format.${f}`)}</option>{/each}
      </select>
    </label>
    {#if format !== 'raw'}
      <label>
        <span>{t('playback.bitrate')}</span>
        <select bind:value={bitrate} disabled={isLocked('max_bitrate')}>
          {#each BITRATES as b (b)}
            <option value={b}>{b === 0 ? t('playback.bitrateNone') : t('playback.kbps', { n: b })}</option>
          {/each}
        </select>
      </label>
    {/if}
  </div>
  <small class="muted">
    {isLocked('stream_format') ? t('navidrome.locked') : t('playback.formatHint')}
  </small>

  <label class="check">
    <input type="checkbox" bind:checked={preload} disabled={isLocked('preload_next')} />
    <span class="text">
      <strong>{t('playback.preload')}</strong>
      <small class="muted">{isLocked('preload_next') ? t('navidrome.locked') : t('playback.preloadHint')}</small>
    </span>
  </label>

  <label class="check">
    <input type="checkbox" bind:checked={scrobble} disabled={isLocked('scrobble')} />
    <span class="text">
      <strong>{t('playback.scrobble')}</strong>
      <small class="muted">{isLocked('scrobble') ? t('navidrome.locked') : t('playback.scrobbleHint')}</small>
    </span>
  </label>

  <label class="check">
    <input type="checkbox" bind:checked={showRatings} disabled={isLocked('show_ratings')} />
    <span class="text">
      <strong>{t('playback.showRatings')}</strong>
      <small class="muted">{isLocked('show_ratings') ? t('navidrome.locked') : t('playback.showRatingsHint')}</small>
    </span>
  </label>

  <label>
    <span>{t('playback.hosts')}</span>
    <input
      type="text"
      bind:value={hosts}
      placeholder="192.168.1.20, 192.168.1.21"
      autocapitalize="off"
      spellcheck="false"
      disabled={isLocked('known_hosts')}
    />
    <small class="muted">{isLocked('known_hosts') ? t('navidrome.locked') : t('playback.hostsHint')}</small>
  </label>

  {#if error}<p class="error" role="alert">{error}</p>{/if}
  <div class="buttons">
    <small class="muted">{dirty ? t('playback.appliesNext') : ''}</small>
    <button class="primary" type="submit" disabled={busy || !dirty}>
      {busy ? t('settings.saving') : t('settings.save')}
    </button>
  </div>
</form>

<style>
  .card.form {
    display: grid;
    gap: 14px;
    padding: 16px;
    margin-top: 8px;
    border-radius: 8px;
    background: var(--surface);
    border: 1px solid var(--border);
  }
  .row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px;
  }
  label {
    display: grid;
    gap: 6px;
  }
  label > span {
    font-weight: 600;
    font-size: 0.9rem;
  }
  .row + small {
    margin-top: -8px;
  }
  small {
    font-size: 0.8rem;
  }
  .check {
    display: flex;
    gap: 10px;
    align-items: flex-start;
  }
  .check input {
    margin-top: 3px;
    accent-color: var(--accent);
  }
  .check .text {
    display: grid;
    gap: 2px;
  }
  .check strong {
    font-size: 0.9rem;
    font-weight: 600; /* same as the other field labels */
  }
  .buttons {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  .error {
    color: var(--danger);
    margin: 0;
  }
</style>
