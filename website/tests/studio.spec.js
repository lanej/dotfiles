import { test, expect } from '@playwright/test';

for (const width of [1440, 390]) {
  test(`Studio workflow is discoverable and readable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('./');
    await page.locator('main').getByRole('link', { name: 'The Studio toolchain', exact: true }).click();
    await expect(page).toHaveURL(/\/studio\/$/);
    await expect(page.locator('main h1')).toHaveText('The Studio toolchain');

    const workflow = page.getByRole('region', { name: 'How the Studio tools work together' });
    await expect(workflow).toBeVisible();
    for (const name of ['Studio', 'Producer', 'Stagehand', 'Copydesk', 'Publisher']) {
      await expect(workflow.getByText(name, { exact: true })).toBeVisible();
    }
    await expect(workflow).toHaveCSS('background-color', 'rgb(13, 21, 19)');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await expect(page.getByRole('link', { name: 'Edit page' })).toHaveAttribute(
      'href', 'https://github.com/lanej/dotfiles/edit/master/docs/studio-toolchain.mdx',
    );
  });
}
