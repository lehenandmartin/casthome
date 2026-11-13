import { t } from './i18n';

/** Short human label for a session, e.g. "Safari on iPhone". Best effort only. */
export function describeUserAgent(ua: string): string {
  if (!ua) return t('sessions.unknownDevice');
  const browser =
    /Edg\//.test(ua) ? 'Edge'
    : /Firefox\/|FxiOS/.test(ua) ? 'Firefox'
    : /Chrome\/|CriOS/.test(ua) ? 'Chrome'
    : /Safari\//.test(ua) ? 'Safari'
    : null;
  const os =
    /iPhone/.test(ua) ? 'iPhone'
    : /iPad/.test(ua) ? 'iPad'
    : /Android/.test(ua) ? 'Android'
    : /Mac OS X|Macintosh/.test(ua) ? 'macOS'
    : /Windows/.test(ua) ? 'Windows'
    : /Linux/.test(ua) ? 'Linux'
    : null;
  if (browser && os) return t('sessions.browserOn', { browser, os });
  return browser ?? os ?? ua.slice(0, 40);
}
