// Reveal a set of pictures together: wait until they are in the browser's
// cache (or failed), with a time limit so a slow image never blocks the page.
export function preloadImages(urls: (string | null | undefined)[], timeoutMs = 2500): Promise<void> {
  const list = urls.filter((url): url is string => Boolean(url));
  if (list.length === 0) return Promise.resolve();
  return new Promise((resolve) => {
    let left = list.length;
    const timer = setTimeout(resolve, timeoutMs);
    const done = () => {
      if (--left > 0) return;
      clearTimeout(timer);
      resolve();
    };
    for (const url of list) {
      const img = new Image();
      img.onload = img.onerror = done;
      img.src = url;
    }
  });
}
