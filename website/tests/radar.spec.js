import { test, expect } from '@playwright/test';

for (const width of [1440, 390]) {
  test(`radar decisions remain reachable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('./');
    await expect(page.locator('.navigation-card .destination-icon')).toHaveCount(5);
    await page.locator('main').getByRole('link', { name: 'Tech radar', exact: true }).click();
    await expect(page).toHaveURL(/\/reference\/radar\/$/);
    const radar = page.getByRole('figure', { name: 'Technology decisions by ring' });
    await expect(radar).toBeVisible();
    await expect(page.getByRole('link', { name: 'Edit page' })).toHaveAttribute('href', 'https://github.com/lanej/dotfiles/edit/master/docs/radar.yaml');
    await expect(radar.getByRole('region', { name: 'Assess decisions' })).toContainText('AeroSpace');
    await expect(radar.getByRole('region', { name: 'Trial decisions' })).not.toContainText('AeroSpace');
    await expect(radar.getByRole('region', { name: 'Trial decisions' })).toContainText('Viewrule');
    await expect(radar.getByRole('region', { name: 'Adopt decisions' })).toContainText('Kitty');
    await expect(radar.getByRole('region', { name: 'Hold decisions' })).toContainText('Ghostty');
    await expect(radar.getByRole('region', { name: 'Hold decisions' })).toContainText('Firstmate');
    await expect(radar.getByRole('region', { name: 'Trial decisions' })).not.toContainText('Firstmate');
    const points = radar.locator('svg a');
    const headings = await page.locator('main h3').allTextContents();
    expect(await points.count()).toBe(headings.length);
    for (const link of await points.all()) {
      const target = await link.getAttribute('href');
      await expect(page.locator(target)).toHaveCount(1);
      const icon = link.locator('image');
      const legendIcon = radar.locator(`.radar-key a[href="${target}"] img`);
      await expect(legendIcon).toHaveAttribute('src', await icon.getAttribute('href'));
      const headingIcon = page.locator(target).locator('img');
      await expect(headingIcon).toHaveAttribute('src', await icon.getAttribute('href'));
      await expect(headingIcon).toHaveAttribute('alt', '');
      await expect.poll(() => headingIcon.evaluate((image) => image.naturalWidth)).toBeGreaterThan(0);
      await expect.poll(() => legendIcon.evaluate((image) => image.naturalWidth)).toBeGreaterThan(0);
      const name = await page.locator(target).textContent();
      expect(await link.getAttribute('aria-label')).toContain(name.trim());
    }
    const kitty = radar.locator('svg a[href="#kitty"]');
    await kitty.focus();
    await expect(kitty).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/#kitty$/);
    await page.goto('./reference/macos/');
    await page.getByRole('link', { name: 'radar.md', exact: true }).click();
    await expect(page).toHaveURL(/\/reference\/radar\/$/);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}
