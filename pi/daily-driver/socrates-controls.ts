import type {
  ExtensionAPI,
  ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import type { Attempt, Attempts } from "./attempts.ts";
import { LeadMode } from "./lead-plan.ts";
import { SpecStatus, specDraft, specText } from "./lead-spec.ts";
import { TaskBeads } from "./task-service.ts";
import { reviewPlan, showTask } from "./ui.ts";

export const specTool = "draft_socrates_specification";

export function registerSocrates(
  pi: ExtensionAPI,
  db: Attempts,
  id: string,
  requireBinding: (ctx: ExtensionContext) => Promise<Attempt>,
  approvalPending: (active: boolean) => void,
) {
  pi.registerCommand("socrates", {
    description: "Start or inspect Socrates discovery for this Beads task",
    async handler(_argument, ctx) {
      if (!ctx.isIdle()) throw new Error("Wait for the lead turn to settle");
      const record = await requireBinding(ctx);
      if (record.specification !== undefined) {
        approvalPending(true);
        try {
          await showTask(ctx, specText(record.specification));
        } finally {
          approvalPending(false);
        }
        return;
      }
      if (
        record.revision === null ||
        record.leadPlan?.mode !== LeadMode.Planning
      )
        throw new Error("Start Socrates before approving implementation");
      const acceptedRevision = record.revision;
      db.change(id, (row) => {
        if (
          row.specification !== undefined ||
          row.leadPlan?.mode !== LeadMode.Planning ||
          row.revision !== acceptedRevision
        )
          throw new Error("The planning session changed");
        row.specification = {
          status: SpecStatus.Interrogating,
          version: 1,
          draft: null,
          acceptedRevision,
        };
        row.leadPlan = { ...row.leadPlan, draft: null };
      });
      pi.sendUserMessage(
        "Begin Socrates discovery for this bead. Establish the objective, scope, observable acceptance criteria and evidence. Ask about blocking choices. Save the proposed specification with draft_socrates_specification.",
      );
    },
  });
  pi.registerTool({
    name: specTool,
    label: "Draft Socrates specification",
    description:
      "Save the current Socrates specification and outstanding questions. The operator freezes it in /spec-freeze.",
    parameters: Type.Object({
      objective: Type.String(),
      scope: Type.Array(Type.String()),
      requirements: Type.Array(
        Type.Object({
          id: Type.String(),
          outcome: Type.String(),
          acceptance: Type.String(),
        }),
      ),
      decisions: Type.Array(
        Type.Object({
          decision: Type.String(),
          basis: Type.Union([
            Type.Literal("observed"),
            Type.Literal("decided"),
            Type.Literal("assumed"),
          ]),
          evidence: Type.String(),
        }),
      ),
      blockingQuestions: Type.Array(Type.String()),
    }),
    async execute(_call, params, _signal, _update, ctx) {
      await requireBinding(ctx);
      const draft = specDraft.parse(params);
      db.change(id, (row) => {
        const specification = row.specification;
        if (
          specification?.status !== SpecStatus.Interrogating ||
          specification.acceptedRevision !== row.revision
        )
          throw new Error("Start or refresh Socrates before drafting");
        row.specification = { ...specification, draft };
      });
      return {
        content: [
          {
            type: "text",
            text:
              draft.blockingQuestions.length > 0
                ? "Draft saved. Resolve the blocking questions with the operator."
                : "Draft saved. The operator can inspect it with /socrates and freeze it with /spec-freeze.",
          },
        ],
        details: {},
      };
    },
  });
  pi.registerCommand("spec-freeze", {
    description: "Freeze the reviewed Socrates specification",
    async handler(_argument, ctx) {
      if (!ctx.isIdle()) throw new Error("Wait for the lead turn to settle");
      const record = await requireBinding(ctx);
      const spec = record.specification;
      if (
        spec?.status !== SpecStatus.Interrogating ||
        spec.draft === null ||
        spec.draft.blockingQuestions.length > 0 ||
        record.revision !== spec.acceptedRevision
      )
        throw new Error(
          "Resolve the blocking questions and draft against the current Beads brief",
        );
      approvalPending(true);
      try {
        if (
          !(await reviewPlan(
            ctx,
            `Freeze specification for ${record.bead.id}`,
            specText(spec),
            "freeze spec",
          ))
        )
          return;
        await new TaskBeads(record.source).requireCurrent(
          record.bead,
          spec.acceptedRevision,
          id,
        );
        db.change(id, (row) => {
          if (
            JSON.stringify(row.specification) !== JSON.stringify(spec) ||
            row.leadPlan?.mode !== LeadMode.Planning ||
            row.revision !== spec.acceptedRevision
          )
            throw new Error("The displayed specification changed");
          row.specification = {
            ...spec,
            status: SpecStatus.Frozen,
            approvalAt: new Date().toISOString(),
          };
        });
      } finally {
        approvalPending(false);
      }
      pi.sendUserMessage(
        "The operator froze the Socrates specification. Draft its implementation graph. Link each task to requirement IDs and own only normalized worktree-relative paths. Wait for /plan-approve before editing.",
      );
    },
  });
}
