import { registerCodeIntelligence } from "./code-intelligence/extension.ts";
import { inspectIntegrations } from "./integrations.ts";
import { registerSearchRendering } from "./search-renderer.ts";
import { installFooter } from "./footer.ts";
import type {
  ExtensionAPI,
  ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import { z } from "zod";
import { registerArchives } from "./archives.ts";
import { directoryProfileType, registerDirectory } from "./directory.ts";
import {
  BeadsReader,
  knownTaskStatus,
  taskDetails,
  taskOverlayLabel,
  taskSchema,
  taskTree,
  TaskStatus,
} from "./beads.ts";
import { delegateTool, registerDelegation } from "./delegation.ts";
import { TaskBeads } from "./task-service.ts";
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
import { focusTaskPane, taskPaneBeads } from "./task-run.ts";
import {
  chooseTask,
  showTask,
  taskStatusGlyph,
  taskStatusLabel,
  TaskAction,
} from "./ui.ts";

const attemptType = "pi-driver:idle-attempt";
const attemptSchema = z.object({ historyId: z.string() });

export default function dailyDriver(
  pi: ExtensionAPI,
  managed?: {
    profile: DriverProfile;
    approvalPending: () => boolean;
    trackedPullRequest: () => string | undefined;
  },
): void {
  const intelligence = registerCodeIntelligence(pi);
  const idle = new IdleSession();
  let removeInputListener: (() => void) | undefined;
  let lifecycle = 0;
  let selectedProfile = managed?.profile;

  const delegation = registerDelegation(
    pi,
    () => selectedProfile,
    () => {
      idle.terminalInput();
    },
  );
  registerArchives(pi);
  registerDirectory(
    pi,
    (sessionId) => delegation.blocks(sessionId),
    () => selectedProfile,
  );
  registerSearchRendering(pi);
  if (managed !== undefined)
    pi.on("session_start", () => {
      delegation.activate();
    });

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
          managed?.trackedPullRequest,
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
          pendingInput:
            ctx.hasPendingMessages() ||
            managed?.approvalPending() === true ||
            delegation.blocks(ctx.sessionManager.getSessionId()),
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
    selectedProfile = managed?.profile;
    if (managed === undefined) {
      const marker = ctx.sessionManager
        .getBranch()
        .findLast(
          (entry) =>
            isEntry(entry, PiEntryType.Custom) &&
            entry.customType === directoryProfileType,
        );
      if (marker !== undefined && isEntry(marker, PiEntryType.Custom)) {
        const profile = driverProfileSchema.safeParse(marker.data);
        if (profile.success) {
          // Consume the handoff before revalidation so a later resume does not
          // override a model or profile the user selected after this switch.
          pi.appendEntry(directoryProfileType, null);
          await selectProfile(profile.data, ctx, true);
        }
      }
    }
    await initialize(ctx);
  });
  pi.on(PiEvent.SessionShutdown, () => {
    release();
  });
  pi.on(PiEvent.SessionTree, async (_event, ctx) => initialize(ctx));
  pi.on(PiEvent.SessionCompact, async (_event, ctx) => initialize(ctx));
  pi.on(PiEvent.ModelSelect, () => {
    selectedProfile = managed?.profile;
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
    if (event.toolName === delegateTool) idle.activity();
    else idle.toolStart(event.toolName);
  });

  pi.registerCommand("tasks", {
    description: "Inspect the authoritative Beads containment tree (read-only)",
    handler: async (argument, ctx) => {
      const config = await loadConfig();
      if (config.beads === undefined && config.beadsService === undefined) {
        ctx.ui.notify(
          "Configure a Beads service or read-only workspace in pi-driver/config.json",
          "warning",
        );
        return;
      }
      const service =
        config.beadsService === undefined
          ? undefined
          : new TaskBeads(config.beadsService);
      const reader =
        service !== undefined
          ? {
              list: async () =>
                z.array(taskSchema).parse((await service.list()).items),
              show: async (id: string) =>
                taskSchema.parse(await service.get(id)),
            }
          : config.beads === undefined
            ? undefined
            : new BeadsReader(config.beads);
      if (reader === undefined) return;
      const label =
        config.beadsService?.projectId ?? config.beads?.database ?? "";
      let id = argument.trim();
      if (id.length === 0) {
        const tasks = await reader.list();
        const rows = taskTree(tasks);
        const live =
          config.beadsService === undefined
            ? new Set<string>()
            : await taskPaneBeads(config.beadsService.projectId);
        const selection = await chooseTask(
          ctx,
          rows.map((row) => ({
            value: row.task.id,
            label: taskOverlayLabel(
              row,
              (status) => taskStatusGlyph(status, ctx.ui.theme),
              (branch) => ctx.ui.theme.fg("muted", branch),
            ),
            canFocus:
              live.has(row.task.id) &&
              knownTaskStatus(row.task.status) === TaskStatus.InProgress,
          })),
          tasks.length === 1000,
        );
        if (selection === undefined) return;
        if (
          selection.action === TaskAction.FocusPane &&
          config.beadsService !== undefined
        ) {
          await focusTaskPane(config.beadsService, selection.id);
          return;
        }
        id = selection.id;
      }
      if (id.length === 0) return;
      const task = await reader.show(id);
      await showTask(
        ctx,
        taskDetails(task, label, (status) =>
          taskStatusLabel(status, ctx.ui.theme),
        ),
      );
    },
  });

  async function selectProfile(
    argument: string,
    ctx: ExtensionContext,
    restoring = false,
  ): Promise<void> {
    if (process.env["PI_DRIVER_ATTEMPT"] !== undefined) {
      ctx.ui.notify("Set the profile on pi-driver start.", "warning");
      return;
    }
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
          knownProvider(role.provider) !== DefaultProvider.ChatGPTSubscription,
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
    if (
      restoring &&
      (ctx.model?.provider !== lead.provider || ctx.model.id !== lead.id)
    ) {
      ctx.ui.notify(
        "The driver profile no longer matches the current model. Select /driver-profile again to enable delegation.",
        "warning",
      );
      return;
    }
    const reasoning = restoring
      ? pi.getThinkingLevel()
      : leadSelection.reasoning;
    if (!(await pi.setModel(lead))) {
      ctx.ui.notify(
        `Cannot switch to ${name}. Authenticate with ${leadSelection.provider} and retry. The current model is still active.`,
        "error",
      );
      return;
    }
    pi.setThinkingLevel(reasoning);
    selectedProfile = name;
    delegation.activate();
  }
  pi.registerCommand("driver-profile", {
    description: "Explicitly select the work or personal lead model",
    handler: (argument, ctx) => selectProfile(argument, ctx),
  });

  pi.registerCommand("driver-status", {
    description: "Inspect the daily-driver capability boundary",
    handler: async (_argument, ctx) => {
      const integrations = await inspectIntegrations(await loadConfig());
      const summary = Object.entries(integrations)
        .map(
          ([name, state]) =>
            `${name}: ${state.available ? "available" : state.reason}`,
        )
        .join("\n");
      ctx.ui.notify(
        `${summary}\n${dispatchGate.reason}\n${intelligence.status()}`,
        "info",
      );
    },
  });
}
