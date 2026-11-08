import { readFileSync, realpathSync } from "node:fs";
import { isAbsolute } from "node:path";
import { z } from "zod";

const score = z.number().finite().min(0).max(1).nullable();
export const repositoryPolicy = z.object({
  directory: z.string().refine(isAbsolute, "Use an absolute repository directory"),
  github: z.string().regex(/^[A-Za-z0-9-]+\/[A-Za-z0-9_.-]+$/),
  remote: z.string().regex(/^[A-Za-z0-9][A-Za-z0-9_.-]*$/).default("origin"),
  minimumConfidence: z.number().finite().min(0).max(1),
  confidence: z.object({ git: score, rerere: score, mergiraf: score }).strict(),
  checks: z.array(z.array(z.string().min(1)).min(1).max(100)).min(1).max(20),
  timeoutSeconds: z.number().int().min(1).max(1800).default(120),
  maxChangedFiles: z.number().int().min(1).max(1000).default(50),
  maxDiffBytes: z.number().int().min(1).max(8 * 1024 * 1024).default(512 * 1024),
}).strict();
export const maintenanceConfig = z.object({
  version: z.literal(1), repositories: z.array(repositoryPolicy).max(100),
}).strict();
export type RepositoryPolicy = z.infer<typeof repositoryPolicy>;
export type Strategy = keyof RepositoryPolicy["confidence"];
export function readMaintenancePolicy(file: string, directory: string | null): RepositoryPolicy | null {
  let raw: string;
  try { raw = readFileSync(file, "utf8"); }
  catch (error) { if ((error as NodeJS.ErrnoException).code === "ENOENT") return null; throw error; }
  const config = maintenanceConfig.parse(JSON.parse(raw));
  if (!directory) return null;
  const canonical = realpathSync(directory);
  const matches = config.repositories.filter(value => realpathSync(value.directory) === canonical);
  if (matches.length > 1) throw new Error("Multiple PR maintenance policies select this repository");
  return matches[0] ? { ...matches[0], directory: canonical } : null;
}
