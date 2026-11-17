// The colour of an album, taken from its cover: Now Playing borrows it for its
// seek bar and play button, so each album gives the player its own light.
// Only the hue and saturation are kept; the lightness is set by the theme, so
// the colour always has enough contrast (see NowPlaying.svelte).

export interface AlbumColor {
  h: number; // 0-360
  s: number; // 0-100
}

/** Below this saturation a cover reads as grey: the app's amber is kept. */
const MIN_SATURATION = 18;

/**
 * The dominant vivid colour of RGBA pixels: an average weighted by saturation,
 * so a pink dress on a black stage gives pink, not dark grey.
 * Null when the picture is grey (black and white photos, plain covers).
 */
export function dominantColor(pixels: ArrayLike<number>): AlbumColor | null {
  let r = 0;
  let g = 0;
  let b = 0;
  let weight = 0;
  for (let i = 0; i + 3 < pixels.length; i += 4) {
    if (pixels[i + 3] < 128) continue;
    const pr = pixels[i] / 255;
    const pg = pixels[i + 1] / 255;
    const pb = pixels[i + 2] / 255;
    const max = Math.max(pr, pg, pb);
    const min = Math.min(pr, pg, pb);
    const chroma = max - min;
    // Near-black and near-white pixels say little about the colour.
    if (max < 0.12 || min > 0.92) continue;
    const w = chroma * chroma;
    r += pr * w;
    g += pg * w;
    b += pb * w;
    weight += w;
  }
  if (weight === 0) return null;
  const { h, s } = toHsl(r / weight, g / weight, b / weight);
  return s < MIN_SATURATION ? null : { h: Math.round(h), s: Math.round(Math.min(s, 72)) };
}

function toHsl(r: number, g: number, b: number): { h: number; s: number } {
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const d = max - min;
  if (d === 0) return { h: 0, s: 0 };
  const l = (max + min) / 2;
  const s = d / (1 - Math.abs(2 * l - 1));
  let h: number;
  if (max === r) h = ((g - b) / d) % 6;
  else if (max === g) h = (b - r) / d + 2;
  else h = (r - g) / d + 4;
  return { h: (h * 60 + 360) % 360, s: s * 100 };
}

const cache = new Map<string, Promise<AlbumColor | null>>();

/** The colour of a cover (same-origin URL), read from a 24×24 copy of it. */
export function albumColor(url: string): Promise<AlbumColor | null> {
  let found = cache.get(url);
  if (!found) {
    found = new Promise((resolve) => {
      const img = new Image();
      img.decoding = 'async';
      img.onload = () => {
        try {
          const canvas = document.createElement('canvas');
          canvas.width = canvas.height = 24;
          const ctx = canvas.getContext('2d', { willReadFrequently: true });
          if (!ctx) return resolve(null);
          ctx.drawImage(img, 0, 0, 24, 24);
          resolve(dominantColor(ctx.getImageData(0, 0, 24, 24).data));
        } catch {
          resolve(null);
        }
      };
      img.onerror = () => resolve(null);
      img.src = url;
    });
    cache.set(url, found);
  }
  return found;
}
