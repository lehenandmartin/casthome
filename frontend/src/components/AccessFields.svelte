<script lang="ts">
  // Access mode and CastHome password, shared by the setup and Settings.
  import { t } from '../lib/i18n';
  import type { AccessMode } from '../lib/types';

  let {
    mode = $bindable(),
    password = $bindable(''),
    confirm = $bindable(''),
    keepPassword = false,
    clientIsLocal = null,
  }: {
    mode: AccessMode;
    password?: string;
    confirm?: string;
    /** A password is set: blank keeps it. */
    keepPassword?: boolean;
    /** Whether this browser is on the local network (null: unknown). */
    clientIsLocal?: boolean | null;
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
            {#if clientIsLocal !== null}
              <span class="muted note">{clientIsLocal ? t('access.youAreLocal') : t('access.youAreRemote')}</span>
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
    gap: 14px;
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
    margin-top: 3px;
    accent-color: var(--accent);
  }
  .text {
    display: grid;
    gap: 2px;
  }
  .text .muted {
    font-size: 0.85rem;
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
    font-size: 0.9rem;
  }
  .error {
    color: var(--danger);
  }
</style>
