<script lang="ts">
  // Settings: one section per topic. Add new sections here as cards.
  import { api } from '../lib/api';
  import { t } from '../lib/i18n';
  import { store } from '../lib/store.svelte';
  import Icon from './Icon.svelte';
  import Sessions from './Sessions.svelte';

  let username = $state<string | null>(null);

  store.run(async () => {
    username = (await api.me()).username;
  });

  async function signOut() {
    await store.run(api.logout);
    store.signedOut();
  }
</script>

<section>
  <h2>{t('settings.title')}</h2>

  <section class="block">
    <h3>{t('settings.account')}</h3>
    <div class="card account">
      <span class="avatar"><Icon name="account" size={24} /></span>
      <span class="text">
        <strong>{username ?? '…'}</strong>
        <span class="muted">{t('settings.accountDetail')}</span>
      </span>
      <button onclick={signOut}><Icon name="logout" size={18} />{t('nav.signOut')}</button>
    </div>
  </section>

  <section class="block">
    <h3>{t('sessions.title')}</h3>
    <Sessions embedded />
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
  .account button {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    flex: none;
  }
</style>
