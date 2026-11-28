import { test, expect } from '@playwright/test';

test('look up generated theme tokens and compare presets on a narrow screen', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('./design-system/');
  await page.getByRole('link', { name: 'token reference', exact: true }).last().click();
  await expect(page.getByRole('heading', { name: 'Theme token reference' })).toBeVisible();
  await expect(page.locator('[aria-labelledby="palette-sage"]')).toContainText('Default preset');

  const search = page.getByRole('searchbox', { name: 'Find a token or color' });
  await search.fill('syntax.string');
  const role = page.locator('[id="color-roles-syntax.string"]');
  await expect(role.getByRole('cell').locator('code')).toHaveText(['#B7CB91', '#A3BE8C']);
  await expect(page.locator('[aria-labelledby="palettes"]')).toBeHidden();

  await search.fill('access.approved');
  const state = page.locator('[id="semantic-states-access.approved"]');
  await expect(state).toContainText('ASCII');
  await expect(state.getByLabel('Octicon ').first()).toBeVisible();
  await state.getByRole('link', { name: '@accent', exact: true }).click();
  await expect(search).toHaveValue('');
  await expect(page.locator('[id="color-roles-accent"]')).toBeInViewport();
  await search.fill('access.approved');
  await state.getByRole('link', { name: '@accent', exact: true }).click();
  await expect(search).toHaveValue('');
  await expect(page.locator('[id="color-roles-accent"]')).toBeInViewport();

  await search.fill('symbol.git.summary.branch');
  await expect(page.locator('[id="presentation-tokens-symbol.git.summary.branch"]')).toContainText('');
  await search.fill('statusline.mode.fill');
  const mode = page.locator('[id="presentation-tokens-statusline.mode.fill"]');
  const [sage, nord] = await mode.getByRole('cell').all();
  await expect(mode.getByRole('rowheader')).toContainText('statusline.mode.fill');
  await expect(sage).toContainText('Sage');
  await expect(nord).toContainText('Nord');
  await expect(sage.getByText('NORMAL')).toHaveCSS('background-color', 'rgb(23, 35, 30)');
  await expect(nord.getByText('NORMAL')).toHaveCSS('background-color', 'rgb(136, 192, 208)');
  await expect(sage.locator('.literal')).toContainText('false');
  await expect(sage.locator('.literal')).toHaveCSS('color', 'rgb(196, 178, 217)');
  await expect(sage.locator('.setting-mark')).toHaveText('○');
  await expect(nord.locator('.setting-mark')).toHaveText('●');
  await search.fill('U+F467');
  const diagnostic = page.locator('[id="presentation-tokens-symbol.diagnostic.error"]');
  const error = diagnostic.getByRole('cell').first();
  await expect(error.getByText('Error', { exact: true })).toHaveCSS('color', 'rgb(241, 140, 150)');
  await expect(error.locator('.glyph')).toHaveCSS('font-family', /Dotfiles Symbols/);
  await expect(error).toContainText('U+F467');
  await search.fill('no-such-token');
  await expect(page.getByText('No matching tokens or colors.')).toBeVisible();
  await page.getByRole('button', { name: 'Clear' }).click();
  await expect(search).toBeFocused();
  await expect(page.locator('[aria-labelledby="palettes"]')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
});

test('inspect native theme examples and follow atomic composition', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('./design-system/');
  await expect(page.getByRole('heading', { name: 'Terminal design system', exact: true })).toBeVisible();
  await expect(page.locator('#theme-roles')).toContainText('Resolved theme roles');
  await expect(page.locator('section[aria-labelledby="theme-roles"] strong')).toHaveText('sage');
  const visibleGitStyle = page.locator('#git-style-git-file-modified');
  await expect(visibleGitStyle).toBeVisible();
  const dimPreview = page.locator('#git-style-git-file-stashed .token-value');
  await expect(dimPreview).toHaveCSS('color', 'rgb(154, 162, 158)');
  await expect(dimPreview).toHaveCSS('opacity', '1');
  const headingToken = page.locator('#token-emphasis-heading');
  await page.locator('details').filter({ has: headingToken }).locator('summary').click();
  await headingToken.getByRole('link', { name: 'components', exact: true }).click();
  await expect(page.locator('#component-heading')).toBeVisible();
  const gitToken = page.locator('#token-symbol-git-file-modified');
  await page.locator('details').filter({ has: gitToken }).locator('summary').click();
  await expect(gitToken).toContainText('starship');
  await expect(gitToken).toContainText('string');
  await expect(gitToken).toContainText('symbol.diff.change');
  await expect(gitToken).toContainText('U+F459');
  await expect(gitToken).toContainText('ASCII');
  const peerTokens = page.locator('details').filter({ has: gitToken }).locator('.token');
  expect((await peerTokens.nth(0).boundingBox())?.y).toBe((await peerTokens.nth(1).boundingBox())?.y);
  expect(await page.evaluate(async () => (await document.fonts.load('16px "Dotfiles Symbols"', '')).length)).toBeGreaterThan(0);
  await gitToken.getByRole('link', { name: 'components', exact: true }).click();
  const gitStyle = page.locator('#git-style-git-file-modified');
  await expect(gitStyle).toBeVisible();
  await expect(gitStyle).toContainText('@git.file.modified');
  await gitStyle.getByRole('link', { name: 'starship', exact: true }).click();
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

test('Sage compares the default preset with Nord', async ({ page }) => {
  await page.goto('./design-system/');
  await page.getByRole('link', { name: 'Sage preset', exact: true }).first().click();
  await expect(page).toHaveURL(/\/design-system\/sage\/$/);
  await expect(page.getByRole('heading', { name: 'Sage preset', exact: true })).toBeVisible();
  await expect(page.locator('section[aria-labelledby="preset-palette"]')).toContainText('#ACC8B7');
  const sage = page.locator('[data-preset-preview="sage"]');
  const nord = page.locator('[data-preset-preview="nord"]');
  await expect(sage).toHaveCSS('background-color', 'rgb(13, 21, 19)');
  await expect(sage.locator('.tabs')).toHaveCSS('background-color', 'rgb(23, 35, 30)');
  await expect(sage.locator('.selected')).toHaveCSS('background-color', 'rgb(38, 53, 45)');
  await expect(nord).toHaveCSS('background-color', 'rgb(46, 52, 64)');
  await expect(sage.getByText('Failed', { exact: true })).toHaveCSS('color', 'rgb(241, 140, 150)');
  await expect(sage.locator('.tab-error')).toHaveCSS('color', 'rgb(241, 140, 150)');
  await expect(sage.locator('.tab-error')).toHaveCSS('background-color', 'rgb(13, 21, 19)');
  await expect(sage.locator('.selected')).toHaveCSS('box-shadow', 'rgb(172, 200, 183) 3px 0px 0px 0px inset');
  await page.setViewportSize({ width: 390, height: 844 });
  await sage.scrollIntoViewIfNeeded();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('Sage exposes all semantic token families with distinct meanings', async ({ page }) => {
  await page.goto('./design-system/sage/');
  const catalog = page.locator('[data-semantic-catalog="sage"]');
  await expect(catalog.locator('[data-semantic-family]')).toHaveCount(8);
  await expect(catalog.locator('[data-semantic-state]')).toHaveCount(39);
  for (const [id, color] of [
    ['configuration.on', 'rgb(172, 200, 183)'],
    ['configuration.off', 'rgb(144, 159, 149)'],
    ['severity.trace', 'rgb(144, 159, 149)'],
    ['severity.debug', 'rgb(163, 177, 167)'],
    ['severity.info', 'rgb(140, 197, 204)'],
    ['severity.warning', 'rgb(232, 200, 139)'],
    ['severity.error', 'rgb(241, 140, 150)'],
    ['execution.input', 'rgb(221, 167, 131)'],
    ['execution.succeeded', 'rgb(166, 205, 130)'],
    ['health.unknown', 'rgb(163, 177, 167)'],
    ['execution.paused', 'rgb(163, 177, 167)'],
    ['execution.retrying', 'rgb(232, 200, 139)'],
    ['execution.skipped', 'rgb(144, 159, 149)'],
    ['interaction.focused', 'rgb(196, 178, 217)'],
    ['interaction.selected', 'rgb(172, 200, 183)'],
    ['interaction.disabled', 'rgb(144, 159, 149)'],
    ['connectivity.connecting', 'rgb(140, 197, 204)'],
    ['connectivity.connected', 'rgb(143, 185, 168)'],
    ['connectivity.disconnected', 'rgb(144, 159, 149)'],
    ['connectivity.reconnecting', 'rgb(232, 200, 139)'],
    ['connectivity.lost', 'rgb(241, 140, 150)'],
    ['data.fresh', 'rgb(143, 185, 168)'],
    ['data.stale', 'rgb(232, 200, 139)'],
    ['data.missing', 'rgb(163, 177, 167)'],
    ['data.invalid', 'rgb(241, 140, 150)'],
    ['access.readwrite', 'rgb(172, 200, 183)'],
    ['access.readonly', 'rgb(163, 177, 167)'],
    ['access.approval', 'rgb(221, 167, 131)'],
    ['access.approved', 'rgb(172, 200, 183)'],
    ['access.denied', 'rgb(241, 140, 150)'],
  ]) {
    await expect(catalog.locator(`[data-semantic-state="${id}"] .state-label`)).toHaveCSS('color', color);
  }
  await expect(catalog.locator('[data-semantic-state="severity.fatal"] .state-label')).toHaveCSS('font-weight', '700');
  await expect(catalog.locator('[data-semantic-state="access.approval"] .state-label')).toHaveCSS('font-weight', '700');
  await expect(catalog.locator('[data-semantic-state="access.approved"] .glyph')).toHaveText('✓');
  await expect(catalog.getByText('connectivity.connected', { exact: true })).toBeVisible();
  await expect(catalog.locator('[data-semantic-state="connectivity.connecting"] .glyph')).toHaveText('◐');
  await expect(catalog.locator('[data-semantic-state="configuration.off"]')).toHaveCSS('box-shadow', 'rgb(172, 200, 183) 3px 0px 0px 0px inset');
  await page.setViewportSize({ width: 390, height: 844 });
  await catalog.scrollIntoViewIfNeeded();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
