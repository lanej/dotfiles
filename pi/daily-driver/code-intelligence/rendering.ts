import type { DriverConfig } from "../config.ts";
import { inlineDiagnosticLines, syntaxDiffRows } from "./diff.ts";
import type {
  ExtensionAPI,
  ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import { z } from "zod";
import {
  diagnosticRows,
  diagnosticSnapshot,
  type DiagnosticSnapshot,
} from "./diagnostics.ts";
import type { CodeIntelligence } from "./service.ts";

const detailsSchema = z.object({
  piDriverDiagnostics: z.object({
    contentIndex: z.number().int().nonnegative(),
    snapshot: diagnosticSnapshot,
  }),
});
interface View {
  snapshot: DiagnosticSnapshot;
  settled: boolean;
  invalidate?: () => void;
}
export function registerDiagnosticRendering(
  pi: ExtensionAPI,
  intelligence: CodeIntelligence,
  diffDisplay: () => DriverConfig["display"],
) {
  const views = new Map<string, View>();
  const latest = new Map<string, string>();
  const diffs = new Map<string, { path: string; diff: string }>();
  const clear = () => {
    views.clear();
    latest.clear();
    diffs.clear();
  };
  const restore = (_event: unknown, ctx: ExtensionContext) => {
    clear();
    for (const entry of ctx.sessionManager.getBranch()) {
      const parsed = z
        .object({
          type: z.literal("custom_message"),
          customType: z.literal("pi-driver:diagnostics"),
          details: z.object({
            toolCallId: z.string(),
            snapshot: diagnosticSnapshot,
          }),
        })
        .safeParse(entry);
      if (parsed.success)
        views.set(parsed.data.details.toolCallId, {
          snapshot: parsed.data.details.snapshot,
          settled: true,
        });
    }
  };
  pi.on("session_start", restore);
  pi.on("session_tree", restore);
  pi.on("session_shutdown", clear);
  intelligence.onDiagnostics((snapshot) => {
    const id = latest.get(snapshot.path);
    if (id === undefined) return;
    const view = views.get(id);
    if (
      view === undefined ||
      JSON.stringify(view.snapshot) === JSON.stringify(snapshot)
    )
      return;
    view.snapshot = snapshot;
    view.invalidate?.();
    if (view.settled)
      pi.sendMessage(
        {
          customType: "pi-driver:diagnostics",
          content: JSON.stringify({ lsp: snapshot }),
          display: false,
          details: { toolCallId: id, snapshot },
        },
        { triggerTurn: false },
      );
  });
  pi.registerToolRenderer((name, next) => {
    const base = next();
    const render = base?.renderResult;
    if ((name !== "edit" && name !== "write") || render === undefined)
      return base;
    const renderCall = base?.renderCall;
    return {
      ...base,
      ...(name === "edit" && renderCall !== undefined
        ? {
            renderCall(args, theme, context) {
              const native = renderCall(args, theme, context);
              return {
                invalidate() {
                  native.invalidate();
                },
                render(width) {
                  const value = diffs.get(context.toolCallId);
                  return value === undefined
                    ? native.render(width)
                    : syntaxDiffRows(
                        value.diff,
                        value.path,
                        theme,
                        width,
                        context.cwd,
                        undefined,
                        diffDisplay(),
                        views.get(context.toolCallId)?.snapshot.diagnostics,
                      );
                },
              };
            },
          }
        : {}),
      renderResult(result, options, theme, context) {
        const diff = z.object({ diff: z.string() }).safeParse(result.details);
        const args = z.object({ path: z.string() }).safeParse(context.args);
        if (
          name === "edit" &&
          !context.isError &&
          diff.success &&
          args.success &&
          diffs.get(context.toolCallId)?.diff !== diff.data.diff
        ) {
          diffs.set(context.toolCallId, {
            path: args.data.path,
            diff: diff.data.diff,
          });
        }
        const parsed = detailsSchema.safeParse(result.details);
        if (!parsed.success || options.isPartial)
          return render(result, options, theme, context);
        const annotation = parsed.data.piDriverDiagnostics;
        let view = views.get(context.toolCallId);
        if (view === undefined) {
          view = { snapshot: annotation.snapshot, settled: true };
          views.set(context.toolCallId, view);
        }
        view.invalidate = context.invalidate;
        const current = view;
        const original = render(
          {
            ...result,
            content: result.content.filter(
              (_item, index) => index !== annotation.contentIndex,
            ),
          },
          options,
          theme,
          { ...context, lastComponent: undefined },
        );
        return {
          invalidate() {
            original.invalidate();
          },
          render(width) {
            const edit = diffs.get(context.toolCallId);
            const inlineLines =
              renderCall !== undefined &&
              edit !== undefined &&
              width >= 3 &&
              diffDisplay().inline_diagnostics
                ? inlineDiagnosticLines(edit.diff)
                : undefined;
            const diagnostics = diagnosticRows(
              current.snapshot,
              theme,
              width,
              options.expanded,
              inlineLines,
            );
            return [
              ...original.render(width),
              ...(diagnostics.length === 0 ? [] : ["", ...diagnostics]),
            ];
          },
        };
      },
    };
  });
  return {
    watch(id: string, path: string) {
      latest.set(path, id);
      views.set(id, {
        snapshot: { path, state: "pending", diagnostics: [] },
        settled: false,
      });
    },
    finish(id: string, snapshot: DiagnosticSnapshot) {
      const view = views.get(id);
      if (view !== undefined) {
        view.snapshot = snapshot;
        view.settled = true;
      }
    },
  };
}
