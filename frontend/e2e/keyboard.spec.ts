// Using CastHome with the keyboard alone, on a desktop.

import { expect, test } from '@playwright/test';
import { setUp, signIn } from './helpers';

test.beforeAll(async ({ request }) => setUp(request));
test.beforeEach(({ isMobile }) => test.skip(isMobile, 'keyboard navigation is checked on a desktop'));

test('Tab first reaches "Skip to content", which moves to the page', async ({ page }) => {
  await signIn(page);
  await page.keyboard.press('Tab');
  const skip = page.getByRole('button', { name: 'Skip to content' });
  await expect(skip).toBeFocused();
  await expect(skip).toBeInViewport();
  await page.keyboard.press('Enter');
  await expect(page.locator('main')).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.locator('main')).toContainText(await page.evaluate(() => (document.activeElement as HTMLElement).innerText));
});

test('reorder the queue with the keyboard, with spoken feedback', async ({ page }) => {
  await signIn(page);
  await page.goto('/#/album/al1');
  await page.getByRole('main').getByRole('button', { name: 'Play', exact: true }).click();
  await page.getByRole('button', { name: /^Queue/ }).first().click();
  const upcoming = page.getByRole('list', { name: 'Next from: Fake Album' });
  await expect(upcoming.getByRole('listitem')).toHaveCount(2);

  await upcoming.getByRole('listitem').first().getByRole('button', { name: 'Drag to reorder' }).focus();
  await page.keyboard.press('Space'); // pick up "Song Two" (and not play/pause)
  await expect(page.locator('#dnd-action-aria-alert')).toContainText('Picked up Song Two');
  await page.keyboard.press('ArrowDown');
  await expect(page.locator('#dnd-action-aria-alert')).toContainText('Song Two, Fake Artist: position 2 of 2 in Next from: Fake Album');
  await page.keyboard.press('Space'); // drop it after "Song Three"
  await expect(page.locator('#dnd-action-aria-alert')).toContainText('Dropped Song Two');
  await expect(page.getByRole('contentinfo').getByRole('button', { name: 'Pause' }).filter({ visible: true })).toBeVisible();
  await expect(upcoming.getByRole('listitem')).toHaveText([/Song Three/, /Song Two/]);
  // The queue keeps following the server after a keyboard drag: a track added
  // elsewhere shows up.
  expect((await page.request.post('/api/queue', { data: { song_ids: ['s1'], mode: 'queue', replace: false } })).ok()).toBeTruthy();
  await expect(page.getByRole('list', { name: 'Next in queue' }).getByRole('listitem')).toHaveText([/Song One/]);
  // The order is the server's, not only on screen.
  await page.reload();
  await page.getByRole('button', { name: /^Queue/ }).first().click();
  await expect(page.getByRole('list', { name: 'Next from: Fake Album' }).getByRole('listitem')).toHaveText([/Song Three/, /Song Two/]);
});

test('dialogs keep the focus inside, and give it back when closed', async ({ page }) => {
  await signIn(page);
  const opener = page.getByRole('contentinfo').getByRole('button', { name: /^Play on/ }).filter({ visible: true });
  await opener.focus();
  await page.keyboard.press('Enter');
  const picker = page.getByRole('dialog', { name: 'Play on' });
  await expect(picker).toBeVisible();
  await expect(picker.locator(':focus')).toHaveCount(1);
  for (let i = 0; i < 6; i++) {
    await page.keyboard.press('Tab');
    await expect(picker.locator(':focus')).toHaveCount(1);
  }
  await page.keyboard.press('Shift+Tab');
  await expect(picker.locator(':focus')).toHaveCount(1);
  await page.keyboard.press('Escape');
  await expect(picker).toHaveCount(0);
  await expect(opener).toBeFocused();
});
