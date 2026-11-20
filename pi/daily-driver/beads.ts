import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { z } from "zod";
import type { DriverConfig } from "./config.ts";
import { run } from "./process.ts";

const dependency = z.union([
  z
    .object({
      id: z.string(),
      dependency_type: z.string(),
    })
    .passthrough(),
  z
    .object({ depends_on_id: z.string(), type: z.string() })
    .passthrough()
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
    description: z.string().optional(),
    acceptance_criteria: z.string().optional(),
    parent: z.string().optional(),
    parent_id: z.string().optional(),
    dependencies: z.array(dependency).optional(),
  })
  .passthrough();
export type Task = z.infer<typeof taskSchema>;
export interface TreeRow {
  task: Task;
  depth: number;
  warning?: string;
}

export function parentId(task: Task): string | undefined {
  return (
    task.parent ??
    task.parent_id ??
    task.dependencies?.find((edge) => edge.dependency_type === "parent-child")
      ?.id
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
    if (parent && byId.has(parent))
      children.set(parent, [...(children.get(parent) ?? []), task]);
  }
  const rows: TreeRow[] = [];
  const seen = new Set<string>();
  const visit = (root: Task, depth: number, warning?: string) => {
    const stack = [{ task: root, depth, warning }];
    while (stack.length) {
      const row = stack.pop();
      if (!row || seen.has(row.task.id)) continue;
      seen.add(row.task.id);
      rows.push(row);
      for (const child of [...(children.get(row.task.id) ?? [])].reverse())
        stack.push({ task: child, depth: row.depth + 1, warning: undefined });
    }
  };
  for (const task of tasks) {
    const parent = parentId(task);
    if (!parent || !byId.has(parent))
      visit(
        task,
        0,
        parent ? `Parent ${parent} is outside this result` : undefined,
      );
  }
  for (const task of tasks)
    if (!seen.has(task.id))
      visit(task, 0, "Cyclic containment; inspect source tasks");
  return rows;
}

export function taskLabel(row: TreeRow): string {
  return `${"  ".repeat(Math.min(row.depth, 12))}${row.depth > 12 ? "… " : ""}${row.task.id} · ${row.task.title} · ${row.task.status}${row.warning ? " ⚠" : ""}`.replace(
    // biome-ignore lint/suspicious/noControlCharactersInRegex: Task text is untrusted terminal display content.
    /[\x00-\x1f\x7f]/g,
    " ",
  );
}

export function taskDetails(task: Task, workspace: string): string {
  const blockers =
    task.dependencies
      ?.filter((edge) => edge.dependency_type === "blocks")
      .map((edge) => edge.id) ?? [];
  return [
    `${workspace} / ${task.id}`,
    `Status: ${task.status}`,
    `Parent: ${parentId(task) ?? "None"}`,
    `Blocked by: ${blockers.join(", ") || "None reported"}`,
    "",
    task.description || "Not specified in task description",
    "",
    "Acceptance criteria:",
    task.acceptance_criteria || "Not specified in task",
    "",
    "Read-only observation; this view does not accept scope or authorize execution.",
  ]
    .join("\n")
    .replace(
      // biome-ignore lint/suspicious/noControlCharactersInRegex: Preserve line breaks, remove executable terminal controls.
      /[\x00-\x09\x0b-\x1f\x7f]/g,
      "",
    );
}

export class BeadsReader {
  constructor(private readonly settings: NonNullable<DriverConfig["beads"]>) {}

  async verify(): Promise<void> {
    const metadata = z
      .object({ dolt_mode: z.literal("server"), dolt_database: z.string() })
      .passthrough()
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
    if (!id || id.startsWith("-"))
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
    env.BD_LAST_TOUCHED_FALLBACK = "0";
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
