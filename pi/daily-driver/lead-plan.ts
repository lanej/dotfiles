import { createHash } from "node:crypto";
import { z } from "zod";
import { taskWaves } from "./smart-plan-graph.ts";
import { worktreeRelativePath } from "./worktree-path.ts";

export enum LeadMode {
  Planning = "planning",
  Applying = "applying",
  Implementing = "implementing",
}

const taskKey = z.string().regex(/^[a-z][a-z0-9-]{0,31}$/u);
export const draftSchema = z
  .strictObject({
    summary: z.string().trim().min(1).max(8000),
    tasks: z
      .array(
        z.strictObject({
          key: taskKey,
          title: z.string().trim().min(1).max(200),
          description: z.string().trim().min(1).max(2000),
          acceptance: z.string().trim().min(1).max(2000),
          blockedBy: z.array(taskKey).max(12).default([]),
          requirements: z
            .array(z.string().regex(/^R[1-9]\d*$/u))
            .max(20)
            .default([]),
          owns: z.array(worktreeRelativePath).max(20).default([]),
        }),
      )
      .max(12),
  })
  .superRefine((draft, ctx) => {
    try {
      taskWaves(draft.tasks);
    } catch (error) {
      ctx.addIssue({
        code: "custom",
        path: ["tasks"],
        message: error instanceof Error ? error.message : String(error),
      });
    }
    if (
      1 +
        2 * draft.tasks.length +
        draft.tasks.reduce((count, task) => count + task.blockedBy.length, 0) >
      100
    )
      ctx.addIssue({
        code: "custom",
        path: ["tasks"],
        message: "The task graph exceeds one atomic Beads batch",
      });
  });

export type LeadDraft = z.infer<typeof draftSchema>;
const childBeads = z.record(taskKey, z.string().min(1));
export const leadPlanSchema = z.discriminatedUnion("mode", [
  z.strictObject({
    mode: z.literal(LeadMode.Planning),
    draft: draftSchema.nullable(),
    children: childBeads.optional(),
  }),
  z.strictObject({
    mode: z.literal(LeadMode.Applying),
    draft: draftSchema,
    digest: z.string(),
    specificationVersion: z.number().int().positive().optional(),
    children: childBeads.optional(),
  }),
  z.strictObject({
    mode: z.literal(LeadMode.Implementing),
    draft: draftSchema,
    digest: z.string(),
    specificationVersion: z.number().int().positive().optional(),
    children: childBeads,
  }),
]);

export function planDigest(draft: LeadDraft): string {
  return createHash("sha256").update(JSON.stringify(draft)).digest("hex");
}

// Wave grouping adapts Smart Plan's src/render.ts at 3e51e33acd63a7743391e21598042438746aafa0.
export function orderedTasks(draft: LeadDraft): LeadDraft["tasks"] {
  const waves = taskWaves(draft.tasks);
  return [...draft.tasks].sort(
    (left, right) => (waves.get(left.key) ?? 0) - (waves.get(right.key) ?? 0),
  );
}

export function describePlan(draft: LeadDraft): string {
  const waves = taskWaves(draft.tasks);
  let displayedWave = 0;
  return [
    draft.summary,
    ...orderedTasks(draft).flatMap((task) => {
      const wave = waves.get(task.key) ?? 0;
      const heading =
        wave === displayedWave ? [] : ["", `Wave ${String(wave)}`];
      displayedWave = wave;
      return [
        ...heading,
        "",
        `├─ ${task.key} · ${task.title}`,
        task.description,
        `Acceptance · ${task.acceptance}`,
        ...(task.requirements.length > 0
          ? [`Requirements · ${task.requirements.join(", ")}`]
          : []),
        ...(task.owns.length > 0 ? [`Owns · ${task.owns.join(", ")}`] : []),
        ...(task.blockedBy.length > 0
          ? [`Blocked by · ${task.blockedBy.join(", ")}`]
          : []),
      ];
    }),
  ].join("\n");
}
