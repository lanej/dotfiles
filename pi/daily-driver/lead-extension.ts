import { lspTool, renameTool } from "./code-intelligence/extension.ts";
import { githubLink, renderReferences } from "./github-links.ts";
import { FooterStatus } from "./runtime.ts";
import type {
  ExtensionAPI,
  ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import { lstat, realpath } from "node:fs/promises";
import { dirname, isAbsolute, relative, resolve, sep } from "node:path";
import { Type } from "typebox";
import { z } from "zod";
import { type Attempts, type Attempt, Phase } from "./attempts.ts";
import { readDeliveryInbox } from "./delivery.ts";
import { appendOctoEvents } from "./transcript-events.ts";
import { delegateTool } from "./delegation.ts";
import {
  describePlan,
  draftSchema,
  LeadMode,
  planDigest,
} from "./lead-plan.ts";
import { SpecStatus } from "./socrates/spec.ts";
import { askTool, registerSocrates, specTool } from "./socrates/controls.ts";
import { reviewPlan, showTask } from "./ui.ts";
import { BeadChanged, owner, TaskBeads } from "./task-service.ts";

const planTool = "draft_implementation_plan";
const inspectTools = new Set([
  "read",
  "ls",
  "find",
  "grep",
  lspTool,
  delegateTool,
  planTool,
]);
const implementationTools = new Set([
  "write",
  "edit",
  "task_submit_result",
  renameTool,
]);

async function worktreeWritePath(cwd: string, input: unknown): Promise<string> {
  const { path } = z.object({ path: z.string().min(1) }).parse(input);
  const root = await realpath(cwd);
  const target = resolve(root, path);
  const within = relative(root, target);
  if (
    within.length === 0 ||
    isAbsolute(within) ||
    within === ".." ||
    within.startsWith(`..${sep}`) ||
    within.split(sep).includes(".git")
  )
    throw new Error("Lead edits must target files in the managed worktree");
  let ancestor = target;
  while (ancestor !== root) {
    try {
      const info = await lstat(ancestor);
      if (info.isSymbolicLink() || (await realpath(ancestor)) !== ancestor)
        throw new Error(
          "Lead edits cannot follow links in the managed worktree",
        );
      break;
    } catch (error) {
      if (!z.object({ code: z.literal("ENOENT") }).safeParse(error).success)
        throw error;
      ancestor = dirname(ancestor);
    }
  }
  return target;
}

export function registerLeadControls(
  pi: ExtensionAPI,
  db: Attempts,
  id: string,
  requireBinding: (ctx: ExtensionContext) => Promise<Attempt>,
  approvalPending: (active: boolean) => void,
) {
  const mode = () => db.get(id).leadPlan?.mode;
  registerSocrates(pi, db, id, requireBinding, approvalPending);
  const permits = (tool: string) => {
    const spec = db.get(id).specification;
    if (tool === specTool || tool === askTool) {
      return (
        mode() === LeadMode.Planning &&
        spec?.status === SpecStatus.Interrogating
      );
    }
    if (tool === planTool && spec?.status === SpecStatus.Interrogating)
      return false;
    return (
      inspectTools.has(tool) ||
      (mode() === LeadMode.Implementing && implementationTools.has(tool))
    );
  };
  const applyTools = (ctx: ExtensionContext) => {
    pi.setActiveTools(
      pi
        .getAllTools()
        .filter((tool) => permits(tool.name))
        .map((tool) => tool.name),
    );
    ctx.ui.setStatus(FooterStatus.Plan, mode() ?? LeadMode.Planning);
  };
  const accepted = async (ctx: ExtensionContext) => {
    const record = await requireBinding(ctx);
    if (record.revision === null)
      throw new Error("The accepted Beads revision is missing");
    return {
      record,
      revision: record.revision,
      beads: new TaskBeads(record.source),
    };
  };

  pi.on("before_agent_start", (_event, ctx) => {
    applyTools(ctx);
  });
  pi.on("session_before_switch", () => ({ cancel: true }));
  pi.on("session_before_fork", () => ({ cancel: true }));
  pi.on("user_bash", () => ({
    result: {
      output:
        "Run operator shell commands in another pane. This lead uses the agreed verifier for execution.",
      exitCode: 1,
      cancelled: false,
      truncated: false,
    },
  }));
  pi.on("tool_call", async (event, ctx) => {
    if (!permits(event.toolName))
      return {
        block: true,
        reason: "This tool is unavailable in the current lead mode",
      };
    if (!implementationTools.has(event.toolName)) return;
    try {
      const { record, revision, beads } = await accepted(ctx);
      await beads.requireCurrent(record.bead, revision, id);
      if (event.toolName === "write" || event.toolName === "edit")
        event.input["path"] = await worktreeWritePath(ctx.cwd, event.input);
      return undefined;
    } catch (cause) {
      if (cause instanceof BeadChanged) {
        db.change(id, (row) => {
          row.leadPlan = {
            mode: LeadMode.Planning,
            draft: null,
            children: row.leadPlan?.children,
          };
        });
        applyTools(ctx);
      }
      return {
        block: true,
        reason: cause instanceof Error ? cause.message : String(cause),
      };
    }
  });

  pi.registerTool({
    name: planTool,
    label: "Draft implementation plan",
    description:
      "Save a proposed plan for operator approval. Optional tasks become Beads children only on approval. List blockers before their dependents.",
    parameters: Type.Object({
      summary: Type.String(),
      tasks: Type.Array(
        Type.Object({
          key: Type.String(),
          title: Type.String(),
          description: Type.String(),
          acceptance: Type.String(),
          blockedBy: Type.Optional(Type.Array(Type.String())),
          requirements: Type.Optional(Type.Array(Type.String())),
          owns: Type.Optional(Type.Array(Type.String())),
        }),
      ),
    }),
    async execute(_call, args, _signal, _update, ctx) {
      await requireBinding(ctx);
      const draft = draftSchema.parse(args);
      db.change(id, (row) => {
        if (row.leadPlan?.mode !== LeadMode.Planning)
          throw new Error("This session is not drafting a plan");
        const specification = row.specification;
        if (specification !== undefined) {
          if (
            specification.status !== SpecStatus.Frozen ||
            specification.draft === null ||
            specification.acceptedRevision !== row.revision
          )
            throw new Error(
              "Freeze the specification against the current Beads revision first",
            );
          const known = new Set(
            specification.draft.requirements.map(
              (requirement) => requirement.id,
            ),
          );
          if (
            draft.tasks.some(
              (task) =>
                task.requirements.length === 0 ||
                task.requirements.some(
                  (requirement) => !known.has(requirement),
                ),
            )
          )
            throw new Error(
              "Every child task must link to a frozen requirement",
            );
          const covered = new Set(
            draft.tasks.flatMap((task) => task.requirements),
          );
          if (
            draft.tasks.length > 0 &&
            [...known].some((requirement) => !covered.has(requirement))
          )
            throw new Error(
              "Every frozen requirement must be covered by the task breakdown",
            );
        }
        row.leadPlan = { ...row.leadPlan, draft };
      });
      return {
        content: [
          {
            type: "text",
            text: "Draft saved. Await operator approval from /plan-approve.",
          },
        ],
        details: {},
      };
    },
  });
  pi.registerCommand("octo-inbox", {
    description: "Inspect durable Octo review notices for this lead",
    async handler(_argument, ctx) {
      if (!ctx.isIdle()) throw new Error("Wait for the lead turn to settle");
      const record = await requireBinding(ctx);
      if (record.delivery === undefined) {
        ctx.ui.notify("This lead has no Octo publication yet", "info");
        return;
      }
      approvalPending(true);
      try {
        const inbox = await readDeliveryInbox(db, record);
        if (inbox.url !== undefined)
          appendOctoEvents(pi, ctx, inbox.url, inbox.receipts);
        await showTask(
          ctx,
          inbox.url === undefined
            ? inbox.text
            : [
                githubLink(inbox.url) ?? inbox.url,
                renderReferences(
                  inbox.text.replace(/(?!\n)\p{Cc}/gu, ""),
                  (link) => ctx.ui.theme.fg("accent", link),
                ),
              ]
                .filter((line) => line !== "")
                .join("\n\n"),
        );
      } finally {
        approvalPending(false);
      }
    },
  });
  pi.registerCommand("plan", {
    description: "Show the proposed plan and Beads breakdown",
    async handler(_argument, ctx) {
      const { leadPlan } = await requireBinding(ctx);
      ctx.ui.notify(
        leadPlan?.draft != null
          ? describePlan(leadPlan.draft)
          : "No plan drafted yet",
        "info",
      );
    },
  });
  pi.registerCommand("plan-refresh", {
    description: "Read a revised Beads brief before drafting a new plan",
    async handler(_argument, ctx) {
      if (!ctx.isIdle()) throw new Error("Wait for the lead turn to settle");
      const { record, revision, beads } = await accepted(ctx);
      const current = await beads.get(record.bead.id);
      if (
        current.assignee !== owner(id) ||
        current.status !== "in_progress" ||
        current.metadata["pi.attempt"] !== id
      )
        throw new Error("This lead no longer owns the task");
      db.change(id, (row) => {
        if (row.revision !== revision)
          throw new Error("The accepted brief changed during refresh. Retry.");
        if (row.leadPlan?.mode === LeadMode.Applying)
          throw new Error(
            "Inspect the in-flight plan receipt before refreshing",
          );
        if (
          (row.phase !== Phase.Running &&
            row.phase !== Phase.Verified &&
            row.phase !== Phase.CheckFailed &&
            row.phase !== Phase.NeedsReview) ||
          row.delivery?.merge !== undefined
        )
          throw new Error(
            "Settle the active verification or delivery before refreshing",
          );
        if (row.specification !== undefined) {
          row.specHistory = [...(row.specHistory ?? []), row.specification];
          row.specification = {
            ...row.specification,
            status: SpecStatus.Interrogating,
            version: row.specification.version + 1,
            acceptedRevision: current.revision,
            approvalAt: undefined,
            exchange: undefined,
          };
        }
        row.bead = current;
        row.revision = current.revision;
        row.leadPlan = {
          mode: LeadMode.Planning,
          draft: null,
          children: row.leadPlan?.children,
        };
        row.phase = Phase.Running;
        row.verification = null;
        row.message =
          "The refreshed brief requires plan approval and verification";
      });
      applyTools(ctx);
      if (record.specification !== undefined) {
        pi.sendUserMessage(
          "Reassess Socrates discovery against the refreshed Beads brief. Revisit only decisions the revised brief affects.",
        );
        return;
      }
      ctx.ui.notify(
        "Current Beads brief loaded. Draft and approve a new plan before editing.",
        "info",
      );
    },
  });
  pi.registerCommand("plan-approve", {
    description:
      "Review and approve the current plan and optional task breakdown",
    async handler(_argument, ctx) {
      if (!ctx.isIdle()) throw new Error("Wait for the lead turn to settle");
      const { record, revision, beads } = await accepted(ctx);
      const plan = record.leadPlan;
      if (plan?.mode !== LeadMode.Planning || plan.draft === null) {
        ctx.ui.notify("No draft to approve", "warning");
        return;
      }
      const draft = plan.draft;
      const specification = record.specification;
      if (
        specification !== undefined &&
        (specification.status !== SpecStatus.Frozen ||
          specification.acceptedRevision !== revision)
      )
        throw new Error(
          "The Socrates specification is not frozen against the current Beads revision",
        );
      const digest = planDigest(draft);
      const specificationVersion = specification?.version;
      approvalPending(true);
      try {
        if (
          !(await reviewPlan(
            ctx,
            `Approve the plan for ${record.bead.id}`,
            describePlan(draft),
            "start implementation",
          ))
        )
          return;
        await beads.requireCurrent(record.bead, revision, id);
        db.change(id, (row) => {
          if (
            row.leadPlan?.mode !== LeadMode.Planning ||
            row.leadPlan.draft === null ||
            planDigest(row.leadPlan.draft) !== digest ||
            row.revision !== revision ||
            JSON.stringify(row.specification) !== JSON.stringify(specification)
          )
            throw new Error("The displayed plan or task revision changed");
          row.leadPlan = {
            mode: LeadMode.Applying,
            children: row.leadPlan.children,
            draft,
            digest,
            specificationVersion,
          };
        });
        let result: Awaited<ReturnType<TaskBeads["applyPlan"]>>;
        try {
          result = await beads.applyPlan(
            record.bead,
            revision,
            id,
            digest,
            draft,
          );
        } catch (cause) {
          // A dropped batch acknowledgement may follow a committed task graph.
          // Keep the attempted digest and require reconciliation before another write.
          if (cause instanceof BeadChanged && draft.tasks.length === 0)
            db.change(id, (row) => {
              row.leadPlan = {
                mode: LeadMode.Planning,
                draft: null,
                children: row.leadPlan?.children,
              };
            });
          throw cause;
        }
        db.change(id, (row) => {
          if (
            row.leadPlan?.mode !== LeadMode.Applying ||
            row.leadPlan.digest !== digest
          )
            throw new Error(
              "The pending plan changed before Beads confirmed it",
            );
          row.revision = result.revision;
          row.leadPlan = {
            mode: LeadMode.Implementing,
            draft,
            digest,
            specificationVersion,
            children: { ...row.leadPlan.children, ...result.children },
          };
        });
        applyTools(ctx);
        ctx.ui.notify("Plan approved. The lead can implement it.", "info");
      } finally {
        approvalPending(false);
      }
    },
  });
  return applyTools;
}
