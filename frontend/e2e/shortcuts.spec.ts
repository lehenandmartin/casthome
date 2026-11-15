// Keyboard shortcuts on a desktop, and the interface in another language.

import { expect, test } from '@playwright/test';
import { playButton, setUp, signIn } from './helpers';

test.beforeAll(async ({ request }) => setUp(request));

test('Space plays and pauses, / opens the search', async ({ page, isMobile }) => {
  test.skip(isMobile, 'keyboard shortcuts are for computers');
  await signIn(page);

  await page.getByRole('link', { name: /Fake Album/ }).first().click();
  await page.getByRole('main').getByRole('button', { name: 'Play', exact: true }).click();
  await playButton(page, 'Pause');

  // The Play button keeps the focus after the click: Space pauses, it does not click it again.
  await page.keyboard.press('Space');
  await playButton(page, 'Play');
  await page.keyboard.press('Space');
  await playButton(page, 'Pause');

  // "/" opens the search with the field focused, and is not typed into it.
  await page.keyboard.press('/');
  await expect(page).toHaveURL(/#\/search/);
  const field = page.getByRole('searchbox');
  await expect(field).toBeFocused();
  await expect(field).toHaveValue('');

  // While typing, Space and / are just characters.
  await page.keyboard.type('song /');
  await expect(field).toHaveValue('song /');
  await playButton(page, 'Pause');
});

for (const [language, queue, play] of [
  ['de', 'Warteschlange', 'Abspielen'],
  ['es', 'Cola', 'Reproducir'],
] as const) {
  test(`interface in ${language}`, async ({ page, isMobile }) => {
    test.skip(isMobile, 'once is enough');
    await signIn(page);
    await page.evaluate((lang) => localStorage.setItem('casthome.language', lang), language);
    await page.reload();
    await expect(page.locator('html')).toHaveAttribute('lang', language);
    await expect(page.getByRole('button', { name: new RegExp(`^${queue}`) }).first()).toBeVisible();
    await page.getByRole('link', { name: /Fake Album/ }).first().click();
    await expect(page.getByRole('main').getByRole('button', { name: play, exact: true })).toBeVisible();
  });
}
