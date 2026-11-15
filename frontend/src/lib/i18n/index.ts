import { en, type MessageKey } from './en';
import { de } from './de';
import { es } from './es';
import { fr } from './fr';
import { currentLanguage, type Language } from './lang.svelte';

export { LANGUAGES, browserLanguage, currentLanguage, languageState, setLanguage, type LanguagePref } from './lang.svelte';

const locales: Record<Language, Record<MessageKey, string>> = { en, fr, de, es };

/** Translate a UI string. Reactive: re-renders when the language changes. */
export function t(key: MessageKey, params: Record<string, unknown> = {}): string {
  const template = locales[currentLanguage()][key] ?? en[key] ?? key;
  return template.replace(/\{(\w+)\}/g, (_, name: string) => String(params[name] ?? ''));
}

/** Translate a backend error/notification code. */
export function tCode(code: string, params: Record<string, unknown> = {}): string {
  const key = `error.${code}` as MessageKey;
  return key in en ? t(key, params) : t('error.unknown');
}
