<script lang="ts">
  import { api } from './lib/api';
  import { t } from './lib/i18n';
  import { store } from './lib/store.svelte';
  import AlbumView from './components/AlbumView.svelte';
  import Albums from './components/Albums.svelte';
  import Login from './components/Login.svelte';
  import PlayerBar from './components/PlayerBar.svelte';
  import QueueView from './components/QueueView.svelte';
  import Toasts from './components/Toasts.svelte';

  let hash = $state(location.hash);
  window.addEventListener('hashchange', () => (hash = location.hash));

  const route = $derived.by(() => {
    const albumMatch = hash.match(/^#\/album\/(.+)$/);
    if (albumMatch) return { name: 'album' as const, id: decodeURIComponent(albumMatch[1]) };
    if (hash === '#/queue') return { name: 'queue' as const };
    return { name: 'albums' as const };
  });

  // Restore the session (cookie) on load.
  api
    .me()
    .then(() => store.signedIn())
    .catch(() => store.signedOut());

  async function signOut() {
    await store.run(api.logout);
    store.signedOut();
  }
</script>

<Toasts />

{#if store.auth === 'signed-out'}
  <Login />
{:else if store.auth === 'signed-in'}
  <nav>
    <a href="#/" class:active={route.name === 'albums'}>{t('nav.albums')}</a>
    <a href="#/queue" class:active={route.name === 'queue'}>{t('nav.queue')}</a>
    <button class="link" onclick={signOut}>{t('nav.signOut')}</button>
  </nav>
  <main class="content">
    {#if route.name === 'album'}
      <AlbumView id={route.id} />
    {:else if route.name === 'queue'}
      <QueueView />
    {:else}
      <Albums />
    {/if}
  </main>
  <PlayerBar />
{/if}

<style>
  nav {
    position: sticky;
    top: 0;
    z-index: 5;
    display: flex;
    gap: 16px;
    align-items: center;
    padding: calc(12px + env(safe-area-inset-top)) 16px 12px;
    background: var(--bg);
    border-bottom: 1px solid var(--border);
  }
  nav a {
    color: var(--muted);
    text-decoration: none;
    font-weight: 600;
  }
  nav a.active {
    color: var(--text);
  }
  .link {
    margin-left: auto;
    background: none;
    border: 0;
    color: var(--muted);
  }
  .content {
    padding: 16px 16px 180px;
    max-width: 1100px;
    margin: 0 auto;
  }
</style>
