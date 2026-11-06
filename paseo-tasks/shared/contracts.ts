import { defineRpc } from "@getpaseo/plugin";
import { z } from "zod";

export const address = z.object({ serverId: z.string().min(1), taskId: z.uuid() }).strict();
export const conversationAddress = z.object({ serverId: z.string().min(1), agentId: z.string().min(1) }).strict();
export const brief = z.object({
  title: z.string().trim().min(1).max(200),
  outcome: z.string().trim().max(8000),
  successCriteria: z.array(z.string().trim().min(1).max(2000)).max(30),
  constraints: z.array(z.string().trim().min(1).max(2000)).max(30),
  kind: z.enum(["coding", "investigation", "planning", "decision"]),
  repository: z.string().min(1).nullable(),
  baseRef: z.string().min(1).nullable(),
}).strict();
export const workStatus = z.enum(["draft", "active", "question", "blocked", "decision", "complete"]);
export const update = z.object({
  approach: z.string().max(8000).optional(),
  progress: z.string().max(8000).optional(),
  evidence: z.array(z.string().max(4000)).max(50).optional(),
  blocker: z.string().max(4000).nullable().optional(),
  nextAction: z.string().max(4000).optional(),
  status: workStatus.exclude(["draft"]).optional(),
}).strict();
export const treehouseReservation = z.object({
  primary: z.string(), root: z.string(), branch: z.string(), baseRef: z.string(),
  baseCommit: z.string(), treehouseBase: z.string(),
  holder: z.string(), attempted: z.boolean(),
}).strict();
export const treehouseLease = z.object({
  path: z.string(), lease_id: z.string(), lease_holder: z.string(), leased_at: z.string(),
  base_branch: z.string(), branch: z.string(), primary: z.string(), root: z.string(),
}).strict();
export const prWatch = z.object({
  url: z.string(), head: z.string(), base: z.string(),
  phase: z.enum(["checks", "repair", "review", "unknown", "closed"]),
  detail: z.string(), observedAt: z.string(),
});
export const task = brief.extend({
  ...address.shape,
  revision: z.number().int().positive(),
  status: workStatus,
  control: z.enum(["running", "pausing", "paused", "archiving", "archived"]),
  priority: z.number().int().min(0).max(100),
  group: z.string().max(200).nullable(),
  worker: z.object({ agentId: z.string(), workspaceId: z.string(), cwd: z.string() }).nullable(),
  coordinator: conversationAddress.nullable().default(null),
  coordinatorReport: z.object({
    id: z.uuid(), delivery: z.enum(["queued", "sending", "received", "unknown", "superseded"]),
    error: z.string().nullable(),
  }).nullable().default(null),
  treehouseReservation: treehouseReservation.nullable().default(null),
  treehouseLease: treehouseLease.nullable().default(null),
  prWatches: z.array(prWatch).default([]),
  activity: z.enum(["unknown", "idle", "running", "failed", "question", "closed"]),
  approach: z.string(),
  progress: z.string(),
  evidence: z.array(z.string()),
  blocker: z.string().nullable(),
  nextAction: z.string(),
  github: z.array(z.string()),
  proposals: z.array(z.object({ id: z.uuid(), brief, accepted: z.boolean() })),
  launch: z.enum(["none", "reserved", "creating", "bound", "unknown"]),
  lastCompletedTurn: z.string().nullable().default(null),
  createdAt: z.string(),
  updatedAt: z.string(),
  observedAt: z.string().nullable(),
  error: z.string().nullable(),
  migration: z.object({
    home: z.string(), legacyId: z.string(), generation: z.string(),
    sessionFile: z.string().nullable(), sessionId: z.string().nullable(),
    ownership: z.enum(["firstmate", "released", "tasks"]),
  }).nullable(),
}).strict();
export type Task = z.infer<typeof task>;
export type Brief = z.infer<typeof brief>;
export type Address = z.infer<typeof address>;
export type Update = z.infer<typeof update>;
export type ConversationAddress = z.infer<typeof conversationAddress>;
export const coordinatorReport = z.object({
  id: z.uuid(), coordinator: conversationAddress, task, createdAt: z.string(),
}).strict().refine(value => value.task.worker !== null &&
  value.task.coordinator?.agentId === value.coordinator.agentId &&
  value.task.coordinator?.serverId === value.coordinator.serverId, "Report must name its assigned worker and coordinator");
export type CoordinatorReport = z.infer<typeof coordinatorReport>;
export const outgoingReport = z.object({
  report: coordinatorReport,
  delivery: z.enum(["queued", "sending", "received", "unknown", "superseded"]),
  error: z.string().nullable(),
});
export const incomingReport = z.object({
  report: coordinatorReport,
  delivery: z.enum(["queued", "sending", "awaiting", "accepted", "unknown", "superseded"]),
  error: z.string().nullable(),
});
export type OutgoingReport = z.infer<typeof outgoingReport>;
export type IncomingReport = z.infer<typeof incomingReport>;
export const ready = (value: Brief, existingCheckout = false) => !!value.outcome && value.successCriteria.length > 0 &&
  (value.kind !== "coding" || !!value.repository && (existingCheckout || !!value.baseRef));
export const control = z.enum(["pause", "resume", "archive", "reprioritize"]);
export const controlInput = z.object({
  tasks: z.array(address).min(1).max(100),
  action: control,
  priority: z.number().int().min(0).max(100).optional(),
}).strict();
export const controlResult = z.object({
  ...address.shape, result: z.enum(["applied", "pending", "failed", "unknown"]), message: z.string(),
});
export const event = z.object({
  id: z.string(), taskId: z.uuid(), kind: z.enum(["start", "continue", "feedback", "github"]),
  body: z.string(), source: z.string().nullable(), payload: z.record(z.string(), z.unknown()),
  delivery: z.enum(["queued", "sending", "accepted", "unknown", "handled"]),
  createdAt: z.string(), receipt: z.string().nullable(),
});
export type TaskEvent = z.infer<typeof event>;
export const hostSnapshot = z.object({
  serverId: z.string(), label: z.string(), connection: z.string(),
  observedAt: z.string().nullable(), error: z.string().nullable(), tasks: z.array(task),
});
export const listRpc = defineRpc({
  name: "tasks.list", input: z.object({ aggregate: z.boolean().default(true) }),
  output: z.array(hostSnapshot),
});
export const createInput = z.object({
  serverId: z.string(), brief, start: z.boolean().default(true),
  group: z.string().max(200).nullable().default(null),
  requestId: z.uuid(),
  coordinator: conversationAddress.nullable().default(null),
});
export const createRpc = defineRpc({ name: "tasks.create", input: createInput, output: task });
export const bulkRpc = defineRpc({ name: "tasks.bulk", input: controlInput, output: z.array(controlResult) });
export const acceptRpc = defineRpc({
  name: "tasks.accept", input: address.extend({ proposalId: z.uuid(), revision: z.number().int() }), output: task,
});
export const discoverRpc = defineRpc({
  name: "tasks.discover", input: z.object({ serverId: z.string() }),
  output: z.array(z.object({
    serverId: z.string(), agentId: z.string(), workspaceId: z.string().nullable(),
    title: z.string(), cwd: z.string(), provider: z.string(), activity: z.string(),
  })),
});
export const adoptRpc = defineRpc({
  name: "tasks.adopt", input: createInput.extend({ agentId: z.string() }), output: task,
});
export const managerRpc = defineRpc({
  name: "tasks.manager", input: z.object({ cwd: z.string().min(1) }), output: z.object({ agentId: z.string(), serverId: z.string() }),
});
export const migrateRpc = defineRpc({
  name: "tasks.migrate", input: address, output: task,
});
