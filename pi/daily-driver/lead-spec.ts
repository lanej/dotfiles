import { z } from "zod";

export enum SpecStatus {
  Interrogating = "interrogating",
  Frozen = "frozen",
}

const text = z.string().trim().min(1).max(2000);
const requirementId = z.string().regex(/^R[1-9]\d*$/u);
export const specDraft = z
  .strictObject({
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
      .max(20),
    decisions: z
      .array(
        z.strictObject({
          decision: text,
          basis: z.enum(["observed", "decided", "assumed"]),
          evidence: text,
        }),
      )
      .max(20),
    blockingQuestions: z.array(text).max(12),
  })
  .superRefine((value, ctx) => {
    if (
      new Set(value.requirements.map((entry) => entry.id)).size !==
      value.requirements.length
    )
      ctx.addIssue({
        code: "custom",
        message: "Requirement IDs must be unique",
      });
  });

export const specRecord = z.strictObject({
  status: z.enum(SpecStatus),
  version: z.number().int().positive(),
  draft: specDraft.nullable(),
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
    ...draft.decisions.map(
      (decision) =>
        `${decision.decision} · ${decision.basis}: ${decision.evidence}`,
    ),
    "",
    ...(draft.blockingQuestions.length > 0
      ? ["Open questions", ...draft.blockingQuestions]
      : []),
  ].join("\n");
}
