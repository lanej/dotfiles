import { test, expect } from '@playwright/test';

test('inspect native theme examples and follow atomic composition', async ({ page }) => {
  await page.goto('./design-system/');
  await expect(page.getByRole('heading', { name: 'Terminal design system', exact: true })).toBeVisible();
  await expect(page.locator('#theme-roles')).toContainText('Resolved theme roles');
  const headingToken = page.locator('#token-emphasis-heading');
  await page.locator('details').filter({ has: headingToken }).locator('summary').click();
  await headingToken.getByRole('link', { name: 'components', exact: true }).click();
  await expect(page.locator('#component-heading')).toBeVisible();
  const gitToken = page.locator('#token-symbol-git-file-modified');
  await page.locator('details').filter({ has: gitToken }).locator('summary').click();
  await expect(gitToken).toContainText('starship');
  await expect(gitToken).toContainText('string');
  await expect(gitToken).toContainText('None');
  await page.evaluate(() => document.fonts.ready);
  expect(await page.evaluate(() => document.fonts.check('16px "Dotfiles Symbols"', ''))).toBe(true);
  await gitToken.getByRole('link', { name: 'starship', exact: true }).click();
  await expect(page.locator('#integration-starship')).toBeVisible();
  await expect(page.locator('#component-status')).toContainText('Diagnostic*');
  await page.locator('details').filter({ has: page.locator('#component-tab-label') }).locator('summary').click();
  await page.locator('#component-tab-label').getByRole('link', { name: 'status', exact: true }).click();
  await expect(page).toHaveURL(/#component-status$/);
  await expect(page.locator('#component-status').getByRole('link', { name: 'metadata-row', exact: true })).toBeVisible();
  await expect(page.locator('#integration-external-color-owners')).toContainText('interactive audits');
  await page.setViewportSize({ width: 390, height: 844 });
  await gitToken.scrollIntoViewIfNeeded();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.locator('#component-status').scrollIntoViewIfNeeded();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  const source = page.locator('#component-status .sources a');
  await source.focus();
  await expect(source).toBeFocused();
});

test('Nord is documented as a preset with its own palette and native captures', async ({ page }) => {
  await page.goto('./design-system/');
  await page.getByRole('link', { name: 'Nord preset', exact: true }).first().click();
  await expect(page).toHaveURL(/\/design-system\/nord\/$/);
  await expect(page.getByRole('heading', { name: 'Nord preset', exact: true })).toBeVisible();
  await expect(page.locator('#preset-palette')).toBeVisible();
  const examples = page.locator('main img');
  await expect(examples).toHaveCount(7);
  for (const example of await examples.all()) {
    await example.scrollIntoViewIfNeeded();
    await expect.poll(() => example.evaluate((image: HTMLImageElement) => image.naturalWidth)).toBeGreaterThan(0);
    await expect(example).toHaveAttribute('src', /\/presets\/nord\//);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator('#preset-palette').scrollIntoViewIfNeeded();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
