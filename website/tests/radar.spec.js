import { test, expect } from '@playwright/test';

for (const width of [1440, 390]) {
  test(`radar decisions remain reachable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('./reference/radar/');
    const radar = page.getByRole('figure', { name: 'Technology decisions by ring' });
    await expect(radar).toBeVisible();
    await expect(radar.getByRole('region', { name: 'Assess decisions' })).toContainText('No tools here yet.');
    await expect(radar.getByRole('region', { name: 'Adopt decisions' })).toContainText('Kitty');
    await expect(radar.getByRole('region', { name: 'Hold decisions' })).toContainText('Ghostty');
    const points = radar.locator('svg a');
    const headings = await page.locator('main h3').allTextContents();
    expect(await points.count()).toBe(headings.length);
    for (const link of await points.all()) {
      const target = await link.getAttribute('href');
      await expect(page.locator(target)).toHaveCount(1);
      const icon = link.locator('image');
      const legendIcon = radar.locator(`.radar-key a[href="${target}"] img`);
      await expect(legendIcon).toHaveAttribute('src', await icon.getAttribute('href'));
      await expect.poll(() => legendIcon.evaluate((image) => image.naturalWidth)).toBeGreaterThan(0);
      const name = await page.locator(target).textContent();
      expect(await link.getAttribute('aria-label')).toContain(name.trim());
    }
    await points.first().focus();
    await expect(points.first()).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/#kitty$/);
    await page.goto('./reference/macos/');
    await page.getByRole('link', { name: 'radar.md', exact: true }).click();
    await expect(page).toHaveURL(/\/reference\/radar\/$/);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}
