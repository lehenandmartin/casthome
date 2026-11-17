<script lang="ts">
  // Settings: one section per topic. Add new sections here as cards.
  import { ApiError, api } from '../lib/api';
  import { LANGUAGES, browserLanguage, languageState, setLanguage, t, tCode, type LanguagePref } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import { setTheme, themeState, type ThemePref } from '../lib/theme.svelte';
  import type { AccessMode, NavidromeForm, ServerSettings } from '../lib/types';
  import AccessFields from './AccessFields.svelte';
  import AppMark, { BOOT_END } from './AppMark.svelte';
  import Icon from './Icon.svelte';
  import NavidromeFields from './NavidromeFields.svelte';
  import PlaybackSettings from './PlaybackSettings.svelte';
  import Sessions from './Sessions.svelte';

  let settings = $state<ServerSettings | null>(null);
  // How far the About screen's mark is in switching on (AppMark): its text follows.
  let bootElapsed = $state(0);

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

  const REPO_URL = 'https://github.com/lehenandmartin/casthome';

  load();
</script>

<section>
  <h2>{t('settings.title')}</h2>

  <!-- An LCD set into the case, like Now Playing's: the mark switching on,
       the name and version (a link to the code, underlined), the credit. -->
  <div class="about lcd lcd-screen recessed">
    <AppMark size={56} boot bare bind:elapsed={bootElapsed} />
    <span class="lines">
      <a
        class:off={bootElapsed < BOOT_END + 150}
        href={REPO_URL}
        target="_blank"
        rel="noopener noreferrer"
        title={t('settings.sourceCode') + (settings?.revision ? ` (${settings.revision})` : '')}
        >CastHome{settings ? ` v${settings.version}` : ''}<span class="sr-only">, {t('settings.sourceCode')}</span></a
      >
      <span class="credit" class:off={bootElapsed < BOOT_END + 350}>{t('settings.credit')}</span>
    </span>
  </div>

  <section class="block">
    <h3>{t('settings.navidrome')}</h3>
    {#if store.navidromeRejected}<p class="alert" role="alert">{t('navidrome.rejected')}</p>{/if}
    {#if editingNavidrome && settings}
      <form class="group form" onsubmit={saveNavidrome}>
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
      <div class="group">
        <div class="item">
          <span class="text">
            <strong class="ellipsis">{settings?.navidrome.username ?? '…'}</strong>
            <span class="muted ellipsis">{settings?.navidrome.url ?? t('settings.navidromeIntro')}</span>
          </span>
          <button onclick={editNavidrome} disabled={!settings}>{t('settings.edit')}</button>
        </div>
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
    <h3>{t('settings.access')}</h3>
    {#if editingAccess && settings}
      <form class="group form" onsubmit={saveAccess}>
        <p class="muted intro">{t('settings.accessIntro')}</p>
        <AccessFields
          bind:mode
          bind:password
          bind:confirm
          keepPassword={settings.access.has_password}
          client={settings}
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
      <div class="group">
        <div class="item">
          <Icon name={settings?.access.mode === 'open' ? 'unlock' : 'lock'} size={18} />
          <strong class="text">{settings ? t(MODE_LABEL[settings.access.mode]) : '…'}</strong>
          <button onclick={editAccess} disabled={!settings}>{t('settings.edit')}</button>
        </div>
        {#if store.me && !store.me.open_session}
          <div class="item">
            <Icon name="logout" size={18} />
            <span class="text">{t('sessions.current')}</span>
            <button onclick={signOut}>{t('nav.signOut')}</button>
          </div>
        {/if}
      </div>
      {#if settings?.access.mode === 'lan' && settings.untrusted_proxy}
        <p class="alert" role="alert">{t('access.untrustedProxy', { address: settings.client_address })}</p>
      {/if}
    {/if}
  </section>

  {#if settings && settings.access.mode !== 'open'}
    <section class="block">
      <h3>{t('sessions.title')}</h3>
      <Sessions embedded />
    </section>
  {/if}

  <!-- Kept on this device only, not on the server. -->
  <section class="block">
    <h3>{t('settings.device')}</h3>
    <div class="group">
      <label class="item">
        <span class="text">{t('settings.language')}</span>
        <select value={languageState.pref} onchange={(e) => setLanguage(e.currentTarget.value as LanguagePref)}>
          <option value="auto">{t('settings.languageAuto', { language: t(`language.${autoLanguage}`) })}</option>
          {#each LANGUAGES as lang (lang)}<option value={lang}>{t(`language.${lang}`)}</option>{/each}
        </select>
      </label>
      <label class="item">
        <span class="text">{t('settings.theme')}</span>
        <select value={themeState.pref} onchange={(e) => setTheme(e.currentTarget.value as ThemePref)}>
          <option value="auto">{t('settings.themeAuto')}</option>
          <option value="light">{t('settings.themeLight')}</option>
          <option value="dark">{t('settings.themeDark')}</option>
        </select>
      </label>
    </div>
  </section>
</section>

<style>
  /* Grouped like the iPod's menus: one card per topic, its rows split by
     hairlines, the topic's name above in small muted text. */
  .block {
    margin-top: 24px;
  }
  .block h3 {
    margin: 0 0 8px;
    font-size: var(--text-xs);
    font-weight: 500;
    color: var(--muted);
  }
  .group {
    border-radius: 12px;
    background: var(--surface);
    border: 1px solid var(--border);
  }
  .item {
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 56px;
    padding: 8px 16px;
    color: var(--muted);
  }
  .item + .item {
    border-top: 1px solid var(--border);
  }
  /* A setting's name on its row, in the row's own size. */
  label.item > .text {
    font-size: inherit;
    font-weight: 400;
  }
  .item .text {
    flex: 1;
    display: grid;
    min-width: 0;
    color: var(--text);
  }
  .item strong {
    font-weight: 500;
  }
  .item > button {
    flex: none;
  }
  .item select {
    flex: 0 1 220px;
    min-width: 0;
  }
  .group.form {
    display: grid;
    gap: 12px;
    padding: 16px;
  }
  /* The LCD, in Chicago at Now Playing's size; room around it for its lip. */
  .about {
    --radius-w: 10px;
    display: flex;
    align-items: center;
    gap: 16px;
    margin-top: 16px;
    padding: 16px;
    border-radius: var(--radius-w);
    font-size: 20px;
    line-height: 22px;
  }
  .about .lines {
    display: grid;
    gap: 4px;
    min-width: 0;
  }
  /* Once the mark is on, the text appears line by line, each line snapping
     on like the pixels (still read by screen readers meanwhile). */
  .about .lines > .off {
    opacity: 0;
  }
  /* The name and version lead to the code: underlined, a 2px rule of ink. */
  .about a {
    justify-self: start;
    color: inherit;
    text-decoration: underline;
    text-decoration-thickness: 2px;
    text-underline-offset: 4px;
  }
  @media (hover: hover) {
    .about a:hover {
      color: var(--lcd-dim);
    }
  }
  .credit {
    color: var(--lcd-dim);
  }
  .ellipsis {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
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
    font-weight: 500;
    font-size: var(--text-sm);
  }
  .intro,
  .note {
    margin: 0;
    font-size: var(--text-sm);
  }
  .alert {
    margin: 0 0 8px;
    padding: 12px;
    border-radius: 8px;
    border: 1px solid var(--danger);
  }
  .group + .alert {
    margin: 8px 0 0;
  }
  .error {
    color: var(--danger);
    margin: 0;
  }
  .ok {
    color: var(--accent);
    margin: 0;
  }
</style>
