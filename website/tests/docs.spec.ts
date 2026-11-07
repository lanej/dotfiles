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
  await expect(page.locator('main')).toContainText('Ctrl-f p or Ctrl-f ] reads the dedicated session buffer.');
  await expect(page.locator('main')).toContainText('The terminal’s paste shortcut remains the path from the system clipboard.');
  await page.getByRole('link', { name: 'Zellij keybindings reference', exact: true }).click();
  await expect(page).toHaveURL(/\/dotfiles\/reference\/zellij-keybinds\//);
  await expect(page.getByRole('heading', { name: 'Everyday keys', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Edit page' })).toHaveAttribute('href', 'https://github.com/lanej/dotfiles/edit/master/docs/zellij-keybinds.mdx');
  await page.getByText('Resize and layout controls', { exact: true }).click();
  await expect(page.getByText('Modern prefix = balances an aligned pane group in place; g applies the golden-ratio width guard and cap, and G bypasses the guard.', { exact: true })).toBeVisible();
});

test('review Go style defaults and gradual adoption on desktop and mobile', async ({ page }) => {
  await page.goto('./reference/go-style/');
  await expect(page.getByRole('heading', { name: 'Go style guide', exact: true })).toBeVisible();
  await expect(page.getByRole('row', { name: /cuddle-max-statements 1/ })).toBeVisible();
  await expect(page.getByRole('row', { name: /branch-max-lines 2/ })).toBeVisible();
  await expect(page.getByRole('link', { name: 'lint profile', exact: true })).toHaveAttribute('href', 'https://github.com/lanej/dotfiles/blob/master/ai/skills/go/assets/golangci.yml');
  await expect(page.locator('main')).toContainText('A new file has no allowance.');
  await expect(page.locator('main')).toContainText('not proof of individual defect identity');
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('heading', { name: 'Go style guide', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole('link', { name: 'repository bootstrap guide', exact: true }).click();
  await expect(page).toHaveURL(/\/dotfiles\/reference\/repository-bootstrap\//);
  await expect(page.locator('main')).toContainText('repo-bootstrap --repo ~/src/service --go-retrofit');
});
