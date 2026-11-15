// Shared by the end-to-end tests.

import { expect, type Page, type APIRequestContext } from '@playwright/test';

const SUBSONIC = 'http://127.0.0.1:4599';
export const PASSWORD = 'letmein';

/** First run: the setup is open to whoever comes first (done once per run). */
export async function setUp(request: APIRequestContext) {
  const status = await (await request.get('/api/status')).json();
  if (!status.setup_required) return;
  const r = await request.post('/api/setup', {
    data: {
      navidrome: { url: SUBSONIC, public_url: 'http://subsonic.test:4599', username: 'me', password: 'sesame' },
      access: { mode: 'password', password: PASSWORD, remember: true },
    },
  });
  expect(r.ok(), await r.text()).toBeTruthy();
}

/** Sign in, then start from an empty queue (it lives on the server). */
export async function signIn(page: Page) {
  await page.goto('/');
  await page.getByLabel(/password/i).fill(PASSWORD);
  await page.getByRole('button', { name: /sign in/i }).click();
  await expect(page.getByRole('link', { name: /Fake Album/ }).first()).toBeVisible();
  expect((await page.request.delete('/api/queue')).ok()).toBeTruthy();
  await page.reload();
}

/** The play/pause button of the player bar shows `label` ("Play" or "Pause"). */
export async function playButton(page: Page, label: 'Play' | 'Pause') {
  await expect(page.getByRole('contentinfo').getByRole('button', { name: label, exact: true }).filter({ visible: true })).toBeVisible();
}
