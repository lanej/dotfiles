import type {
  ExtensionAPI,
  ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import { realpath } from "node:fs/promises";
import { Type } from "typebox";
import { z } from "zod";
import { Attempts, Phase, stateDirectory, type Attempt } from "./attempts.ts";
import { DriverProfile } from "./config.ts";
import { processStart } from "./process.ts";
import { TaskBeads } from "./task-service.ts";
import { submitResult } from "./task-verification.ts";

async function matchWorker(
  ctx: ExtensionContext,
  record: Attempt,
): Promise<number> {
  if (
    ctx.sessionManager.getSessionId() !== record.id ||
    record.checkout === null ||
    (await realpath(ctx.cwd)) !== (await realpath(record.checkout.path)) ||
    process.env["ZELLIJ_SESSION_NAME"] !== record.session
  ) {
    throw new Error(
      "Pi session, checkout or Zellij session differs from the registered attempt",
    );
  }
  const pane = z.coerce
    .number()
    .int()
    .nonnegative()
    .parse(process.env["ZELLIJ_PANE_ID"]);
  if (
    (record.pid !== null && record.pid !== process.pid) ||
    (record.pane !== null && record.pane !== pane)
  )
    throw new Error("Another Pi process or pane owns this attempt");
  return pane;
}

export default function managedWorker(pi: ExtensionAPI): void {
  const id = process.env["PI_DRIVER_ATTEMPT"];
  if (id === undefined) return;
  z.uuid().parse(id);
  const db = new Attempts(stateDirectory());
  let lifetime = new AbortController();
  const submissions = new Set<Promise<string>>();
  let binding: Attempt | undefined;
  pi.on("session_start", async (event, ctx) => {
    binding = undefined;
    lifetime = new AbortController();
    if (ctx.sessionManager.getSessionId() !== id) return;
    try {
      const record = db.get(id);
      const pane = await matchWorker(ctx, record);
      if (record.revision === null)
        throw new Error("Missing admitted Beads revision");
      if (
        record.profile === DriverProfile.Work &&
        !/^https:\/\/bedrock-mantle\.[a-z0-9-]+\.api\.aws(?:\/|$)/u.test(
          ctx.model?.baseUrl ?? "",
        )
      ) {
        throw new Error(
          "The work worker must resolve to its configured HTTPS Bedrock Mantle endpoint",
        );
      }
      if (
        ctx.model?.id !== record.model.model ||
        ctx.model.provider !== record.model.provider
      )
        throw new Error(
          "Pi selected a different model from the accepted worker profile",
        );
      const started = await processStart(process.pid);
      const first = record.pid === null;
      if (first)
        await new TaskBeads(record.source).requireCurrent(
          record.bead,
          record.revision,
          id,
        );
      binding = db.change(id, (row) => {
        if (first && row.phase !== Phase.Launching)
          throw new Error(
            `This launch is ${row.phase} and needs reconciliation`,
          );
        row.live = true;
        row.processStarted = started;
        row.pane = pane;
        row.pid = process.pid;
        row.transcript = ctx.sessionManager.getSessionFile() ?? null;
        if (first) {
          row.phase = Phase.Running;
          row.message = "Pi is running in the managed worktree";
        }
      });
      ctx.ui.setStatus("pi-bead", record.bead.id);
      if (first && event.reason === "startup")
        pi.sendUserMessage(
          `Work on the accepted bead ${record.bead.id}: ${record.bead.title}`,
        );
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : String(cause);
      db.change(id, (row) => {
        if (row.phase === Phase.Launching) {
          row.phase = Phase.Reconcile;
          row.message = message;
        }
      });
      ctx.ui.notify(message, "error");
    }
  });
  pi.on("before_agent_start", (event, ctx) => {
    if (binding === undefined || ctx.sessionManager.getSessionId() !== id)
      return;
    const { bead } = binding;
    return {
      systemPrompt:
        event.systemPrompt +
        "\n\nYour accepted coding task in this worktree:\n" +
        JSON.stringify({
          id: bead.id,
          title: bead.title,
          description: bead.description,
          acceptance_criteria: bead.acceptance_criteria,
          verifier: binding.check,
        }) +
        "\nUse task_submit_result to submit the outcome. The driver runs the operator's agreed check and records the result.",
    };
  });
  const submit = async (
    summary: string,
    ctx: ExtensionContext,
    toolSignal?: AbortSignal,
  ) => {
    if (binding === undefined)
      throw new Error("This Pi session has no verified local task binding");
    const signal =
      toolSignal === undefined
        ? lifetime.signal
        : AbortSignal.any([lifetime.signal, toolSignal]);
    const result = matchWorker(ctx, db.get(id)).then(() =>
      submitResult(db, id, summary, signal),
    );
    submissions.add(result);
    try {
      return await result;
    } finally {
      submissions.delete(result);
    }
  };
  pi.registerCommand("task-submit", {
    description: "Verify a result against this bead's accepted criteria",
    handler: async (summary, ctx) => {
      ctx.ui.notify(await submit(summary, ctx), "info");
    },
  });
  pi.registerTool({
    name: "task_submit_result",
    label: "Submit task result",
    description:
      "Run the operator's agreed check and submit evidence for the accepted bead.",
    parameters: Type.Object({
      summary: Type.String({ minLength: 1, maxLength: 4000 }),
    }),
    execute: async (_call, params, signal, _onUpdate, ctx) => {
      const text = await submit(params.summary, ctx, signal);
      return {
        content: [{ type: "text", text }],
        details: { bead: db.get(id).bead.id },
      };
    },
  });
  pi.on("session_shutdown", async (event) => {
    lifetime.abort(
      new Error("The worker session ended before verification finished"),
    );
    await Promise.allSettled(submissions);
    if (binding !== undefined)
      db.change(id, (row) => {
        if (row.pid === process.pid) row.live = false;
      });
    binding = undefined;
    if (event.reason === "quit" || event.reason === "reload") db.close();
  });
}
