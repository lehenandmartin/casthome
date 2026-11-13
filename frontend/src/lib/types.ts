export interface Song {
  id: string;
  title: string;
  artist: string;
  artist_id: string | null;
  album: string;
  album_id: string | null;
  cover_art: string | null;
  duration: number;
  track: number | null;
  disc: number | null;
}

export interface QueueItem extends Song {
  uid: number;
}

export interface Album {
  id: string;
  name: string;
  artist: string;
  artist_id: string | null;
  cover_art: string | null;
  year: number | null;
  song_count: number;
  duration: number;
  songs?: Song[] | null;
}

export interface Device {
  uuid: string;
  name: string;
  model: string;
  cast_type: 'cast' | 'audio' | 'group' | string;
  host: string;
  port: number;
}

export type PlayerStatus = 'stopped' | 'loading' | 'buffering' | 'playing' | 'paused';
export type RepeatMode = 'off' | 'all' | 'one';

export interface PlayerState {
  device_uuid: string | null;
  device_name: string | null;
  connected: boolean;
  status: PlayerStatus;
  index: number | null;
  current: Song | null;
  position: number;
  duration: number | null;
  volume: number;
  muted: boolean;
  shuffle: boolean;
  repeat: RepeatMode;
  queue_version: number;
}

export interface QueueState {
  version: number;
  index: number | null;
  items: QueueItem[];
}

export interface Notification {
  id: number;
  level: 'info' | 'warning' | 'error';
  code: string;
  params: Record<string, unknown>;
}

export interface Artist {
  id: string;
  name: string;
  album_count: number;
  cover_art: string | null;
}

export interface ArtistDetail extends Artist {
  albums: Album[];
}

export interface Genre {
  name: string;
  song_count: number;
  album_count: number;
}

export interface SearchResult {
  artists: Artist[];
  albums: Album[];
  songs: Song[];
}

export type AlbumListType = 'newest' | 'recent' | 'random' | 'frequent' | 'alphabeticalByName' | 'byGenre';
export type AddMode = 'now' | 'next' | 'end';
