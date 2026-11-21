import { z } from "zod";

export const worktreeReservation = z
  .object({
    primary: z.string(),
    root: z.string(),
    holder: z.string(),
    agent: z.string(),
    branch: z.string(),
    baseRef: z.string(),
    baseCommit: z.string(),
    attempted: z.boolean(),
  })
  .strict();
export const worktreeAllocation = z
  .object({
    primary: z.string(),
    root: z.string(),
    path: z.string(),
    task_id: z.string(),
    owner_id: z.string(),
    agent: z.string(),
    branch: z.string(),
    created_at: z.string(),
    base_ref: z.string(),
  })
  .strict();
