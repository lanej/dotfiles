import { run } from "./process.ts";

type GitChanges = {
  files: number;
  added: number;
  removed: number;
  untracked: number;
};

export type FooterGit = {
  linked?: boolean;
  changes?: GitChanges;
  pullRequest?: string;
};

async function gitChanges(cwd: string): Promise<GitChanges> {
  const git = (...args: string[]) =>
    run("git", ["--no-optional-locks", ...args], { cwd, timeout: 2500 });
  const [diff, untracked] = await Promise.all([
    git(
      "diff",
      "--numstat",
      "-z",
      "--no-renames",
      "--no-ext-diff",
      "--no-textconv",
      "HEAD",
      "--",
      ":/",
    ),
    git("ls-files", "--others", "--exclude-standard", "-z", "--", ":/"),
  ]);
  const changes = {
    files: 0,
    added: 0,
    removed: 0,
    untracked: untracked.split("\0").filter((path) => path !== "").length,
  };
  for (const line of diff.split("\0")) {
    if (line === "") continue;
    const [, added = "", removed = ""] =
      /^(\d+|-)\t(\d+|-)\t/u.exec(line) ?? [];
    if (added === "" || removed === "")
      throw new Error("Unrecognized Git numstat row");
    changes.files++;
    changes.added += added === "-" ? 0 : Number(added);
    changes.removed += removed === "-" ? 0 : Number(removed);
  }
  return changes;
}

export function watchFooterGit(
  cwd: string,
  trackedPullRequest: (() => string | undefined) | undefined,
  update: (status: FooterGit) => void,
): () => void {
  let disposed = false;
  let busy = false;
  let linked: boolean | undefined;
  let previous = "";
  const refresh = async () => {
    if (busy) return;
    busy = true;
    try {
      if (linked === undefined) {
        const dirs = await run(
          "git",
          [
            "rev-parse",
            "--path-format=absolute",
            "--git-dir",
            "--git-common-dir",
          ],
          { cwd, timeout: 1500 },
        ).catch(() => "");
        const [checkout, common] = dirs.trimEnd().split("\n");
        if (checkout !== undefined && common !== undefined)
          linked = checkout !== common;
      }
      const changes =
        linked === undefined
          ? undefined
          : await gitChanges(cwd).catch(() => undefined);
      const pullRequest = trackedPullRequest?.();
      const status = {
        ...(linked === undefined ? {} : { linked }),
        ...(changes === undefined ? {} : { changes }),
        ...(pullRequest === undefined ? {} : { pullRequest }),
      };
      const signature = JSON.stringify(status);
      if (!disposed && previous !== signature) {
        previous = signature;
        update(status);
      }
    } finally {
      busy = false;
    }
  };
  const tick = () => {
    void refresh().catch(() => {});
  };
  tick();
  const timer = setInterval(tick, 8000).unref();
  return () => {
    disposed = true;
    clearInterval(timer);
  };
}
