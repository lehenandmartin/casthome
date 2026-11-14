<script lang="ts">
  import { api, coverUrl } from '../lib/api';
  import { menu, type MenuSpec } from '../lib/contextMenu.svelte';
  import { t } from '../lib/i18n';
  import { albumMenu, artistMenu, playlistMenu } from '../lib/menus';
  import { startRadio } from '../lib/radio';
  import { store } from '../lib/store.svelte';
  import type { HomeData } from '../lib/types';
  import HomeRow from './HomeRow.svelte';
  import Icon from './Icon.svelte';
  import SongList from './SongList.svelte';

  // Kept for the whole visit: coming back to Home shows the last data at once,
  // then refreshes it in the background.
  let data = $state<HomeData | null>(homeCache.value);

  async function refresh() {
    const fresh = await api.home();
    data = fresh;
    homeCache.value = fresh;
  }
  store.run(refresh);

  interface Tile {
    href: string;
    label: string;
    cover: string | null;
    icon: 'starFilled' | 'disc' | 'playlist';
    play?: () => Promise<void>;
    albumId?: string;
    playlistId?: string;
    /** Right-click menu (album and playlist tiles). */
    menu?: () => MenuSpec;
  }

  // Recently played row, without what is already on screen: the albums in the
  // quick-access tiles and in Recently added.
  const recentRow = $derived.by(() => {
    if (!data) return [];
    const shown = new Set([
      ...tiles.map((tile) => tile.albumId).filter(Boolean),
      ...data.recently_added.map((a) => a.id),
    ]);
    return data.recently_played.filter((a) => !shown.has(a.id)).slice(0, 12);
  });

  // Playlists row, without the ones already in the quick-access tiles.
  const playlistRow = $derived.by(() => {
    if (!data) return [];
    const shown = new Set(tiles.map((tile) => tile.playlistId).filter(Boolean));
    return data.playlists.filter((p) => !shown.has(p.id)).slice(0, 12);
  });

  // Quick access: favourite tracks, then recently played albums and recently
  // edited playlists, interleaved, up to six tiles.
  const tiles = $derived.by((): Tile[] => {
    if (!data) return [];
    const out: Tile[] = [];
    if (data.favorite_song_count > 0) {
      out.push({ href: '#/tracks?fav=1', label: t('home.favoriteTracks'), cover: null, icon: 'starFilled' });
    }
    const albums = data.recently_played.slice(0, 3).map(
      (a): Tile => ({
        href: `#/album/${encodeURIComponent(a.id)}`,
        label: a.name,
        cover: a.cover_art,
        icon: 'disc',
        albumId: a.id,
        play: () => api.playAlbum(a.id),
        menu: () => albumMenu(a),
      }),
    );
    const lists = data.playlists.slice(0, 3).map(
      (p): Tile => ({
        href: `#/playlist/${encodeURIComponent(p.id)}`,
        label: p.name,
        cover: p.cover_art,
        icon: 'playlist',
        playlistId: p.id,
        play: () => api.playPlaylist(p.id),
        menu: () => playlistMenu(p, refresh),
      }),
    );
    for (let i = 0; out.length < 6 && (i < albums.length || i < lists.length); i++) {
      if (albums[i]) out.push(albums[i]);
      if (lists[i] && out.length < 6) out.push(lists[i]);
    }
    return out.slice(0, 6);
  });

</script>

<script lang="ts" module>
  import type { HomeData as Cached } from '../lib/types';
  const homeCache: { value: Cached | null } = { value: null };
</script>

<section class="home">
  {#if !data}
    <div aria-busy="true" aria-hidden="true">
      <div class="tiles">
        {#each { length: 6 } as _, i (i)}<span class="skeleton sk-tile"></span>{/each}
      </div>
      {#each { length: 2 } as _, row (row)}
        <span class="skeleton text sk-heading"></span>
        <div class="sk-row">
          {#each { length: 8 } as _, i (i)}
            <div class="card">
              <span class="skeleton sk-cover"></span>
              <span class="skeleton text" style:width="80%"></span>
              <span class="skeleton text" style:width="50%"></span>
            </div>
          {/each}
        </div>
      {/each}
    </div>
  {/if}

  {#if tiles.length > 0}
    <div class="tiles">
      {#each tiles as tile (tile.href)}
        <div class="tile" use:menu={() => tile.menu?.() ?? null}>
          <a href={tile.href} class="tile-link">
            {#if tile.cover}
              <img src={coverUrl(tile.cover, 120)} alt="" loading="lazy" />
            {:else}
              <span class="tile-icon" class:fav={tile.icon === 'starFilled'}><Icon name={tile.icon} size={22} /></span>
            {/if}
            <span class="tile-label">{tile.label}</span>
          </a>
          {#if tile.play}
            <button class="tile-play" aria-label={t('album.play')} onclick={() => store.run(tile.play!)}>
              <Icon name="play" size={16} />
            </button>
          {/if}
        </div>
      {/each}
    </div>
  {/if}

  {#if recentRow.length > 0}
    <HomeRow title={t('home.recentlyPlayed')} seeAll="#/albums?type=recent">
      {#each recentRow as album (album.id)}
        <a class="card" href={`#/album/${encodeURIComponent(album.id)}`} use:menu={() => albumMenu(album)}>
          <img src={coverUrl(album.cover_art, 300)} alt="" loading="lazy" />
          <strong class="ellipsis">{album.name}</strong>
          <span class="muted ellipsis">{album.artist}</span>
        </a>
      {/each}
    </HomeRow>
  {/if}

  {#if data && data.recently_added.length > 0}
    <HomeRow title={t('home.recentlyAdded')} seeAll="#/albums?type=newest">
      {#each data.recently_added as album (album.id)}
        <a class="card" href={`#/album/${encodeURIComponent(album.id)}`} use:menu={() => albumMenu(album)}>
          <img src={coverUrl(album.cover_art, 300)} alt="" loading="lazy" />
          <strong class="ellipsis">{album.name}</strong>
          <span class="muted ellipsis">{album.artist}</span>
        </a>
      {/each}
    </HomeRow>
  {/if}

  {#if data && data.favorite_artists.length > 0}
    <HomeRow
      title={data.artists_are_favorites ? t('home.favoriteArtists') : t('home.topArtists')}
      seeAll={data.artists_are_favorites ? '#/artists?fav=1' : '#/artists'}
    >
      {#each data.favorite_artists as artist (artist.id)}
        <a class="card artist" href={`#/artist/${encodeURIComponent(artist.id)}`} use:menu={() => artistMenu(artist)}>
          <img src={coverUrl(artist.cover_art, 300)} alt="" loading="lazy" />
          <strong class="ellipsis">{artist.name}</strong>
        </a>
      {/each}
    </HomeRow>
  {/if}

  {#if data && data.on_repeat.length > 0}
    <section class="repeat">
      <div class="repeat-head">
        <h3>{t('home.onRepeat')}</h3>
        <button class="chip" onclick={() => startRadio(data!.on_repeat[0])}>
          <Icon name="radio" size={16} />{t('song.startRadio')}
        </button>
      </div>
      <p class="muted hint">{t('home.onRepeatHint')}</p>
      <SongList
        songs={data.on_repeat}
        numbered
        onplay={(i) => store.run(() => api.playSongs(data!.on_repeat.map((s) => s.id), i, t('home.onRepeat')))}
      />
    </section>
  {/if}

  {#if playlistRow.length > 0}
    <HomeRow title={t('home.yourPlaylists')} seeAll="#/playlists">
      {#each playlistRow as playlist (playlist.id)}
        <a class="card" href={`#/playlist/${encodeURIComponent(playlist.id)}`} use:menu={() => playlistMenu(playlist, refresh)}>
          {#if playlist.cover_art}
            <img src={coverUrl(playlist.cover_art, 300)} alt="" loading="lazy" />
          {:else}
            <span class="cover-icon"><Icon name="playlist" size={40} /></span>
          {/if}
          <strong class="ellipsis">{playlist.name}</strong>
          <span class="muted ellipsis">{t('playlists.tracks', { count: playlist.song_count })}</span>
        </a>
      {/each}
    </HomeRow>
  {/if}

  {#if data && !tiles.length && !data.recently_added.length}
    <p class="muted">{t('albums.empty')}</p>
  {/if}
</section>

<style>
  /* Placeholders on the first visit (later visits show the last data at once). */
  .sk-tile {
    height: 56px;
    border-radius: 8px;
  }
  .sk-heading {
    width: 180px;
    height: 1.15rem;
    margin: 30px 0 12px;
  }
  .sk-row {
    display: flex;
    gap: 14px;
    overflow: hidden;
  }
  .sk-row .card {
    flex: none;
  }
  .sk-cover {
    width: 100%;
    aspect-ratio: 1;
    border-radius: 8px;
  }
  .home {
    padding-top: 4px;
  }
  /* --- quick access tiles --- */
  .tiles {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }
  @media (min-width: 900px) {
    .tiles {
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }
  }
  .tile {
    position: relative;
    display: flex;
    align-items: center;
    border-radius: 8px;
    background: var(--surface-2);
    overflow: hidden;
    min-width: 0;
  }
  .tile-link {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
    color: inherit;
    text-decoration: none;
  }
  .tile img,
  .tile-icon {
    width: 52px;
    height: 52px;
    object-fit: cover;
    flex: none;
    background: var(--surface-3);
  }
  .tile-icon {
    display: grid;
    place-items: center;
    color: var(--muted);
  }
  .tile-icon.fav {
    background: linear-gradient(135deg, var(--accent), color-mix(in srgb, var(--accent) 40%, var(--star)));
    color: #fff;
  }
  .tile-label {
    font-weight: 700;
    font-size: 0.85rem;
    line-height: 1.2;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    padding-right: 6px;
  }
  .tile-play {
    display: none;
    place-items: center;
    width: 32px;
    height: 32px;
    min-height: 0;
    padding: 0;
    margin-right: 8px;
    border-radius: 50%;
    background: var(--accent);
    color: var(--on-accent);
    flex: none;
  }
  @media (hover: hover) and (pointer: fine) {
    .tile:hover .tile-play {
      display: grid;
    }
  }
  /* --- cards in rows --- */
  .card {
    width: 140px;
    display: grid;
    gap: 4px;
    color: inherit;
    text-decoration: none;
  }
  @media (min-width: 900px) {
    .card {
      width: 170px;
    }
  }
  .card img,
  .cover-icon {
    width: 100%;
    aspect-ratio: 1;
    object-fit: cover;
    border-radius: 8px;
    background: var(--surface-2);
  }
  .cover-icon {
    display: grid;
    place-items: center;
    color: var(--muted);
  }
  .card.artist {
    text-align: center;
    width: 120px;
  }
  .card.artist img {
    border-radius: 50%;
  }
  .card strong {
    font-size: 0.9rem;
  }
  /* --- on repeat --- */
  .repeat {
    margin-top: 26px;
  }
  .repeat-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  .repeat-head h3 {
    margin: 0;
    font-size: 1.15rem;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.85rem;
    padding: 6px 12px;
    min-height: 32px;
  }
  .hint {
    margin: 2px 0 6px;
    font-size: 0.8rem;
  }
</style>
