export default async function ({ page, context, checkpoint }) {
  const serverId = process.env.PASEO_TASKS_UI_SERVER_ID;
  if (!serverId) throw new Error("Set PASEO_TASKS_UI_SERVER_ID to the connected overview host");
  const origin = new URL(page.url()).origin;
  await context.grantPermissions(["local-network-access"], { origin });
  await page.evaluate(theme => {
    const key = "@paseo:app-settings";
    const settings = JSON.parse(localStorage.getItem(key) ?? "{}");
    localStorage.setItem(key, JSON.stringify({ ...settings, theme }));
  }, checkpoint.name);
  await page.goto(`${origin}/h/${encodeURIComponent(serverId)}/plugin/tasks/surface/tasks`, { waitUntil: "load" });
  await page.locator("[data-testid='tasks-screen'] [aria-label='Open task conversation']").first().waitFor({ state: "visible" });
}
