import { execFile } from "node:child_process";
import { isAbsolute, join, resolve } from "node:path";
import { promisify } from "node:util";
import { z } from "zod";
import {
  worktreeAllocation,
  type worktreeReservation,
} from "../shared/contracts";

type Reservation = z.infer<typeof worktreeReservation>;
type Allocation = z.infer<typeof worktreeAllocation>;
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
    attempting: () => void,
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
    if (!primary || !isAbsolute(primary))
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
    attempting: () => void,
  ): Promise<Allocation> {
    const { primary, root, holder, branch, baseCommit, agent } = reservation;
    const status = JSON.parse(
      await command(primary, this.executable, ["status", "--json"]),
    );
    const rows = z
      .array(z.object({ owner_id: z.string().optional() }).passthrough())
      .parse(status.result.tasks);
    const owned = rows
      .filter((row) => row.owner_id === holder)
      .map((row) => managedTask.parse(row));
    if (owned.length > 1)
      throw new Error(
        "Multiple managed allocations claim this task; reconcile before launch",
      );
    let allocated: z.infer<typeof managedTask>;
    if (owned.length) {
      allocated = owned[0];
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
      attempting();
      const response = JSON.parse(
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
      allocated = managedTask.parse(response.result);
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
