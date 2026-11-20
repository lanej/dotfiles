import type {
  ExtensionAPI,
  ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import { BeadsReader, taskDetails, taskLabel, taskTree } from "./beads.ts";
import { dispatchGate } from "./capabilities.ts";
import { loadConfig } from "./config.ts";
import { IdleCompactor } from "./idle.ts";

const attemptType = "pi-driver:idle-attempt";

export default function dailyDriver(pi: ExtensionAPI): void {
  let compactor: IdleCompactor | undefined;
  let removeInputListener: (() => void) | undefined;
  let settled = false;
  let dialogs = 0;
  let childWork = false;
  let lifecycle = 0;

  const release = () => {
    lifecycle++;
    compactor?.stop();
    compactor = undefined;
    removeInputListener?.();
    removeInputListener = undefined;
  };

  const initialize = async (ctx: ExtensionContext) => {
    release();
    const generation = lifecycle;
    settled = ctx.isIdle();
    dialogs = 0;
    childWork = false;
    try {
      ctx.ui.setStatus("pi-driver", undefined);
      const config = await loadConfig();
      if (generation !== lifecycle) return;
      if (!config.idleCompaction.enabled || ctx.mode !== "tui") return;
      const entries = () => ctx.sessionManager.getBranch();
      const history = () =>
        [...entries()].reverse().find((entry) => entry.type === "message")
          ?.id ?? null;
      const controller = new IdleCompactor(
        {
          snapshot: () => ({
            sessionId: ctx.sessionManager.getSessionId(),
            // The controller compares this leaf within its idle window; persisted markers use message identity.
            branchId: ctx.sessionManager.getLeafId(),
            historyId: history(),
            settled: settled && ctx.isIdle(),
            pendingInput: ctx.hasPendingMessages(),
            editorText: ctx.ui.getEditorText(),
            dialogs,
            children: childWork ? 1 : 0,
            percent: ctx.getContextUsage()?.percent ?? null,
          }),
          compact: (callbacks) =>
            ctx.compact({
              customInstructions:
                "Preserve task and workspace identity, accepted scope and criteria, worktree and source references, delegated findings, outstanding decisions, and pending or uncertain external effects. Keep observed task text distinct from accepted authorization.",
              onComplete: callbacks.complete,
              onError: callbacks.error,
            }),
          recordAttempt: (historyId) =>
            pi.appendEntry(attemptType, { historyId }),
          notify: (error) =>
            ctx.ui.notify(
              `Idle compaction failed: ${error.message}. Use /compact to retry.`,
              "error",
            ),
          schedule: (callback, delay) => {
            const timer = setTimeout(callback, delay);
            timer.unref();
            return () => clearTimeout(timer);
          },
        },
        config.idleCompaction.idleMs,
        config.idleCompaction.minimumContextPercent,
      );
      const marker = [...entries()]
        .reverse()
        .find(
          (entry) =>
            entry.type === "custom" && entry.customType === attemptType,
        );
      const markedHistory =
        marker?.type === "custom"
          ? (marker.data as { historyId?: unknown } | undefined)?.historyId
          : undefined;
      // Native/manual compaction also satisfies the current history; metadata entries must not retrigger it.
      const lastCompact = [...entries()]
        .reverse()
        .findIndex((entry) => entry.type === "compaction");
      const lastMessage = [...entries()]
        .reverse()
        .findIndex((entry) => entry.type === "message");
      controller.restore(
        lastCompact >= 0 && lastCompact < lastMessage
          ? history()
          : typeof markedHistory === "string"
            ? markedHistory
            : null,
      );
      compactor = controller;
      removeInputListener = ctx.ui.onTerminalInput(() => {
        controller.activity();
        if (settled) controller.settled();
        return undefined;
      });
      ctx.ui.setStatus(
        "pi-driver",
        `idle compact ≥${config.idleCompaction.minimumContextPercent}% / ${config.idleCompaction.idleMs / 60_000}m`,
      );
      if (settled) controller.settled();
    } catch (error) {
      if (generation === lifecycle && ctx.hasUI)
        ctx.ui.notify(
          error instanceof Error ? error.message : String(error),
          "error",
        );
    }
  };

  pi.on("session_start", async (_event, ctx) => initialize(ctx));
  pi.on("session_shutdown", () => release());
  pi.on("session_tree", async (_event, ctx) => initialize(ctx));
  pi.on("session_compact", async (_event, ctx) => initialize(ctx));
  pi.on("input", () => {
    compactor?.activity();
  });
  pi.on("agent_start", () => {
    settled = false;
    compactor?.activity();
  });
  pi.on("agent_settled", () => {
    settled = true;
    compactor?.settled();
  });
  pi.on("ui_prompt_start", () => {
    dialogs++;
    compactor?.activity();
  });
  pi.on("ui_prompt_end", () => {
    dialogs = Math.max(0, dialogs - 1);
    if (settled) compactor?.settled();
  });
  pi.on("tool_execution_start", (event) => {
    // Unknown third-party subagent tools do not have a reliable active-child count. Fail closed for this runtime.
    if (/subagent|delegate|spawn_agent/.test(event.toolName)) childWork = true;
    compactor?.activity();
  });

  pi.registerCommand("tasks", {
    description: "Inspect the authoritative Beads containment tree (read-only)",
    handler: async (argument, ctx) => {
      const config = await loadConfig();
      if (!config.beads) {
        ctx.ui.notify(
          "Configure beads.workspace, database, and branch in pi-driver/config.json first",
          "warning",
        );
        return;
      }
      const reader = new BeadsReader(config.beads);
      let id = argument.trim();
      if (!id) {
        const tasks = await reader.list();
        const rows = taskTree(tasks);
        const labels = rows.map(taskLabel);
        const selection = await ctx.ui.select(
          `Beads · ${config.beads.database}@${config.beads.branch}${tasks.length === 1000 ? " · first 1000 records" : ""}`,
          labels,
        );
        if (!selection) return;
        id = rows[labels.indexOf(selection)]?.task.id ?? "";
      }
      if (!id) return;
      const task = await reader.show(id);
      await ctx.ui.select(taskDetails(task, config.beads.workspace), [
        "Back to conversation",
      ]);
    },
  });

  pi.registerCommand("driver-profile", {
    description: "Explicitly select the work or personal lead model",
    handler: async (argument, ctx) => {
      if (!ctx.isIdle() || ctx.hasPendingMessages()) {
        ctx.ui.notify(
          "Wait for the conversation and queued messages to settle before changing profiles",
          "warning",
        );
        return;
      }
      const config = await loadConfig();
      const name = argument.trim();
      if (name !== "work" && name !== "personal") {
        ctx.ui.notify(
          "Use /driver-profile work or /driver-profile personal",
          "warning",
        );
        return;
      }
      const profile = config.profiles[name];
      if (!profile) {
        ctx.ui.notify(
          `Configure the ${name} profile first; pi-driver config --example shows the role selections`,
          "warning",
        );
        return;
      }
      const models = Object.values(profile).map((role) =>
        ctx.modelRegistry.find(role.provider, role.model),
      );
      if (models.some((model) => !model)) {
        ctx.ui.notify(
          "A configured role model is missing from Pi's registry; no model was changed",
          "error",
        );
        return;
      }
      if (
        name === "personal" &&
        Object.values(profile).some((role) => role.provider !== "openai-codex")
      ) {
        ctx.ui.notify(
          "The personal profile must use Pi's openai-codex subscription provider",
          "error",
        );
        return;
      }
      if (
        name === "work" &&
        models.some(
          (model) =>
            !model ||
            !/^https:\/\/bedrock-mantle\.[a-z0-9-]+\.api\.aws(?:\/|$)/.test(
              model.baseUrl,
            ),
        )
      ) {
        ctx.ui.notify(
          "The work profile must resolve to an explicit HTTPS Bedrock Mantle endpoint",
          "error",
        );
        return;
      }
      const lead = models[0];
      if (!lead) return;
      if (await pi.setModel(lead)) {
        pi.setThinkingLevel(profile.lead.reasoning);
        ctx.ui.setStatus(
          "pi-driver-profile",
          `${name} · ${profile.lead.model} · ${profile.lead.reasoning}`,
        );
        ctx.ui.notify(
          `Selected ${name}; managed delegation remains disabled by the Beads revision gate`,
          "info",
        );
      }
    },
  });

  pi.registerCommand("driver-status", {
    description: "Inspect the daily-driver capability boundary",
    handler: async (_argument, ctx) => {
      ctx.ui.notify(dispatchGate.reason, "warning");
    },
  });
}
