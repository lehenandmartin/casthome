<script lang="ts">
  import { api } from './lib/api';
  import { t } from './lib/i18n';
  import { store } from './lib/store.svelte';
  import AlbumView from './components/AlbumView.svelte';
  import Albums from './components/Albums.svelte';
  import ArtistView from './components/ArtistView.svelte';
  import Artists from './components/Artists.svelte';
  import GenreView from './components/GenreView.svelte';
  import Genres from './components/Genres.svelte';
  import Login from './components/Login.svelte';
  import PlayerBar from './components/PlayerBar.svelte';
  import QueueView from './components/QueueView.svelte';
  import Search from './components/Search.svelte';
  import Toasts from './components/Toasts.svelte';

  let hash = $state(location.hash);
  window.addEventListener('hashchange', () => {
    hash = location.hash;
    window.scrollTo(0, 0);
  });

  type Route =
    | { name: 'albums' | 'artists' | 'genres' | 'search' | 'queue' }
    | { name: 'album' | 'artist' | 'genre'; id: string };

  const route = $derived.by((): Route => {
    const path = hash.split('?')[0];
    const detail = path.match(/^#\/(album|artist|genre)\/(.+)$/);
    if (detail) return { name: detail[1] as 'album' | 'artist' | 'genre', id: decodeURIComponent(detail[2]) };
    const simple = path.match(/^#\/(artists|genres|search|queue)$/);
    if (simple) return { name: simple[1] as 'artists' | 'genres' | 'search' | 'queue' };
    return { name: 'albums' };
  });

  const section = $derived(
    route.name === 'album' ? 'albums' : route.name === 'artist' ? 'artists' : route.name === 'genre' ? 'genres' : route.name,
  );

  const NAV = [
    { href: '#/', name: 'albums', label: 'nav.albums' },
    { href: '#/artists', name: 'artists', label: 'nav.artists' },
    { href: '#/genres', name: 'genres', label: 'nav.genres' },
    { href: '#/search', name: 'search', label: 'nav.search' },
    { href: '#/queue', name: 'queue', label: 'nav.queue' },
  ] as const;

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
    <div class="links">
      {#each NAV as item (item.name)}
        <a href={item.href} class:active={section === item.name}>{t(item.label)}</a>
      {/each}
    </div>
    <button class="link" onclick={signOut}>{t('nav.signOut')}</button>
  </nav>
  <main class="content">
    {#if route.name === 'album'}
      <AlbumView id={route.id} />
    {:else if route.name === 'artist'}
      <ArtistView id={route.id} />
    {:else if route.name === 'genre'}
      {#key route.id}<GenreView name={route.id} />{/key}
    {:else if route.name === 'artists'}
      <Artists />
    {:else if route.name === 'genres'}
      <Genres />
    {:else if route.name === 'search'}
      <Search />
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
  .links {
    display: flex;
    gap: 16px;
    overflow-x: auto;
    min-width: 0;
    scrollbar-width: none;
  }
  nav a {
    flex: none;
    color: var(--muted);
    text-decoration: none;
    font-weight: 600;
  }
  nav a.active {
    color: var(--text);
  }
  .link {
    flex: none;
    margin-left: auto;
    background: none;
    border: 0;
    color: var(--muted);
    padding: 0;
  }
  .content {
    padding: 16px 16px 180px;
    max-width: 1100px;
    margin: 0 auto;
  }
</style>
