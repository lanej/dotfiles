import { defineConfig } from '@playwright/test';
import { base } from './site.config.mjs';
const previewURL = `http://127.0.0.1:4321${base}/`;
export default defineConfig({
  testDir: './tests',
  use: {
    baseURL: previewURL,
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH },
  },
  webServer: {
    // Keep Astro in the foreground so Playwright owns the server lifecycle.
    command: 'npm run preview -- --port 4321 --ignore-lock',
    url: previewURL,
    reuseExistingServer: !process.env.CI,
  },
});
