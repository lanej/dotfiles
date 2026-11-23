import { integrationStatus, requireIntegration } from "./integrations.ts";
import { randomUUID } from "node:crypto";
import {
  mkdirSync,
  readdirSync,
  readFileSync,
  renameSync,
  writeFileSync,
} from "node:fs";
import { homedir } from "node:os";
import { isAbsolute, join } from "node:path";
import type {
  AgentSession,
  ExtensionAPI,
  ToolDefinition,
} from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { z } from "zod";
import {
  AgentRole,
  DefaultProvider,
  DriverProfile,
  knownProvider,
  loadConfig,
  ReasoningLevel,
} from "./config.ts";
import { processFailure, run } from "./process.ts";

export const delegateTool = "driver_delegate";
const roles = [AgentRole.Explorer, AgentRole.Reviewer] as const;
const roleSchema = z.enum(roles);
const allocation = z.object({
  id: z.string().regex(/^[a-f0-9]{32}$/),
  path: z.string().refine(isAbsolute),
  branch: z.string().min(1),
  agent: z.literal("pi"),
  owner_id: z.string(),
  state: z.literal("active"),
});
enum State {
  Allocating = "allocating",
  Ready = "ready",
  Launching = "launching",
  Complete = "complete",
  Failed = "failed",
  Cancelled = "cancelled",
  Uncertain = "uncertain",
}
const recordSchema = z.object({
  id: z.uuid(),
  parent: z.string(),
  role: roleSchema,
  source: z.string(),
  repository: z.string(),
  model: z.string(),
  reasoning: z.string(),
  state: z.enum(State),
  worktree: allocation.optional(),
  session: z.string().optional(),
  sessionFile: z.string().optional(),
});
type Attempt = z.infer<typeof recordSchema>;

const textResult = (text: string) => ({
  content: [{ type: "text" as const, text }],
  details: undefined,
});
const stateHome = () =>
  join(
    process.env["XDG_STATE_HOME"] ?? join(homedir(), ".local/state"),
    "pi-driver",
  );
const attemptRoot = () => join(stateHome(), "attempts");

function save(attempt: Attempt): void {
  const root = attemptRoot();
  mkdirSync(root, { recursive: true, mode: 0o700 });
  const file = join(root, `${attempt.id}.json`);
  const tmp = `${file}.${randomUUID()}`;
  writeFileSync(tmp, `${JSON.stringify(attempt)}\n`, {
    flag: "wx",
    mode: 0o600,
    flush: true,
  });
  renameSync(tmp, file);
}

function unresolved(attempt: Attempt): boolean {
  return (
    attempt.state === State.Allocating ||
    attempt.state === State.Ready ||
    attempt.state === State.Launching ||
    attempt.state === State.Uncertain
  );
}

function existing(): Attempt[] {
  try {
    return readdirSync(attemptRoot())
      .filter((name) => name.endsWith(".json"))
      .map((name) =>
        recordSchema.parse(
          JSON.parse(readFileSync(join(attemptRoot(), name), "utf8")),
        ),
      );
  } catch (error) {
    if (processFailure(error).code === "ENOENT") return [];
    throw error;
  }
}

export function settledDelegates(
  parent: string,
): { id: string; path: string }[] {
  const attempts = existing().filter((attempt) => attempt.parent === parent);
  if (attempts.some(unresolved))
    throw new Error(
      "Resolve the lead's outstanding delegation before archiving",
    );
  return attempts.flatMap((attempt) =>
    attempt.sessionFile === undefined
      ? []
      : [{ id: attempt.id, path: attempt.sessionFile }],
  );
}

const commit = z.string().regex(/^(?:[0-9a-f]{40}|[0-9a-f]{64})$/);
const createEnvelope = z.object({
  schema_version: z.literal(1),
  command: z.literal("create"),
  result: allocation,
});
const inventory = z.object({
  schema_version: z.literal(1),
  command: z.literal("status"),
  result: z.object({
    tasks: z.array(z.looseObject({ owner_id: z.string().optional() })),
  }),
});

async function allocate(
  attempt: Attempt,
  primary: string,
  executable: string,
): Promise<z.infer<typeof allocation>> {
  let receipt: z.infer<typeof allocation>;
  try {
    receipt = createEnvelope.parse(
      JSON.parse(
        await run(
          executable,
          [
            "create",
            "--agent",
            "pi",
            "--owner-id",
            attempt.id,
            "--base",
            attempt.source,
            "--json",
          ],
          { cwd: attempt.repository, timeout: 90_000 },
        ),
      ),
    ).result;
  } catch {
    // A failed command may have created a protected checkout. Recover identity,
    // but leave admission uncertain because provisioning hooks may have failed.
    const stdout = await run(executable, ["status", "--json"], {
      cwd: attempt.repository,
    }).catch((error: unknown) => processFailure(error).stdout ?? "");
    const scan = inventory.safeParse(
      stdout.length > 0 ? JSON.parse(stdout) : null,
    );
    if (scan.success) {
      const matches = scan.data.result.tasks.filter(
        (task) => task.owner_id === attempt.id,
      );
      const recovered = allocation.safeParse(
        matches.length === 1 ? matches[0] : null,
      );
      if (recovered.success) attempt.worktree = recovered.data;
    }
    throw new Error(
      "Worktree allocation could not be confirmed. Inspect the recorded owner before retrying.",
    );
  }
  if (
    receipt.owner_id !== attempt.id ||
    receipt.path !== join(primary, ".worktrees", `pi-${receipt.id.slice(0, 8)}`)
  )
    throw new Error("Worktree manager returned an unexpected allocation");
  attempt.worktree = receipt;
  const cwd = receipt.path;
  const [head, branch] = await Promise.all([
    run("git", ["rev-parse", "--verify", "HEAD"], { cwd }),
    run("git", ["symbolic-ref", "--short", "HEAD"], { cwd }),
  ]);
  if (head.trim() !== attempt.source || branch.trim() !== receipt.branch)
    throw new Error("Managed checkout identity changed before launch");
  return receipt;
}

async function snapshotTools(
  cwd: string,
  sha: string,
): Promise<ToolDefinition[]> {
  const output = await run("git", ["ls-tree", "-rz", sha], { cwd });
  const blobs = new Map<string, string>();
  for (const entry of output.split("\0")) {
    const match = /^(100644|100755) blob ([a-f0-9]+)\t([\s\S]+)$/.exec(entry);
    if (match?.[2] !== undefined && match[3] !== undefined)
      blobs.set(match[3], match[2]);
  }
  const file = async (path: string) => {
    const oid = blobs.get(path);
    if (oid === undefined)
      throw new Error("Choose a regular file from the committed snapshot");
    const size = Number(
      (await run("git", ["cat-file", "-s", oid], { cwd })).trim(),
    );
    if (!Number.isSafeInteger(size) || size > 256 * 1024)
      throw new Error("File exceeds the 256 KiB inspection limit");
    const content = await run("git", ["cat-file", "blob", oid], { cwd });
    if (content.includes("\0")) throw new Error("Choose a text file");
    return content;
  };
  const query = Type.Object({
    query: Type.String({ minLength: 1, maxLength: 512 }),
  });
  const pathParam = Type.Object({
    path: Type.String({ minLength: 1, maxLength: 4096 }),
  });
  return [
    {
      name: "ls",
      label: "List files",
      description:
        "List the first 200 regular files in the committed snapshot.",
      parameters: Type.Object({}),
      execute: () =>
        Promise.resolve(textResult([...blobs.keys()].slice(0, 200).join("\n"))),
    },
    {
      name: "find",
      label: "Find files",
      description:
        "Find up to 200 paths by literal substring in the committed snapshot.",
      parameters: query,
      execute: (_id, params) => {
        const { query: needle } = queryInput.parse(params);
        return Promise.resolve(
          textResult(
            [...blobs.keys()]
              .filter((path) => path.includes(needle))
              .slice(0, 200)
              .join("\n"),
          ),
        );
      },
    },
    {
      name: "read",
      label: "Read file",
      description:
        "Read a regular file at an exact path from the committed snapshot.",
      parameters: pathParam,
      execute: async (_id, params) =>
        textResult(await file(pathInput.parse(params).path)),
    },
    {
      name: "grep",
      label: "Search file",
      description:
        "Search a single snapshot file for literal text. Returns up to 80 matching lines.",
      parameters: Type.Object({ ...query.properties, ...pathParam.properties }),
      execute: async (_id, params) => {
        const { path, query: needle } = pathInput
          .extend(queryInput.shape)
          .parse(params);
        return textResult(
          (await file(path))
            .split("\n")
            .flatMap((line, index) =>
              line.includes(needle)
                ? [`${String(index + 1)}: ${line.slice(0, 512)}`]
                : [],
            )
            .slice(0, 80)
            .join("\n"),
        );
      },
    },
  ];
}

const queryInput = z.object({ query: z.string().min(1).max(512) });
const pathInput = z.object({ path: z.string().min(1).max(4096) });
const delegateInput = z
  .object({ role: roleSchema, brief: z.string().trim().min(1).max(8000) })
  .strict();

export function registerDelegation(
  pi: ExtensionAPI,
  profile: () => DriverProfile | undefined,
  onChange: () => void,
) {
  const active = new Map<string, AbortController>();
  let enabled = false;

  pi.on("session_start", async () => {
    const activeTools = pi
      .getActiveTools()
      .filter((name) => name !== delegateTool);
    pi.setActiveTools(activeTools);
    enabled = false;
    try {
      const config = await loadConfig();
      enabled =
        config.delegation.enabled &&
        (await integrationStatus(config, "worktrees")).available;
    } catch {
      // The driver's session initializer reports configuration errors.
    }
  });
  pi.on("session_shutdown", () => {
    for (const child of active.values()) child.abort();
  });

  pi.registerTool({
    name: delegateTool,
    label: "Delegate repository inspection",
    description:
      "Ask an Explorer or Reviewer to inspect the committed repository in a managed worktree.",
    exposure: "model-only",
    parameters: Type.Object(
      {
        role: Type.Union([
          Type.Literal(AgentRole.Explorer),
          Type.Literal(AgentRole.Reviewer),
        ]),
        brief: Type.String({ minLength: 1, maxLength: 8000 }),
      },
      { additionalProperties: false },
    ),
    async execute(_call, params, signal, _update, ctx) {
      const { role, brief } = delegateInput.parse(params);
      const config = await loadConfig();
      const managerExecutable = await requireIntegration(config, "worktrees");
      const selected = profile();
      const roles =
        selected === undefined ? undefined : config.profiles[selected];
      const settings = roles?.[role];
      const lead = roles?.[AgentRole.Lead];
      if (
        !enabled ||
        !config.delegation.enabled ||
        settings === undefined ||
        lead === undefined ||
        ctx.model?.provider !== lead.provider ||
        ctx.model.id !== lead.model
      )
        throw new Error(
          "Select an explicit driver profile with delegation enabled",
        );
      if (ctx.sessionManager.getSessionFile() === undefined)
        throw new Error("Delegation requires a persistent lead session");
      if (
        pi
          .getAllTools()
          .some(
            (tool) =>
              tool.name === "Agent" ||
              tool.name === "subagent" ||
              tool.name === "SubagentWorkflow",
          )
      )
        throw new Error(
          "Unload the standalone subagent extension before using managed delegation",
        );
      const model = ctx.modelRegistry.find(settings.provider, settings.model);
      if (
        model?.provider !== settings.provider ||
        model.id !== settings.model ||
        !ctx.modelRegistry.hasConfiguredAuth(model) ||
        (selected === DriverProfile.Personal &&
          knownProvider(model.provider) !==
            DefaultProvider.ChatGPTSubscription) ||
        (selected === DriverProfile.Work &&
          !/^https:\/\/bedrock-mantle\.[a-z0-9-]+\.api\.aws(?:\/|$)/.test(
            model.baseUrl,
          ))
      )
        throw new Error(
          "The configured role model is unavailable in the selected profile",
        );
      const parent = ctx.sessionManager.getSessionId();
      if (
        active.size >= 2 ||
        existing().some(
          (attempt) =>
            attempt.parent === parent &&
            unresolved(attempt) &&
            !active.has(attempt.id),
        )
      )
        throw new Error(
          "Delegation is at capacity or has an unresolved attempt",
        );
      const id = randomUUID();
      const controller = new AbortController();
      active.set(id, controller);
      onChange();
      let attempt: Attempt | undefined;
      let child: AgentSession | undefined;
      try {
        const abort =
          signal === undefined
            ? controller.signal
            : AbortSignal.any([signal, controller.signal]);
        abort.throwIfAborted();
        const runner = await import("./plugin-runner.mjs");
        const [head, listing] = await Promise.all([
          run("git", ["rev-parse", "--verify", "HEAD"], { cwd: ctx.cwd }),
          run("git", ["worktree", "list", "--porcelain", "-z"], {
            cwd: ctx.cwd,
          }),
          run(managerExecutable, ["--version"], { cwd: ctx.cwd }),
        ]);
        const primary = listing.split("\0")[0]?.replace(/^worktree /, "");
        if (primary === undefined || !isAbsolute(primary))
          throw new Error("Cannot identify the primary checkout");
        const source = commit.parse(head.trim());
        abort.throwIfAborted();
        attempt = {
          id,
          parent,
          role,
          source,
          repository: ctx.cwd,
          model: `${model.provider}/${model.id}`,
          reasoning: settings.reasoning,
          state: State.Allocating,
        };
        save(attempt);
        const worktree = await allocate(attempt, primary, managerExecutable);
        const record = attempt;
        record.state = State.Ready;
        save(record);
        const driverTools = await snapshotTools(worktree.path, source);
        abort.throwIfAborted();
        record.state = State.Launching;
        save(record);
        const sessionDir = join(stateHome(), "sessions", id);
        mkdirSync(sessionDir, { recursive: true, mode: 0o700 });
        const result = await runner.runChild(ctx, role, brief, {
          pi,
          cwd: worktree.path,
          configCwd: ctx.cwd,
          model,
          thinkingLevel: settings.reasoning,
          maxTurns: 8,
          signal: abort,
          agentId: id,
          sessionDir,
          driverTools,
          onSessionCreated(session) {
            child = session;
            if (
              session.model?.provider !== model.provider ||
              session.model.id !== model.id ||
              z.enum(ReasoningLevel).safeParse(session.thinkingLevel).data !==
                settings.reasoning
            )
              throw new Error(
                "The child runtime changed the requested model or reasoning level",
              );
            record.session = session.sessionManager.getSessionId();
            const file = session.sessionManager.getSessionFile();
            if (file !== undefined) record.sessionFile = file;
            save(record);
          },
        });
        const cancelled = abort.aborted || result.aborted;
        const failure = result.failure;
        record.state = cancelled
          ? State.Cancelled
          : failure === undefined
            ? State.Complete
            : State.Failed;
        save(record);
        const summary = cancelled
          ? "Child cancelled"
          : (failure ?? result.responseText);
        return {
          ...textResult(summary.slice(0, 16_000)),
          details: {
            id,
            source,
            worktree: worktree.id,
            session: record.session,
            state: record.state,
          },
        };
      } catch (error) {
        if (attempt !== undefined && unresolved(attempt)) {
          attempt.state =
            attempt.state === State.Ready ? State.Failed : State.Uncertain;
          save(attempt);
        }
        throw new Error(`Delegation ${id}: ${processFailure(error).message}`);
      } finally {
        child?.dispose();
        active.delete(id);
        onChange();
      }
    },
  });
  return {
    blocks(parent: string): boolean {
      if (active.size > 0) return true;
      try {
        return existing().some(
          (attempt) => attempt.parent === parent && unresolved(attempt),
        );
      } catch {
        return true;
      }
    },
    activate() {
      if (enabled && !pi.getActiveTools().includes(delegateTool))
        pi.setActiveTools([...pi.getActiveTools(), delegateTool]);
    },
  };
}
