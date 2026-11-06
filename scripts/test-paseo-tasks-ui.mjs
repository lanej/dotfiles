import assert from "node:assert/strict";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const required = name => {
  const value = process.env[name];
  if (!value) throw new Error(`Set ${name} before running the live Tasks UI detector`);
  return value;
};
const overview = new URL(required("PASEO_TASKS_UI_URL"));
const storageState = required("PASEO_TASKS_UI_STATE");
const cases = JSON.parse(await readFile(required("PASEO_TASKS_UI_CASES"), "utf8"));
assert.ok(Array.isArray(cases) && cases.length > 0, "Supply acceptance task addresses");
for (const value of cases) {
  for (const field of ["serverId", "taskId", "workspaceId"]) {
    assert.match(value[field], /^[A-Za-z0-9_-]+$/, `Invalid ${field}`);
  }
  if (value.coordinator) {
    for (const field of ["serverId", "workspaceId", "agentId"]) {
      assert.match(value.coordinator[field], /^[A-Za-z0-9_-]+$/, `Invalid coordinator ${field}`);
    }
  }
}
const output = resolve(required("PASEO_TASKS_UI_OUTPUT"));
await mkdir(output, { recursive: true, mode: 0o700 });
const { chromium } = await import(pathToFileURL(required("PASEO_TASKS_PLAYWRIGHT_MODULE")).href);
const findings = [];
let browser;
try {
  browser = await chromium.launch({
    headless: true,
    args: process.env.PASEO_TASKS_UI_LOCAL_TLS === "1" ? ["--ignore-certificate-errors"] : [],
  });
  for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
    const context = await browser.newContext({ viewport, storageState,
      ...(process.env.PASEO_TASKS_UI_ALLOWED_HOSTS ? { serviceWorkers: "block" } : {}) });
    try {
      await context.grantPermissions(["local-network-access"], { origin: overview.origin });
      if (process.env.PASEO_TASKS_UI_ALLOWED_HOSTS) {
        const allowed = new Set(process.env.PASEO_TASKS_UI_ALLOWED_HOSTS.split(","));
        await context.route("**/*", route => allowed.has(new URL(route.request().url()).hostname) ?
          route.continue() : route.abort());
        await context.routeWebSocket("**/*", socket => allowed.has(new URL(socket.url()).hostname) ?
          socket.connectToServer() : socket.close());
      }
      const page = await context.newPage();
      page.setDefaultTimeout(60000);
      for (const theme of ["light", "dark"]) {
        await page.goto(overview.href);
        await page.evaluate(value => {
          const key = "@paseo:app-settings";
          const current = JSON.parse(localStorage.getItem(key) ?? "{}");
          localStorage.setItem(key, JSON.stringify({ ...current, theme: value }));
        }, theme);
        await page.reload();
        const surface = page.getByTestId("tasks-screen");
        await surface.waitFor();
        await page.getByTestId(`task-card-${cases[0].serverId}-${cases[0].taskId}`)
          .getByRole("button", { name: "Open task conversation", exact: true }).waitFor();
        const prefix = `${viewport.width}-${theme}`;
        await page.screenshot({ path: `${output}/${prefix}-overview.png` });
        for (const value of cases) {
          const card = page.getByTestId(`task-card-${value.serverId}-${value.taskId}`);
          await card.getByRole("button", { name: "Open task conversation", exact: true }).waitFor();
          const geometry = await card.evaluate(element => {
            const rect = element.getBoundingClientRect();
            return {
              x: rect.x, width: rect.width, viewport: innerWidth,
              scrollWidth: element.scrollWidth, clientWidth: element.clientWidth,
              bodyWidth: document.body.scrollWidth,
            };
          });
          assert.ok(geometry.x >= 0 && geometry.x + geometry.width <= geometry.viewport + 1,
            `${prefix}: task ${value.taskId} extends beyond the viewport`);
          assert.ok(geometry.scrollWidth <= geometry.clientWidth + 1 &&
            geometry.bodyWidth <= geometry.viewport + 1,
          `${prefix}: horizontal clipping for task ${value.taskId}`);
          await card.screenshot({ path: `${output}/${prefix}-${value.taskId}.png` });
          await card.getByRole("button", { name: "Select task", exact: true }).click();
          await card.getByRole("button", { name: "Deselect task", exact: true }).waitFor();
          await page.getByRole("button", { name: "Reprioritize", exact: true }).waitFor();
          await card.getByRole("button", { name: "Deselect task", exact: true }).click();
          await card.getByRole("button", { name: "Open task conversation", exact: true }).click();
          await page.waitForURL(url => url.pathname ===
            `/h/${value.serverId}/workspace/${value.workspaceId}`);
          const chat = page.getByTestId("agent-chat-scroll");
          await chat.waitFor();
          const marker = `[task-event:start:${value.taskId}]`;
          const firstPrompt = page.getByTestId("chat-outline-tick-1");
          if (await firstPrompt.isVisible()) await firstPrompt.click();
          for (let attempt = 0; attempt < 30 && !(await chat.innerText()).includes(marker); attempt++) {
            await chat.hover();
            await page.mouse.wheel(0, -100000);
            await page.waitForTimeout(750);
          }
          assert.ok((await chat.innerText()).includes(marker),
            `${prefix}: assigned task ${value.taskId} is absent from the actual conversation history`);
          findings.push({ viewport: viewport.width, theme, ...value, geometry,
            conversationPath: new URL(page.url()).pathname });
          await page.goto(overview.href);
          await surface.waitFor();
          if (value.coordinator) {
            await card.getByRole("button", { name: "Open coordinator conversation", exact: true }).click();
            await page.waitForURL(url => url.pathname ===
              `/h/${value.coordinator.serverId}/workspace/${value.coordinator.workspaceId}`);
            await page.getByTestId("agent-chat-scroll").waitFor();
            await page.waitForFunction(address => {
              const saved = JSON.parse(localStorage.getItem("workspace-layout-state") ?? "null");
              const layout = saved?.state?.layoutByWorkspace?.[`${address.serverId}:${address.workspaceId}`];
              const findFocused = node => {
                if (node?.kind === "pane") return node.pane.id === layout.focusedPaneId ? node.pane : null;
                for (const child of node?.group?.children ?? []) {
                  const found = findFocused(child);
                  if (found) return found;
                }
                return null;
              };
              const pane = findFocused(layout?.root);
              const target = pane?.tabs.find(tab => tab.tabId === pane.focusedTabId)?.target;
              return target?.kind === "agent" && target.agentId === address.agentId;
            }, value.coordinator);
            if (viewport.width === 1440) {
              assert.equal(await page.getByTestId(`workspace-tab-agent_${value.coordinator.agentId}`)
                .getAttribute("aria-selected"), "true");
            }
            await page.goto(overview.href);
            await surface.waitFor();
          }
        }
      }
    } finally {
      await context.close();
    }
  }
  await writeFile(`${output}/results.json`, JSON.stringify({ findings }, null, 2) + "\n", { mode: 0o600 });
  console.log(JSON.stringify({ passed: findings.length, output }));
} finally {
  await browser?.close();
}
