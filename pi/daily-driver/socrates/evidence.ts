import { Type } from "typebox";
import { z } from "zod";
import { worktreeRelativePath } from "../worktree-path.ts";

const label = z.string().trim().min(1).max(2000);
const evidence = z.union([
  z.strictObject({
    label,
    url: z.url({ protocol: /^https?$/u, normalize: true }),
  }),
  z.strictObject({
    label,
    path: worktreeRelativePath,
    line: z.int().positive().optional(),
  }),
  z.strictObject({
    label,
    observation: z.string().trim().min(1).max(2000),
  }),
]);

export type QuestionEvidence = z.infer<typeof evidence>;
export const questionEvidence = z.array(evidence).max(8).optional();

export const questionEvidenceParameter = Type.Optional(
  Type.Array(
    Type.Union([
      Type.Object({
        label: Type.String(),
        url: Type.String({ description: "HTTP(S) evidence URL" }),
      }),
      Type.Object({
        label: Type.String(),
        path: Type.String({
          description: "Evidence path relative to the managed worktree",
        }),
        line: Type.Optional(Type.Integer({ minimum: 1 })),
      }),
      Type.Object({
        label: Type.String(),
        observation: Type.String({
          description: "Observed fact, command output, or log excerpt",
        }),
      }),
    ]),
    { maxItems: 8 },
  ),
);
