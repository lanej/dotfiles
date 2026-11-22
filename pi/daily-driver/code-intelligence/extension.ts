import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { readFile } from "node:fs/promises";
import { Type } from "typebox";
import { z } from "zod";
import { loadConfig } from "../config.ts";
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
  const renameCalls = new Set<string>();
  pi.on("session_start", async () => {
    await intelligence.stop();
    intelligence.enabled = (await loadConfig()).lsp.enabled;
  });
  pi.on("session_shutdown", async () => {
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
        return await intelligence.serial(async () =>
          result(
            await intelligence.lookup(
              ctx.cwd,
              args.action,
              args.path,
              args.line ?? 1,
              args.column ?? 1,
              args.query ?? "",
              signal,
            ),
          ),
        );
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
    try {
      const diagnostics = await intelligence.serial(() =>
        intelligence.diagnostics(ctx.cwd, input.data.path),
      );
      return {
        content: [...event.content, ...result({ lsp: diagnostics }).content],
      };
    } catch (error) {
      return {
        content: [
          ...event.content,
          ...result({ lsp: { state: "unavailable", message: message(error) } })
            .content,
        ],
      };
    }
  });
  return intelligence;
}
