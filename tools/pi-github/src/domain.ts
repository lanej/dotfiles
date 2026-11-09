import { createHash } from "node:crypto";

export type Status = "queued" | "running" | "conflicted" | "resolving" | "retry_wait" | "cancelling" | "cancelled" | "succeeded" | "failed" | "interrupted";
export type Task = { kind: "summarize_pr"; url: string } | { kind: "resolve_conflict" };
export interface Attempt { number: number; startedAt: number; endedAt?: number; pid?: number; exitObservedAt?: number; error?: string }
export interface Job {
  id: string; requestId: string; digest: string; task: Task; status: Status;
  createdAt: number; updatedAt: number; attempts: Attempt[]; retryCount: number;
  availableAt: number; result?: string; error?: string; fixture?: string;
}
export interface JobEvent { seq: number; jobId: string; at: number; kind: string; detail: string }
export interface Snapshot { scheduler: "running" | "paused" | "stopping" | "stopped"; worker: "idle" | "busy" | "recovering"; jobs: Job[]; events: JobEvent[]; recoveryPid?: number }
export const activeStates: Status[] = ["running", "conflicted", "resolving", "cancelling"];
export const terminalStates: Status[] = ["succeeded", "failed", "cancelled", "interrupted"];
const edges: Record<Status, Status[]> = {
  queued: ["running", "cancelled"], running: ["conflicted", "succeeded", "failed", "retry_wait", "cancelling", "interrupted"],
  conflicted: ["resolving", "failed", "retry_wait", "cancelling", "interrupted"],
  resolving: ["succeeded", "failed", "retry_wait", "cancelling", "interrupted"],
  retry_wait: ["queued", "cancelled"], cancelling: ["cancelled", "interrupted"],
  cancelled: [], succeeded: [], failed: ["queued"], interrupted: ["queued"],
};
export function transition(job: Job, next: Status, now: number): Job {
  if (!edges[job.status].includes(next)) throw new Error(`Invalid transition: ${job.status} -> ${next}`);
  return { ...job, status: next, updatedAt: now };
}
export function parseTask(value: unknown): Task {
  if (!value || typeof value !== "object") throw new Error("Task must be an object");
  const v = value as Record<string, unknown>;
  if (v.kind === "resolve_conflict" && Object.keys(v).length === 1) return { kind: v.kind };
  if (v.kind === "summarize_pr" && Object.keys(v).length === 2 && typeof v.url === "string") {
    const match = /^https:\/\/github\.com\/([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+)\/pull\/([1-9][0-9]*)\/?$/.exec(v.url);
    if (!match || match[1] === "." || match[1] === ".." || match[2] === "." || match[2] === "..") throw new Error("Expected a github.com pull request URL");
    return { kind: v.kind, url: v.url.replace(/\/$/, "") };
  }
  throw new Error("Unsupported task or fields");
}
export function digest(task: Task): string { return createHash("sha256").update(JSON.stringify(task)).digest("hex"); }
export function nextReady(jobs: Job[], now: number): Job | undefined {
  // WHY: The store supplies durable insertion order; wall-clock adjustments must not reorder accepted work.
  return jobs.find(j => j.status === "queued" && j.availableAt <= now);
}
export function retryDelay(retryCount: number): number | undefined { return [1000, 5000][retryCount]; }
export function cleanText(value: string, limit = 16000): string {
  return value.replace(/\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|$))/g, "").replace(/[\x00-\x08\x0b-\x1f\x7f]/g, "").slice(0, limit);
}
