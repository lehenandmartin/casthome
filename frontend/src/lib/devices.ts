import type { IconName } from './icons';
import { isIOS } from './browserPlayer';
import { t } from './i18n';

/** What a Cast device is: a group, its model, or a speaker / TV. */
export function deviceDetail(type: string, model: string): string {
  if (type === 'group') return t('devices.group');
  return model || (type === 'audio' ? t('devices.speaker') : t('devices.tv'));
}

export function deviceIcon(type: string | null | undefined): IconName {
  switch (type) {
    case 'browser':
      return isIOS || /Android/.test(navigator.userAgent) ? 'phone' : 'laptop';
    case 'group':
      return 'speakers';
    case 'audio':
      return 'speaker';
    case 'cast':
      return 'tv';
    default:
      return 'cast';
  }
}
