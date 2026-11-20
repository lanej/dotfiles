import createClient from "openapi-fetch";
import { fetch as nodeFetch } from "undici";
import { z } from "zod";
import { task, type Task } from "../shared/contracts";
import type { paths, components } from "./generated/beads";

const content = task
  .pick({
    title: true,
    outcome: true,
    successCriteria: true,
    constraints: true,
    kind: true,
    repository: true,
    baseRef: true,
    status: true,
    priority: true,
    group: true,
    approach: true,
    progress: true,
    evidence: true,
    blocker: true,
    nextAction: true,
    github: true,
  })
  .strip();
export type TaskContent = z.infer<typeof content>;
const attachment = content.extend({
  schema: z.literal(1),
  taskId: z.uuid(),
  serverId: z.string().min(1),
});
const issue = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string().default(""),
  acceptance_criteria: z.string().default(""),
  status: z.string(),
  priority: z.number().int().min(0).max(4),
  assignee: z.string().default(""),
  metadata: z
    .record(z.string(), z.unknown())
    .nullish()
    .transform((value) => value ?? {}),
});
type Issue = z.infer<typeof issue>;
const nativeStatus: Record<Task["status"], string> = {
  draft: "deferred",
  active: "in_progress",
  question: "blocked",
  blocked: "blocked",
  decision: "deferred",
  complete: "closed",
};
const fromStatus: Record<string, Task["status"]> = {
  open: "active",
  in_progress: "active",
  blocked: "blocked",
  deferred: "draft",
  closed: "complete",
};
const priority = (value: number) => Math.round((100 - value) / 25);
export const taskContent = (value: Task): TaskContent => content.parse(value);
const unpack = (metadata: Record<string, unknown>) =>
  Object.fromEntries(
    Object.entries(metadata)
      .filter(([key]) => key.startsWith("paseo."))
      .map(([key, value]) => [key.slice(6), value]),
  );
const pack = (value: Record<string, unknown>) =>
  Object.fromEntries(
    Object.entries(value).map(([key, entry]) => [`paseo.${key}`, entry]),
  );
export const beadId = (id: string) => `tasks-${z.uuid().parse(id)}`;
const actor = (value: Task, worker = value.worker?.agentId ?? value.taskId) =>
  `paseo:${value.serverId}/${worker}`;

export class BeadsError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly problem: unknown,
  ) {
    super(message);
  }
}

/** The service owns task content; SQLite retains local execution and delivery state. */
export class Beads {
  private readonly client;
  constructor(
    readonly url: string,
    readonly authority: string,
    token?: string,
  ) {
    const target = new URL(url);
    if (
      !["http:", "https:"].includes(target.protocol) ||
      target.username ||
      target.password ||
      target.search ||
      target.hash ||
      target.pathname !== "/"
    )
      throw new Error(
        "Beads URL must name an HTTP(S) service origin without credentials",
      );
    if (
      target.protocol === "http:" &&
      !["127.0.0.1", "localhost", "[::1]"].includes(target.hostname)
    )
      throw new Error(
        "Non-loopback Beads endpoints require HTTPS; use a loopback tunnel for private HTTP services",
      );
    z.uuid().parse(authority);
    this.client = createClient<paths>({
      baseUrl: target.origin,
      headers: {
        "Bd-Project-Id": authority,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      fetch: async (request) =>
        nodeFetch(request.url, {
          method: request.method,
          headers: Object.fromEntries(request.headers.entries()),
          body: request.body ? await request.text() : undefined,
          signal: AbortSignal.timeout(30_000),
          redirect: "error",
        }),
    });
  }
  private async result<T>(
    pending: Promise<{ data?: T; error?: unknown; response: Response }>,
  ): Promise<T> {
    const response = await pending;
    if (!response.response.ok || response.data === undefined) {
      const problem = z
        .object({ code: z.string().optional(), reason: z.string().optional() })
        .passthrough()
        .safeParse(response.error);
      throw new BeadsError(
        `Beads HTTP ${response.response.status}${problem.success ? `: ${problem.data.code ?? "unknown"} ${problem.data.reason ?? ""}` : ""}`,
        response.response.status,
        response.error,
      );
    }
    return response.data;
  }
  async verifyAuthority() {
    const context = await this.result(this.client.GET("/v0/beads/context"));
    if (
      context.project_id !== this.authority ||
      context.backend !== "dolt" ||
      context.dolt_mode !== "server"
    )
      throw new Error(
        "Beads authority differs from configured service project; refusing foreign or embedded storage",
      );
    for (const capability of [
      "project.enforce",
      "issues.get",
      "issues.create",
      "issues.update",
    ])
      if (!context.capabilities?.includes(capability))
        throw new Error(
          `Beads service lacks required capability: ${capability}`,
        );
  }
  private async readIssue(
    value: Pick<Task, "taskId" | "serverId">,
  ): Promise<Issue> {
    await this.verifyAuthority();
    const observed = issue.parse(
      await this.result(
        this.client.GET("/v0/beads/issues/{id}", {
          params: { path: { id: beadId(value.taskId) } },
        }),
      ),
    );
    if (observed.id !== beadId(value.taskId))
      throw new Error("Beads task identity is ambiguous");
    const saved = attachment.parse(unpack(observed.metadata));
    if (saved.taskId !== value.taskId || saved.serverId !== value.serverId)
      throw new Error("Beads task belongs to another host or task");
    return observed;
  }
  async read(value: Task): Promise<TaskContent> {
    const observed = await this.readIssue(value);
    const saved = attachment.parse(unpack(observed.metadata));
    const status =
      nativeStatus[saved.status] === observed.status
        ? saved.status
        : fromStatus[observed.status];
    if (!status)
      throw new Error(`Unsupported Beads task status: ${observed.status}`);
    let criteria: string[];
    try {
      criteria = z
        .array(z.string())
        .parse(JSON.parse(observed.acceptance_criteria));
    } catch {
      criteria = observed.acceptance_criteria
        ? [observed.acceptance_criteria]
        : [];
    }
    return content.parse({
      ...saved,
      title: observed.title,
      outcome: observed.description,
      successCriteria: criteria,
      status,
      priority:
        priority(saved.priority) === observed.priority
          ? saved.priority
          : 100 - 25 * observed.priority,
    });
  }
  async create(value: Task) {
    await this.verifyAuthority();
    try {
      await this.result(
        this.client.POST("/v0/beads/issues", {
          body: {
            actor: actor(value),
            issue_type: "task",
            id: beadId(value.taskId),
            force_id_prefix: true,
            ephemeral: false,
            no_history: false,
            inherit_labels_from_parent: false,
            title: value.title,
            description: value.outcome,
            acceptance_criteria: JSON.stringify(value.successCriteria),
            status: nativeStatus[value.status],
            priority: priority(value.priority),
            metadata: pack({
              ...taskContent(value),
              schema: 1,
              taskId: value.taskId,
              serverId: value.serverId,
            }),
            external_ref: `paseo:${value.serverId}/${value.taskId}`,
            ...(value.worker ? { assignee: actor(value) } : {}),
          },
        }),
      );
    } catch (error) {
      // WHY: Stable ids permit read-only reconciliation after a lost creation response; writes are never retried blindly.
      if (error instanceof BeadsError && error.status !== 409) throw error;
      let existing: TaskContent;
      try {
        existing = await this.read(value);
      } catch {
        throw error;
      }
      if (JSON.stringify(existing) !== JSON.stringify(taskContent(value)))
        throw error;
    }
    if (
      JSON.stringify(await this.read(value)) !==
      JSON.stringify(taskContent(value))
    )
      throw new Error("Beads creation readback differs from requested content");
  }
  async assertOwner(value: Task) {
    if (value.worker && (await this.readIssue(value)).assignee !== actor(value))
      throw new Error(
        "Beads ownership changed; pause and reconcile the retained worker before more execution",
      );
  }
  async claim(value: Task, worker: string) {
    const observed = await this.readIssue(value);
    if (
      (await this.read(value)).status !== "active" ||
      !["open", "in_progress"].includes(observed.status)
    )
      throw new Error(
        "Beads task is not active; refusing to reopen or launch it",
      );
    const owner = actor(value, worker);
    if (observed.assignee && observed.assignee !== owner)
      throw new Error("Beads task is claimed by another actor");
    await this.result(
      this.client.PATCH("/v0/beads/issues/{id}", {
        params: { path: { id: observed.id } },
        body: {
          actor: owner,
          force_close_policy: false,
          force_assignee_transfer: false,
          expected_status: observed.status,
          expected_assignee: observed.assignee,
          patch: { assignee: owner, status: "in_progress" },
        },
      }),
    );
    if ((await this.readIssue(value)).assignee !== owner)
      throw new Error("Beads did not confirm worker ownership");
  }
  async update(before: Task, after: Task) {
    const previous = taskContent(before),
      next = taskContent(after);
    if (JSON.stringify(previous) === JSON.stringify(next)) return;
    const observed = await this.readIssue(before);
    if (
      (before.worker || observed.assignee) &&
      observed.assignee !== actor(before)
    )
      throw new Error(
        "Beads task ownership changed or is claimed by another actor",
      );
    if (JSON.stringify(await this.read(before)) !== JSON.stringify(previous))
      throw new Error("Beads task changed; refresh before applying the update");
    const changed = Object.keys(next).filter(
      (key) =>
        JSON.stringify(previous[key as keyof TaskContent]) !==
        JSON.stringify(next[key as keyof TaskContent]),
    );
    const patch: components["schemas"]["IssuePatchBody"] = {
      metadata: {
        merge: pack(
          Object.fromEntries(
            changed.map((key) => [key, next[key as keyof TaskContent]]),
          ),
        ),
      },
    };
    if (previous.title !== next.title) patch.title = next.title;
    if (previous.outcome !== next.outcome) patch.description = next.outcome;
    if (
      JSON.stringify(previous.successCriteria) !==
      JSON.stringify(next.successCriteria)
    )
      patch.acceptance_criteria = JSON.stringify(next.successCriteria);
    if (previous.status !== next.status)
      patch.status = nativeStatus[next.status];
    if (previous.priority !== next.priority)
      patch.priority = priority(next.priority);
    await this.result(
      this.client.PATCH("/v0/beads/issues/{id}", {
        params: { path: { id: observed.id } },
        body: {
          actor: actor(before),
          force_close_policy: false,
          force_assignee_transfer: false,
          expected_status: observed.status,
          expected_assignee: observed.assignee,
          patch,
        },
      }),
    );
    const confirmed = await this.read(after);
    if (
      changed.some(
        (key) =>
          JSON.stringify(confirmed[key as keyof TaskContent]) !==
          JSON.stringify(next[key as keyof TaskContent]),
      )
    )
      throw new Error(
        "Beads update has an uncertain or concurrent outcome; inspect before retrying",
      );
    return confirmed;
  }
}
