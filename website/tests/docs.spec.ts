import { test, expect } from '@playwright/test';

test('copy setup instructions and find the Zellij workflow', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('./');
  await expect(page).toHaveURL(/\/dotfiles\/$/);
  await expect(page.getByRole('link', { name: 'Back to lanej.io open source' })).toHaveAttribute('href', 'https://lanej.io/open-source/#dotfiles');
  await expect(page.getByRole('link', { name: 'Set up a machine', exact: true })).toHaveAttribute('href', '/dotfiles/reference/install/');
  await page.locator('.expressive-code').first().getByRole('button', { name: 'Copy to clipboard' }).click();
  await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe('curl -fsSL https://raw.githubusercontent.com/lanej/dotfiles/master/install.sh | sh');
  await page.getByRole('link', { name: 'Know where things live' }).click();
  await expect(page).toHaveURL(/\/dotfiles\/architecture\//);
  await expect(page.getByRole('heading', { name: 'How configuration fits together', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Edit page' })).toHaveAttribute('href', 'https://github.com/lanej/dotfiles/edit/master/docs/architecture.mdx');
  await page.getByRole('button', { name: 'Search' }).click();
  await page.getByPlaceholder('Search', { exact: true }).fill('dedicated session buffer');
  await page.locator('.pagefind-ui__result-link').filter({ hasText: 'Zellij' }).first().click();
  await expect(page).toHaveURL(/\/dotfiles\/reference\/zellij\//);
  await expect(page.getByRole('heading', { name: 'Keyboard selection and paste', exact: true })).toBeVisible();
  const terminalImage = page.getByRole('img', { name: 'Zellij with the Nord top tab bar and split terminal panes' });
  await terminalImage.scrollIntoViewIfNeeded();
  await expect.poll(() => terminalImage.evaluate((image: HTMLImageElement) => image.naturalWidth)).toBeGreaterThan(0);
  await expect(page.locator('main')).toContainText('Ctrl-f p reads the dedicated session buffer.');
  await expect(page.locator('main')).toContainText('The terminal’s paste shortcut remains the path from the system clipboard.');
});
