import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { z } from "zod";
import type { DriverConfig } from "./config.ts";
import { run } from "./process.ts";

export enum TaskStatus {
  Open = "open",
  InProgress = "in_progress",
  Blocked = "blocked",
  Deferred = "deferred",
  Closed = "closed",
}

export enum TaskRelationship {
  ParentChild = "parent-child",
  Blocks = "blocks",
}

export function knownTaskStatus(value: string): TaskStatus | undefined {
  const parsed = z.enum(TaskStatus).safeParse(value);
  return parsed.success ? parsed.data : undefined;
}

function knownRelationship(value: string): TaskRelationship | undefined {
  const parsed = z.enum(TaskRelationship).safeParse(value);
  return parsed.success ? parsed.data : undefined;
}

function inlineText(value: string): string {
  return value.replace(/\p{Cc}/gu, " ");
}

const dependency = z.union([
  z
    .object({
      id: z.string(),
      dependency_type: z.string(),
    })
    .loose(),
  z
    .object({ depends_on_id: z.string(), type: z.string() })
    .loose()
    .transform((edge) => ({
      ...edge,
      id: edge.depends_on_id,
      dependency_type: edge.type,
    })),
]);
export const taskSchema = z
  .object({
    id: z.string().min(1),
    title: z.string(),
    status: z.string(),
    assignee: z.string().optional(),
    description: z.string().optional(),
    acceptance_criteria: z.string().optional(),
    parent: z.string().optional(),
    parent_id: z.string().optional(),
    dependencies: z.array(dependency).optional(),
  })
  .loose();
export type Task = z.infer<typeof taskSchema>;
export interface TreeRow {
  task: Task;
  depth: number;
  branch?: string;
  warning?: string;
}

export function parentId(task: Task): string | undefined {
  return (
    task.parent ??
    task.parent_id ??
    task.dependencies?.find(
      (edge) =>
        knownRelationship(edge.dependency_type) ===
        TaskRelationship.ParentChild,
    )?.id
  );
}

/** Dependency blockers never become containment edges. Cycles remain inspectable. */
export function taskTree(tasks: Task[]): TreeRow[] {
  const byId = new Map(tasks.map((task) => [task.id, task]));
  if (byId.size !== tasks.length)
    throw new Error("Beads returned duplicate task identities");
  const children = new Map<string, Task[]>();
  for (const task of tasks) {
    const parent = parentId(task);
    if (parent !== undefined && byId.has(parent))
      children.set(parent, [...(children.get(parent) ?? []), task]);
  }
  const rows: TreeRow[] = [];
  const seen = new Set<string>();
  const visit = (root: Task, warning?: string) => {
    const stack: (TreeRow & { guides: string; moreSiblings: boolean })[] = [
      {
        task: root,
        depth: 0,
        guides: "",
        moreSiblings: false,
        ...(warning === undefined ? {} : { warning }),
      },
    ];
    while (stack.length > 0) {
      const row = stack.pop();
      if (row === undefined || seen.has(row.task.id)) continue;
      const { task, depth, guides, moreSiblings, warning } = row;
      seen.add(task.id);
      rows.push({
        task,
        depth,
        ...(depth === 0
          ? {}
          : {
              branch: `${depth > 5 ? "… " : ""}${guides}${moreSiblings ? "├─ " : "└─ "}`,
            }),
        ...(warning === undefined ? {} : { warning }),
      });
      // Keep deep guides within the panel's width while retaining nearby ancestry.
      const childGuides =
        depth === 0
          ? ""
          : `${guides}${moreSiblings ? "│  " : "   "}`.slice(-12);
      const directChildren = (children.get(task.id) ?? [])
        .filter((child) => !seen.has(child.id))
        .reverse();
      for (const [index, child] of directChildren.entries())
        stack.push({
          task: child,
          depth: depth + 1,
          guides: childGuides,
          moreSiblings: index !== 0,
        });
    }
  };
  for (const task of tasks) {
    const parent = parentId(task);
    if (parent === undefined || !byId.has(parent))
      visit(
        task,
        parent !== undefined
          ? `Parent ${parent} is outside this result`
          : undefined,
      );
  }
  for (const task of tasks)
    if (!seen.has(task.id))
      visit(task, "Cyclic containment; inspect source tasks");
  return rows;
}

export function taskLabel(row: TreeRow): string {
  const indent = "  ".repeat(Math.min(row.depth, 12));
  const omitted = row.depth > 12 ? "… " : "";
  return inlineText(
    `${indent}${omitted}${row.task.id} · ${row.task.title}  ${row.task.status}${row.warning === undefined ? "" : " ⚠"}`,
  );
}

export function taskOverlayLabel(
  row: TreeRow,
  renderStatus: (status: string) => string,
  renderBranch: (branch: string) => string,
): string {
  const branch = row.branch === undefined ? "" : renderBranch(row.branch);
  const label = inlineText(`${row.task.id} · ${row.task.title}`);
  return `${branch}${renderStatus(inlineText(row.task.status))} ${label}${row.warning === undefined ? "" : " ⚠"}`;
}

export function taskDetails(
  task: Task,
  workspace: string,
  renderStatus: (status: string) => string = (status) => status,
): string {
  const blockers =
    task.dependencies
      ?.filter(
        (edge) =>
          knownRelationship(edge.dependency_type) === TaskRelationship.Blocks,
      )
      .map((edge) => edge.id) ?? [];
  const parent = parentId(task);
  const lines = [
    `${workspace} / ${task.id} · ${task.title}`,
    `Status: ${task.status}`,
    parent !== undefined ? `Parent: ${parent}` : undefined,
    blockers.length > 0 ? `Blocked by: ${blockers.join(", ")}` : undefined,
    "",
    task.description,
    task.acceptance_criteria !== undefined
      ? `\nAcceptance criteria:\n${task.acceptance_criteria}`
      : undefined,
  ]
    .filter((line) => line !== undefined)
    .map((line) => line.replace(/(?!\n)\p{Cc}/gu, ""));
  lines[1] = `Status: ${renderStatus(inlineText(task.status))}`;
  return lines.join("\n");
}

export class BeadsReader {
  constructor(private readonly settings: NonNullable<DriverConfig["beads"]>) {}

  async verify(): Promise<void> {
    const metadata = z
      .object({ dolt_mode: z.literal("server"), dolt_database: z.string() })
      .loose()
      .parse(
        JSON.parse(
          await readFile(
            join(this.settings.workspace, ".beads/metadata.json"),
            "utf8",
          ),
        ),
      );
    if (metadata.dolt_database !== this.settings.database)
      throw new Error(
        "Configured Beads database does not match workspace metadata",
      );
    const branch = z
      .array(z.object({ branch: z.string() }))
      .parse(await this.call(["sql", "SELECT ACTIVE_BRANCH() AS branch"]));
    if (branch.length !== 1 || branch[0]?.branch !== this.settings.branch)
      throw new Error(
        "Configured Beads branch does not match the authoritative workspace",
      );
  }

  async list(): Promise<Task[]> {
    await this.verify();
    return z
      .array(taskSchema)
      .parse(await this.call(["list", "--all", "--limit", "1000"]));
  }

  async show(id: string): Promise<Task> {
    if (id.length === 0 || id.startsWith("-"))
      throw new Error("An explicit Beads task ID is required");
    await this.verify();
    const tasks = z.array(taskSchema).parse(await this.call(["show", id]));
    if (tasks.length !== 1 || tasks[0]?.id !== id)
      throw new Error("Beads returned a different task identity");
    return tasks[0];
  }

  private async call(args: string[]): Promise<unknown> {
    const env = Object.fromEntries(
      Object.entries(process.env).filter(
        ([key]) => !key.startsWith("BEADS_") && !key.startsWith("BD_"),
      ),
    );
    env["BD_LAST_TOUCHED_FALLBACK"] = "0";
    return JSON.parse(
      await run(
        this.settings.executable,
        [
          "-C",
          this.settings.workspace,
          "--sandbox",
          "--readonly",
          "--json",
          ...args,
        ],
        { cwd: this.settings.workspace, env },
      ),
    );
  }
}
