// Light or dark: automatic (the system's) or chosen in Settings. Kept per
// device, like the language. The root carries data-theme, which app.css reads;
// index.html sets it once before the first paint, this keeps it up to date.

export type ThemePref = 'auto' | 'light' | 'dark';

const KEY = 'casthome.theme';
const COLORS = { light: '#f3f3f0', dark: '#131413' }; // --bg, for the browser's bars
const system = matchMedia('(prefers-color-scheme: dark)');

function readPref(): ThemePref {
  try {
    const value = localStorage.getItem(KEY);
    return value === 'light' || value === 'dark' ? value : 'auto';
  } catch {
    return 'auto';
  }
}

export const themeState = $state({ pref: readPref() });

function apply(): void {
  const theme = themeState.pref === 'auto' ? (system.matches ? 'dark' : 'light') : themeState.pref;
  document.documentElement.dataset.theme = theme;
  document.querySelector<HTMLMetaElement>('meta[name="theme-color"]')?.setAttribute('content', COLORS[theme]);
}

export function setTheme(pref: ThemePref): void {
  themeState.pref = pref;
  try {
    localStorage.setItem(KEY, pref);
  } catch {
    /* storage unavailable: applies to this visit only */
  }
  apply();
}

// Automatic follows the system when it changes.
system.addEventListener('change', () => {
  if (themeState.pref === 'auto') apply();
});
apply();
