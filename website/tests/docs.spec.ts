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
  await page.locator('.pagefind-ui__result-link').filter({ hasText: 'Copy and paste' }).first().click();
  await expect(page).toHaveURL(/\/dotfiles\/reference\/zellij\/copy-paste\//);
  await expect(page.getByRole('heading', { name: 'Select text from scrollback', exact: true })).toBeVisible();
  await expect(page.locator('main')).toContainText('Ctrl-f p reads the dedicated session buffer.');
  await expect(page.locator('main')).toContainText('The terminal’s paste shortcut remains the path from the system clipboard.');
  await expect(page.getByRole('link', { name: 'Edit page' })).toHaveAttribute('href', 'https://github.com/lanej/dotfiles/edit/master/docs/zellij/copy-paste.mdx');
  await page.goto('./reference/zellij/');
  await page.locator('main').getByRole('link', { name: 'keybinding map', exact: true }).first().click();
  await expect(page).toHaveURL(/\/dotfiles\/reference\/zellij-keybinds\//);
  await expect(page.getByRole('heading', { name: 'Everyday keys', exact: true })).toBeVisible();
  await page.getByRole('link', { name: /Equalize the focused pane/ }).click();
  await expect(page).toHaveURL(/\/dotfiles\/reference\/zellij\/equalize\//);
  await expect(page.locator('main')).toContainText('Ctrl-f =');

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

test('browse Zellij features and use the mobile keybinding map', async ({ page }) => {
  await page.goto('./reference/zellij/');
  const main = page.locator('main');
  await main.getByRole('link', { name: 'Notifications and history', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Notifications and history', exact: true })).toBeVisible();
  const image = page.getByRole('img', { name: 'Notification history beside the source pane’s current contents' });
  await image.scrollIntoViewIfNeeded();
  await expect.poll(() => image.evaluate((img: HTMLImageElement) => img.naturalWidth)).toBeGreaterThan(0);
  await page.setViewportSize({ width: 390, height: 844 });
  const commandExample = page.locator('main pre').first();
  await commandExample.focus();
  await expect(commandExample).toBeFocused();
  await commandExample.press('ArrowRight');
  await expect.poll(() => commandExample.evaluate((element) => element.scrollLeft)).toBeGreaterThan(0);
  await page.goto('./reference/zellij-keybinds/');
  await expect(page.getByRole('heading', { name: 'Zellij keybinding map', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole('button', { name: 'Menu', exact: true }).click();
  const sidebar = page.locator('#starlight__sidebar');
  await expect(sidebar.getByText('Zellij', { exact: true })).toBeVisible();
  await sidebar.getByText('Text and attention', { exact: true }).click();
  await sidebar.getByRole('link', { name: 'Copy and paste', exact: true }).click();
  await expect(page).toHaveURL(/\/reference\/zellij\/copy-paste\//);
  await expect(page.getByRole('heading', { name: 'Copy and paste', exact: true })).toBeVisible();
});

test('Zellij feature links, images, and retained overview anchors resolve locally', async ({ page, request, baseURL }) => {
  test.setTimeout(90_000);
  await page.goto('./reference/zellij/');
  const featureLinks = await page.locator('main a[href*="/reference/zellij/"]').evaluateAll((links) =>
    [...new Set(links.map((link) => (link as HTMLAnchorElement).href).filter((href) => !href.includes('#')))]);
  expect(featureLinks).toHaveLength(18);
  for (const url of featureLinks) {
    await page.goto(url);
    await expect(page.locator('main h1')).toBeVisible();
    const editLink = page.getByRole('link', { name: 'Edit page' });
    await expect(editLink).toHaveAttribute('href', /github\.com\/lanej\/dotfiles\/edit\/master\/docs\/zellij\/.*\.mdx$/);
    const targets = await page.locator('main a[href], main img[src]').evaluateAll((elements) =>
      elements.map((element) => element instanceof HTMLAnchorElement ? element.href : (element as HTMLImageElement).src));
    for (const target of new Set(targets)) {
      const destination = new URL(target);
      if (destination.origin !== new URL(baseURL!).origin) continue;
      const response = await request.get(destination.href);
      expect(response.ok(), destination.href).toBe(true);
      if (destination.hash) {
        await page.goto(destination.href);
        expect(await page.evaluate((hash) => !!document.getElementById(decodeURIComponent(hash.slice(1))), destination.hash), destination.href).toBe(true);
      }
    }
  }
  await page.goto('./reference/zellij/');
  for (const id of ['start-a-session', 'familiar-keys', 'smart-pane-navigation', 'equalize-layout', 'shared-popup-and-session-shutdown', 'forwarded-ssh-agents', 'keyboard-selection-and-paste', 'native-agent-status-and-attention', 'inbox-notices-and-history', 'history-and-recovery', 'differences-that-remain']) {
    await expect(page.locator(`[id="${id}"]`)).toHaveCount(1);
  }
  const maintenance = await request.get('./reference/zellij-maintenance/');
  expect(maintenance.status()).toBe(404);
});
