import { spawn } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { type Attempts, Phase } from "./attempts.ts";
import { LeadMode } from "./lead-plan.ts";
import { run } from "./process.ts";
import { BeadChanged, TaskBeads, type Verification } from "./task-service.ts";

async function gitState(cwd: string, branch: string) {
  const git = async (...args: string[]) =>
    (await run("git", args, { cwd })).trim();
  if ((await git("symbolic-ref", "--short", "HEAD")) !== branch)
    throw new Error("The managed checkout changed branches");
  const head = await git("rev-parse", "HEAD");
  // A private index fingerprints staged, unstaged and new nonignored files without changing the operator's index.
  const temporary = await mkdtemp(join(tmpdir(), "pi-driver-index-"));
  try {
    const env = { ...process.env, GIT_INDEX_FILE: join(temporary, "index") };
    const indexed = async (...args: string[]) =>
      (await run("git", args, { cwd, env })).trim();
    await indexed("read-tree", head);
    await indexed("add", "-A", "--", ".");
    return { gitHead: head, gitState: await indexed("write-tree") };
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
}

async function runCheck(
  argv: string[],
  cwd: string,
  signal?: AbortSignal,
): Promise<{ exitCode: number | null; output: string }> {
  const [program, ...args] = argv;
  if (program === undefined || program.length === 0)
    throw new Error("A verification executable is required");
  signal?.throwIfAborted();
  return new Promise((resolve, reject) => {
    const child = spawn(program, args, {
      cwd,
      stdio: ["ignore", "pipe", "pipe"],
      shell: false,
      detached: true,
    });
    let tail = Buffer.alloc(0);
    const collect = (chunk: Buffer) => {
      tail = Buffer.concat([tail, chunk.subarray(-8192)]).subarray(-8192);
    };
    child.stdout.on("data", collect);
    child.stderr.on("data", collect);
    let escalation: NodeJS.Timeout | undefined;
    const terminate = (name: NodeJS.Signals) => {
      if (child.pid === undefined) return;
      try {
        process.kill(-child.pid, name);
      } catch (error) {
        if (
          !(error instanceof Error && "code" in error && error.code === "ESRCH")
        )
          reject(error instanceof Error ? error : new Error(String(error)));
      }
    };
    const cancel = () => {
      terminate("SIGTERM");
      escalation = setTimeout(() => {
        terminate("SIGKILL");
      }, 1000);
      escalation.unref();
    };
    signal?.addEventListener("abort", cancel, { once: true });
    child.once("error", reject);
    child.once("close", (code, termination) => {
      signal?.removeEventListener("abort", cancel);
      if (escalation !== undefined) {
        clearTimeout(escalation);
        terminate("SIGKILL");
      }
      if (signal?.aborted === true) {
        reject(new Error("Verification cancelled. The bead remains open"));
        return;
      }
      const output = tail.toString("utf8");
      resolve({
        exitCode: code,
        output:
          termination === null
            ? output
            : `${output}\nTerminated by ${termination}`,
      });
    });
  });
}

export async function submitResult(
  db: Attempts,
  id: string,
  summary: string,
  signal?: AbortSignal,
): Promise<string> {
  if (summary.trim().length === 0 || summary.length > 4000)
    throw new Error("Supply a result summary of 1–4000 characters");
  const previous = db.get(id);
  const service = new TaskBeads(previous.source);
  if (previous.phase === Phase.Closed)
    return "This result is already recorded and the bead is closed";
  if (
    (previous.phase === Phase.Reconcile || previous.phase === Phase.Checking) &&
    previous.verification !== null &&
    previous.verification.exitCode === 0 &&
    (await service.closedWith(previous.bead.id, id, previous.verification))
  ) {
    db.change(id, (row) => {
      row.phase = Phase.Closed;
      row.message = "Confirmed the previously submitted result";
    });
    return "Beads confirmed the previous result and closure";
  }
  const current = db.change(id, (row) => {
    if (
      row.leadPlan !== undefined &&
      row.leadPlan.mode !== LeadMode.Implementing
    )
      throw new Error("Approve the lead plan before submitting a result");
    if (
      row.phase !== Phase.Running &&
      row.phase !== Phase.CheckFailed &&
      row.phase !== Phase.Verified
    )
      throw new Error(
        `Result submission requires a running worker. Current state: ${row.phase}. ${row.message}`,
      );
    row.phase = Phase.Checking;
    row.message = "Verifying the accepted result";
    row.verification = null;
  });
  const verification: Verification = {
    summary: summary.trim(),
    check: current.check,
    exitCode: null,
    gitHead: "",
    gitState: "",
    output: "",
  };
  let phase = Phase.NeedsReview;
  try {
    if (current.checkout === null || current.revision === null)
      throw new Error("Managed checkout or accepted revision is missing");
    const { path, branch } = current.checkout;
    await service.requireCurrent(current.bead, current.revision, id);
    Object.assign(verification, await gitState(path, branch));
    if (
      current.check.length === 0 ||
      current.bead.acceptance_criteria.trim().length === 0
    ) {
      throw new Error(
        "Human review is required because the accepted task has no complete machine-verifiable criteria",
      );
    }
    phase = Phase.CheckFailed;
    Object.assign(verification, await runCheck(current.check, path, signal));
    if (verification.exitCode !== 0)
      throw new Error(
        `The agreed check exited with ${String(verification.exitCode)}`,
      );
    phase = Phase.NeedsReview;
    if (current.source.reviewOnly === true)
      throw new Error(
        "The agreed check passed. This Beads service requires human review",
      );
    const after = await gitState(path, branch);
    if (
      after.gitState !== verification.gitState ||
      after.gitHead !== verification.gitHead
    )
      throw new Error("The tested Git state changed while the check ran");
    await service.requireCurrent(current.bead, current.revision, id);
    signal?.throwIfAborted();
    if (current.leadPlan !== undefined) {
      db.change(id, (row) => {
        row.phase = Phase.Verified;
        row.verification = verification;
        row.message =
          "Verification passed. Waiting for Octo delivery and confirmed merge";
      });
      return "Verification passed. The bead remains in progress until delivery is confirmed.";
    }
    // The evidence must survive a process exit after Beads commits and before local confirmation.
    db.change(id, (row) => {
      row.verification = verification;
      row.message = "Confirming the result in Beads";
    });
    phase = Phase.Reconcile;
    await service.complete(
      current.bead,
      current.revision,
      id,
      verification,
      signal,
    );
    db.change(id, (row) => {
      row.phase = Phase.Closed;
      row.message = "Beads confirmed the evidence and closure";
    });
    return (
      "Agreed check passed. Beads recorded the evidence and closed " +
      current.bead.id
    );
  } catch (cause) {
    const reason = cause instanceof Error ? cause.message : String(cause);
    if (
      cause instanceof BeadChanged ||
      (signal?.aborted === true && cause === signal.reason)
    )
      phase = Phase.NeedsReview;
    if (phase !== Phase.Reconcile) verification.reason = reason;
    db.change(id, (row) => {
      row.phase = phase;
      row.message = reason;
      row.verification = verification;
    });
    return reason;
  }
}
