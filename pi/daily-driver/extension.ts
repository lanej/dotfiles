import type {
  ExtensionAPI,
  ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import { z } from "zod";
import { BeadsReader, taskDetails, taskLabel, taskTree } from "./beads.ts";
import { dispatchGate } from "./capabilities.ts";
import {
  AgentRole,
  DefaultProvider,
  DriverProfile,
  driverProfileSchema,
  knownProvider,
  loadConfig,
} from "./config.ts";
import { IdleSession, type IdleSessionHost } from "./idle.ts";
import {
  isEntry,
  PiEntryType,
  PiEvent,
  PiMode,
  piModeSchema,
} from "./runtime.ts";
import { chooseTask, installFooter, showTask, statusPill } from "./ui.ts";

const attemptType = "pi-driver:idle-attempt";
const attemptSchema = z.object({ historyId: z.string() });

export default function dailyDriver(pi: ExtensionAPI): void {
  const idle = new IdleSession();
  let removeInputListener: (() => void) | undefined;
  let lifecycle = 0;
  let selectedProfile: DriverProfile | undefined;

  const release = () => {
    lifecycle++;
    idle.stop();
    removeInputListener?.();
    removeInputListener = undefined;
  };

  const initialize = async (ctx: ExtensionContext) => {
    release();
    const generation = lifecycle;
    try {
      ctx.ui.setStatus("pi-driver", undefined);
      const config = await loadConfig();
      if (generation !== lifecycle) return;
      const mode = piModeSchema.parse(ctx.mode);
      if (mode === PiMode.Tui)
        installFooter(
          ctx,
          () => pi.getThinkingLevel(),
          () => selectedProfile,
        );
      if (!config.idleCompaction.enabled || mode !== PiMode.Tui) return;
      const entries = () => ctx.sessionManager.getBranch();
      const history = () =>
        [...entries()]
          .reverse()
          .find((entry) => isEntry(entry, PiEntryType.Message))?.id ?? null;
      const host: IdleSessionHost = {
        snapshot: () => ({
          sessionId: ctx.sessionManager.getSessionId(),
          // The controller compares this leaf within its idle window; persisted markers use message identity.
          branchId: ctx.sessionManager.getLeafId(),
          historyId: history(),
          settled: ctx.isIdle(),
          pendingInput: ctx.hasPendingMessages(),
          editorText: ctx.ui.getEditorText(),
          percent: ctx.getContextUsage()?.percent ?? null,
        }),
        compact: (callbacks) => {
          ctx.compact({
            customInstructions:
              "Preserve task and workspace identity, accepted scope and criteria, worktree and source references, delegated findings, outstanding decisions, and pending or uncertain external effects. Keep observed task text distinct from accepted authorization.",
            onComplete: () => {
              callbacks.complete();
            },
            onError: (error) => {
              callbacks.error(error);
            },
          });
        },
        recordAttempt: (historyId) => {
          pi.appendEntry(attemptType, { historyId });
        },
        notify: (error) => {
          ctx.ui.notify(
            `Idle compaction failed: ${error.message}. Use /compact to retry.`,
            "error",
          );
        },
        schedule: (callback, delay) => {
          const timer = setTimeout(callback, delay);
          timer.unref();
          return () => {
            clearTimeout(timer);
          };
        },
      };
      const marker = [...entries()]
        .reverse()
        .find(
          (entry) =>
            isEntry(entry, PiEntryType.Custom) &&
            entry.customType === attemptType,
        );
      const markedHistory = attemptSchema.safeParse(
        marker !== undefined && isEntry(marker, PiEntryType.Custom)
          ? marker.data
          : undefined,
      );
      // Native/manual compaction also satisfies the current history; metadata entries must not retrigger it.
      const lastCompact = [...entries()]
        .reverse()
        .findIndex((entry) => isEntry(entry, PiEntryType.Compaction));
      const lastMessage = [...entries()]
        .reverse()
        .findIndex((entry) => isEntry(entry, PiEntryType.Message));
      idle.initialize(
        host,
        config.idleCompaction.idleMs,
        config.idleCompaction.minimumContextPercent,
        lastCompact >= 0 && lastCompact < lastMessage
          ? history()
          : markedHistory.success
            ? markedHistory.data.historyId
            : null,
      );
      removeInputListener = ctx.ui.onTerminalInput(() => {
        idle.terminalInput();
        return undefined;
      });
    } catch (error) {
      if (generation === lifecycle && ctx.hasUI)
        ctx.ui.notify(
          error instanceof Error ? error.message : String(error),
          "error",
        );
    }
  };

  pi.on(PiEvent.SessionStart, async (_event, ctx) => {
    idle.newSession();
    selectedProfile = undefined;
    await initialize(ctx);
  });
  pi.on(PiEvent.SessionShutdown, () => {
    release();
  });
  pi.on(PiEvent.SessionTree, async (_event, ctx) => initialize(ctx));
  pi.on(PiEvent.SessionCompact, async (_event, ctx) => initialize(ctx));
  pi.on(PiEvent.ModelSelect, () => {
    selectedProfile = undefined;
  });
  pi.on(PiEvent.Input, () => {
    idle.activity();
  });
  pi.on(PiEvent.AgentStart, () => {
    idle.agentStart();
  });
  pi.on(PiEvent.AgentSettled, () => {
    idle.agentSettled();
  });
  pi.on(PiEvent.PromptStart, () => {
    idle.promptStart();
  });
  pi.on(PiEvent.PromptEnd, () => {
    idle.promptEnd();
  });
  pi.on(PiEvent.ToolStart, (event) => {
    idle.toolStart(event.toolName);
  });

  pi.registerCommand("tasks", {
    description: "Inspect the authoritative Beads containment tree (read-only)",
    handler: async (argument, ctx) => {
      const config = await loadConfig();
      if (config.beads === undefined) {
        ctx.ui.notify(
          "Configure beads.workspace, database, and branch in pi-driver/config.json first",
          "warning",
        );
        return;
      }
      const reader = new BeadsReader(config.beads);
      let id = argument.trim();
      if (id.length === 0) {
        const tasks = await reader.list();
        const rows = taskTree(tasks);
        const selection = await chooseTask(
          ctx,
          `Tasks · ${config.beads.database}${tasks.length === 1000 ? " · first 1000" : ""}`,
          rows.map((row) => ({
            value: row.task.id,
            label: taskLabel(row, (status) => statusPill(status, ctx.ui.theme)),
          })),
        );
        if (selection === undefined) return;
        id = selection;
      }
      if (id.length === 0) return;
      const task = await reader.show(id);
      await showTask(
        ctx,
        taskDetails(task, config.beads.database, (status) =>
          statusPill(status, ctx.ui.theme),
        ),
      );
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
      const parsedName = driverProfileSchema.safeParse(argument.trim());
      if (!parsedName.success) {
        ctx.ui.notify(
          "Use /driver-profile work or /driver-profile personal",
          "warning",
        );
        return;
      }
      const name = parsedName.data;
      const profile = config.profiles[name];
      if (profile === undefined) {
        ctx.ui.notify(
          `Configure the ${name} profile first; pi-driver config --example shows the role selections`,
          "warning",
        );
        return;
      }
      const models = Object.values(profile).map((role) =>
        ctx.modelRegistry.find(role.provider, role.model),
      );
      if (models.some((model) => model === undefined)) {
        ctx.ui.notify(
          "A configured role model is missing from Pi's registry; no model was changed",
          "error",
        );
        return;
      }
      if (
        name === DriverProfile.Personal &&
        Object.values(profile).some(
          (role) =>
            knownProvider(role.provider) !==
            DefaultProvider.ChatGPTSubscription,
        )
      ) {
        ctx.ui.notify(
          "The personal profile must use Pi's openai-codex subscription provider",
          "error",
        );
        return;
      }
      if (
        name === DriverProfile.Work &&
        models.some(
          (model) =>
            model === undefined ||
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
      const leadSelection = profile[AgentRole.Lead];
      const lead = ctx.modelRegistry.find(
        leadSelection.provider,
        leadSelection.model,
      );
      if (lead === undefined) return;
      if (await pi.setModel(lead)) {
        pi.setThinkingLevel(leadSelection.reasoning);
        selectedProfile = name;
      }
    },
  });

  pi.registerCommand("driver-status", {
    description: "Inspect the daily-driver capability boundary",
    handler: (_argument, ctx) => {
      ctx.ui.notify(dispatchGate.reason, "warning");
      return Promise.resolve();
    },
  });
}
