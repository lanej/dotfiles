import { test, expect } from '@playwright/test';

test('find the Zellij copy workflow from the documentation home', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Search' }).click();
  await page.getByPlaceholder('Search', { exact: true }).fill('dedicated session buffer');
  await page.locator('.pagefind-ui__result-link').filter({ hasText: 'Zellij' }).first().click();
  await expect(page).toHaveURL(/\/reference\/zellij\//);
  await expect(page.getByRole('heading', { name: 'Keyboard selection and paste', exact: true })).toBeVisible();
  await expect(page.locator('main')).toContainText('Ctrl-f p reads the dedicated session buffer.');
  await expect(page.locator('main')).toContainText('The terminal’s paste shortcut remains the path from the system clipboard.');
});
