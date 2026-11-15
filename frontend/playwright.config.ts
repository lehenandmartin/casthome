import { existsSync } from 'node:fs';
import { defineConfig, devices } from '@playwright/test';

// End-to-end tests: the real backend serving the built interface (run
// `npm run build` first), against a fake Subsonic server. No Cast device is
// needed: the tests play on "This browser".
//
// The Cast URL cannot be a loopback address, so the fake server is announced to
// the browser as subsonic.test, which Chromium resolves to 127.0.0.1.

const CASTHOME_PORT = 4588;
const SUBSONIC_PORT = 4599;
const python = process.env.E2E_PYTHON ?? (existsSync('../.venv/bin/python') ? '../.venv/bin/python' : 'python3');

export default defineConfig({
  testDir: 'e2e',
  fullyParallel: false,
  workers: 1, // one CastHome, one queue
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['list']] : 'list',
  use: {
    baseURL: `http://127.0.0.1:${CASTHOME_PORT}`,
    locale: 'en-US',
    serviceWorkers: 'block',
    trace: 'retain-on-failure',
    launchOptions: {
      args: [
        `--host-resolver-rules=MAP subsonic.test 127.0.0.1`,
        '--autoplay-policy=no-user-gesture-required',
      ],
    },
  },
  projects: [
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: [
    {
      command: `${python} e2e/fake_subsonic.py ${SUBSONIC_PORT}`,
      url: `http://127.0.0.1:${SUBSONIC_PORT}/rest/ping`,
      reuseExistingServer: false,
    },
    {
      // A fresh data folder each run: CastHome starts at its first-run setup.
      command: `rm -rf e2e/.data && ${python} -m casthome.main`,
      url: `http://127.0.0.1:${CASTHOME_PORT}/api/health`,
      reuseExistingServer: false,
      env: {
        HOST: '127.0.0.1',
        PORT: String(CASTHOME_PORT),
        DATA_DIR: 'e2e/.data',
        FRONTEND_DIST: 'dist',
        LOG_LEVEL: 'WARNING',
      },
    },
  ],
});
