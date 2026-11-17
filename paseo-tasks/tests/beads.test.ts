import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { fileURLToPath, URL } from "node:url";
import { Beads, beadId } from "../server/beads";
import { Store } from "../server/store";
import { TaskService } from "../server/service";
import type { Brief } from "../shared/contracts";

await test("native Beads preserves identity, CLI independence, claims and interrupted projection", {
  skip: !process.env.PASEO_TASKS_NATIVE_BEADS,
}, async () => {
  const root = mkdtempSync(join(tmpdir(), "beads-tasks-"));
  const binary = process.env.PASEO_TASKS_NATIVE_BEADS!;
  const env: NodeJS.ProcessEnv = {
    ...process.env,
    HOME: root,
    BD_DISABLE_METRICS: "1",
    GIT_CONFIG_COUNT: "4",
    GIT_CONFIG_KEY_0: "user.name",
    GIT_CONFIG_VALUE_0: "Fixture",
    GIT_CONFIG_KEY_1: "user.email",
    GIT_CONFIG_VALUE_1: "fixture@example.invalid",
    GIT_CONFIG_KEY_2: "commit.gpgsign",
    GIT_CONFIG_VALUE_2: "false",
    GIT_CONFIG_KEY_3: "core.hooksPath",
    GIT_CONFIG_VALUE_3: "/dev/null",
  };
  const run = (command: string, args: string[]) => {
    const result = spawnSync(command, args, {
      cwd: root,
      env,
      encoding: "utf8",
      timeout: 30_000,
    });
    assert.equal(
      result.status,
      0,
      [result.error?.message, result.stdout, result.stderr]
        .filter(Boolean)
        .join("\n"),
    );
    return result.stdout;
  };
  const bd = (...args: string[]) =>
    JSON.parse(run(binary, ["--json", "--sandbox", ...args]));
  const specification: Brief = {
    title: "Pilot task",
    outcome: "Verify independent inspection",
    successCriteria: ["CLI shows current state"],
    constraints: ["Do not merge"],
    kind: "investigation",
    repository: null,
    baseRef: null,
  };
  const file = join(root, "runtime.sqlite");
  let store: Store | undefined;
  const originalEnvironment = { ...process.env };
  try {
    Object.assign(process.env, env);
    const tools = join(root, "tools");
    mkdirSync(tools);
    symlinkSync(binary, join(tools, "bd"));
    env.PATH = `${tools}:${process.env.PATH}`;
    Object.assign(process.env, env);
    writeFileSync(
      join(root, "AGENTS.md"),
      "Authored instructions stay canonical\n",
    );
    const initializer = fileURLToPath(
      new URL("../../scripts/init-beads-coordinator", import.meta.url),
    );
    run("sh", [initializer, root]);
    const authority = bd("kv", "get", "paseo.authority").value;
    run("sh", [initializer, root]);
    assert.equal(bd("kv", "get", "paseo.authority").value, authority);
    assert.equal(
      readFileSync(join(root, "AGENTS.md"), "utf8"),
      "Authored instructions stay canonical\n",
    );
    assert.equal(existsSync(join(root, ".agents/skills")), false);
    assert.throws(
      () => new Beads(root, randomUUID(), binary),
      /authority differs/,
    );
    const records = new Beads(root, authority, binary);
    store = new Store(file, "mac");
    const legacy = store.create(specification, null, randomUUID(), "paused");
    store.bind(legacy.taskId, "worker-a", "workspace-a", "/retained/checkout");
    const pending = store.addEvent(
      legacy.taskId,
      "feedback",
      "Retain this follow-up",
    );
    store.close();
    store = new Store(file, "mac", undefined, records);
    const migrated = store.migrateBeads(legacy.taskId);
    assert.equal(
      readdirSync(join(root, "backups")).some(
        (name) =>
          name.startsWith(`before-beads-${legacy.taskId}-`) &&
          name.endsWith(".sqlite"),
      ),
      true,
    );
    assert.equal(migrated.taskId, legacy.taskId);
    assert.equal(migrated.worker?.agentId, "worker-a");
    assert.equal(store.events(legacy.taskId)[0].id, pending.id);
    assert.equal(store.events(legacy.taskId)[0].delivery, "queued");
    assert.equal(
      bd("show", beadId(legacy.taskId))[0].title,
      specification.title,
    );
    const stale = store.get(legacy.taskId).revision;
    bd(
      "update",
      beadId(legacy.taskId),
      "--title",
      "Edited without Paseo",
      "--acceptance",
      "Human-readable acceptance",
    );
    assert.equal(store.get(legacy.taskId).title, "Edited without Paseo");
    assert.deepEqual(store.get(legacy.taskId).successCriteria, [
      "Human-readable acceptance",
    ]);
    assert.throws(
      () =>
        store!.change(
          legacy.taskId,
          (v) => {
            v.title = "stale overwrite";
          },
          stale,
        ),
      /changed/,
    );
    assert.throws(
      () => records.claim(store!.get(legacy.taskId), "competing-worker"),
      /claimed/,
    );
    assert.throws(
      () =>
        store!.workerUpdate(legacy.taskId, "worker-a", {
          status: "complete",
          evidence: ["CLI observed"],
        }),
      /pending assigned feedback/,
    );
    store.workerUpdate(legacy.taskId, "worker-a", {
      progress: "Current evidence is in Beads",
    });
    assert.equal(
      bd("show", beadId(legacy.taskId))[0].metadata["paseo.progress"],
      "Current evidence is in Beads",
    );
    const shim = join(root, "bd-inject");
    const marker = join(root, "injected");
    writeFileSync(
      shim,
      `#!${process.execPath}
const {spawnSync} = require('node:child_process');
const fs = require('node:fs');
const args = process.argv.slice(2);
if(args.includes('update') && args.includes('--metadata') && !fs.existsSync(${JSON.stringify(marker)})) {
 fs.writeFileSync(${JSON.stringify(marker)},'once');
 const edit=spawnSync(${JSON.stringify(binary)},['--json','--sandbox','update',${JSON.stringify(beadId(legacy.taskId))},'--metadata',JSON.stringify({'paseo.evidence':['Concurrent CLI evidence'],'unrelated':'preserve me','paseo.blocker':'temporary'})],{stdio:'pipe'});
 if(edit.status!==0) { process.stderr.write(edit.stderr); process.exit(1); }
}
const result=spawnSync(${JSON.stringify(binary)},args,{stdio:'inherit'});
process.exit(result.status ?? 1);
`,
      { mode: 0o755 },
    );
    store.close();
    store = new Store(file, "mac", undefined, new Beads(root, authority, shim));
    const concurrent = store.workerUpdate(legacy.taskId, "worker-a", {
      progress: "Patch preserves unrelated edits",
    });
    assert.deepEqual(concurrent.evidence, ["Concurrent CLI evidence"]);
    assert.equal(
      bd("show", beadId(legacy.taskId))[0].metadata.unrelated,
      "preserve me",
    );
    store.workerUpdate(legacy.taskId, "worker-a", {
      evidence: [],
      blocker: null,
    });
    assert.deepEqual(store.get(legacy.taskId).evidence, []);
    assert.equal(store.get(legacy.taskId).blocker, null);
    bd(
      "update",
      beadId(legacy.taskId),
      "--assignee",
      "another-worker",
      "--force",
    );
    store.change(legacy.taskId, (v) => {
      v.control = "running";
    });
    const service = new TaskService(
      store,
      {} as never,
      {} as never,
      {} as never,
      "fixture",
    );
    await assert.rejects(
      service.deliver(store.get(legacy.taskId)),
      /ownership changed/,
    );
    assert.throws(
      () =>
        store!.workerUpdate(legacy.taskId, "worker-a", {
          progress: "Must not write",
        }),
      /ownership changed/,
    );
    bd(
      "update",
      beadId(legacy.taskId),
      "--assignee",
      "paseo:mac/worker-a",
      "--force",
    );
    const bound = store.get(legacy.taskId);
    bd(
      "update",
      beadId(legacy.taskId),
      "--if-assignee",
      "paseo:mac/worker-a",
      "--assignee",
      "",
    );
    assert.throws(
      () =>
        records.update(bound, {
          ...bound,
          progress: "Unassigned worker must not write",
        }),
      /ownership changed/,
    );
    bd("update", beadId(legacy.taskId), "--assignee", "paseo:mac/worker-a");
    const repairUrl = "https://example.invalid/pr/1";
    store.change(legacy.taskId, (value) => {
      value.prWatches = [
        {
          url: repairUrl,
          head: "head",
          base: "base",
          phase: "repair",
          detail: "fixture",
          observedAt: new Date().toISOString(),
        },
      ];
    });
    const repair = store.addEvent(
      legacy.taskId,
      "github",
      "Controlled repair",
      { payload: { type: "repair", url: repairUrl } },
    );
    let sent = 0;
    const handle = {
      status: "idle",
      activeTurn: null,
      pendingPermissions: [],
      refresh: async () => true,
      send: async () => {
        sent++;
      },
    };
    const changingOwnerService = new TaskService(
      store,
      { agents: { ref: () => handle } } as never,
      {} as never,
      {} as never,
      "fixture",
      undefined,
      undefined,
      {
        handle: async () => {
          bd(
            "update",
            beadId(legacy.taskId),
            "--assignee",
            "another-worker",
            "--force",
          );
          return false;
        },
      } as never,
    );
    changingOwnerService.sessionOpened("worker-a", "worker");
    await assert.rejects(
      changingOwnerService.deliver(store.get(legacy.taskId)),
      /ownership changed/,
    );
    assert.equal(sent, 0);
    assert.equal(
      store.events(legacy.taskId).find((entry) => entry.id === repair.id)
        ?.delivery,
      "queued",
    );
    bd(
      "update",
      beadId(legacy.taskId),
      "--assignee",
      "paseo:mac/worker-a",
      "--force",
    );
    store.saveEvent({ ...repair, delivery: "handled" });
    store.db.exec(
      "CREATE TRIGGER fail_projection BEFORE UPDATE ON tasks BEGIN SELECT RAISE(ABORT,'fixture projection failure'); END;",
    );
    assert.throws(
      () =>
        store!.change(legacy.taskId, (v) => {
          v.progress = "Canonical write survived";
        }),
      /projection failure/,
    );
    store.db.exec("DROP TRIGGER fail_projection");
    store.close();
    store = new Store(file, "mac", undefined, records);
    assert.equal(store.get(legacy.taskId).progress, "Canonical write survived");
    assert.equal(store.events(legacy.taskId)[0].delivery, "queued");
    const feedback = store.events(legacy.taskId)[0];
    store.saveEvent({ ...feedback, delivery: "handled" });
    store.workerUpdate(legacy.taskId, "worker-a", {
      status: "complete",
      evidence: ["CLI observed current state"],
    });
    assert.equal(bd("show", beadId(legacy.taskId))[0].status, "closed");
    assert.equal(bd("history", beadId(legacy.taskId)).length > 0, true);
    for (const status of ["closed", "blocked", "deferred"]) {
      const unbound = store.create(specification);
      bd("update", beadId(unbound.taskId), "--status", status);
      const currentService = new TaskService(
        store,
        {} as never,
        {} as never,
        {} as never,
        "fixture",
      );
      await currentService.start(unbound.taskId);
      assert.equal(bd("show", beadId(unbound.taskId))[0].status, status);
      assert.equal(store.get(unbound.taskId).worker, null);
    }
    store.close();
    store = new Store(file, "mac");
    assert.throws(() => store!.get(legacy.taskId), /authority unavailable/);
  } finally {
    store?.close();
    for (const key of Object.keys(process.env))
      if (!(key in originalEnvironment)) delete process.env[key];
    Object.assign(process.env, originalEnvironment);
    rmSync(root, { recursive: true, force: true });
  }
});
