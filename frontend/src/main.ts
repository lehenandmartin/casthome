import { mount } from 'svelte';
import App from './App.svelte';
import './app.css';

export default mount(App, { target: document.getElementById('app')! });

// Installable PWA. Service workers need HTTPS (or localhost); on plain-HTTP LAN
// access this is skipped and "Add to Home Screen" still works on iOS.
if ('serviceWorker' in navigator && window.isSecureContext && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  });
}
