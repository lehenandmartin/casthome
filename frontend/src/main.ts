import { mount } from 'svelte';
import App from './App.svelte';
import './app.css';
import { reportErrors } from './lib/errorReport';
import { watchIntent } from './lib/intent';
import { fadeInCovers } from './lib/fade';

reportErrors();

// Missing cover art: swap in a neutral disc instead of the browser's broken-image icon.
const PLACEHOLDER =
  'data:image/svg+xml,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><g fill="none" stroke="#9a948c" stroke-opacity=".45" stroke-width="2"><circle cx="24" cy="24" r="12"/><circle cx="24" cy="24" r="3"/></g></svg>',
  );
document.addEventListener(
  'error',
  (event) => {
    const img = event.target;
    if (img instanceof HTMLImageElement && img.src !== PLACEHOLDER) img.src = PLACEHOLDER;
  },
  true,
);

export default mount(App, { target: document.getElementById('app')! });

watchIntent();
fadeInCovers();

// Installable PWA. Service workers need HTTPS (or localhost); on plain-HTTP LAN
// access this is skipped and "Add to Home Screen" still works on iOS.
if ('serviceWorker' in navigator && window.isSecureContext && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  });
}
