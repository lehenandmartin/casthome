// Volume: CastHome sets it only on Cast devices. Playing in a browser, the
// phone or computer sets it (its buttons, the system volume): no slider, no
// − / + buttons, and the + / − keys do nothing. (The Cast case needs a real
// speaker: see docs/device-checklist.md.)

import { expect, test, type Page } from '@playwright/test';
import { playButton, setUp, signIn } from './helpers';

test.beforeAll(async ({ request }) => setUp(request));

async function playAlbum(page: Page) {
  await signIn(page);
  await page.goto('/#/album/al1');
  await page.getByRole('main').getByRole('button', { name: 'Play', exact: true }).click();
  await playButton(page, 'Pause');
}

test('no volume control when playing in the browser', async ({ page, isMobile }) => {
  await playAlbum(page);
  const volumeControls = page.getByRole('slider', { name: 'Volume' }).or(page.getByRole('button', { name: /^Volume (up|down)$/ }));

  if (isMobile) {
    await page.getByRole('button', { name: 'Open the player' }).first().click();
    await expect(page.getByRole('dialog', { name: 'Now playing' })).toBeVisible();
  } else {
    await page.keyboard.press('+');
    await page.keyboard.press('-');
  }
  await expect(volumeControls).toHaveCount(0);

  const bar = isMobile ? page.getByRole('dialog', { name: 'Now playing' }) : page.getByRole('contentinfo');
  await bar.getByRole('button', { name: /^Play on/ }).filter({ visible: true }).first().click();
  await expect(page.getByRole('dialog', { name: 'Play on' })).toBeVisible();
  await expect(volumeControls).toHaveCount(0);

  // The browser plays at full volume; the keys did not change it.
  const volume = await page.evaluate(() => fetch('/api/state').then((r) => r.json()).then((s) => s.player?.volume));
  expect(volume).toBe(1);
});
