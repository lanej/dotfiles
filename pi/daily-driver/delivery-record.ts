import { z } from "zod";
export const sha = z.string().regex(/^[0-9a-f]{40}$/u);
export const prUrl = z
  .string()
  .regex(/^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/pull\/[1-9]\d*$/u);
export const identifier = z.string().min(1);
export const deliverySchema = z.object({
  requestId: identifier,
  requestDigest: identifier,
  head: sha,
  octoSubmission: identifier.optional(),
  url: prUrl.optional(),
  pr: identifier.optional(),
  agent: identifier.optional(),
  merge: z
    .object({
      notice: z.uuid(),
      head: sha,
      chain: identifier,
      entry: identifier,
    })
    .optional(),
  inbox: z
    .record(
      z.string(),
      z.object({
        id: identifier,
        body: z.string(),
        acknowledged: z.boolean(),
      }),
    )
    .default({}),
});
