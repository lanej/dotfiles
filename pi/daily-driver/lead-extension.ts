import type {
  ExtensionAPI,
  ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import { lstat, realpath } from "node:fs/promises";
import { dirname, isAbsolute, relative, resolve, sep } from "node:path";
import { Type } from "typebox";
import { z } from "zod";
import type { Attempts, Attempt } from "./attempts.ts";
import { delegateTool } from "./delegation.ts";
import {
  describePlan,
  draftSchema,
  LeadMode,
  planDigest,
} from "./lead-plan.ts";
import { BeadChanged, owner, TaskBeads } from "./task-service.ts";

const planTool = "draft_implementation_plan";
const inspectTools = new Set([
  "read",
  "ls",
  "find",
  "grep",
  delegateTool,
  planTool,
]);
const implementationTools = new Set(["write", "edit", "task_submit_result"]);

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
  const permits = (tool: string) =>
    inspectTools.has(tool) ||
    (mode() === LeadMode.Implementing && implementationTools.has(tool));
  const applyTools = (ctx: ExtensionContext) => {
    pi.setActiveTools(
      pi
        .getAllTools()
        .filter((tool) => permits(tool.name))
        .map((tool) => tool.name),
    );
    ctx.ui.setStatus(
      "pi-plan",
      mode() === LeadMode.Implementing ? "Implementing" : "Planning",
    );
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
          row.leadPlan = { mode: LeadMode.Planning, draft: null };
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
        }),
      ),
    }),
    async execute(_call, args, _signal, _update, ctx) {
      await requireBinding(ctx);
      const draft = draftSchema.parse(args);
      db.change(id, (row) => {
        if (row.leadPlan?.mode !== LeadMode.Planning)
          throw new Error("This session is not drafting a plan");
        row.leadPlan = { mode: LeadMode.Planning, draft };
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
      const { record, beads } = await accepted(ctx);
      if (record.leadPlan?.mode === LeadMode.Applying)
        throw new Error("Inspect the in-flight plan receipt before refreshing");
      const current = await beads.get(record.bead.id);
      if (
        current.assignee !== owner(id) ||
        current.status !== "in_progress" ||
        current.metadata["pi.attempt"] !== id
      )
        throw new Error("This lead no longer owns the task");
      db.change(id, (row) => {
        row.bead = current;
        row.revision = current.revision;
        row.leadPlan = { mode: LeadMode.Planning, draft: null };
      });
      applyTools(ctx);
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
      const digest = planDigest(draft);
      approvalPending(true);
      try {
        if (
          !(await ctx.ui.confirm(
            `Approve the plan for ${record.bead.id}`,
            describePlan(draft),
          ))
        )
          return;
        await beads.requireCurrent(record.bead, revision, id);
        db.change(id, (row) => {
          if (
            row.leadPlan?.mode !== LeadMode.Planning ||
            row.leadPlan.draft === null ||
            planDigest(row.leadPlan.draft) !== digest ||
            row.revision !== revision
          )
            throw new Error("The displayed plan or task revision changed");
          row.leadPlan = { mode: LeadMode.Applying, draft, digest };
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
              row.leadPlan = { mode: LeadMode.Planning, draft: null };
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
            children: result.children,
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
