import { execFile } from "node:child_process";
import { isAbsolute, join, resolve } from "node:path";
import { promisify } from "node:util";
import { z } from "zod";
import {
  worktreeAllocation,
  type worktreeReservation,
} from "./worktree-contracts.ts";

export type Reservation = z.infer<typeof worktreeReservation>;
export type Allocation = z.infer<typeof worktreeAllocation>;
export interface Worktrees {
  prepare(
    repository: string,
    holder: string,
    branch: string,
    baseRef: string,
    agent?: string,
  ): Promise<Reservation>;
  acquire(
    reservation: Reservation,
    attempting: () => void | Promise<void>,
  ): Promise<Allocation>;
}
const command = async (cwd: string, executable: string, args: string[]) =>
  (
    await promisify(execFile)(executable, args, {
      cwd,
      timeout: 180000,
      maxBuffer: 2 * 1024 * 1024,
    })
  ).stdout.trim();
const inspectTasks = async (cwd: string, executable: string) => {
  let output: string;
  try {
    output = await command(cwd, executable, ["status", "--json"]);
  } catch (error) {
    // Status exits 1 for incomplete inventory, including unrelated missing repositories.
    if (
      !(error instanceof Error) ||
      !("code" in error) ||
      error.code !== 1 ||
      !("stdout" in error) ||
      typeof error.stdout !== "string"
    )
      throw error;
    output = error.stdout;
  }
  return z
    .object({
      schema_version: z.literal(1),
      command: z.literal("status"),
      result: z.object({
        tasks: z.array(z.object({ owner_id: z.string().optional() }).loose()),
      }),
    })
    .parse(JSON.parse(output)).result.tasks;
};
const managedTask = z.object({
  id: z.string().regex(/^[a-f0-9]{32}$/),
  path: z.string(),
  branch: z.string(),
  owner_id: z.string(),
  agent: z.string(),
  created_at: z.string(),
  state: z.string(),
  observation: z.string().optional(),
  observed_path: z.string().nullable().optional(),
});

export class WorktreeManager implements Worktrees {
  constructor(readonly executable = "worktree") {}
  async requireAllocation(allocation: Allocation): Promise<void> {
    const inventory = await inspectTasks(allocation.primary, this.executable);
    const task = managedTask.parse(
      inventory.find((entry) => entry["id"] === allocation.task_id),
    );
    if (
      task.owner_id !== allocation.owner_id ||
      task.agent !== allocation.agent ||
      task.path !== allocation.path ||
      task.branch !== allocation.branch ||
      task.state !== "active"
    )
      throw new Error(
        "The worktree manager cannot verify this active allocation",
      );
  }

  async prepare(
    repository: string,
    holder: string,
    branch: string,
    baseRef: string,
    agent = "paseo",
  ): Promise<Reservation> {
    if (!/^[a-z0-9][a-z0-9-]{0,47}$/.test(agent))
      throw new Error("Invalid worktree agent slug");
    const listing = await command(repository, "git", [
      "worktree",
      "list",
      "--porcelain",
      "-z",
    ]);
    const primary = listing
      .split("\0")
      .find((line) => line.startsWith("worktree "))
      ?.slice(9);
    if (primary === undefined || primary === "" || !isAbsolute(primary))
      throw new Error(
        "Cannot resolve the primary Git checkout for worktree allocation",
      );
    const root = join(primary, ".worktrees");
    try {
      await command(primary, "git", [
        "check-ignore",
        "--quiet",
        "--no-index",
        "--",
        join(root, `${agent}-allocation`),
      ]);
    } catch {
      throw new Error(
        `Worktree destination ${root} must be ignored by this repository`,
      );
    }
    try {
      await command(primary, this.executable, ["--version"]);
    } catch {
      throw new Error(
        "Worktree manager is unavailable; run make install before allocating a coding worker",
      );
    }
    const baseCommit = await command(repository, "git", [
      "rev-parse",
      "--verify",
      "--end-of-options",
      `${baseRef}^{commit}`,
    ]);
    if (!/^[a-f0-9]{40,64}$/.test(baseCommit))
      throw new Error("The requested base did not resolve to a Git commit");
    return {
      primary,
      root,
      holder,
      branch,
      baseRef,
      baseCommit,
      agent,
      attempted: false,
    };
  }
  async acquire(
    reservation: Reservation,
    attempting: () => void | Promise<void>,
  ): Promise<Allocation> {
    const { primary, root, holder, branch, baseCommit, agent } = reservation;
    const rows = await inspectTasks(primary, this.executable);
    const owned = rows
      .filter((row) => row.owner_id === holder)
      .map((row) => managedTask.parse(row));
    if (owned.length > 1)
      throw new Error(
        "Multiple managed allocations claim this task; reconcile before launch",
      );
    let allocated: z.infer<typeof managedTask>;
    if (owned.length > 0) {
      const existing = owned[0];
      if (existing === undefined) throw new Error("Missing managed allocation");
      allocated = existing;
      if (
        allocated.observation !== "available" ||
        allocated.observed_path !== allocated.path
      )
        throw new Error(
          "Managed allocation is unavailable or moved; reconcile before launch",
        );
    } else {
      if (reservation.attempted)
        throw new Error(
          "Worktree acquisition outcome remains unknown; inspect worktree status before retrying. No second allocation was requested",
        );
      await attempting();
      const response: unknown = JSON.parse(
        await command(primary, this.executable, [
          "create",
          "--agent",
          agent,
          "--owner-id",
          holder,
          "--branch",
          branch,
          "--base",
          baseCommit,
          "--json",
        ]),
      );
      const receipt = managedTask
        .pick({
          id: true,
          path: true,
          branch: true,
          owner_id: true,
          agent: true,
          state: true,
        })
        .parse(z.object({ result: z.unknown() }).parse(response).result);
      // Agent callers receive a compact receipt. Inventory supplies the creation record and confirms the protected checkout.
      const inventory = await inspectTasks(primary, this.executable);
      const matching = inventory.filter((row) => row.owner_id === holder);
      if (matching.length !== 1)
        throw new Error(
          "Cannot confirm the manager allocation; reconcile its owner before retrying",
        );
      allocated = managedTask.parse(matching[0]);
      if (
        allocated.id !== receipt.id ||
        allocated.path !== receipt.path ||
        receipt.owner_id !== holder ||
        receipt.agent !== agent ||
        receipt.branch !== branch ||
        receipt.state !== "active" ||
        allocated.observation !== "available" ||
        allocated.observed_path !== allocated.path
      ) {
        throw new Error(
          "The manager's receipt and worktree inventory disagree",
        );
      }
    }
    if (
      allocated.state !== "active" ||
      allocated.owner_id !== holder ||
      allocated.agent !== agent ||
      allocated.branch !== branch ||
      !isAbsolute(allocated.path) ||
      resolve(allocated.path) !==
        join(root, `${agent}-${allocated.id.slice(0, 8)}`)
    )
      throw new Error(
        "Worktree manager returned an unexpected allocation; retain it for reconciliation",
      );
    const actual = await command(allocated.path, "git", [
      "symbolic-ref",
      "-q",
      "HEAD",
    ]);
    if (actual !== `refs/heads/${branch}`)
      throw new Error(
        "Managed checkout branch differs from its task reservation",
      );
    const checkouts = await command(allocated.path, "git", [
      "worktree",
      "list",
      "--porcelain",
      "-z",
    ]);
    if (checkouts.split("\0")[0] !== `worktree ${primary}`)
      throw new Error("Managed checkout belongs to a different repository");
    return worktreeAllocation.parse({
      primary,
      root,
      path: allocated.path,
      task_id: allocated.id,
      owner_id: holder,
      agent,
      branch,
      created_at: allocated.created_at,
      base_ref: reservation.baseRef,
    });
  }
}
