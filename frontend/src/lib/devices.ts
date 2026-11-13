import type { IconName } from './icons';
import { isIOS } from './browserPlayer';

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
