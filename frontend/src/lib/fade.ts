// Covers fade in when they arrive slowly instead of popping in.
//
// A cover that shows within a moment (already in the browser's cache, even if
// not decoded yet when the page is built) appears directly: fading those made
// pages flash right after appearing. Only a cover still missing after
// GRACE_MS fades in when it arrives. Pictures drawn over a low-resolution
// background (the album header) are left alone.

const COVER = /\/api\/cover\//;
const GRACE_MS = 150;

function prepare(img: HTMLImageElement): void {
  if (img.dataset.fade || !COVER.test(img.src) || img.style.background) return;
  img.dataset.fade = '1';
  if (img.complete && img.naturalWidth > 0) return;
  const started = performance.now();
  img.addEventListener(
    'load',
    () => {
      if (performance.now() - started > GRACE_MS) img.classList.add('fade-in');
    },
    { once: true },
  );
}

function scan(node: Node): void {
  if (node instanceof HTMLImageElement) prepare(node);
  else if (node instanceof HTMLElement) node.querySelectorAll('img').forEach(prepare);
}

export function fadeInCovers(): void {
  scan(document.body);
  new MutationObserver((records) => {
    for (const record of records) record.addedNodes.forEach(scan);
  }).observe(document.body, { childList: true, subtree: true });
}
