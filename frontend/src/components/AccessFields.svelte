<script lang="ts">
  // Access mode and CastHome password, shared by the setup and Settings.
  import { t } from '../lib/i18n';
  import type { AccessMode, ClientInfo } from '../lib/types';

  let {
    mode = $bindable(),
    password = $bindable(''),
    confirm = $bindable(''),
    keepPassword = false,
    client = null,
  }: {
    mode: AccessMode;
    password?: string;
    confirm?: string;
    /** A password is set: blank keeps it. */
    keepPassword?: boolean;
    /** How CastHome sees this browser (null: unknown). */
    client?: ClientInfo | null;
  } = $props();

  const MODES: { mode: AccessMode; label: 'access.password' | 'access.lan' | 'access.open'; detail: 'access.passwordDetail' | 'access.lanDetail' | 'access.openDetail' }[] = [
    { mode: 'password', label: 'access.password', detail: 'access.passwordDetail' },
    { mode: 'lan', label: 'access.lan', detail: 'access.lanDetail' },
    { mode: 'open', label: 'access.open', detail: 'access.openDetail' },
  ];

  const mismatch = $derived(confirm.length > 0 && password !== confirm);
</script>

<div class="fields">
  <div class="modes" role="radiogroup">
    {#each MODES as option (option.mode)}
      <label class="mode" class:selected={mode === option.mode}>
        <input type="radio" name="access-mode" value={option.mode} bind:group={mode} />
        <span class="text">
          <strong>{t(option.label)}</strong>
          <span class="muted">{t(option.detail)}</span>
          {#if option.mode === 'lan' && mode === 'lan'}
            <span class="muted note">{t('access.lanProxyNote')}</span>
            {#if client?.untrusted_proxy}
              <span class="warning note" role="alert">{t('access.untrustedProxy', { address: client.client_address })}</span>
            {:else if client}
              <span class="muted note">
                {t(client.client_is_local ? 'access.seenLocal' : 'access.seenRemote', { address: client.client_address })}
              </span>
            {/if}
          {/if}
        </span>
      </label>
    {/each}
  </div>

  {#if mode !== 'open'}
    <label>
      <span>{keepPassword ? t('settings.newPasswordKeep') : t('access.newPassword')}</span>
      <input type="password" bind:value={password} autocomplete="new-password" required={!keepPassword} />
    </label>
    {#if password}
      <label>
        <span>{t('access.confirm')}</span>
        <input type="password" bind:value={confirm} autocomplete="new-password" required />
        {#if mismatch}<small class="error">{t('access.mismatch')}</small>{/if}
      </label>
    {/if}
  {/if}
</div>

<style>
  .fields {
    display: grid;
    gap: 12px;
  }
  .modes {
    display: grid;
    gap: 8px;
  }
  .mode {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 12px;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--surface);
    cursor: pointer;
  }
  .mode.selected {
    border-color: var(--accent);
    background: var(--accent-soft);
  }
  .mode input {
    margin-top: 4px;
    accent-color: var(--accent);
  }
  .text {
    display: grid;
    gap: 2px;
  }
  .text .muted {
    font-size: var(--text-sm);
  }
  .note {
    margin-top: 4px;
  }
  label:not(.mode) {
    display: grid;
    gap: 6px;
  }
  label:not(.mode) > span {
    font-weight: 600;
    font-size: var(--text-sm);
  }
  .error {
    color: var(--danger);
  }
  .warning {
    font-size: var(--text-sm);
    color: var(--danger);
  }
</style>
