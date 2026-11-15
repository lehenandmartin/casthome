// Accessibility: axe-core checks (contrast, ARIA roles and names, labels) on
// the main screens, in light and dark, on a phone and on a desktop.

import AxeBuilder from '@axe-core/playwright';
import { writeFileSync } from 'node:fs';
import { expect, test, type Page } from '@playwright/test';
import { setUp, signIn } from './helpers';

test.beforeAll(async ({ request }) => setUp(request));

async function check(page: Page, screen: string) {
  // Let fades and skeletons settle.
  await page.waitForTimeout(400);
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
  const found = results.violations.map((v) => ({
    screen,
    rule: v.id,
    impact: v.impact,
    help: v.help,
    nodes: v.nodes.map((n) => `${n.target.join(' ')} — ${n.failureSummary?.split('\n').slice(1, 2).join('')}`),
  }));
  return found;
}

for (const scheme of ['light', 'dark'] as const) {
  test(`main screens pass axe (${scheme})`, async ({ page, isMobile }, info) => {
    await page.emulateMedia({ colorScheme: scheme });
    await signIn(page);
    const found = [];

    found.push(...(await check(page, 'home')));

    await page.goto('/#/albums');
    found.push(...(await check(page, 'albums')));

    await page.goto('/#/artists');
    found.push(...(await check(page, 'artists')));

    await page.goto('/#/artist/ar1');
    found.push(...(await check(page, 'artist')));

    await page.goto('/#/search');
    await page.getByRole('searchbox').fill('song');
    await expect(page.getByRole('main').getByText('Song One')).toBeVisible();
    found.push(...(await check(page, 'search')));

    await page.goto('/#/settings');
    found.push(...(await check(page, 'settings')));

    await page.goto('/#/album/al1');
    await expect(page.getByRole('heading', { name: 'Fake Album' })).toBeVisible();
    found.push(...(await check(page, 'album')));

    await page.getByRole('main').getByRole('button', { name: 'Play', exact: true }).click();
    await expect(page.getByRole('contentinfo').getByRole('button', { name: 'Pause' }).filter({ visible: true })).toBeVisible();
    found.push(...(await check(page, 'album playing')));

    if (isMobile) {
      await page.getByRole('button', { name: 'Open the player' }).first().click();
      found.push(...(await check(page, 'now playing')));
      await page.getByRole('button', { name: 'Queue', exact: true }).click();
    } else {
      await page.getByRole('button', { name: /^Queue/ }).first().click();
    }
    await expect(page.getByText('Next from: Fake Album')).toBeVisible();
    found.push(...(await check(page, 'queue')));

    // Action menu, as the menu key or Shift+F10 opens it (headless Chromium
    // does not turn those keys into the event): no position, Shift held.
    const queue = page.getByRole(isMobile ? 'dialog' : 'region', { name: 'Queue' });
    if (!isMobile) {
      const row = queue.getByRole('button', { name: /Song Two/ });
      await row.focus();
      await row.dispatchEvent('contextmenu', { bubbles: true, cancelable: true, clientX: 0, clientY: 0, shiftKey: true });
      await expect(page.getByRole('menuitem').first()).toBeFocused();
      found.push(...(await check(page, 'action menu')));
      await page.keyboard.press('Escape');
    }

    // Confirmation dialog: clear the queue.
    await queue.getByRole('button', { name: 'More actions' }).click();
    await page.getByRole('menuitem', { name: 'Clear everything' }).click();
    await expect(page.getByRole('dialog', { name: 'Clear everything' })).toBeVisible();
    found.push(...(await check(page, 'confirm dialog')));
    await page.keyboard.press('Escape');
    if (isMobile) await page.keyboard.press('Escape');

    // Device picker.
    await page.getByRole('button', { name: /^Play on/ }).filter({ visible: true }).first().click();
    await expect(page.getByRole('dialog', { name: 'Play on' })).toBeVisible();
    found.push(...(await check(page, 'device picker')));

    if (process.env.AXE_REPORT) writeFileSync(`${process.env.AXE_REPORT}/${info.project.name}-${scheme}.json`, JSON.stringify(found, null, 2));
    expect(found, JSON.stringify(found, null, 2)).toEqual([]);
  });
}
