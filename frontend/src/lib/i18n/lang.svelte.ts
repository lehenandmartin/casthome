// The interface language: automatic (the browser's) or chosen in Settings.
// Kept per device, like the browser language it defaults to.

export const LANGUAGES = ['en', 'fr', 'de', 'es'] as const;
export type Language = (typeof LANGUAGES)[number];
export type LanguagePref = 'auto' | Language;

const KEY = 'casthome.language';

function readPref(): LanguagePref {
  try {
    const value = localStorage.getItem(KEY);
    return value === 'auto' || (LANGUAGES as readonly string[]).includes(value ?? '') ? (value as LanguagePref) : 'auto';
  } catch {
    return 'auto';
  }
}

/** First of the browser's preferred languages that CastHome has, else English. */
export function browserLanguage(): Language {
  const preferred = navigator.languages?.length ? navigator.languages : [navigator.language];
  for (const tag of preferred) {
    const base = tag.toLowerCase().split('-')[0];
    if ((LANGUAGES as readonly string[]).includes(base)) return base as Language;
  }
  return 'en';
}

export const languageState = $state({ pref: readPref() });

/** The language in use (reactive: reading it in a template re-renders on change). */
export function currentLanguage(): Language {
  return languageState.pref === 'auto' ? browserLanguage() : languageState.pref;
}

export function setLanguage(pref: LanguagePref): void {
  languageState.pref = pref;
  try {
    localStorage.setItem(KEY, pref);
  } catch {
    /* storage unavailable: applies to this visit only */
  }
  document.documentElement.lang = currentLanguage();
}

document.documentElement.lang = currentLanguage();
