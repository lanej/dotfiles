import { parse } from "smol-toml";
import { existsSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { homedir } from "node:os";
import { extname, isAbsolute, join } from "node:path";
import { z } from "zod";

export enum DriverProfile {
  Work = "work",
  Personal = "personal",
}
export const driverProfileSchema = z.enum(DriverProfile);

export enum AgentRole {
  Lead = "lead",
  Worker = "worker",
  Reviewer = "reviewer",
  Explorer = "explorer",
}

export enum DefaultProvider {
  BedrockMantle = "bedrock-mantle",
  ChatGPTSubscription = "openai-codex",
}

export enum ReasoningLevel {
  Off = "off",
  Minimal = "minimal",
  Low = "low",
  Medium = "medium",
  High = "high",
  ExtraHigh = "xhigh",
}
export function knownProvider(value: string): DefaultProvider | undefined {
  const parsed = z.enum(DefaultProvider).safeParse(value);
  return parsed.success ? parsed.data : undefined;
}

export const selection = z
  .object({
    provider: z.string().min(1),
    model: z.string().min(1),
    reasoning: z.enum(ReasoningLevel),
  })
  .strict();
const profile = z
  .object({
    [AgentRole.Lead]: selection,
    [AgentRole.Worker]: selection,
    [AgentRole.Reviewer]: selection,
    [AgentRole.Explorer]: selection,
  })
  .strict();
const optionalIntegration = (executable: string) =>
  z
    .object({
      enabled: z.boolean().default(false),
      executable: z
        .string()
        .min(1)
        .refine(
          (value) => !value.includes("/") || isAbsolute(value),
          "Use an executable name or absolute path",
        )
        .default(executable),
    })
    .strict()
    .prefault({});
export const defaultMinSplitColumns = 40;

export const configSchema = z
  .object({
    integrations: z
      .object({
        zellij: optionalIntegration("zellij"),
        worktrees: optionalIntegration("worktree"),
        octo: optionalIntegration("octo-manager"),
      })
      .strict()
      .prefault({}),
    display: z
      .strictObject({
        min_split_columns: z
          .number()
          .int()
          .positive()
          .default(defaultMinSplitColumns),
        inline_diagnostics: z.boolean().default(true),
        added_background: z
          .string()
          .regex(/^#[0-9a-f]{6}$/iu)
          .optional(),
        removed_background: z
          .string()
          .regex(/^#[0-9a-f]{6}$/iu)
          .optional(),
      })
      .default({
        min_split_columns: defaultMinSplitColumns,
        inline_diagnostics: true,
      }),
    lsp: z
      .object({ enabled: z.boolean().default(true) })
      .strict()
      .default({ enabled: true }),
    delegation: z
      .object({ enabled: z.boolean().default(false) })
      .strict()
      .default({ enabled: false }),
    archives: z
      .object({
        database: z
          .string()
          .refine(isAbsolute, "Use an absolute archive database path")
          .optional(),
      })
      .strict()
      .default({}),
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
    beadsService: z
      .object({
        url: z.url(),
        projectId: z.uuid(),
        reviewOnly: z.boolean().optional(),
        tokenFile: z
          .string()
          .refine(isAbsolute, "Use an absolute token-file path")
          .optional(),
      })
      .strict()
      .optional(),
    profiles: z
      .object({
        [DriverProfile.Work]: profile.optional(),
        [DriverProfile.Personal]: profile.optional(),
      })
      .strict()
      .default({}),
  })
  .strict();
export type DriverConfig = z.infer<typeof configSchema>;

export function configPath(): string {
  const explicit = process.env["PI_DRIVER_CONFIG"];
  if (explicit !== undefined) return explicit;
  const directory = join(
    process.env["XDG_CONFIG_HOME"] ?? join(homedir(), ".config"),
    "pi-driver",
  );
  const toml = join(directory, "config.toml");
  const json = join(directory, "config.json");
  return existsSync(toml) || !existsSync(json) ? toml : json;
}

export async function loadConfig(path = configPath()): Promise<DriverConfig> {
  try {
    const contents = await readFile(path, "utf8");
    return configSchema.parse(
      extname(path) === ".toml" ? parse(contents) : JSON.parse(contents),
    );
  } catch (error) {
    if (
      z.object({ code: z.literal("ENOENT") }).safeParse(error).success &&
      path === configPath() &&
      process.env["PI_DRIVER_CONFIG"] === undefined
    ) {
      return configSchema.parse({});
    }
    throw new Error(
      `Cannot load Pi driver configuration ${path}: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
}

const roles = (provider: string, prefix: string) => ({
  [AgentRole.Lead]: {
    provider,
    model: `${prefix}gpt-6.1-sol`,
    reasoning: ReasoningLevel.High,
  },
  [AgentRole.Worker]: {
    provider,
    model: `${prefix}gpt-6.1-sol`,
    reasoning: ReasoningLevel.Medium,
  },
  [AgentRole.Reviewer]: {
    provider,
    model: `${prefix}gpt-6.1-sol`,
    reasoning: ReasoningLevel.Medium,
  },
  [AgentRole.Explorer]: {
    provider,
    model: `${prefix}gpt-6.1-sol`,
    reasoning: ReasoningLevel.Low,
  },
});

export const exampleConfig = {
  display: {
    min_split_columns: defaultMinSplitColumns,
    inline_diagnostics: true,
  },
  lsp: { enabled: true },
  integrations: {
    zellij: { enabled: true, executable: "zellij" },
    worktrees: { enabled: true, executable: "worktree" },
    octo: { enabled: true, executable: "octo-manager" },
  },
  delegation: { enabled: false },
  idleCompaction: { enabled: true, idleMs: 300_000, minimumContextPercent: 60 },
  beadsService: {
    url: "http://127.0.0.1:8790",
    projectId: "11111111-1111-4111-8111-111111111111",
  },
  profiles: {
    [DriverProfile.Work]: roles(DefaultProvider.BedrockMantle, "openai."),
    [DriverProfile.Personal]: roles(DefaultProvider.ChatGPTSubscription, ""),
  },
};
