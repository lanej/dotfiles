import { registerDiagnosticRendering } from "./rendering.ts";
import type { DiagnosticSnapshot } from "./diagnostics.ts";
import { resolve } from "node:path";
import type {
  ExtensionAPI,
  ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import {
  getAgentDir,
  ProjectTrustStore,
} from "@earendil-works/pi-coding-agent";
import { readFile, realpath } from "node:fs/promises";
import { Type } from "typebox";
import { z } from "zod";
import {
  defaultMinSplitColumns,
  loadConfig,
  type DriverConfig,
} from "../config.ts";
import { CodeIntelligence, Lookup } from "./service.ts";

export const lspTool = "driver_lsp";
export const renameTool = "driver_lsp_rename";
const location = {
  path: Type.String({
    description:
      "File in the active checkout; also selects the server for workspace queries",
  }),
  line: Type.Optional(Type.Integer({ minimum: 1 })),
  column: Type.Optional(
    Type.Integer({ minimum: 1, description: "One-based UTF-16 column" }),
  ),
};
function result(value: unknown, isError = false) {
  const serialized = JSON.stringify(value, null, 2);
  return {
    content: [
      {
        type: "text" as const,
        text:
          serialized.length > 24_000
            ? `${serialized.slice(0, 24_000)}\n[truncated; narrow the query]`
            : serialized,
      },
    ],
    details: {},
    isError,
  };
}
const message = (error: unknown) =>
  error instanceof Error ? error.message : String(error);

export function registerCodeIntelligence(pi: ExtensionAPI): CodeIntelligence {
  const intelligence = new CodeIntelligence();
  let diffDisplay: DriverConfig["display"] = {
    min_split_columns: defaultMinSplitColumns,
    inline_diagnostics: true,
  };
  const display = registerDiagnosticRendering(
    pi,
    intelligence,
    () => diffDisplay,
  );
  const renameCalls = new Set<string>();
  let approvedProject: string | undefined;
  let lifecycle = 0;
  const approved = async (ctx: ExtensionContext): Promise<boolean> => {
    if (!ctx.isProjectTrusted()) return false;
    const root = await realpath(ctx.cwd);
    return (
      approvedProject === root ||
      new ProjectTrustStore(getAgentDir()).get(root) === true
    );
  };
  const requireTrust = async (ctx: ExtensionContext): Promise<void> => {
    if (await approved(ctx)) return;
    approvedProject = undefined;
    await intelligence.stop();
    throw new Error(
      "LSP requires explicit project trust before starting language servers. Use /lsp-trust to approve execution for this session, or record trust through Pi's normal trust flow.",
    );
  };
  pi.registerCommand("lsp-trust", {
    description:
      "Approve language-server execution for this project in this session",
    handler: async (_argument, ctx) => {
      if (await approved(ctx)) {
        ctx.ui.notify(
          "Language-server execution is already approved for this project",
          "info",
        );
        return;
      }
      if (!ctx.isProjectTrusted()) {
        ctx.ui.notify(
          "Approve the project through Pi's normal trust flow first, then use /lsp-trust",
          "warning",
        );
        return;
      }
      const generation = lifecycle;
      const root = await realpath(ctx.cwd);
      const allowed = await ctx.ui.confirm(
        "Allow language-server execution?",
        `${root}\n\nLanguage servers can execute project code, including Rust build scripts and proc macros. Allow this for the current session?`,
      );
      if (
        !allowed ||
        generation !== lifecycle ||
        !ctx.isProjectTrusted() ||
        (await realpath(ctx.cwd)) !== root
      )
        return;
      approvedProject = root;
      ctx.ui.notify(
        "Language-server execution approved for this project in this session",
        "info",
      );
    },
  });
  pi.on("session_start", async () => {
    lifecycle++;
    approvedProject = undefined;
    await intelligence.stop();
    const config = await loadConfig();
    intelligence.enabled = config.lsp.enabled;
    diffDisplay = config.display;
  });
  pi.on("session_shutdown", async () => {
    lifecycle++;
    approvedProject = undefined;
    await intelligence.stop();
  });
  pi.on("before_agent_start", (event) => ({
    systemPrompt: `${event.systemPrompt}\nWhen LSP is available, prefer driver_lsp for definitions, references, implementations and types of known symbols. Use text search for discovery and textual dependencies. Diagnostics marked pending or unversioned do not establish a clean file. Preview semantic renames with driver_lsp_rename, inspect the proposed changes, then apply the preview token.`,
  }));
  pi.registerTool({
    name: lspTool,
    label: "Code intelligence",
    description:
      "Query an installed language server. Read-only semantic navigation and diagnostics for Go, Rust and TypeScript/JavaScript. Positions use one-based lines and UTF-16 columns. Missing servers are reported explicitly; use text search when unavailable.",
    parameters: Type.Object({
      action: Type.Enum(Lookup),
      ...location,
      query: Type.Optional(Type.String()),
    }),
    async execute(_id, args, signal, _update, ctx) {
      try {
        return await intelligence.serial(async () => {
          await requireTrust(ctx);
          return result(
            await intelligence.lookup(
              ctx.cwd,
              args.action,
              args.path,
              args.line ?? 1,
              args.column ?? 1,
              args.query ?? "",
              signal,
            ),
          );
        });
      } catch (error) {
        return result({ error: message(error) }, true);
      }
    },
  });
  pi.registerTool({
    name: renameTool,
    label: "Semantic rename",
    description:
      "Preview or apply an LSP semantic rename. Preview returns unified diffs and a five-minute token. Inspect the proposal before applying. Apply rechecks originals and uses Pi write tools and their authorization hooks; partial failures return recovery evidence. File resource operations are unsupported.",
    parameters: Type.Union([
      Type.Object({
        action: Type.Literal("preview"),
        ...location,
        newName: Type.String({ minLength: 1 }),
      }),
      Type.Object({
        action: Type.Literal("apply"),
        token: Type.String({ minLength: 1 }),
      }),
    ]),
    async execute(_id, args, signal, _update, ctx) {
      try {
        return await intelligence.serial(async () => {
          await requireTrust(ctx);
          if (args.action === "preview")
            return result(
              intelligence.describe(
                await intelligence.preview(
                  ctx.cwd,
                  args.path,
                  args.line ?? 1,
                  args.column ?? 1,
                  args.newName,
                  signal,
                ),
              ),
            );
          const preview = await intelligence.consume(ctx.cwd, args.token);
          pi.appendEntry("pi-driver:rename-recovery", preview);
          const applied: string[] = [];
          const diagnostics: unknown[] = [];
          renameCalls.add(_id);
          try {
            for (const file of preview.files) {
              if (
                signal?.aborted === true ||
                (await readFile(file.path, "utf8")) !== file.before
              )
                return result(
                  {
                    error: "Rename interrupted or file changed",
                    applied,
                    recoveryEntry: preview.token,
                    recovery:
                      "Original and proposed contents are retained in the pi-driver:rename-recovery session entry",
                  },
                  true,
                );
              const outcome = await ctx.executeTool(
                "write",
                { path: file.path, content: file.after },
                signal === undefined ? {} : { signal },
              );
              if (outcome.isError)
                return result(
                  {
                    error: "Pi blocked or failed a rename write",
                    failed: file.path,
                    applied,
                    recoveryEntry: preview.token,
                    recovery:
                      "Original and proposed contents are retained in the pi-driver:rename-recovery session entry",
                    writeResult: outcome.result.content,
                  },
                  true,
                );
              applied.push(file.path);
            }
          } catch (error) {
            return result(
              { error: message(error), applied, recoveryEntry: preview.token },
              true,
            );
          } finally {
            renameCalls.delete(_id);
          }
          for (const path of applied) {
            try {
              diagnostics.push(await intelligence.diagnostics(ctx.cwd, path));
            } catch (error) {
              diagnostics.push({ path, error: message(error) });
            }
          }
          return result({ applied, diagnostics });
        });
      } catch (error) {
        return result({ error: message(error) }, true);
      }
    },
  });
  pi.on("tool_result", async (event, ctx) => {
    if (
      !intelligence.enabled ||
      event.isError ||
      (event.toolName !== "edit" && event.toolName !== "write")
    )
      return;
    // Nested rename writes run inside the same serialized operation; their diagnostics follow the rename.
    if (
      event.parentToolCallId !== undefined &&
      renameCalls.has(event.parentToolCallId)
    )
      return;
    const input = z.object({ path: z.string() }).safeParse(event.input);
    if (!input.success) return;
    const path = resolve(await realpath(ctx.cwd), input.data.path);
    display.watch(event.toolCallId, path);
    let diagnostics: DiagnosticSnapshot;
    try {
      diagnostics = await intelligence.serial(async () => {
        await requireTrust(ctx);
        return intelligence.diagnostics(ctx.cwd, input.data.path);
      });
    } catch (error) {
      diagnostics = {
        path,
        state: "unavailable",
        message: message(error),
        diagnostics: [],
      };
    }
    display.finish(event.toolCallId, diagnostics);
    const native = z.record(z.string(), z.unknown()).safeParse(event.details);
    return {
      content: [...event.content, ...result({ lsp: diagnostics }).content],
      details: {
        ...(native.success ? native.data : {}),
        piDriverDiagnostics: {
          contentIndex: event.content.length,
          snapshot: diagnostics,
        },
      },
    };
  });
  return intelligence;
}
