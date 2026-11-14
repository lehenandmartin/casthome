<script lang="ts">
  // First-run setup: the Navidrome connection, then access to CastHome.
  // Only the steps still missing are shown (e.g. after an upgrade, only access).
  import { ApiError, api } from '../lib/api';
  import { t, tCode } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { AccessMode, ClientInfo, LockedField, NavidromeForm } from '../lib/types';
  import AccessFields from './AccessFields.svelte';
  import Icon from './Icon.svelte';
  import NavidromeFields from './NavidromeFields.svelte';

  type Step = 'navidrome' | 'access';

  let steps = $state<Step[]>([]);
  let index = $state(0);
  let locked = $state<LockedField[]>([]);
  let client = $state<ClientInfo | null>(null);
  let navidrome = $state<NavidromeForm>({ url: '', public_url: '', username: '', password: '' });
  let mode = $state<AccessMode>('password');
  let password = $state('');
  let confirm = $state('');
  let remember = $state(true);
  let busy = $state(false);
  let error = $state<string | null>(null);
  let publicUrlError = $state(false);

  const step = $derived(steps[index]);
  const last = $derived(index === steps.length - 1);

  async function load() {
    try {
      const info = await api.setupInfo();
      locked = info.locked;
      client = info;
      navidrome = { ...info.navidrome, password: '' };
      steps = (['navidrome', 'access'] as Step[]).filter((s) => info.setup[s]);
    } catch (err) {
      if (err instanceof ApiError && err.code === 'setup_done') await store.checkStatus();
      else error = describe(err);
    }
  }

  function describe(err: unknown): string {
    return err instanceof ApiError ? tCode(err.code, err.params) : tCode('unknown');
  }

  const accessValid = $derived(mode === 'open' || (password.length > 0 && password === confirm));

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    error = null;
    if (step === 'access' && !accessValid) {
      error = t('access.mismatch');
      return;
    }
    busy = true;
    try {
      if (step === 'navidrome' && !last) {
        await api.setupTest(navidrome);
        index += 1;
      } else {
        await api.setup(
          steps.includes('navidrome') ? navidrome : null,
          steps.includes('access') ? { mode, password: mode === 'open' ? null : password, remember } : null,
        );
        await store.checkStatus();
      }
    } catch (err) {
      error = describe(err);
      publicUrlError = err instanceof ApiError && err.params.field === 'public_url';
    } finally {
      busy = false;
    }
  }

  load();
</script>

<main class="setup">
  <form onsubmit={submit}>
    <header>
      <div class="brand"><Icon name="cast" size={26} />{t('app.name')}</div>
      <h1>{t('setup.title')}</h1>
      {#if steps.length > 1}<p class="muted">{t('setup.step', { n: index + 1, total: steps.length })}</p>{/if}
    </header>

    {#if step === 'navidrome'}
      <section>
        <h2>{t('setup.navidromeTitle')}</h2>
        <p class="muted">{t('setup.navidromeIntro')}</p>
        <NavidromeFields bind:value={navidrome} {locked} focusPublicUrl={publicUrlError} />
      </section>
    {:else if step === 'access'}
      <section>
        <h2>{t('setup.accessTitle')}</h2>
        <p class="muted">
          {t('setup.accessIntro')}
          {#if !steps.includes('navidrome')}{t('setup.restoredHint')}{/if}
        </p>
        <AccessFields bind:mode bind:password bind:confirm {client} />
        {#if mode !== 'open'}
          <label class="check">
            <input type="checkbox" bind:checked={remember} />
            <span>{t('access.remember')}</span>
          </label>
        {/if}
      </section>
    {/if}

    {#if error}<p class="error" role="alert">{error}</p>{/if}

    {#if step}
      <div class="buttons">
        {#if index > 0}
          <button type="button" onclick={() => ((index -= 1), (error = null))} disabled={busy}>{t('setup.back')}</button>
        {/if}
        <button class="primary" type="submit" disabled={busy}>
          {#if busy}
            {last ? t('setup.finishing') : t('setup.testing')}
          {:else}
            {last ? t('setup.finish') : t('setup.next')}
          {/if}
        </button>
      </div>
    {/if}
  </form>
</main>

<style>
  .setup {
    min-height: 100dvh;
    display: grid;
    place-items: center;
    padding: calc(env(safe-area-inset-top) + 24px) 16px calc(env(safe-area-inset-bottom) + 24px);
  }
  form {
    width: min(460px, 100%);
    display: grid;
    gap: 20px;
  }
  header {
    display: grid;
    gap: 6px;
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 800;
    color: var(--accent);
  }
  h1 {
    margin: 4px 0 0;
  }
  header p {
    margin: 0;
  }
  h2 {
    margin: 0 0 4px;
    font-size: 1.15rem;
  }
  section > p {
    margin: 0 0 16px;
  }
  .check {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 14px;
  }
  .error {
    color: var(--danger);
    margin: 0;
  }
  .buttons {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }
</style>
