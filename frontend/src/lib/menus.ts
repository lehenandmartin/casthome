// The action menus of tracks, queue items, albums, playlists and artists,
// shared by every place that shows them (⋯ buttons and right-clicks).
import { api } from './api';
import { contextMenu, type MenuAction, type MenuSpec } from './contextMenu.svelte';
import { dialogs } from './dialog.svelte';
import { t } from './i18n';
import { startRadio } from './radio';
import { store } from './store.svelte';
import type { Album, Artist, Playlist, QueueItem, Song, StarKind } from './types';

const albumHref = (id: string) => `#/album/${encodeURIComponent(id)}`;
const artistHref = (id: string) => `#/artist/${encodeURIComponent(id)}`;

function queued(run: () => Promise<unknown>): Promise<void> {
  return store.run(async () => {
    await run();
    store.notify('added_to_queue', {}, 'info');
  });
}

/** Favorite toggle; `item.starred` is updated at once and restored on failure. */
function starItem(kind: StarKind, item: { id: string; starred: boolean }): MenuAction {
  const starred = item.starred;
  return {
    label: starred ? t('star.remove') : t('star.add'),
    icon: starred ? 'starFilled' : 'star',
    action: async () => {
      item.starred = !starred;
      try {
        await api.setStarred(kind, item.id, !starred);
      } catch {
        item.starred = starred;
        store.notify('navidrome_unavailable');
      }
    },
  };
}

/** Radio, playlist and navigation entries common to every track menu. */
function trackLinks(song: Song): MenuAction[] {
  return [
    { label: t('song.startRadio'), icon: 'radio', action: () => startRadio(song) },
    { label: t('song.addToPlaylist'), icon: 'playlist', action: () => contextMenu.pickPlaylist([song.id]) },
    ...(song.album_id ? [{ label: t('song.goToAlbum'), icon: 'disc' as const, href: albumHref(song.album_id) }] : []),
    ...(song.artist_id ? [{ label: t('song.goToArtist'), icon: 'artist' as const, href: artistHref(song.artist_id) }] : []),
  ];
}

function songHead(song: Song): Pick<MenuSpec, 'title' | 'subtitle' | 'rating'> {
  return {
    title: song.title,
    subtitle: `${song.artist}${song.album ? ` · ${song.album}` : ''}`,
    rating: { id: song.id, value: song.user_rating, onchange: (value) => (song.user_rating = value) },
  };
}

/** A track in a list: play, queue, radio, playlist, album, artist (+ extras). */
export function songMenu(song: Song, extra: MenuAction[] = []): MenuSpec {
  return {
    ...songHead(song),
    items: [
      { label: t('song.playNow'), icon: 'play', action: () => store.run(() => api.queueSongs([song.id], 'now')) },
      { label: t('song.addToQueue'), icon: 'queue', action: () => queued(() => api.queueSongs([song.id], 'queue')) },
      ...trackLinks(song),
      ...extra,
    ],
  };
}

/** The track playing now (player bar, Now Playing). */
export function currentSongMenu(song: Song): MenuSpec {
  return { ...songHead(song), items: [starItem('song', song), ...trackLinks(song)] };
}

/** A queue row. `toNextInQueue` is set for album/playlist rows not yet in "Next in queue". */
export function queueItemMenu(item: QueueItem, toNextInQueue?: () => void): MenuSpec {
  return {
    ...songHead(item),
    items: [
      { label: t('song.playNow'), icon: 'play', action: () => store.run(() => api.jump(item.uid)) },
      toNextInQueue && { label: t('queue.moveToNext'), icon: 'queue', action: toNextInQueue },
      ...trackLinks(item),
      { label: t('queue.remove'), icon: 'trash', danger: true, action: () => store.run(() => api.removeItem(item.uid)) },
    ],
  };
}

export function albumMenu(album: Album): MenuSpec {
  return {
    title: album.name,
    subtitle: album.artist,
    rating: { id: album.id, value: album.user_rating, onchange: (value) => (album.user_rating = value) },
    items: [
      { label: t('album.play'), icon: 'play', action: () => store.run(() => api.playAlbum(album.id)) },
      { label: t('album.addToQueue'), icon: 'queue', action: () => queued(() => api.queueAlbum(album.id)) },
      starItem('album', album),
      !!album.artist_id && { label: t('song.goToArtist'), icon: 'artist', href: artistHref(album.artist_id!) },
    ],
  };
}

export function artistMenu(artist: Pick<Artist, 'id' | 'name' | 'starred'>): MenuSpec {
  return {
    title: artist.name,
    items: [
      { label: t('artist.playAll'), icon: 'play', action: () => store.run(() => api.playArtist(artist.id)) },
      { label: t('song.addToQueue'), icon: 'queue', action: () => queued(() => api.queueArtist(artist.id)) },
      starItem('artist', artist),
    ],
  };
}

/** `onchange` runs after a rename or a deletion, to refresh the list shown. */
export function playlistMenu(playlist: Playlist, onchange?: () => unknown): MenuSpec {
  return {
    title: playlist.name,
    subtitle: t('playlists.tracks', { count: playlist.song_count }),
    items: [
      { label: t('playlist.play'), icon: 'play', action: () => store.run(() => api.playPlaylist(playlist.id)) },
      { label: t('song.addToQueue'), icon: 'queue', action: () => queued(() => api.queuePlaylist(playlist.id)) },
      {
        label: t('playlist.rename'),
        icon: 'edit',
        action: async () => {
          const name = (
            await dialogs.prompt({ title: t('playlist.rename'), value: playlist.name, confirmLabel: t('playlist.save') })
          )?.trim();
          if (!name || name === playlist.name) return;
          await store.run(async () => {
            await api.updatePlaylist(playlist.id, { name });
            playlist.name = name;
            await onchange?.();
          });
        },
      },
      {
        label: t('playlist.delete'),
        icon: 'trash',
        danger: true,
        action: async () => {
          const ok = await dialogs.confirm({
            title: t('playlist.delete'),
            message: t('playlist.deleteConfirm', { name: playlist.name }),
            confirmLabel: t('playlist.delete'),
            danger: true,
          });
          if (!ok) return;
          await store.run(async () => {
            await api.deletePlaylist(playlist.id);
            await onchange?.();
          });
        },
      },
    ],
  };
}
