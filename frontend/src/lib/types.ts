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
  starred: boolean;
  user_rating: number;
}

export interface QueueItem extends Song {
  uid: number;
  /** In "next in queue" (added by hand, not played yet). */
  queued: boolean;
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
  starred: boolean;
  user_rating: number;
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
  device_type: 'cast' | 'audio' | 'group' | 'browser' | string | null;
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
  /** Album or playlist the "next from" part comes from (the seed track's title for a radio). */
  context_name?: string | null;
  /** The "next from" part is an endless radio of similar tracks. */
  radio?: boolean;
  /** Where the radio's tracks come from: audiomuse | similar | similar_artists | top_songs. */
  radio_source?: string | null;
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
  starred: boolean;
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
/** 'now' plays right away; 'queue' adds to "next in queue", before the rest of the album. */
export type AddMode = 'now' | 'queue';

export interface Playlist {
  id: string;
  name: string;
  comment: string;
  owner: string;
  public: boolean;
  song_count: number;
  duration: number;
  cover_art: string | null;
  changed: string | null;
  songs?: Song[] | null;
}

export type StarKind = 'song' | 'album' | 'artist';

export interface SessionInfo {
  id: string;
  persistent: boolean;
  created_at: number;
  last_seen_at: number;
  expires_at: number;
  user_agent: string;
  ip: string;
  current: boolean;
}

export type SongSort = 'recent' | 'title' | 'artist' | 'album' | 'frequent' | 'played';

export interface SongPage {
  items: Song[];
  total: number;
}

export interface HomeData {
  recently_played: Album[];
  recently_added: Album[];
  favorite_artists: Artist[];
  /** false: favorite_artists is a fallback (artists of the most played albums). */
  artists_are_favorites: boolean;
  favorite_song_count: number;
  /** Most played tracks among those played in the last 30 days. */
  on_repeat: Song[];
  /** Most recently edited first. */
  playlists: Playlist[];
}

export type AccessMode = 'password' | 'lan' | 'open';

/** Public: what to show first. */
export interface AppStatus {
  setup_required: boolean;
  setup: { navidrome: boolean; access: boolean };
  signed_in: boolean;
}

export interface Me {
  username: string | null;
  session_id: string;
  access_mode: AccessMode;
  /** Let in without a password (open access, or the local network in LAN mode). */
  open_session: boolean;
}

export interface NavidromeFields {
  url: string;
  public_url: string;
  username: string;
}

/** Fields an environment variable sets (shown read-only). */
export type LockedField = 'url' | 'public_url' | 'username' | 'password';

export interface NavidromeForm extends NavidromeFields {
  /** Blank keeps the saved password (same server and account only). */
  password: string;
}

export interface SetupInfo {
  setup: { navidrome: boolean; access: boolean };
  navidrome: NavidromeFields;
  locked: LockedField[];
  client_is_local: boolean;
}

export interface ServerSettings {
  navidrome: NavidromeFields & { has_password: boolean };
  locked: LockedField[];
  access: { mode: AccessMode; has_password: boolean };
  client_is_local: boolean;
}

export interface AccessForm {
  mode: AccessMode;
  password?: string | null;
  current_password?: string | null;
  remember?: boolean;
}
