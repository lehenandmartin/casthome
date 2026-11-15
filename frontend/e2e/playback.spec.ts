// The main path, on a phone and on a desktop: set up, open an album, play it
// on "This browser", find the rest of the album in the queue, remove a track,
// skip to the next one.

import { expect, test, type Locator, type Page } from '@playwright/test';

const SUBSONIC = 'http://127.0.0.1:4599';
const PASSWORD = 'letmein';

test.beforeAll(async ({ request }) => {
  // First run: the setup is open to whoever comes first. Once done, sign in.
  const status = await (await request.get('/api/status')).json();
  if (!status.setup_required) return;
  const r = await request.post('/api/setup', {
    data: {
      navidrome: { url: SUBSONIC, public_url: 'http://subsonic.test:4599', username: 'me', password: 'sesame' },
      access: { mode: 'password', password: PASSWORD, remember: true },
    },
  });
  expect(r.ok(), await r.text()).toBeTruthy();
});

async function signIn(page: Page) {
  await page.goto('/');
  await page.getByLabel(/password/i).fill(PASSWORD);
  await page.getByRole('button', { name: /sign in/i }).click();
  await expect(page.getByRole('link', { name: /Fake Album/ }).first()).toBeVisible();
}

/** "This browser" plays: the server only says "playing" once the browser's
 * audio has reported it, and the play button turns into Pause. */
async function playing(page: Page) {
  await expect(page.getByRole('button', { name: 'Pause', exact: true }).first()).toBeVisible();
}

/** A real finger swipe (touch events, which the page sees as touch pointers). */
async function swipeLeft(page: Page, target: Locator) {
  const box = await target.boundingBox();
  if (!box) throw new Error('nothing to swipe');
  const cdp = await page.context().newCDPSession(page);
  const y = box.y + box.height / 2;
  const touch = (type: string, x: number) =>
    cdp.send('Input.dispatchTouchEvent', { type, touchPoints: type === 'touchEnd' ? [] : [{ x, y }] });
  const from = box.x + box.width * 0.8;
  await touch('touchStart', from);
  for (let i = 1; i <= 10; i++) await touch('touchMove', from - (box.width * 0.6 * i) / 10);
  await touch('touchEnd', from - box.width * 0.6);
  await cdp.detach();
}

test('play an album on this browser, then edit the queue', async ({ page, isMobile }) => {
  await signIn(page);
  // The queue lives on the server: start from an empty one.
  expect((await page.request.delete('/api/queue')).ok()).toBeTruthy();
  await page.reload();

  await page.getByRole('link', { name: /Fake Album/ }).first().click();
  await expect(page.getByRole('heading', { name: 'Fake Album' })).toBeVisible();
  await expect(page.getByRole('main').getByText('Song Three')).toBeVisible();

  await page.getByRole('button', { name: 'Play', exact: true }).first().click();
  await playing(page);
  await expect(page.getByRole('contentinfo').getByText('Song One').filter({ visible: true })).toBeVisible();

  // The rest of the album comes next. On a phone the queue opens from the player.
  if (isMobile) {
    await page.getByRole('button', { name: 'Open the player' }).first().click();
    await page.getByRole('button', { name: 'Queue', exact: true }).click();
  } else {
    await page.getByRole('button', { name: /^Queue/ }).first().click();
  }
  const queue = page.getByRole('region', { name: 'Queue' });
  await expect(queue.getByText('Next from: Fake Album')).toBeVisible();
  await expect(queue.getByRole('button', { name: /Song Two/ })).toBeVisible();
  await expect(queue.getByRole('button', { name: /Song Three/ })).toBeVisible();

  // Remove "Song Two" (swipe left on a phone, ✕ on a desktop): "Song Three" is next.
  const row = queue.getByRole('listitem').filter({ hasText: 'Song Two' });
  await expect(row.getByLabel('Drag to reorder')).toBeVisible();
  if (isMobile) {
    await swipeLeft(page, row);
  } else {
    await row.hover();
    await row.getByRole('button', { name: 'Remove from queue' }).click();
  }
  await expect(queue.getByText('Song Two')).toHaveCount(0);

  // Skip ahead: Next on a desktop; on a phone the queue sheet covers the
  // player, so tap the track in the queue.
  if (isMobile) await queue.getByRole('button', { name: /Song Three/ }).click();
  else await page.getByRole('contentinfo').getByRole('button', { name: 'Next', exact: true }).click();
  await expect(queue.getByRole('button', { name: /Song Three/ })).toHaveCount(1);
  await expect(queue.getByText('Now playing').locator('xpath=following-sibling::button[1]')).toContainText('Song Three');
});
