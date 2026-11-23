import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import {
  mkdtemp,
  mkdir,
  writeFile,
  readFile,
  realpath,
  rename,
  rm,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { promisify } from "node:util";
import { WorktreeManager } from "../server/worktrees";

const execute = promisify(execFile);
const binary = process.env.WORKTREE_MANAGER_BINARY || "worktree";

await test("native manager allocations preserve base, ownership and lost-response identity", async () => {
  const root = await realpath(await mkdtemp(join(tmpdir(), "paseo-worktree-")));
  const previous = { ...process.env };
  try {
    for (const key of Object.keys(process.env))
      if (
        key.startsWith("GIT_") ||
        key.startsWith("XDG_") ||
        key.startsWith("WORKTREE_")
      )
        delete process.env[key];
    Object.assign(process.env, {
      HOME: join(root, "home"),
      XDG_STATE_HOME: join(root, "state"),
      GIT_CONFIG_GLOBAL: "/dev/null",
      GIT_CONFIG_NOSYSTEM: "1",
    });
    const repo = join(root, "repo");
    await mkdir(repo);
    const git = async (...args: string[]) =>
      (
        await execute("git", [
          "-C",
          repo,
          "-c",
          "user.name=Test",
          "-c",
          "user.email=test@example.invalid",
          "-c",
          "commit.gpgsign=false",
          ...args,
        ])
      ).stdout.trim();
    const manager = new WorktreeManager(binary);
    await git("init", "-q", "--initial-branch=main");
    await writeFile(join(repo, ".gitignore"), ".worktrees/\n");
    await git("add", ".gitignore");
    await git("commit", "-qm", "initial");
    const initial = await git("rev-parse", "HEAD");
    const beforeMissingManager = await git("worktree", "list", "--porcelain");
    await assert.rejects(
      () =>
        new WorktreeManager(join(root, "missing-manager")).prepare(
          repo,
          "paseo-task:missing-manager",
          "task/missing-manager",
          "main",
          "pi",
        ),
      /Worktree manager is unavailable/,
    );
    assert.equal(
      await git("worktree", "list", "--porcelain"),
      beforeMissingManager,
    );
    const stale = join(root, "stale");
    await git("clone", "-q", repo, stale);
    await execute(binary, ["backfill", stale, "--json"]);
    await rm(stale, { recursive: true });
    // Historical tasks can have no agent metadata; owner reconciliation ignores them.
    const manual = JSON.parse(
      (await execute(binary, ["create", "--repo", repo, "--json"])).stdout,
    ).result;
    const oldRecord = join(
      root,
      "state/worktree-manager/tasks",
      `${manual.id}.json`,
    );
    const old = JSON.parse(await readFile(oldRecord, "utf8"));
    delete old.agent;
    await writeFile(oldRecord, JSON.stringify(old));
    const reserved = await manager.prepare(
      manual.path,
      "paseo-task:host:full-id",
      "task/example",
      "main",
      "pi",
    );
    assert.equal(reserved.baseCommit, initial);
    await git("commit", "--allow-empty", "-qm", "ahead after reservation");
    let attempts = 0;
    const attempting = () => {
      attempts++;
      reserved.attempted = true;
    };
    const allocated = await manager.acquire(reserved, attempting);
    assert.equal(allocated.agent, "pi");
    assert.equal(allocated.owner_id, reserved.holder);
    assert.equal(
      allocated.path,
      join(repo, ".worktrees", `pi-${allocated.task_id.slice(0, 8)}`),
    );
    assert.equal(await git("rev-parse", "task/example"), initial);
    assert.deepEqual(await manager.acquire(reserved, attempting), allocated);
    assert.equal(
      attempts,
      1,
      "lost-response reconciliation must not allocate twice",
    );
    const displaced = join(root, "displaced");
    await rename(allocated.path, displaced);
    try {
      await assert.rejects(
        () => manager.acquire(reserved, attempting),
        /unavailable or moved/,
      );
      assert.equal(attempts, 1);
    } finally {
      await rename(displaced, allocated.path);
    }
    const before = await git("worktree", "list", "--porcelain");
    await assert.rejects(
      () =>
        manager.acquire(
          { ...reserved, holder: "unknown-owner", attempted: true },
          attempting,
        ),
      /outcome remains unknown/,
    );
    assert.equal(await git("worktree", "list", "--porcelain"), before);
    await git("-C", allocated.path, "branch", "-m", "renamed-task");
    await assert.rejects(
      () => manager.acquire(reserved, attempting),
      /branch differs/,
    );
    assert.equal(attempts, 1);
    const hook = join(repo, ".git/hooks/post-checkout");
    await writeFile(hook, "#!/bin/sh\nexit 7\n", { mode: 0o755 });
    const partial = await manager.prepare(
      repo,
      "paseo-task:host:partial",
      "task/partial",
      "main",
      "pi",
    );
    await assert.rejects(() =>
      manager.acquire(partial, () => {
        partial.attempted = true;
      }),
    );
    await rm(hook);
    const recovered = await manager.acquire(partial, () =>
      assert.fail("must reconcile surviving task"),
    );
    assert.equal(recovered.owner_id, partial.holder);
    const status = JSON.parse(
      await execute(binary, ["status", "--json"]).then(
        (result) => result.stdout,
        (error: { code: number; stdout: string }) => {
          assert.equal(error.code, 1);
          return error.stdout;
        },
      ),
    ).result;
    assert.equal(
      status.tasks.filter(
        (row: { owner_id?: string }) => row.owner_id === partial.holder,
      ).length,
      1,
    );
  } finally {
    for (const key of Object.keys(process.env))
      if (!(key in previous)) delete process.env[key];
    Object.assign(process.env, previous);
    await rm(root, { recursive: true, force: true });
  }
});
