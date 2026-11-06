import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { isAbsolute, join, resolve } from "node:path";
import { z } from "zod";
import { treehouseLease, treehouseReservation } from "../shared/contracts";

type Reservation = z.infer<typeof treehouseReservation>;
type Lease = z.infer<typeof treehouseLease>;
export interface Worktrees {
  prepare(repository: string, holder: string, branch: string, baseRef: string): Promise<Reservation>;
  acquire(reservation: Reservation, attempting: () => void): Promise<Lease>;
}
const command = async (cwd: string, executable: string, args: string[]) =>
  (await promisify(execFile)(executable, args, { cwd, timeout: 180000, maxBuffer: 2 * 1024 * 1024 })).stdout.trim();
const allocation = treehouseLease.pick({
  path: true, lease_id: true, lease_holder: true, leased_at: true, base_branch: true,
});

export class Treehouse implements Worktrees {
  async prepare(repository: string, holder: string, branch: string, baseRef: string): Promise<Reservation> {
    const listing = await command(repository, "git", ["worktree", "list", "--porcelain"]);
    const primary = listing.split("\n").find(line => line.startsWith("worktree "))?.slice(9);
    if (!primary || !isAbsolute(primary)) throw new Error("Cannot resolve the primary Git checkout for Treehouse");
    const root = join(primary, ".worktrees");
    try {
      await command(primary, "git", ["check-ignore", "--quiet", join(root, ".treehouse", "task-slot")]);
    } catch {
      throw new Error(`Treehouse task pool ${root}/.treehouse must be excluded by this repository's ignore rules`);
    }
    try { await command(primary, "treehouse", ["--version"]); }
    catch { throw new Error("Treehouse is unavailable; install it through dotfiles bootstrap.sh before allocating a coding worker"); }
    const baseCommit = await command(primary, "git", ["rev-parse", "--verify", `${baseRef}^{commit}`]);
    if (!/^[a-f0-9]{40,64}$/.test(baseCommit)) throw new Error("The requested base did not resolve to a Git commit");
    return { primary, root, holder, branch, baseRef, baseCommit,
      treehouseBase: branch.replace(/^task\//, "task-base/"), attempted: false };
  }
  async acquire(reservation: Reservation, attempting: () => void): Promise<Lease> {
    const { primary, root, holder, branch, baseCommit, treehouseBase } = reservation;
    const rows: unknown = JSON.parse(await command(primary, "treehouse", ["--root", root, "status", "--json"]));
    const status = z.array(z.object({
      path: z.string(), branch: z.string().optional(), lease_id: z.string().optional(),
      lease_holder: z.string().optional(), leased_at: z.string().optional(),
    }).passthrough()).parse(rows);
    const owned = status.filter(row => row.lease_holder === holder);
    if (owned.length > 1) throw new Error("Multiple Treehouse leases claim this task; reconcile before launch");
    let leased: z.infer<typeof allocation>;
    if (owned.length) {
      const found = owned[0];
      if (found.branch !== branch) throw new Error("Treehouse task lease branch changed; preserve it and reconcile ownership");
      // WHY: Status omits base_branch; the task's immutable base branch survives a lost get response.
      leased = allocation.parse({ path: found.path, lease_id: found.lease_id, lease_holder: found.lease_holder,
        leased_at: found.leased_at, base_branch: treehouseBase });
    } else {
      if (reservation.attempted) throw new Error("Treehouse acquisition outcome remains unknown; inspect the pool before retrying. No second lease was requested");
      const refs = await command(primary, "git", ["for-each-ref", "--format=%(objectname)", `refs/heads/${treehouseBase}`]);
      if (refs && refs !== baseCommit) throw new Error("The task's Treehouse base branch changed; reconcile before acquisition");
      // WHY: Treehouse accepts branch names and may prefer an ahead local branch; pin the exact requested commit.
      if (!refs) await command(primary, "git", ["branch", "--", treehouseBase, baseCommit]);
      attempting();
      const response = await command(primary, "treehouse", [
        "--root", root, "get", "--no-fetch", "--lease", "--json", "--lease-holder", holder, "--branch", branch, "--base", treehouseBase,
      ]);
      leased = allocation.parse(JSON.parse(response));
    }
    if (leased.lease_holder !== holder || !isAbsolute(leased.path) || resolve(leased.path) === resolve(primary)) {
      throw new Error("Treehouse returned an unexpected task lease; retain it for reconciliation");
    }
    const actual = await command(leased.path, "git", ["symbolic-ref", "-q", "HEAD"]);
    if (actual !== `refs/heads/${branch}`) throw new Error("Treehouse checkout branch differs from its task reservation");
    const checkouts = await command(leased.path, "git", ["worktree", "list", "--porcelain"]);
    if (checkouts.split("\n")[0] !== `worktree ${primary}`) throw new Error("Treehouse checkout belongs to a different repository");
    return treehouseLease.parse({ ...leased, branch, primary, root });
  }
}
