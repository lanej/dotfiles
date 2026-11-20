import { readFile } from "node:fs/promises";
import { homedir } from "node:os";
import { isAbsolute, join } from "node:path";
import { z } from "zod";

const selection = z
  .object({
    provider: z.string().min(1),
    model: z.string().min(1),
    reasoning: z.enum(["off", "minimal", "low", "medium", "high", "xhigh"]),
  })
  .strict();
const profile = z
  .object({
    lead: selection,
    worker: selection,
    reviewer: selection,
    explorer: selection,
  })
  .strict();
export const configSchema = z
  .object({
    idleCompaction: z
      .object({
        enabled: z.boolean().default(true),
        idleMs: z.number().int().min(1000).max(86_400_000).default(300_000),
        minimumContextPercent: z.number().min(1).max(100).default(60),
      })
      .strict()
      .default({ enabled: true, idleMs: 300_000, minimumContextPercent: 60 }),
    beads: z
      .object({
        workspace: z
          .string()
          .refine(isAbsolute, "Use an absolute Beads workspace path"),
        database: z.string().min(1),
        branch: z.string().min(1),
        executable: z.string().min(1).default("bd"),
      })
      .strict()
      .optional(),
    profiles: z
      .object({ work: profile.optional(), personal: profile.optional() })
      .strict()
      .default({}),
  })
  .strict();
export type DriverConfig = z.infer<typeof configSchema>;

export function configPath(): string {
  return (
    process.env.PI_DRIVER_CONFIG ??
    join(
      process.env.XDG_CONFIG_HOME ?? join(homedir(), ".config"),
      "pi-driver/config.json",
    )
  );
}

export async function loadConfig(path = configPath()): Promise<DriverConfig> {
  try {
    return configSchema.parse(JSON.parse(await readFile(path, "utf8")));
  } catch (error) {
    if (
      (error as NodeJS.ErrnoException).code === "ENOENT" &&
      path === configPath() &&
      !process.env.PI_DRIVER_CONFIG
    ) {
      return configSchema.parse({});
    }
    throw new Error(
      `Cannot load Pi driver configuration ${path}: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
}

const roles = (provider: string, prefix: string) => ({
  lead: { provider, model: `${prefix}gpt-6.1-sol`, reasoning: "high" },
  worker: { provider, model: `${prefix}gpt-6.1-sol`, reasoning: "medium" },
  reviewer: { provider, model: `${prefix}gpt-6.1-sol`, reasoning: "medium" },
  explorer: { provider, model: `${prefix}gpt-6.1-terra`, reasoning: "low" },
});

export const exampleConfig = {
  idleCompaction: { enabled: true, idleMs: 300_000, minimumContextPercent: 60 },
  beads: {
    workspace: "/absolute/path/to/authoritative-workspace",
    database: "YOUR_DATABASE",
    branch: "main",
    executable: "bd",
  },
  profiles: {
    work: roles("bedrock-mantle", "openai."),
    personal: roles("openai-codex", ""),
  },
};
