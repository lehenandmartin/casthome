<script lang="ts">
  // Settings: one section per topic. Add new sections here as cards.
  import { ApiError, api } from '../lib/api';
  import { LANGUAGES, browserLanguage, languageState, setLanguage, t, tCode, type LanguagePref } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import type { AccessMode, NavidromeForm, ServerSettings } from '../lib/types';
  import AccessFields from './AccessFields.svelte';
  import Icon from './Icon.svelte';
  import NavidromeFields from './NavidromeFields.svelte';
  import PlaybackSettings from './PlaybackSettings.svelte';
  import Sessions from './Sessions.svelte';

  let settings = $state<ServerSettings | null>(null);

  // Navidrome form
  let editingNavidrome = $state(false);
  let navidrome = $state<NavidromeForm>({ url: '', public_url: '', username: '', password: '' });
  let navidromeBusy = $state<'test' | 'save' | null>(null);
  let navidromeMessage = $state<{ ok: boolean; text: string } | null>(null);
  let publicUrlError = $state(false);

  // Access form
  let editingAccess = $state(false);
  let mode = $state<AccessMode>('password');
  let password = $state('');
  let confirm = $state('');
  let currentPassword = $state('');
  let accessBusy = $state(false);
  let accessError = $state<string | null>(null);

  async function load() {
    await store.run(async () => {
      settings = await api.settings();
    });
    // Navidrome refused the saved password: go straight to the form.
    if (store.navidromeRejected && settings && !editingNavidrome) editNavidrome();
  }

  const describe = (err: unknown) => (err instanceof ApiError ? tCode(err.code, err.params) : tCode('unknown'));

  function editNavidrome() {
    if (!settings) return;
    const { url, public_url, username } = settings.navidrome;
    navidrome = { url, public_url: public_url === url ? '' : public_url, username, password: '' };
    navidromeMessage = null;
    editingNavidrome = true;
  }

  async function testNavidrome() {
    navidromeBusy = 'test';
    navidromeMessage = null;
    try {
      await api.testNavidrome(navidrome);
      navidromeMessage = { ok: true, text: t('navidrome.testOk') };
    } catch (err) {
      navidromeMessage = { ok: false, text: describe(err) };
      publicUrlError = err instanceof ApiError && err.params.field === 'public_url';
    } finally {
      navidromeBusy = null;
    }
  }

  async function saveNavidrome(event: SubmitEvent) {
    event.preventDefault();
    navidromeBusy = 'save';
    navidromeMessage = null;
    try {
      await api.updateNavidrome(navidrome);
      editingNavidrome = false;
      store.notify('settings_saved', {}, 'info');
      await load();
    } catch (err) {
      navidromeMessage = { ok: false, text: describe(err) };
      publicUrlError = err instanceof ApiError && err.params.field === 'public_url';
    } finally {
      navidromeBusy = null;
    }
  }

  function editAccess() {
    if (!settings) return;
    mode = settings.access.mode;
    password = confirm = currentPassword = '';
    accessError = null;
    editingAccess = true;
  }

  async function saveAccess(event: SubmitEvent) {
    event.preventDefault();
    if (password && password !== confirm) {
      accessError = t('access.mismatch');
      return;
    }
    accessBusy = true;
    accessError = null;
    try {
      await api.updateAccess({
        mode,
        password: mode === 'open' || !password ? null : password,
        current_password: settings?.access.has_password ? currentPassword : null,
        remember: true,
      });
      editingAccess = false;
      store.notify('settings_saved', {}, 'info');
      store.signedIn(); // refresh how this browser is signed in
      await load();
    } catch (err) {
      accessError = describe(err);
    } finally {
      accessBusy = false;
    }
  }

  async function signOut() {
    await store.run(api.logout);
    await store.checkStatus();
  }

  // What "Automatic" picks: this browser's language.
  const autoLanguage = browserLanguage();

  const MODE_LABEL = { password: 'access.password', lan: 'access.lan', open: 'access.open' } as const;
  const MODE_DETAIL = { password: 'access.passwordDetail', lan: 'access.lanDetail', open: 'access.openDetail' } as const;

  const REPO_URL = 'https://github.com/lehenandmartin/casthome';

  load();
</script>

<section>
  <h2>{t('settings.title')}</h2>

  <section class="block">
    <h3>{t('settings.navidrome')}</h3>
    {#if store.navidromeRejected}<p class="alert" role="alert">{t('navidrome.rejected')}</p>{/if}
    {#if editingNavidrome && settings}
      <form class="card form" onsubmit={saveNavidrome}>
        <NavidromeFields bind:value={navidrome} locked={settings.locked} keepPassword={settings.navidrome.has_password} focusPublicUrl={publicUrlError} />
        {#if navidromeMessage}
          <p class:ok={navidromeMessage.ok} class:error={!navidromeMessage.ok} role="status">{navidromeMessage.text}</p>
        {/if}
        <div class="buttons">
          <button type="button" onclick={testNavidrome} disabled={navidromeBusy !== null}>
            {navidromeBusy === 'test' ? t('setup.testing') : t('navidrome.test')}
          </button>
          <span class="spacer"></span>
          <button type="button" onclick={() => (editingNavidrome = false)} disabled={navidromeBusy !== null}>
            {t('settings.cancel')}
          </button>
          <button class="primary" type="submit" disabled={navidromeBusy !== null}>
            {navidromeBusy === 'save' ? t('settings.saving') : t('settings.save')}
          </button>
        </div>
      </form>
    {:else}
      <div class="card">
        <span class="avatar"><Icon name="account" size={24} /></span>
        <span class="text">
          <strong>{settings?.navidrome.username ?? '…'}</strong>
          <span class="muted ellipsis">{settings?.navidrome.url ?? t('settings.navidromeIntro')}</span>
        </span>
        <button onclick={editNavidrome} disabled={!settings}>{t('settings.edit')}</button>
      </div>
    {/if}
  </section>

  {#if settings}
    <section class="block">
      <h3>{t('playback.title')}</h3>
      <PlaybackSettings initial={settings.playback} locked={settings.playback.locked} onsaved={load} />
    </section>
  {/if}

  <section class="block">
    <h3>{t('settings.language')}</h3>
    <div class="card language">
      <select
        value={languageState.pref}
        onchange={(e) => setLanguage(e.currentTarget.value as LanguagePref)}
        aria-label={t('settings.language')}
      >
        <option value="auto">{t('settings.languageAuto', { language: t(`language.${autoLanguage}`) })}</option>
        {#each LANGUAGES as lang (lang)}<option value={lang}>{t(`language.${lang}`)}</option>{/each}
      </select>
      <small class="muted">{t('settings.languageHint')}</small>
    </div>
  </section>

  <section class="block">
    <h3>{t('settings.access')}</h3>
    {#if editingAccess && settings}
      <form class="card form" onsubmit={saveAccess}>
        <p class="muted intro">{t('settings.accessIntro')}</p>
        <AccessFields
          bind:mode
          bind:password
          bind:confirm
          keepPassword={settings.access.has_password}
          clientIsLocal={settings.client_is_local}
        />
        {#if settings.access.has_password && mode !== 'open' && password}
          <p class="muted note">{t('settings.passwordChangeNote')}</p>
        {/if}
        {#if settings.access.has_password}
          <label>
            <span>{t('settings.currentPassword')}</span>
            <input type="password" bind:value={currentPassword} autocomplete="current-password" required />
          </label>
        {/if}
        {#if accessError}<p class="error" role="alert">{accessError}</p>{/if}
        <div class="buttons">
          <span class="spacer"></span>
          <button type="button" onclick={() => (editingAccess = false)} disabled={accessBusy}>{t('settings.cancel')}</button>
          <button class="primary" type="submit" disabled={accessBusy}>
            {accessBusy ? t('settings.saving') : t('settings.save')}
          </button>
        </div>
      </form>
    {:else}
      <div class="card">
        <span class="avatar"><Icon name={settings?.access.mode === 'open' ? 'unlock' : 'lock'} size={22} /></span>
        <span class="text">
          {#if settings}
            <strong>{t(MODE_LABEL[settings.access.mode])}</strong>
            <span class="muted">{t(MODE_DETAIL[settings.access.mode])}</span>
          {:else}
            <strong>…</strong>
          {/if}
        </span>
        <button onclick={editAccess} disabled={!settings}>{t('settings.edit')}</button>
      </div>
      {#if store.me && !store.me.open_session}
        <div class="card">
          <span class="text">
            <strong>{t('sessions.current')}</strong>
          </span>
          <button onclick={signOut}><Icon name="logout" size={18} />{t('nav.signOut')}</button>
        </div>
      {:else if store.me?.open_session}
        <p class="muted note">{t('settings.signedInOpen')}</p>
      {/if}
    {/if}
  </section>

  {#if settings && settings.access.mode !== 'open'}
    <section class="block">
      <h3>{t('sessions.title')}</h3>
      <Sessions embedded />
    </section>
  {/if}

  <section class="block">
    <h3>{t('settings.about')}</h3>
    <div class="card">
      <span class="avatar"><Icon name="cast" size={22} /></span>
      <span class="text">
        <strong>CastHome</strong>
        <span class="muted">
          {settings
            ? t('settings.version', { version: settings.version }) + (settings.revision ? ` (${settings.revision})` : '')
            : '…'}
        </span>
        <a href={REPO_URL} target="_blank" rel="noopener noreferrer">{t('settings.sourceCode')}</a>
      </span>
    </div>
  </section>
</section>

<style>
  .block {
    margin-top: 24px;
  }
  .block h3 {
    margin: 0 0 4px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--muted);
  }
  .card {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    margin-top: 8px;
    border-radius: 8px;
    background: var(--surface);
    border: 1px solid var(--border);
  }
  .card.form {
    display: grid;
    gap: 14px;
    padding: 16px;
  }
  .avatar {
    display: grid;
    place-items: center;
    width: 42px;
    height: 42px;
    border-radius: 50%;
    background: var(--accent-soft);
    color: var(--accent);
    flex: none;
  }
  .text {
    flex: 1;
    display: grid;
    min-width: 0;
  }
  .ellipsis {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .card > button {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    flex: none;
  }
  .buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .spacer {
    flex: 1;
  }
  label {
    display: grid;
    gap: 6px;
  }
  label > span {
    font-weight: 600;
    font-size: 0.9rem;
  }
  .intro,
  .note {
    margin: 0;
    font-size: 0.85rem;
  }
  .note {
    margin-top: 8px;
  }
  .form .note {
    margin-top: 0;
  }
  .alert {
    margin: 8px 0 0;
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid var(--danger);
  }
  .error {
    color: var(--danger);
    margin: 0;
  }
  .ok {
    color: var(--accent);
    margin: 0;
  }
  .card.language {
    display: grid;
    gap: 8px;
    justify-items: start;
  }
</style>
