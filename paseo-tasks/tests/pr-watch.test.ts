import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import type { GitHubPort } from "../server/github";
import { PRMaintenance } from "../server/pr-maintenance";
import {
  latestChecks,
  latestStatuses,
  type PullRequest,
  watchPR,
} from "../server/pr-watch";
import { Store } from "../server/store";
import { maintenanceFixture } from "./maintenance-fixture";

function programFixture(mode: "clean" | "recorded" | "structural" = "clean") {
  const repo = maintenanceFixture(mode);
  const store = new Store(join(repo.root, "tasks.sqlite"), "host");
  const value = store.create({
    title: "Maintain PR",
    outcome: "Deliver the change",
    kind: "coding",
    repository: repo.repository,
    baseRef: "main",
    successCriteria: ["Configured checks pass"],
    constraints: [],
  });
  store.bind(value.taskId, randomUUID(), randomUUID(), repo.repository);
  store.change(value.taskId, (current) => {
    current.github = ["https://github.com/o/r/pull/1"];
    current.status = "decision";
  });
  const entry = store.addEvent(value.taskId, "github", "Repair conflict", {
    payload: {
      type: "repair",
      url: "https://github.com/o/r/pull/1",
      revision: repo.pr.head,
      baseRevision: repo.pr.base,
      repair: { conflict: true },
      previousStatus: "decision",
    },
  });
  const github = {
    observe: async () => ({
      head: repo.pr.head,
      pullRequest: repo.pr,
      state: repo.pr,
      events: [],
    }),
  } as unknown as GitHubPort;
  const program = new PRMaintenance(
    store,
    github,
    repo.root,
    () => repo.policy,
  );
  return {
    ...repo,
    store,
    entry,
    value: store.get(value.taskId),
    github,
    program,
    cleanup: () => {
      store.close();
      repo.cleanup();
    },
  };
}

await test("current check attempts and commit status contexts replace historical failures without hiding other apps", () => {
  const checks = latestChecks([
    {
      id: 1,
      name: "test",
      app: 10,
      status: "completed",
      conclusion: "failure",
      completedAt: "earlier",
      url: null,
    },
    {
      id: 3,
      name: "test",
      app: 10,
      status: "completed",
      conclusion: "success",
      completedAt: "later",
      url: null,
    },
    {
      id: 2,
      name: "test",
      app: 11,
      status: "completed",
      conclusion: "failure",
      completedAt: "earlier",
      url: null,
    },
  ]);
  assert.deepEqual(
    checks.map((value) => value.id),
    [2, 3],
  );
  const statuses = latestStatuses([
    { id: 30, context: "build", state: "success", url: null },
    { id: 20, context: "build", state: "failure", url: null },
  ]);
  assert.deepEqual(
    statuses.map((value) => value.id),
    [30],
  );
  const clean: PullRequest = {
    state: "open",
    merged: false,
    draft: false,
    head: "h",
    base: "b",
    mergeable: true,
    mergeableState: "clean",
    checks: [checks[1]],
    statuses,
  };
  assert.equal(watchPR(clean).phase, "review");
  assert.equal(watchPR({ ...clean, checks }).phase, "repair");
  assert.equal(watchPR({ ...clean, mergeable: null }).phase, "unknown");
  assert.equal(watchPR({ ...clean, mergeable: false }).repair!.conflict, true);
  assert.equal(watchPR({ ...clean, checks: [], statuses: [] }).phase, "checks");
  assert.equal(
    watchPR({ ...clean, state: "closed", mergeable: false, checks }).phase,
    "closed",
  );
});

await test("program publishes validated Git and recorded resolutions without changing the worker checkout", async () => {
  for (const recorded of [false, true]) {
    const f = programFixture(recorded ? "recorded" : "clean");
    try {
      const before = f.git("status", "--porcelain");
      assert.equal(
        await f.program.handle(f.value, f.entry, async () => true),
        true,
      );
      const record = f.program.records(f.value.taskId)[0];
      assert.equal(record.state, "published", record.reason);
      assert.equal(record.candidate!.strategy, recorded ? "rerere" : "git");
      assert.equal(
        f.git("ls-remote", "origin", "refs/heads/feature").split(/\s+/)[0],
        record.candidate!.head,
      );
      assert.equal(f.git("rev-parse", "HEAD"), f.pr.head);
      assert.equal(f.git("status", "--porcelain"), before);
      assert.equal(
        readFileSync(join(f.repository, "unrelated.txt"), "utf8"),
        "preserve this local work\n",
      );
      assert.ok(readFileSync(record.candidate!.patch, "utf8").length);
      assert.equal(f.store.events(f.value.taskId)[0].delivery, "handled");
      assert.equal(f.store.get(f.value.taskId).status, "decision");
      const restarted = new PRMaintenance(
        f.store,
        f.github,
        f.root,
        () => f.policy,
      );
      assert.equal(
        await restarted.handle(f.value, f.entry, async () => true),
        true,
      );
      assert.equal(restarted.records(f.value.taskId).length, 1);
    } finally {
      f.cleanup();
    }
  }
});

await test("below-threshold or failed validation escalates with evidence and never publishes", async () => {
  for (const mode of ["threshold", "validation", "mutation"]) {
    const f = programFixture("recorded");
    try {
      if (mode === "threshold") f.policy.minimumConfidence = 0.99;
      if (mode === "validation")
        f.policy.checks = [[process.execPath, "-e", "process.exit(1)"]];
      if (mode === "mutation")
        f.policy.checks = [
          [
            process.execPath,
            "-e",
            "require('node:fs').writeFileSync('value.txt','changed')",
          ],
        ];
      assert.equal(
        await f.program.handle(f.value, f.entry, async () => true),
        false,
      );
      const record = f.program.records(f.value.taskId)[0];
      assert.equal(record.state, "needs_agent");
      assert.match(
        record.reason,
        mode === "threshold"
          ? /confidence/
          : mode === "mutation"
            ? /modified/
            : /validation/,
      );
      assert.equal(
        f.git("ls-remote", "origin", "refs/heads/feature").split(/\s+/)[0],
        f.pr.head,
      );
      assert.equal(
        (
          f.store.events(f.value.taskId)[0].payload.maintenance as {
            id: string;
          }
        ).id,
        record.id,
      );
    } finally {
      f.cleanup();
    }
  }
});

await test("pause, changed revisions and policy revocation prevent program publication", async () => {
  for (const mode of ["pause", "head", "base", "policy"]) {
    const f = programFixture();
    try {
      const prepare = f.program.resolver.prepare.bind(f.program.resolver);
      f.program.resolver.prepare = async (request) => {
        const candidate = await prepare(request);
        if (mode === "pause")
          f.store.change(f.value.taskId, (current) => {
            current.control = "paused";
          });
        if (mode === "head") f.pr.head = "f".repeat(40);
        if (mode === "base") f.pr.base = "f".repeat(40);
        if (mode === "policy") f.policy.minimumConfidence = 0.999;
        return candidate;
      };
      await f.program.handle(f.value, f.entry, async () => true);
      assert.notEqual(f.program.records(f.value.taskId)[0].state, "published");
      assert.equal(
        f.git("ls-remote", "origin", "refs/heads/feature").split(/\s+/)[0],
        f.entry.payload.revision,
      );
    } finally {
      f.cleanup();
    }
  }
});

await test("a lost push response reconciles after restart without a second push even if policy was removed", async () => {
  const f = programFixture("recorded");
  try {
    const publish = f.program.resolver.publish.bind(f.program.resolver);
    let pushes = 0;
    f.program.resolver.publish = async (request, candidate) => {
      pushes++;
      await publish(request, candidate);
      throw new Error("Lost response");
    };
    assert.equal(
      await f.program.handle(f.value, f.entry, async () => true),
      false,
    );
    assert.equal(f.program.records(f.value.taskId)[0].state, "publishing");
    f.pr.head = f.program.records(f.value.taskId)[0].candidate!.head!;
    const restarted = new PRMaintenance(
      f.store,
      f.github,
      f.root,
      () => null,
      f.program.resolver,
    );
    assert.equal(
      await restarted.handle(f.value, f.entry, async () => true),
      true,
    );
    assert.equal(restarted.records(f.value.taskId)[0].state, "published");
    assert.equal(pushes, 1);
  } finally {
    f.cleanup();
  }
});

await test("Mergiraf resolves a real structural conflict and validates both changes before publication", {
  skip:
    spawnSync("mergiraf", ["--version"]).status !== 0
      ? "Optional Mergiraf binary is not installed"
      : false,
}, async () => {
  const f = programFixture("structural");
  try {
    const handled = await f.program.handle(f.value, f.entry, async () => true);
    const record = f.program.records(f.value.taskId)[0];
    assert.equal(record.state, "published", record.reason);
    assert.equal(handled, true);
    assert.equal(record.candidate!.strategy, "mergiraf");
    assert.equal(record.candidate!.confidence, 0.97);
    const result = JSON.parse(
      f.git("show", `${record.candidate!.head}:value.json`),
    );
    assert.deepEqual(result, { base: true, feature: true, upstream: true });
  } finally {
    f.cleanup();
  }
});

await test("unscored structural resolutions and PRs outside the worker branch escalate without publishing", async () => {
  for (const mode of ["unscored", "fork", "branch"]) {
    const f = programFixture("structural");
    try {
      if (mode === "unscored") {
        f.policy.confidence.rerere = null;
        f.policy.confidence.mergiraf = null;
      }
      if (mode === "fork") f.pr.headRepository = "someone/else";
      if (mode === "branch") f.pr.headRef = "main";
      assert.equal(
        await f.program.handle(f.value, f.entry, async () => true),
        false,
      );
      assert.equal(f.program.records(f.value.taskId)[0].state, "needs_agent");
      assert.equal(
        f.git("ls-remote", "origin", "refs/heads/feature").split(/\s+/)[0],
        f.pr.head,
      );
    } finally {
      f.cleanup();
    }
  }
});

await test("an unconfirmed push keeps its identity and escalates without automatic replay", async () => {
  const f = programFixture();
  try {
    let pushes = 0;
    f.program.resolver.publish = async () => {
      pushes++;
      throw new Error("Disconnected before readback");
    };
    assert.equal(
      await f.program.handle(f.value, f.entry, async () => true),
      false,
    );
    const restarted = new PRMaintenance(
      f.store,
      f.github,
      f.root,
      () => f.policy,
      f.program.resolver,
    );
    assert.equal(
      await restarted.handle(f.value, f.entry, async () => true),
      false,
    );
    assert.equal(restarted.records(f.value.taskId)[0].state, "publishing");
    assert.equal(pushes, 1);
  } finally {
    f.cleanup();
  }
});

await test("custom merge drivers cannot inherit the clean Git confidence score", async () => {
  const f = programFixture();
  try {
    writeFileSync(join(f.repository, ".gitattributes"), "*.txt merge=union\n");
    f.git("add", ".gitattributes");
    f.git("commit", "-m", "Configure union driver");
    f.git("push", "origin", "feature");
    f.pr.head = f.git("rev-parse", "HEAD");
    f.entry.payload.revision = f.pr.head;
    f.store.saveEvent(f.entry);
    assert.equal(
      await f.program.handle(f.value, f.entry, async () => true),
      false,
    );
    assert.match(
      f.program.records(f.value.taskId)[0].reason,
      /merge attributes/,
    );
    assert.equal(
      f.git("ls-remote", "origin", "refs/heads/feature").split(/\s+/)[0],
      f.pr.head,
    );
  } finally {
    f.cleanup();
  }
});
