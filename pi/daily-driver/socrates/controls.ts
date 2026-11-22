import type {
  ExtensionAPI,
  ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import { Text } from "@earendil-works/pi-tui";
import { isDeepStrictEqual } from "node:util";
import { Type } from "typebox";
import type { Attempt, Attempts } from "../attempts.ts";
import { LeadMode } from "../lead-plan.ts";
import {
  DecisionDisposition,
  SpecStatus,
  isTrackedDecision,
  preserveDecisions,
  specDraft,
  specQuestion,
  specText,
  type SpecQuestion,
} from "./spec.ts";
import { questionEvidenceParameter } from "./evidence.ts";
import { questionLinks, renderQuestionEvidence } from "./links.ts";
import { chooseQuestion, QuestionSelectionKind } from "./selector.ts";
import { socratesGuidance } from "./guidance.ts";
import { TaskBeads } from "../task-service.ts";
import { reviewPlan, showTask } from "../ui.ts";

export const askTool = "ask_user_question";
export const specTool = "draft_socrates_specification";

export function registerSocrates(
  pi: ExtensionAPI,
  db: Attempts,
  id: string,
  requireBinding: (ctx: ExtensionContext) => Promise<Attempt>,
  approvalPending: (active: boolean) => void,
) {
  async function showQuestion(
    ctx: ExtensionContext,
    spec: NonNullable<Attempt["specification"]>,
    signal?: AbortSignal,
  ) {
    const exchange = spec.exchange;
    if (exchange === undefined || exchange.answer !== undefined)
      throw new Error("There is no unanswered Socrates question");
    if (!ctx.hasUI) throw new Error("Open the managed Pi TUI to answer");
    const record = await requireBinding(ctx);
    const beads = new TaskBeads(record.source);
    await beads.requireCurrent(record.bead, spec.acceptedRevision, id);
    approvalPending(true);
    try {
      const answer = await ask(ctx, exchange.prompt, signal);
      if (answer === undefined) return undefined;
      await requireBinding(ctx);
      await beads.requireCurrent(record.bead, spec.acceptedRevision, id);
      db.change(id, (row) => {
        if (
          row.leadPlan?.mode !== LeadMode.Planning ||
          row.revision !== spec.acceptedRevision ||
          !isDeepStrictEqual(row.specification, spec)
        )
          throw new Error(
            "This Socrates question changed before the answer was saved",
          );
        row.specification = { ...spec, exchange: { ...exchange, answer } };
      });
      return answer;
    } finally {
      approvalPending(false);
    }
  }

  pi.registerTool({
    name: askTool,
    label: "Ask a question",
    description:
      "Ask one open Socrates decision from the saved draft. Use an empty options list for free text. A cancelled dialog leaves the question open until the operator invokes /socrates.",
    executionMode: "sequential",
    renderCall(_args, theme) {
      return new Text(
        theme.fg("toolTitle", theme.bold("Ask a question")),
        0,
        0,
      );
    },
    parameters: Type.Object({
      decisionId: Type.String(),
      question: Type.String(),
      context: Type.Optional(
        Type.String({
          description:
            "Optional question context, rendered as Markdown in the detail view",
        }),
      ),
      evidence: questionEvidenceParameter,
      options: Type.Array(
        Type.Object({
          label: Type.String(),
          description: Type.String({
            description: "Short tradeoff shown beside the choice",
          }),
          details: Type.Optional(
            Type.String({
              description:
                "Longer Markdown explanation shown in the preview and detail view",
            }),
          ),
          evidence: questionEvidenceParameter,
        }),
        { maxItems: 4 },
      ),
    }),
    async execute(_call, params, signal, _update, ctx) {
      if (!ctx.hasUI) throw new Error("Open the managed Pi TUI to answer");
      const record = await requireBinding(ctx);
      const prompt = specQuestion.parse(params);
      const spec = record.specification;
      if (
        spec?.status !== SpecStatus.Interrogating ||
        record.leadPlan?.mode !== LeadMode.Planning ||
        spec.acceptedRevision !== record.revision ||
        spec.exchange !== undefined
      )
        throw new Error(
          "Resolve the saved Socrates question before asking another",
        );
      if (
        spec.draft?.blockingQuestions.includes(prompt.question) !== true ||
        !spec.draft.decisions.some(
          (entry) =>
            isTrackedDecision(entry) &&
            entry.id === prompt.decisionId &&
            entry.disposition === DecisionDisposition.Open,
        )
      )
        throw new Error(
          "Save this exact question and its open decision in the draft first",
        );
      await new TaskBeads(record.source).requireCurrent(
        record.bead,
        spec.acceptedRevision,
        id,
      );
      const pending = { ...spec, exchange: { prompt } };
      db.change(id, (row) => {
        if (
          row.leadPlan?.mode !== LeadMode.Planning ||
          row.revision !== spec.acceptedRevision ||
          !isDeepStrictEqual(row.specification, spec)
        )
          throw new Error("The Socrates draft changed before asking");
        row.specification = pending;
      });
      const answer = await showQuestion(ctx, pending, signal);
      return {
        content: [
          {
            type: "text",
            text:
              answer === undefined
                ? "Question remains open. Wait for the operator to resume with /socrates."
                : `Operator answer for ${prompt.decisionId}: ${answer.text}`,
          },
        ],
        details: { answer, decisionId: prompt.decisionId },
      };
    },
  });

  pi.registerCommand("socrates", {
    description: "Start or inspect Socrates discovery for this Beads task",
    async handler(_argument, ctx) {
      if (!ctx.isIdle()) throw new Error("Wait for the lead turn to settle");
      const record = await requireBinding(ctx);
      const spec = record.specification;
      if (spec?.status === SpecStatus.Interrogating) {
        await socratesGuidance();
        if (record.revision !== spec.acceptedRevision)
          throw new Error("Refresh the Socrates brief before resuming");
        await new TaskBeads(record.source).requireCurrent(
          record.bead,
          spec.acceptedRevision,
          id,
        );
        if (spec.exchange !== undefined) {
          if (
            spec.exchange.answer !== undefined ||
            (await showQuestion(ctx, spec)) !== undefined
          )
            pi.sendUserMessage(
              "Resume Socrates discovery using the recorded operator answer.",
            );
          return;
        }
        if (
          spec.draft === null ||
          spec.draft.blockingQuestions.length > 0 ||
          !specDraft.safeParse(spec.draft).success
        ) {
          pi.sendUserMessage(
            "Resume Socrates discovery for the accepted bead.",
          );
          return;
        }
      }
      if (spec !== undefined) {
        approvalPending(true);
        try {
          await showTask(ctx, specText(spec));
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
      await socratesGuidance();
      const acceptedRevision = record.revision;
      await new TaskBeads(record.source).requireCurrent(
        record.bead,
        acceptedRevision,
        id,
      );
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
        "Begin Socrates discovery for the accepted bead using the shared procedure.",
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
          id: Type.String(),
          decision: Type.String(),
          disposition: Type.Enum(DecisionDisposition),
          uncertainty: Type.String({
            description:
              "Remaining uncertainty, consequence, and check, or None",
          }),
          supersedes: Type.Optional(Type.String()),
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
      const record = await requireBinding(ctx);
      const draft = specDraft.parse(params);
      if (record.revision === null)
        throw new Error("The accepted revision is missing");
      await new TaskBeads(record.source).requireCurrent(
        record.bead,
        record.revision,
        id,
      );
      db.change(id, (row) => {
        const specification = row.specification;
        if (
          specification?.status !== SpecStatus.Interrogating ||
          specification.acceptedRevision !== row.revision ||
          record.revision !== row.revision ||
          row.leadPlan?.mode !== LeadMode.Planning
        )
          throw new Error("Start or refresh Socrates before drafting");
        if (
          specification.exchange !== undefined &&
          specification.exchange.answer === undefined
        )
          throw new Error(
            "Resume /socrates to resolve the open question before replacing the draft",
          );
        preserveDecisions(specification.draft, draft);
        row.specification = { ...specification, draft, exchange: undefined };
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
        spec.exchange !== undefined ||
        !specDraft.safeParse(spec.draft).success ||
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
            !isDeepStrictEqual(row.specification, spec) ||
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

async function ask(
  ctx: ExtensionContext,
  prompt: SpecQuestion,
  signal?: AbortSignal,
) {
  const aborted = () => signal?.aborted === true;
  const options = signal === undefined ? undefined : { signal };
  if (aborted()) return undefined;
  if (prompt.options.length > 0) {
    const selected = await chooseQuestion(ctx, prompt, signal);
    if (selected === undefined || aborted()) return undefined;
    if (selected.kind === QuestionSelectionKind.Choice) {
      const choice = prompt.options[selected.index];
      if (choice === undefined)
        throw new Error("Pi returned an unknown choice");
      return { kind: "option" as const, text: choice.label };
    }
  }
  const title = [
    questionLinks(prompt.question),
    ...(prompt.context === undefined ? [] : [questionLinks(prompt.context)]),
    ...(prompt.evidence ?? []).map((item) =>
      renderQuestionEvidence(item, ctx.cwd),
    ),
  ].join("\n\n");
  const text = (await ctx.ui.input(title, undefined, options))?.trim();
  if (text === undefined || text.length === 0 || aborted()) return undefined;
  if (text.length > 2000)
    throw new Error("Use at most 2000 characters in a Socrates answer");
  return { kind: "custom" as const, text };
}
