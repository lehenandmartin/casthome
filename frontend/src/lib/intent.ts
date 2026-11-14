// Prefetch on intent: when a finger touches a link to an album, artist or
// playlist (or the mouse rests on it), its data and large cover start loading,
// so the page usually opens already filled.
import { prefetch } from './api';

const HOVER_DELAY_MS = 80;
const seen = new Set<string>();

function linkOf(target: EventTarget | null): HTMLAnchorElement | null {
  const link = (target as Element | null)?.closest?.('a');
  const href = link?.getAttribute('href');
  return link && href && /^#\/(album|artist|playlist)\//.test(href) ? link : null;
}

function warm(link: HTMLAnchorElement): void {
  const href = link.getAttribute('href')!;
  prefetch(href); // the API cache drops it if the data is fresh
  if (seen.has(href)) return;
  seen.add(href);
  // The album page shows the cover at 600 px; the card shows a smaller one.
  const img = link.querySelector('img');
  if (img && href.startsWith('#/album/') && /[?&]size=\d+/.test(img.src)) {
    new Image().src = img.src.replace(/([?&]size=)\d+/, '$1600');
  }
}

export function watchIntent(): void {
  // iOS only shows :active (press feedback) when the page listens to touches.
  document.addEventListener('touchstart', () => {}, { passive: true });

  document.addEventListener(
    'pointerdown',
    (event) => {
      const link = linkOf(event.target);
      if (link) warm(link);
    },
    { capture: true, passive: true },
  );

  // Mouse only: a short rest on the link (not every link the pointer crosses).
  let timer: ReturnType<typeof setTimeout> | undefined;
  document.addEventListener(
    'mouseover',
    (event) => {
      const link = linkOf(event.target);
      clearTimeout(timer);
      if (link) timer = setTimeout(() => warm(link), HOVER_DELAY_MS);
    },
    { passive: true },
  );
}
