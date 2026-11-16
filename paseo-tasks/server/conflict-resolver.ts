import { execFile } from "node:child_process";
import { lstatSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { promisify } from "node:util";
import type { RepositoryPolicy, Strategy } from "./maintenance-policy";

export type RepairRequest = {
  id: string;
  directory: string;
  head: string;
  base: string;
  headRef: string;
  baseRef: string;
  policy: RepositoryPolicy;
  deadline?: number;
};
export type Validation = { command: string[]; passed: boolean; output: string };
export type Candidate = {
  strategy: Strategy;
  strategies: Strategy[];
  confidence: number | null;
  head: string | null;
  conflicts: string[];
  checks: Validation[];
  reason: string;
  patch: string;
  worktree: string;
};
export interface ConflictResolver {
  prepare(request: RepairRequest): Promise<Candidate>;
  publish(request: RepairRequest, candidate: Candidate): Promise<void>;
  remoteHead(request: RepairRequest): Promise<string>;
}
export class StaleRevision extends Error {}
const execute = promisify(execFile);
const failure = (error: unknown) =>
  error as Error & { code?: string | number; stdout?: string; stderr?: string };

export class GitConflictResolver implements ConflictResolver {
  constructor(readonly root: string) {
    mkdirSync(root, { recursive: true, mode: 0o700 });
  }
  private async command(
    request: RepairRequest,
    cwd: string,
    executable: string,
    args: string[],
  ) {
    const remaining = Math.min(
      request.policy.timeoutSeconds * 1000,
      request.deadline === undefined ? Infinity : request.deadline - Date.now(),
    );
    if (remaining <= 0)
      throw new Error("PR maintenance preparation exceeded its time budget");
    return (
      await execute(executable, args, {
        cwd,
        timeout: remaining,
        maxBuffer: 8 * 1024 * 1024,
        env: {
          ...process.env,
          GIT_TERMINAL_PROMPT: "0",
          GIT_MERGE_AUTOEDIT: "no",
          mergiraf: "0",
        },
      })
    ).stdout;
  }
  private git(request: RepairRequest, cwd: string, args: string[]) {
    // WHY: A configured merge driver must not silently bypass the selected resolver's score.
    return this.command(request, cwd, "git", [
      "-c",
      "merge.conflictStyle=diff3",
      "-c",
      "merge.default=text",
      "-c",
      "rerere.autoupdate=false",
      ...args,
    ]);
  }
  private async supportedDrivers(
    request: RepairRequest,
    cwd: string,
    paths: string[],
    cached = false,
  ) {
    if (!paths.length) return true;
    const attributes = (
      await this.command(request, cwd, "git", [
        "check-attr",
        ...(cached ? ["--cached"] : []),
        "-z",
        "merge",
        "--",
        ...paths,
      ])
    ).split("\0");
    for (let index = 2; index < attributes.length; index += 3) {
      if (!["unspecified", "set", "mergiraf"].includes(attributes[index]))
        return false;
    }
    return true;
  }
  async remoteHead(request: RepairRequest) {
    const output = await this.git(request, request.policy.directory, [
      "ls-remote",
      "--exit-code",
      "--heads",
      request.policy.remote,
      `refs/heads/${request.headRef}`,
    ]);
    const rows = output.trim().split("\n");
    if (
      rows.length !== 1 ||
      rows[0].split(/\s+/)[1] !== `refs/heads/${request.headRef}`
    ) {
      throw new Error(
        "PR branch identity is unavailable from the configured remote",
      );
    }
    return rows[0].split(/\s+/)[0];
  }
  private async verify(request: RepairRequest) {
    if (
      !/^[a-f0-9]{40,64}$/.test(request.head) ||
      !/^[a-f0-9]{40,64}$/.test(request.base)
    ) {
      throw new Error("PR maintenance requires exact commit identities");
    }
    for (const ref of [request.headRef, request.baseRef]) {
      await this.git(request, request.policy.directory, [
        "check-ref-format",
        `refs/heads/${ref}`,
      ]);
    }
    if (
      (
        await this.git(request, request.directory, [
          "symbolic-ref",
          "--short",
          "HEAD",
        ])
      ).trim() !== request.headRef
    ) {
      throw new Error(
        "The retained worker checkout does not own this PR branch",
      );
    }
    const primary = (
      await this.git(request, request.policy.directory, [
        "rev-parse",
        "--path-format=absolute",
        "--git-common-dir",
      ])
    ).trim();
    const worker = (
      await this.git(request, request.directory, [
        "rev-parse",
        "--path-format=absolute",
        "--git-common-dir",
      ])
    ).trim();
    if (primary !== worker)
      throw new Error("The worker checkout belongs to a different repository");
    const remote = (
      await this.git(request, request.policy.directory, [
        "config",
        "--get",
        `remote.${request.policy.remote}.url`,
      ])
    ).trim();
    const match =
      /^(?:https:\/\/github\.com\/|git@github\.com:)([A-Za-z0-9-]+\/[A-Za-z0-9_.-]+?)(?:\.git)?$/.exec(
        remote,
      );
    if (match?.[1].toLowerCase() !== request.policy.github.toLowerCase()) {
      throw new Error(
        "Configured remote does not match the allowed GitHub repository",
      );
    }
  }
  async prepare(request: RepairRequest): Promise<Candidate> {
    request = {
      ...request,
      deadline: Date.now() + request.policy.timeoutSeconds * 1000,
    };
    await this.verify(request);
    const worktree = resolve(this.root, request.id);
    if (
      !/^[a-f0-9]{64}$/.test(request.id) ||
      worktree !== join(resolve(this.root), request.id)
    ) {
      throw new Error("Invalid maintenance workspace identity");
    }
    const prefix = `refs/paseo-maintenance/${request.id}`;
    await this.git(request, request.policy.directory, [
      "fetch",
      "--no-tags",
      "--no-recurse-submodules",
      request.policy.remote,
      `+refs/heads/${request.headRef}:${prefix}/head`,
      `+refs/heads/${request.baseRef}:${prefix}/base`,
    ]);
    const head = (
      await this.git(request, request.policy.directory, [
        "rev-parse",
        `${prefix}/head`,
      ])
    ).trim();
    const base = (
      await this.git(request, request.policy.directory, [
        "rev-parse",
        `${prefix}/base`,
      ])
    ).trim();
    if (head !== request.head || base !== request.base)
      throw new StaleRevision("PR revisions changed before resolution");
    // WHY: Restarting a pre-publication attempt can recreate only its own disposable checkout.
    try {
      lstatSync(worktree);
      await this.git(request, request.policy.directory, [
        "worktree",
        "remove",
        "--force",
        worktree,
      ]);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    }
    await this.git(request, request.policy.directory, [
      "worktree",
      "add",
      "--detach",
      worktree,
      request.head,
    ]);
    let strategy: Strategy = "git";
    const candidate: Candidate = {
      strategy,
      strategies: [],
      confidence: null,
      head: null,
      conflicts: [],
      checks: [],
      reason: "",
      patch: join(this.root, `${request.id}.patch`),
      worktree,
    };
    try {
      const touched = (
        await this.git(request, worktree, [
          "diff",
          "--name-only",
          "-z",
          request.head,
          request.base,
        ])
      )
        .split("\0")
        .filter(Boolean);
      if (!(await this.supportedDrivers(request, worktree, touched))) {
        throw new Error("Custom merge attributes require agent inspection");
      }
      let conflicted = false;
      try {
        await this.git(request, worktree, [
          "-c",
          "rerere.enabled=false",
          "merge",
          "--no-commit",
          "--no-ff",
          request.base,
        ]);
      } catch (error) {
        if (failure(error).code !== 1) throw error;
        conflicted = true;
      }
      const paths = (
        await this.git(request, worktree, [
          "diff",
          "--name-only",
          "--diff-filter=U",
          "-z",
        ])
      )
        .split("\0")
        .filter(Boolean);
      if (conflicted && !paths.length)
        throw new Error("Merge failed without inspectable conflict paths");
      if (paths.length && request.policy.confidence.rerere !== null) {
        await this.git(request, worktree, [
          "-c",
          "rerere.enabled=true",
          "-c",
          "rerere.autoupdate=true",
          "rerere",
        ]);
        strategy = "rerere";
      }
      const unmerged = new Set(
        (
          await this.git(request, worktree, [
            "diff",
            "--name-only",
            "--diff-filter=U",
            "-z",
          ])
        )
          .split("\0")
          .filter(Boolean),
      );
      const remaining: string[] = [];
      for (const file of paths) {
        if (!unmerged.has(file)) {
          candidate.strategies.push("rerere");
          continue;
        }
        const target = join(worktree, file);
        const stat = lstatSync(target);
        if (!stat.isFile()) {
          remaining.push(file);
          continue;
        }
        const unresolved = () =>
          /^(?:<{7}|={7}|>{7}|\|{7})(?: |$)/m.test(
            readFileSync(target, "utf8"),
          );
        if (!unresolved() || readFileSync(target).includes(0)) {
          remaining.push(file);
          continue;
        }
        let solved = false;
        if (request.policy.confidence.mergiraf !== null) {
          strategy = "mergiraf";
          try {
            await this.command(request, worktree, "mergiraf", [
              "solve",
              "--",
              file,
            ]);
            solved = !unresolved();
          } catch (error) {
            if (failure(error).code !== 1) throw error;
          }
        }
        if (!solved) remaining.push(file);
        else {
          candidate.strategies.push("mergiraf");
          await this.git(request, worktree, ["add", "--", file]);
        }
      }
      candidate.strategy = strategy;
      candidate.strategies = [
        ...new Set(
          candidate.strategies.length ? candidate.strategies : [strategy],
        ),
      ];
      const scores = candidate.strategies.map(
        (used) => request.policy.confidence[used],
      );
      candidate.confidence = scores.some((score) => score === null)
        ? null
        : Math.min(...(scores as number[]));
      candidate.conflicts = remaining;
      const patch = await this.git(request, worktree, [
        "diff",
        "--binary",
        "HEAD",
      ]);
      writeFileSync(candidate.patch, patch, { mode: 0o600 });
      if (remaining.length) {
        candidate.reason = "Unresolved conflicts remain";
        return candidate;
      }
      const changed = (
        await this.git(request, worktree, ["diff", "--name-only", "-z", "HEAD"])
      )
        .split("\0")
        .filter(Boolean);
      if (!(await this.supportedDrivers(request, worktree, changed, true))) {
        candidate.confidence = null;
        candidate.reason = "Custom merge attributes require agent inspection";
        return candidate;
      }
      if (
        changed.length > request.policy.maxChangedFiles ||
        Buffer.byteLength(patch) > request.policy.maxDiffBytes
      ) {
        candidate.reason = "Resolution exceeds the configured change budget";
        return candidate;
      }
      await this.git(request, worktree, ["diff", "--check", "HEAD"]);
      const validatedTree = (
        await this.git(request, worktree, ["write-tree"])
      ).trim();
      const untracked = await this.git(request, worktree, [
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
      ]);
      for (const command of request.policy.checks) {
        try {
          const output = await this.command(
            request,
            worktree,
            command[0],
            command.slice(1),
          );
          candidate.checks.push({
            command,
            passed: true,
            output: output.slice(-4000),
          });
        } catch (error) {
          candidate.checks.push({
            command,
            passed: false,
            output: (
              (failure(error).stdout ?? "") +
              (failure(error).stderr ?? "") +
              failure(error).message
            ).slice(-4000),
          });
          candidate.reason = "Repository validation failed";
          return candidate;
        }
      }
      // WHY: Validation must not silently add formatting, snapshots or generated output to the accepted merge.
      if (
        (await this.git(request, worktree, ["diff", "--binary", "HEAD"])) !==
          patch ||
        (await this.git(request, worktree, [
          "ls-files",
          "--others",
          "--exclude-standard",
          "-z",
        ])) !== untracked ||
        (await this.git(request, worktree, ["write-tree"])).trim() !==
          validatedTree ||
        (await this.git(request, worktree, ["rev-parse", "HEAD"])).trim() !==
          request.head
      ) {
        candidate.reason = "Validation modified the candidate";
        return candidate;
      }
      if (
        candidate.confidence === null ||
        candidate.confidence < request.policy.minimumConfidence
      ) {
        candidate.reason = "Resolution confidence is below host policy";
        return candidate;
      }
      const mergeHead = await this.git(request, worktree, [
        "rev-parse",
        "--git-path",
        "MERGE_HEAD",
      ]);
      try {
        lstatSync(resolve(worktree, mergeHead.trim()));
        await this.git(request, worktree, [
          "commit",
          "-m",
          `Merge ${request.baseRef} into ${request.headRef}`,
        ]);
      } catch (error) {
        if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
      }
      candidate.head = (
        await this.git(request, worktree, ["rev-parse", "HEAD"])
      ).trim();
      if (
        (
          await this.git(request, worktree, [
            "rev-parse",
            `${candidate.head}^{tree}`,
          ])
        ).trim() !== validatedTree
      ) {
        throw new Error("Commit hooks changed the validated candidate");
      }
      await this.git(request, worktree, [
        "merge-base",
        "--is-ancestor",
        request.head,
        candidate.head,
      ]);
      await this.git(request, worktree, [
        "merge-base",
        "--is-ancestor",
        request.base,
        candidate.head,
      ]);
      await this.git(request, worktree, [
        "update-ref",
        `${prefix}/candidate`,
        candidate.head,
      ]);
      candidate.reason = "Resolution and configured validation passed";
      return candidate;
    } finally {
      // The patch is retained for escalation; the worker's own checkout is never modified.
      await this.git(
        { ...request, deadline: undefined },
        request.policy.directory,
        ["worktree", "remove", "--force", worktree],
      );
    }
  }
  async publish(request: RepairRequest, candidate: Candidate) {
    if (!candidate.head)
      throw new Error("No validated commit is available for publication");
    if ((await this.remoteHead(request)) !== request.head)
      throw new StaleRevision("PR head changed before publication");
    await this.git(request, request.policy.directory, [
      "push",
      "--porcelain",
      `--force-with-lease=refs/heads/${request.headRef}:${request.head}`,
      request.policy.remote,
      `${candidate.head}:refs/heads/${request.headRef}`,
    ]);
  }
}
