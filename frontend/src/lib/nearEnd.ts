// Svelte action: call `onNear` when the element comes within ~1200 px of the
// bottom of the screen, e.g. to load a list's next page before the end is
// reached. The element (a "Load more" button) stays as a fallback.
export function nearEnd(node: HTMLElement, onNear: () => void) {
  let callback = onNear;
  const observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((e) => e.isIntersecting)) callback();
    },
    { rootMargin: '0px 0px 1200px 0px' },
  );
  observer.observe(node);
  return {
    update(next: () => void) {
      callback = next;
      // Still in range after a page loaded (short pages): ask again.
      observer.unobserve(node);
      observer.observe(node);
    },
    destroy() {
      observer.disconnect();
    },
  };
}
