import { test, expect } from '@playwright/test';

test('copy setup instructions and find the Zellij workflow', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('/');
  await page.locator('.expressive-code').first().getByRole('button', { name: 'Copy to clipboard' }).click();
  await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe('git clone https://github.com/lanej/dotfiles.git "$HOME/.files" && cd "$HOME/.files" && make base && make bootstrap');
  await page.getByRole('link', { name: 'Know where things live' }).click();
  await expect(page.getByRole('heading', { name: 'How configuration fits together', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Edit page' })).toHaveAttribute('href', 'https://github.com/lanej/dotfiles/edit/master/docs/architecture.mdx');
  await page.getByRole('button', { name: 'Search' }).click();
  await page.getByPlaceholder('Search', { exact: true }).fill('dedicated session buffer');
  await page.locator('.pagefind-ui__result-link').filter({ hasText: 'Zellij' }).first().click();
  await expect(page).toHaveURL(/\/reference\/zellij\//);
  await expect(page.getByRole('heading', { name: 'Keyboard selection and paste', exact: true })).toBeVisible();
  await expect(page.locator('main')).toContainText('Ctrl-f p reads the dedicated session buffer.');
  await expect(page.locator('main')).toContainText('The terminal’s paste shortcut remains the path from the system clipboard.');
});
