import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// In development the backend runs on :4577; Vite proxies the API and the WebSocket.
export default defineConfig({
  plugins: [svelte()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:4577', ws: true, changeOrigin: false },
    },
  },
});
