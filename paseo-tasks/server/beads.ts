import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { z } from "zod";
import { task, type Task } from "../shared/contracts";

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
  metadata: z.record(z.string(), z.unknown()),
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

/** Beads owns task content; SQLite retains execution and delivery state. */
export class Beads {
  readonly directory: string;
  constructor(
    directory: string,
    readonly authority: string,
    readonly binary = "bd",
    readonly sshHost?: string,
  ) {
    this.directory = resolve(directory);
    if (sshHost) {
      if (!/^[A-Za-z0-9][A-Za-z0-9_.@-]*$/.test(sshHost))
        throw new Error("Invalid Beads SSH authority host");
      if (!directory.startsWith("/"))
        throw new Error("Remote Beads directory must be absolute");
    } else {
      const metadata = JSON.parse(
        readFileSync(join(this.directory, ".beads/metadata.json"), "utf8"),
      );
      if (
        metadata.backend !== "dolt" ||
        !["server", "embedded"].includes(metadata.dolt_mode)
      )
        throw new Error("Tasks requires an initialized Beads Dolt workspace");
    }
    z.uuid().parse(authority);
    this.verifyAuthority();
  }
  private run(args: string[], owner = "paseo-tasks"): unknown {
    const command = ["--json", "--sandbox", "--actor", owner, ...args];
    const quote = (value: string) => `'${value.replaceAll("'", "'\"'\"'")}'`;
    const remote = `cd ${quote(this.directory)} && exec env BEADS_DIR=${quote(join(this.directory, ".beads"))} ${[this.binary, ...command].map(quote).join(" ")}`;
    const result = spawnSync(
      this.sshHost ? "ssh" : this.binary,
      this.sshHost
        ? [
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=5",
            this.sshHost,
            remote,
          ]
        : command,
      {
        cwd: this.sshHost ? undefined : this.directory,
        encoding: "utf8",
        timeout: 30_000,
        maxBuffer: 8 * 1024 * 1024,
        env: {
          ...process.env,
          BEADS_DIR: join(this.directory, ".beads"),
          BD_LAST_TOUCHED_FALLBACK: "0",
        },
      },
    );
    if (result.error || result.status !== 0)
      throw new Error(
        `Beads ${args[0]} failed; writes may need readback before retry: ${result.error?.message ?? result.stderr.trim()}`,
      );
    try {
      return JSON.parse(result.stdout);
    } catch {
      throw new Error(
        `Beads ${args[0]} returned unreadable JSON; reconcile before retrying writes`,
      );
    }
  }
  private verifyAuthority() {
    const observed = z
      .object({ found: z.literal(true), value: z.string() })
      .parse(this.run(["kv", "get", "paseo.authority"]));
    if (observed.value !== this.authority)
      throw new Error(
        "Beads authority differs from configured authority; refusing replica or foreign database",
      );
  }
  private readIssue(value: Pick<Task, "taskId" | "serverId">): Issue {
    this.verifyAuthority();
    const rows = z.array(issue).parse(this.run(["show", beadId(value.taskId)]));
    if (rows.length !== 1 || rows[0].id !== beadId(value.taskId))
      throw new Error("Beads task identity is ambiguous");
    const saved = attachment.parse(unpack(rows[0].metadata));
    if (saved.taskId !== value.taskId || saved.serverId !== value.serverId)
      throw new Error("Beads task belongs to another host or task");
    return rows[0];
  }
  read(value: Task): TaskContent {
    const observed = this.readIssue(value);
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
  create(value: Task) {
    this.verifyAuthority();
    const args = [
      "create",
      "--id",
      beadId(value.taskId),
      "--title",
      value.title,
      "--description",
      value.outcome,
      "--acceptance",
      JSON.stringify(value.successCriteria),
      "--status",
      nativeStatus[value.status],
      "--priority",
      String(priority(value.priority)),
      "--metadata",
      JSON.stringify(
        pack({
          ...taskContent(value),
          schema: 1,
          taskId: value.taskId,
          serverId: value.serverId,
        }),
      ),
      "--external-ref",
      `paseo:${value.serverId}/${value.taskId}`,
    ];
    if (value.worker) args.push("--assignee", actor(value));
    // WHY: Stable IDs reconcile a lost creation response without creating another task.
    try {
      this.run(args);
    } catch (error) {
      const existing = this.read(value);
      if (JSON.stringify(existing) !== JSON.stringify(taskContent(value)))
        throw error;
    }
    if (JSON.stringify(this.read(value)) !== JSON.stringify(taskContent(value)))
      throw new Error("Beads creation readback differs from requested content");
  }
  assertOwner(value: Task) {
    if (value.worker && this.readIssue(value).assignee !== actor(value))
      throw new Error(
        "Beads ownership changed; pause and reconcile the retained worker before more execution",
      );
  }
  claim(value: Task, worker: string) {
    const observed = this.readIssue(value);
    if (
      this.read(value).status !== "active" ||
      !["open", "in_progress"].includes(observed.status)
    )
      throw new Error(
        "Beads task is not active; refusing to reopen or launch it",
      );
    const owner = actor(value, worker);
    if (observed.assignee && observed.assignee !== owner)
      throw new Error("Beads task is claimed by another actor");
    this.run(
      [
        "update",
        beadId(value.taskId),
        "--if-status",
        observed.status,
        "--if-assignee",
        observed.assignee,
        "--assignee",
        owner,
        "--status",
        "in_progress",
      ],
      owner,
    );
    if (this.readIssue(value).assignee !== owner)
      throw new Error("Beads did not confirm worker ownership");
  }
  update(before: Task, after: Task) {
    const previous = taskContent(before),
      next = taskContent(after);
    if (JSON.stringify(previous) === JSON.stringify(next)) return;
    const observed = this.readIssue(before);
    if (
      (before.worker || observed.assignee) &&
      observed.assignee !== actor(before)
    )
      throw new Error(
        "Beads task ownership changed or is claimed by another actor",
      );
    if (JSON.stringify(this.read(before)) !== JSON.stringify(previous))
      throw new Error("Beads task changed; refresh before applying the update");
    const args = [
      "update",
      beadId(before.taskId),
      "--if-status",
      observed.status,
      "--if-assignee",
      observed.assignee,
    ];
    if (previous.title !== next.title) args.push("--title", next.title);
    if (previous.outcome !== next.outcome)
      args.push(
        "--description",
        next.outcome,
        ...(next.outcome ? [] : ["--allow-empty-description"]),
      );
    if (
      JSON.stringify(previous.successCriteria) !==
      JSON.stringify(next.successCriteria)
    )
      args.push("--acceptance", JSON.stringify(next.successCriteria));
    if (previous.status !== next.status)
      args.push("--status", nativeStatus[next.status]);
    if (previous.priority !== next.priority)
      args.push("--priority", String(priority(next.priority)));
    const changed = Object.keys(next).filter(
      (key) =>
        JSON.stringify(previous[key as keyof TaskContent]) !==
        JSON.stringify(next[key as keyof TaskContent]),
    );
    const patch = Object.fromEntries(
      changed.map((key) => [key, next[key as keyof TaskContent]]),
    );
    // WHY: Native merge resolves each changed key inside Beads' transaction, preserving concurrent unrelated fields.
    args.push("--metadata", JSON.stringify(pack(patch)));
    this.run(args, actor(before));
    const confirmed = this.read(after);
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
