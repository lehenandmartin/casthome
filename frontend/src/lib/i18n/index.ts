import { en, type MessageKey } from './en';

const locales: Record<string, Partial<Record<MessageKey, string>>> = { en };
const active = locales[navigator.language.split('-')[0]] ?? en;

export function t(key: MessageKey, params: Record<string, unknown> = {}): string {
  const template = active[key] ?? en[key] ?? key;
  return template.replace(/\{(\w+)\}/g, (_, name: string) => String(params[name] ?? ''));
}

/** Translate a backend error/notification code. */
export function tCode(code: string, params: Record<string, unknown> = {}): string {
  const key = `error.${code}` as MessageKey;
  return key in en ? t(key, params) : t('error.unknown');
}
