import { createHash } from "node:crypto";
import { z } from "zod";

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
        }),
      )
      .max(12),
  })
  .superRefine((draft, ctx) => {
    const known = new Set<string>();
    for (const [index, task] of draft.tasks.entries()) {
      if (known.has(task.key)) {
        ctx.addIssue({
          code: "custom",
          path: ["tasks", index, "key"],
          message: "Task keys must be unique",
        });
      }
      if (
        new Set(task.blockedBy).size !== task.blockedBy.length ||
        task.blockedBy.some((key) => !known.has(key) || key === task.key)
      ) {
        ctx.addIssue({
          code: "custom",
          path: ["tasks", index, "blockedBy"],
          message:
            "Name each blocker once and list it before the dependent task",
        });
      }
      known.add(task.key);
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
export const leadPlanSchema = z.discriminatedUnion("mode", [
  z.strictObject({
    mode: z.literal(LeadMode.Planning),
    draft: draftSchema.nullable(),
  }),
  z.strictObject({
    mode: z.literal(LeadMode.Applying),
    draft: draftSchema,
    digest: z.string(),
  }),
  z.strictObject({
    mode: z.literal(LeadMode.Implementing),
    draft: draftSchema,
    digest: z.string(),
    children: z.record(taskKey, z.string().min(1)),
  }),
]);

export function planDigest(draft: LeadDraft): string {
  return createHash("sha256").update(JSON.stringify(draft)).digest("hex");
}

export function describePlan(draft: LeadDraft): string {
  return [
    draft.summary,
    ...draft.tasks.map((task) =>
      [
        "",
        `${task.key} · ${task.title}`,
        task.description,
        `Acceptance · ${task.acceptance}`,
        ...(task.blockedBy.length > 0
          ? [`Blocked by · ${task.blockedBy.join(", ")}`]
          : []),
      ].join("\n"),
    ),
  ].join("\n");
}
