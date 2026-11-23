import { constants } from "node:fs";
import { access, stat } from "node:fs/promises";
import { delimiter, isAbsolute, join } from "node:path";
import { configPath, type DriverConfig } from "./config.ts";

export type Integration = keyof DriverConfig["integrations"];

export async function integrationStatus(
  config: DriverConfig,
  name: Integration,
) {
  const { enabled, executable } = config.integrations[name];
  const candidates = isAbsolute(executable)
    ? [executable]
    : (process.env["PATH"] ?? "")
        .split(delimiter)
        .filter((path) => path.length > 0)
        .map((path) => join(path, executable));
  let resolved: string | undefined;
  for (const candidate of candidates) {
    try {
      await access(candidate, constants.X_OK);
      if (!(await stat(candidate)).isFile()) continue;
      resolved = candidate;
      break;
    } catch {
      // Presence checks never launch a tool or provision an integration.
    }
  }
  const present = resolved !== undefined;
  return {
    enabled,
    present,
    available: enabled && present,
    executable: resolved ?? executable,
    reason: !enabled
      ? `Enable integrations.${name}.enabled in ${configPath()} to use this integration`
      : !present
        ? `Install ${executable} or configure integrations.${name}.executable`
        : "Available",
  };
}

export async function inspectIntegrations(config: DriverConfig) {
  const [zellij, worktrees, octo] = await Promise.all([
    integrationStatus(config, "zellij"),
    integrationStatus(config, "worktrees"),
    integrationStatus(config, "octo"),
  ]);
  return { zellij, worktrees, octo };
}

export async function requireIntegration(
  config: DriverConfig,
  name: Integration,
): Promise<string> {
  const status = await integrationStatus(config, name);
  if (!status.available) throw new Error(`${name}: ${status.reason}`);
  return status.executable;
}
