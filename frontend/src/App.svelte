<script lang="ts">
  import { ApiError, api } from './lib/api';
  import { t } from './lib/i18n';
  import type { IconName } from './lib/icons';
  import type { MessageKey } from './lib/i18n/en';
  import { router } from './lib/router.svelte';
  import { store } from './lib/store.svelte';
  import AlbumView from './components/AlbumView.svelte';
  import Albums from './components/Albums.svelte';
  import ArtistView from './components/ArtistView.svelte';
  import Artists from './components/Artists.svelte';
  import DevicePicker from './components/DevicePicker.svelte';
  import Dialog from './components/Dialog.svelte';
  import Favorites from './components/Favorites.svelte';
  import GenreView from './components/GenreView.svelte';
  import Genres from './components/Genres.svelte';
  import Icon from './components/Icon.svelte';
  import Library from './components/Library.svelte';
  import Login from './components/Login.svelte';
  import NowPlaying from './components/NowPlaying.svelte';
  import PlayerBar from './components/PlayerBar.svelte';
  import PlaylistView from './components/PlaylistView.svelte';
  import Playlists from './components/Playlists.svelte';
  import QueueView from './components/QueueView.svelte';
  import Search from './components/Search.svelte';
  import Sessions from './components/Sessions.svelte';
  import Toasts from './components/Toasts.svelte';
  import Tracks from './components/Tracks.svelte';

  const hash = $derived(router.hash);

  const PAGES = ['artists', 'genres', 'playlists', 'favorites', 'tracks', 'search', 'queue', 'account', 'library'] as const;
  type Page = (typeof PAGES)[number] | 'albums';
  type Route = { name: Page } | { name: 'album' | 'artist' | 'genre' | 'playlist'; id: string };

  const route = $derived.by((): Route => {
    const path = hash.split('?')[0];
    const detail = path.match(/^#\/(album|artist|genre|playlist)\/(.+)$/);
    if (detail) return { name: detail[1] as 'album' | 'artist' | 'genre' | 'playlist', id: decodeURIComponent(detail[2]) };
    const page = path.replace(/^#\//, '');
    return { name: (PAGES as readonly string[]).includes(page) ? (page as Page) : 'albums' };
  });

  const PARENT: Record<string, string> = { album: 'albums', artist: 'artists', genre: 'genres', playlist: 'playlists' };
  const section = $derived(PARENT[route.name] ?? route.name);
  // Mobile tabs: Library groups artists, genres, playlists, favorites and account.
  const LIBRARY_SECTIONS = new Set(['library', 'artists', 'genres', 'playlists', 'favorites', 'tracks', 'account']);
  const tab = $derived(LIBRARY_SECTIONS.has(section) ? 'library' : section);

  interface NavItem {
    href: string;
    name: string;
    label: MessageKey;
    icon: IconName;
  }
  const SIDEBAR: NavItem[] = [
    { href: '#/', name: 'albums', label: 'nav.albums', icon: 'disc' },
    { href: '#/search', name: 'search', label: 'nav.search', icon: 'search' },
    { href: '#/tracks', name: 'tracks', label: 'nav.tracks', icon: 'music' },
    { href: '#/artists', name: 'artists', label: 'nav.artists', icon: 'artist' },
    { href: '#/genres', name: 'genres', label: 'nav.genres', icon: 'tag' },
    { href: '#/playlists', name: 'playlists', label: 'nav.playlists', icon: 'playlist' },
    { href: '#/favorites', name: 'favorites', label: 'nav.favorites', icon: 'star' },
    { href: '#/queue', name: 'queue', label: 'nav.queue', icon: 'queue' },
  ];
  const TABS: NavItem[] = [
    { href: '#/', name: 'albums', label: 'nav.home', icon: 'home' },
    { href: '#/search', name: 'search', label: 'nav.search', icon: 'search' },
    { href: '#/library', name: 'library', label: 'nav.library', icon: 'library' },
    { href: '#/queue', name: 'queue', label: 'nav.queue', icon: 'queue' },
  ];

  const upcoming = $derived(
    store.queue.index !== null ? Math.max(0, store.queue.items.length - store.queue.index - 1) : store.queue.items.length,
  );

  // Restore the session (cookie) on load.
  // Only a 401 signs out: if the server is briefly unreachable, keep the cached
  // state on screen and let the live connection retry.
  api
    .me()
    .then(() => store.signedIn())
    .catch((err) => (err instanceof ApiError && err.status === 401 ? store.signedOut() : store.signedIn()));
</script>

<Toasts />
<Dialog />
<!-- Installed iOS app: the status bar is translucent; keep scrolled content from showing through it. -->
<div class="statusbar-bg" aria-hidden="true"></div>

{#if store.auth === 'signed-out'}
  <Login />
{:else if store.auth === 'signed-in'}
  <aside class="sidebar">
    <div class="brand"><Icon name="cast" size={24} />{t('app.name')}</div>
    <nav>
      {#each SIDEBAR as item (item.name)}
        <a href={item.href} class:active={section === item.name}>
          <Icon name={item.icon} size={20} />{t(item.label)}
          {#if item.name === 'queue' && upcoming > 0}<span class="badge">{upcoming}</span>{/if}
        </a>
      {/each}
    </nav>
    <a class="account" href="#/account" class:active={section === 'account'}>
      <Icon name="account" size={20} />{t('nav.account')}
    </a>
  </aside>

  <main class="content">
    {#if route.name === 'album'}
      <AlbumView id={route.id} />
    {:else if route.name === 'artist'}
      <ArtistView id={route.id} />
    {:else if route.name === 'genre'}
      {#key route.id}<GenreView name={route.id} />{/key}
    {:else if route.name === 'playlist'}
      <PlaylistView id={route.id} />
    {:else if route.name === 'account'}
      <Sessions />
    {:else if route.name === 'library'}
      <Library />
    {:else if route.name === 'playlists'}
      <Playlists />
    {:else if route.name === 'tracks'}
      <Tracks />
    {:else if route.name === 'favorites'}
      <Favorites />
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

  <nav class="tabbar">
    {#each TABS as item (item.name)}
      <a href={item.href} class:active={tab === item.name}>
        <span class="tab-icon">
          <Icon name={item.icon} size={22} />
          {#if item.name === 'queue' && upcoming > 0}<span class="badge">{upcoming > 99 ? '99+' : upcoming}</span>{/if}
        </span>
        <span>{t(item.label)}</span>
      </a>
    {/each}
  </nav>

  {#if store.nowPlayingOpen}<NowPlaying />{/if}
  {#if store.devicePickerOpen}<DevicePicker />{/if}
{/if}

<style>
  .statusbar-bg {
    position: fixed;
    z-index: 45;
    top: 0;
    left: 0;
    right: 0;
    /* Solid under the status bar, then a short fade for content scrolling under it. */
    height: calc(env(safe-area-inset-top) + 14px);
    background: linear-gradient(var(--bg) calc(100% - 14px), transparent);
    pointer-events: none;
  }

  .content {
    /* Extra room at the top: installed iOS apps blur the area under the status bar. */
    padding: calc(env(safe-area-inset-top) + 28px) 16px calc(var(--tabbar-h) + var(--player-h) + 24px);
    max-width: 1200px;
    margin: 0 auto;
  }

  .badge {
    display: inline-grid;
    place-items: center;
    min-width: 18px;
    height: 18px;
    padding: 0 5px;
    border-radius: 999px;
    background: var(--accent);
    color: var(--on-accent);
    font-size: 0.68rem;
    font-weight: 700;
  }

  /* --- mobile tab bar --- */
  .sidebar {
    display: none;
  }
  .tabbar {
    position: fixed;
    z-index: 31;
    left: 0;
    right: 0;
    bottom: 0;
    height: var(--tabbar-h);
    padding-bottom: env(safe-area-inset-bottom);
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    background: var(--surface);
    border-top: 1px solid var(--border);
  }
  .tabbar a {
    display: grid;
    justify-items: center;
    align-content: center;
    gap: 2px;
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--muted);
    text-decoration: none;
  }
  .tabbar a.active {
    color: var(--accent);
  }
  .tab-icon {
    position: relative;
  }
  .tab-icon .badge {
    position: absolute;
    top: -6px;
    left: 14px;
  }

  /* --- desktop sidebar --- */
  @media (min-width: 900px) {
    .tabbar {
      display: none;
    }
    .sidebar {
      position: fixed;
      z-index: 20;
      inset: 0 auto 0 0;
      width: var(--sidebar-w);
      display: flex;
      flex-direction: column;
      gap: 4px;
      /* The player bar starts right of the sidebar, so nothing to clear at the bottom. */
      padding: 20px 12px 20px;
      background: var(--surface);
      border-right: 1px solid var(--border);
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      font-weight: 800;
      font-size: 1.15rem;
      padding: 0 12px 16px;
      color: var(--accent);
    }
    .sidebar nav {
      display: grid;
      gap: 2px;
    }
    .sidebar a {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 12px;
      border-radius: 10px;
      color: var(--muted);
      text-decoration: none;
      font-weight: 600;
    }
    .sidebar a:hover {
      background: var(--surface-2);
      color: var(--text);
    }
    .sidebar a.active {
      background: var(--accent-soft);
      color: var(--accent);
    }
    .sidebar .badge {
      margin-left: auto;
    }
    .account {
      margin-top: auto;
    }
    .content {
      margin-left: var(--sidebar-w);
      padding: 28px 32px 120px;
    }
  }
</style>
