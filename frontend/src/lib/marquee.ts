// Text too long for its line scrolls by like on a dot-matrix display: it jumps
// one column of dots at a time instead of gliding. It waits, steps to its end,
// waits, then starts again. Text that fits stays still. With reduced motion it
// does not move and ends with "…" instead.
//
// Doto draws every character on a grid of dots 0.1em apart, so one column is
// 0.1em of the text's font size. The line is clipped on a whole column too, so
// no half dot shows at its edge.
//
// Use on the line (overflow hidden, one line); the text is its first child.
// The parameter is the text itself, so a new track restarts the scroll.

const COLUMNS_PER_SECOND = 18;
const HOLD = 1600; // ms at each end

export function marquee(line: HTMLElement, _text?: string) {
  let animation: Animation | null = null;

  function start() {
    animation?.cancel();
    animation = null;
    line.classList.remove('scrolling');
    line.style.clipPath = '';
    const text = line.firstElementChild as HTMLElement | null;
    if (!text || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const overflow = text.scrollWidth - line.clientWidth;
    if (overflow <= 1) return;

    const pitch = parseFloat(getComputedStyle(text).fontSize) * 0.1;
    const visible = Math.floor(line.clientWidth / pitch) * pitch;
    const steps = Math.ceil((text.scrollWidth - visible) / pitch);
    const shift = -steps * pitch;
    line.classList.add('scrolling');
    line.style.clipPath = `inset(0 ${line.clientWidth - visible}px 0 0)`;

    const duration = (steps / COLUMNS_PER_SECOND) * 1000 + HOLD * 2;
    const hold = HOLD / duration;
    animation = text.animate(
      [
        { transform: 'translateX(0)', offset: 0 },
        // One jump per column of dots between the two holds.
        { transform: 'translateX(0)', offset: hold, easing: `steps(${steps}, end)` },
        { transform: `translateX(${shift}px)`, offset: 1 - hold },
        { transform: `translateX(${shift}px)`, offset: 1 },
      ],
      { duration, iterations: Infinity },
    );
  }

  const resize = new ResizeObserver(() => start());
  resize.observe(line);
  // Widths change once the display font has loaded.
  document.fonts?.ready.then(() => start());

  return {
    update() {
      // Wait for the new text to be in the page.
      requestAnimationFrame(start);
    },
    destroy() {
      resize.disconnect();
      animation?.cancel();
    },
  };
}
