<script lang="ts">
  // The Navidrome connection form, shared by the setup and Settings.
  import { t } from '../lib/i18n';
  import type { LockedField, NavidromeForm } from '../lib/types';

  let {
    value = $bindable(),
    locked = [],
    keepPassword = false,
    focusPublicUrl = false,
  }: {
    value: NavidromeForm;
    locked?: LockedField[];
    /** A password is saved: blank keeps it. */
    keepPassword?: boolean;
    /** The Cast URL was refused: show it. */
    focusPublicUrl?: boolean;
  } = $props();

  const isLocked = (field: LockedField) => locked.includes(field);
  // Open the advanced part when it holds something worth seeing.
  let advanced = $state(Boolean(value.public_url && value.public_url !== value.url));
  $effect(() => {
    if (focusPublicUrl) advanced = true;
  });
</script>

<div class="fields">
  <label>
    <span>{t('navidrome.url')}</span>
    <input
      type="url"
      bind:value={value.url}
      placeholder="http://192.168.1.10:4533"
      autocomplete="url"
      autocapitalize="off"
      spellcheck="false"
      disabled={isLocked('url')}
      required
    />
    <small class="muted">{isLocked('url') ? t('navidrome.locked') : t('navidrome.urlHint')}</small>
  </label>

  <label>
    <span>{t('navidrome.username')}</span>
    <input
      type="text"
      bind:value={value.username}
      autocomplete="username"
      autocapitalize="off"
      spellcheck="false"
      disabled={isLocked('username')}
      required
    />
    {#if isLocked('username')}<small class="muted">{t('navidrome.locked')}</small>{/if}
  </label>

  <label>
    <span>{t('navidrome.password')}</span>
    {#if isLocked('password')}
      <input type="password" value="••••••••" disabled />
      <small class="muted">{t('navidrome.locked')}</small>
    {:else}
      <input
        type="password"
        bind:value={value.password}
        autocomplete="off"
        placeholder={keepPassword ? '••••••••' : ''}
        required={!keepPassword}
      />
      {#if keepPassword}<small class="muted">{t('navidrome.passwordKeep')}</small>{/if}
    {/if}
  </label>

  <details bind:open={advanced}>
    <summary>{t('navidrome.advanced')}</summary>
    <label>
      <span>{t('navidrome.publicUrl')}</span>
      <input
        type="url"
        bind:value={value.public_url}
        placeholder={value.url || 'http://192.168.1.10:4533'}
        autocapitalize="off"
        spellcheck="false"
        disabled={isLocked('public_url')}
      />
      <small class="muted">{isLocked('public_url') ? t('navidrome.locked') : t('navidrome.publicUrlHint')}</small>
    </label>
  </details>
</div>

<style>
  .fields {
    display: grid;
    gap: 12px;
  }
  label {
    display: grid;
    gap: 6px;
  }
  label > span {
    font-weight: 600;
    font-size: var(--text-sm);
  }
  small {
    font-size: var(--text-xs);
  }
  summary {
    cursor: pointer;
    color: var(--muted);
    font-weight: 600;
    font-size: var(--text-sm);
    padding: 4px 0;
  }
  details[open] summary {
    margin-bottom: 12px;
  }
</style>
