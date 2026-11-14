// Exit transitions (Svelte `out:`) matching the entry animations in app.css and
// the components, so sheets, menus, dialogs and toasts leave the way they came
// instead of vanishing. Use them with `|global`: most of these elements are
// removed together with their component.
import type { TransitionConfig } from 'svelte/transition';

const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
const easeIn = (t: number) => t * t;

/** Fade out (backdrops, toasts, dialogs, popover menus). */
export function fadeOut(_node: Element, { duration = 140 }: { duration?: number } = {}): TransitionConfig {
  return { duration: reduced() ? 0 : duration, easing: easeIn, css: (t) => `opacity: ${t}` };
}

/** Fade in (toasts, dialogs: they had no entry animation). */
export function fadeIn(_node: Element, { duration = 160 }: { duration?: number } = {}): TransitionConfig {
  return { duration: reduced() ? 0 : duration, css: (t) => `opacity: ${t}` };
}

/**
 * A sheet going away: back down on phones (it rose from the bottom), a fade
 * for the centred panel on wide screens and for menus opened at the pointer.
 */
export function sheetOut(node: Element): TransitionConfig {
  if (reduced()) return { duration: 0 };
  // A menu opened at the pointer has the `popover` class (read from the node:
  // the menu's data is already gone when it closes).
  if (node.classList.contains('popover') || matchMedia('(min-width: 720px)').matches) {
    return fadeOut(node, { duration: 120 });
  }
  return {
    duration: 180,
    easing: easeIn,
    css: (t, u) => `transform: translateY(${u * 40}px); opacity: ${t}`,
  };
}

/** The mobile queue sheet: back down (it rose by 12%). */
export function riseOut(_node: Element): TransitionConfig {
  if (reduced()) return { duration: 0 };
  return { duration: 180, easing: easeIn, css: (t, u) => `transform: translateY(${u * 12}%); opacity: ${t}` };
}

/** The desktop queue panel: back to the right (it slid in by 24 px). */
export function slideOutRight(_node: Element): TransitionConfig {
  if (reduced()) return { duration: 0 };
  return { duration: 160, easing: easeIn, css: (t, u) => `transform: translateX(${u * 24}px); opacity: ${t}` };
}
