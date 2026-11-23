import { z } from "zod";
import { questionEvidence } from "./evidence.ts";

export enum SpecStatus {
  Interrogating = "interrogating",
  Frozen = "frozen",
}

export enum DecisionDisposition {
  Open = "open",
  Resolved = "resolved",
  AcceptedUncertainty = "accepted-uncertainty",
  Superseded = "superseded",
}

const text = z.string().trim().min(1).max(2000);
const requirementId = z.string().regex(/^R[1-9]\d*$/u);
const decisionId = z.string().regex(/^D[1-9]\d*$/u);
const legacyDecision = z.strictObject({
  decision: text,
  basis: z.enum(["observed", "decided", "assumed"]),
  evidence: text,
});
const decision = legacyDecision.extend({
  id: decisionId,
  disposition: z.enum(DecisionDisposition),
  uncertainty: text,
  supersedes: decisionId.optional(),
});

const draftFields = {
  objective: text,
  scope: z.array(text).min(1).max(20),
  requirements: z
    .array(
      z.strictObject({
        id: requirementId,
        outcome: text,
        acceptance: text,
      }),
    )
    .min(1)
    .max(20)
    .refine(
      (entries) => new Set(entries.map(({ id }) => id)).size === entries.length,
      "Requirement IDs must be unique",
    ),
  blockingQuestions: z.array(text).max(12),
};
const legacyDraft = z.strictObject({
  ...draftFields,
  decisions: z.array(legacyDecision).max(20),
});
export const specDraft = z
  .strictObject({
    ...draftFields,
    decisions: z.array(decision),
  })
  .superRefine((value, ctx) => {
    const decisions = new Map(
      value.decisions.map((entry) => [entry.id, entry]),
    );
    const replacements = value.decisions.flatMap((entry) =>
      entry.supersedes === undefined ? [] : [entry.supersedes],
    );
    if (
      decisions.size !== value.decisions.length ||
      new Set(replacements).size !== replacements.length ||
      value.decisions.some(
        (entry) =>
          (entry.disposition === DecisionDisposition.Superseded &&
            !replacements.includes(entry.id)) ||
          (entry.supersedes !== undefined &&
            (Number(entry.id.slice(1)) <= Number(entry.supersedes.slice(1)) ||
              decisions.get(entry.supersedes)?.disposition !==
                DecisionDisposition.Superseded)),
      )
    ) {
      ctx.addIssue({
        code: "custom",
        message:
          "Use unique decision IDs and link superseded decisions to their successors",
      });
    }
  });

export const specQuestion = z
  .strictObject({
    decisionId,
    question: text,
    context: text.optional(),
    evidence: questionEvidence,
    options: z
      .array(
        z.strictObject({
          label: text,
          description: text,
          details: text.optional(),
          evidence: questionEvidence,
        }),
      )
      .max(4),
  })
  .superRefine(({ options }, ctx) => {
    const labels = options.map(({ label }) => label);
    if (labels.length === 1 || new Set(labels).size !== labels.length) {
      ctx.addIssue({
        code: "custom",
        message: "Use zero options for text or two to four distinct choices",
      });
    }
  });
export type SpecQuestion = z.infer<typeof specQuestion>;

export const specRecord = z.strictObject({
  status: z.enum(SpecStatus),
  version: z.number().int().positive(),
  draft: z.union([specDraft, legacyDraft]).nullable(),
  exchange: z
    .strictObject({
      prompt: specQuestion,
      answer: z
        .strictObject({
          text,
          kind: z.enum(["option", "custom"]),
        })
        .optional(),
    })
    .optional(),
  acceptedRevision: z.string(),
  approvalAt: z.string().optional(),
});
export type LeadSpecification = z.infer<typeof specRecord>;

export function specText(spec: LeadSpecification): string {
  const draft = spec.draft;
  if (draft === null) return "No specification drafted yet.";
  return [
    `Socrates v${String(spec.version)} · ${spec.status}`,
    "",
    draft.objective,
    "",
    "Scope",
    ...draft.scope,
    "",
    "Requirements",
    ...draft.requirements.map(
      (requirement) =>
        `${requirement.id} · ${requirement.outcome}\nAcceptance · ${requirement.acceptance}`,
    ),
    "",
    "Decisions",
    ...draft.decisions.map((entry) => {
      const basis = `${entry.decision} · ${entry.basis}: ${entry.evidence}`;
      if (!isTrackedDecision(entry)) return basis;
      const history =
        entry.supersedes === undefined
          ? ""
          : ` · Supersedes ${entry.supersedes}`;
      return `${entry.id} · ${entry.disposition} · ${basis}\nUncertainty · ${entry.uncertainty}${history}`;
    }),
    "",
    ...(spec.exchange === undefined
      ? []
      : [
          `Question · ${spec.exchange.prompt.decisionId} · ${spec.exchange.prompt.question}`,
          ...(spec.exchange.answer === undefined
            ? []
            : [`Operator answer · ${spec.exchange.answer.text}`]),
          "",
        ]),
    ...(draft.blockingQuestions.length > 0
      ? ["Open questions", ...draft.blockingQuestions]
      : []),
  ].join("\n");
}

export function isTrackedDecision(
  entry: z.infer<typeof legacyDecision>,
): entry is z.infer<typeof decision> {
  return "id" in entry;
}
export function preserveDecisions(
  previous: LeadSpecification["draft"],
  next: z.infer<typeof specDraft>,
): void {
  for (const entry of previous?.decisions ?? []) {
    if (!isTrackedDecision(entry)) continue;
    const updated = next.decisions.find(({ id }) => id === entry.id);
    if (updated === undefined)
      throw new Error(`Retain decision ${entry.id} in the record`);
    if (entry.disposition === DecisionDisposition.Open) continue;
    const allowed =
      entry.disposition === DecisionDisposition.Superseded
        ? [entry.disposition]
        : [entry.disposition, DecisionDisposition.Superseded];
    if (
      !allowed.includes(updated.disposition) ||
      updated.decision !== entry.decision ||
      updated.basis !== entry.basis ||
      updated.evidence !== entry.evidence ||
      updated.uncertainty !== entry.uncertainty ||
      updated.supersedes !== entry.supersedes
    )
      throw new Error(
        `Preserve settled decision ${entry.id} and link a successor if it changed`,
      );
  }
}
