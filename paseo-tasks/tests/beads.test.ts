import assert from "node:assert/strict";
import { spawn, type ChildProcess, execFile } from "node:child_process";
import { randomUUID } from "node:crypto";
import { mkdtemp, mkdir, rm } from "node:fs/promises";
import { createConnection, createServer } from "node:net";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { promisify } from "node:util";
import { test } from "node:test";
import { Beads, beadId } from "../server/beads";
import { briefFingerprint, Store } from "../server/store";
import type { Brief } from "../shared/contracts";

const execute = promisify(execFile);
const freePort = async () => {
  const server = createServer();
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  assert(address && typeof address !== "string");
  await new Promise<void>((resolve, reject) =>
    server.close((error) => (error ? reject(error) : resolve())),
  );
  return address.port;
};
const specification: Brief = {
  title: "HTTP task acceptance",
  outcome: "Inspect and update through native Beads HTTP",
  successCriteria: ["Ownership guards preserve the retained worker"],
  constraints: ["No live task migration"],
  kind: "investigation",
  repository: null,
  baseRef: null,
};
await test("native Beads HTTP preserves task identity, guards, history and interrupted projection", {
  skip: !process.env.PASEO_TASKS_NATIVE_BEADS,
}, async (t) => {
  const root = await mkdtemp(join(tmpdir(), "beads-http-"));
  const binary = process.env.PASEO_TASKS_NATIVE_BEADS!;
  const dolt = process.env.PASEO_TASKS_NATIVE_DOLT ?? "dolt";
  const env = {
    ...Object.fromEntries(
      Object.entries(process.env).filter(
        ([key]) => !/^(BEADS_|BD_|DOLT_|GIT_)/.test(key),
      ),
    ),
    HOME: root,
    DOLT_ROOT_PATH: join(root, "dolt-home"),
    DOLT_CLI_NO_UPDATE_CHECK: "1",
    GIT_CONFIG_GLOBAL: "/dev/null",
    GIT_CONFIG_NOSYSTEM: "1",
    GIT_CONFIG_COUNT: "3",
    GIT_CONFIG_KEY_0: "user.name",
    GIT_CONFIG_VALUE_0: "Fixture",
    GIT_CONFIG_KEY_1: "user.email",
    GIT_CONFIG_VALUE_1: "fixture@example.invalid",
    GIT_CONFIG_KEY_2: "core.hooksPath",
    GIT_CONFIG_VALUE_2: "/dev/null",
    BD_DISABLE_METRICS: "1",
  };
  const workspace = join(root, "workspace");
  const data = join(root, "data");
  const processes: ChildProcess[] = [];
  let store: Store | undefined;
  let logs = "";
  const launch = (command: string, args: string[], cwd: string) => {
    const child = spawn(command, args, {
      cwd,
      env,
      stdio: ["ignore", "pipe", "pipe"],
    });
    child.stdout?.on("data", (data) => {
      logs += String(data);
    });
    child.stderr?.on("data", (data) => {
      logs += String(data);
    });
    processes.push(child);
    return child;
  };
  try {
    await mkdir(workspace);
    await mkdir(data);
    await execute("git", ["init", "-q", workspace], { env });
    const sqlPort = await freePort();
    const httpPort = await freePort();
    launch(
      dolt,
      [
        "sql-server",
        "--host",
        "127.0.0.1",
        "--port",
        String(sqlPort),
        "--data-dir",
        data,
      ],
      data,
    );
    let sqlReady = false;
    for (let attempt = 0; attempt < 300; attempt++) {
      sqlReady = await new Promise<boolean>((resolve) => {
        const socket = createConnection({ host: "127.0.0.1", port: sqlPort });
        socket.once("connect", () => {
          socket.destroy();
          resolve(true);
        });
        socket.once("error", () => {
          socket.destroy();
          resolve(false);
        });
      });
      if (sqlReady) break;
      if (processes[0].exitCode !== null) throw new Error(logs);
      await delay(100);
    }
    assert(sqlReady, logs);
    await execute(
      binary,
      [
        "init",
        "--server",
        "--external",
        "--server-host",
        "127.0.0.1",
        "--server-port",
        String(sqlPort),
        "--database",
        "tasks",
        "--prefix",
        "tasks",
        "--skip-agents",
        "--skip-hooks",
        "--non-interactive",
      ],
      { cwd: workspace, env, timeout: 60000 },
    );
    const url = `http://127.0.0.1:${httpPort}`;
    launch(binary, ["serve", "--addr", `127.0.0.1:${httpPort}`], workspace);
    let context: { project_id: string } | undefined;
    for (let attempt = 0; attempt < 200; attempt++) {
      try {
        const response = await fetch(`${url}/v0/beads/context`);
        if (response.ok) {
          context = (await response.json()) as { project_id: string };
          break;
        }
      } catch {}
      if (processes.some((child) => child.exitCode !== null))
        throw new Error(logs);
      await delay(100);
    }
    assert(context, logs);
    await assert.rejects(
      () => new Beads(url, randomUUID()).verifyAuthority(),
      /authority differs/,
    );
    const records = new Beads(url, context.project_id);
    await records.verifyAuthority();
    const file = join(root, "runtime.sqlite");
    store = new Store(file, "mac", undefined, records);
    const value = await store.create(specification);
    const id = beadId(value.taskId);
    await records.create(value);
    const bd = async (...args: string[]) =>
      JSON.parse(
        (
          await execute(binary, ["--json", "--sandbox", ...args], {
            cwd: workspace,
            env,
            timeout: 30000,
          })
        ).stdout,
      );
    assert.equal((await bd("show", id))[0].title, specification.title);
    await bd("update", id, "--title", "Edited independently");
    assert.equal((await store.get(value.taskId)).title, "Edited independently");
    await store.bind(
      value.taskId,
      "worker-a",
      "workspace-a",
      "/retained/checkout",
    );
    const event = await store.addEvent(
      value.taskId,
      "feedback",
      "Retain this feedback",
    );
    await store.workerUpdate(value.taskId, "worker-a", {
      progress: "HTTP write confirmed",
    });
    assert.equal(
      (await bd("show", id))[0].metadata["paseo.progress"],
      "HTTP write confirmed",
    );
    await bd("update", id, "--assignee", "other", "--force");
    await assert.rejects(
      () => store!.assertOwner(value.taskId),
      /ownership changed/,
    );
    await bd("update", id, "--assignee", `paseo:mac/worker-a`, "--force");
    store.db.exec(
      `CREATE TRIGGER interrupt_projection BEFORE UPDATE ON tasks WHEN json_extract(NEW.record,'$.progress')='Remote committed before interruption' BEGIN SELECT RAISE(ABORT,'projection interrupted'); END`,
    );
    await assert.rejects(
      () =>
        store!.workerUpdate(value.taskId, "worker-a", {
          progress: "Remote committed before interruption",
        }),
      /projection interrupted/,
    );
    store.db.exec("DROP TRIGGER interrupt_projection");
    assert.equal(
      (await bd("show", id))[0].metadata["paseo.progress"],
      "Remote committed before interruption",
    );
    assert.equal(
      (await store.get(value.taskId)).progress,
      "Remote committed before interruption",
    );
    assert.throws(
      () => new Store(file, "mac", undefined, new Beads(url, randomUUID())),
      /another or unrecorded authority/,
    );
    store.close();
    store = new Store(file, "mac", undefined, records);
    assert.equal((await store.get(value.taskId)).worker?.agentId, "worker-a");
    assert.equal((await store.events(value.taskId))[0].id, event.id);
    assert((await bd("history", id)).length > 1);
    const unrelated = await store.create({
      ...specification,
      title: "Unrelated bead",
    });
    const remoteFetch = globalThis.fetch;
    const unavailable = t.mock.method(
      globalThis,
      "fetch",
      async (request: Request, init?: RequestInit) => {
        if (new URL(request.url).pathname.endsWith(beadId(unrelated.taskId)))
          return Response.json({ code: "unavailable" }, { status: 503 });
        return await remoteFetch(request, init);
      },
    );
    try {
      assert.equal(await store.forAgent("ordinary-conversation"), undefined);
      assert.equal((await store.forAgent("worker-a"))?.taskId, value.taskId);
    } finally {
      unavailable.mock.restore();
    }
    const evaluated = briefFingerprint(await store.get(value.taskId));
    await bd("update", id, "--title", "Changed before submission");
    await assert.rejects(
      () =>
        store!.workerUpdate(
          value.taskId,
          "worker-a",
          { status: "complete", evidence: ["Old evidence"] },
          evaluated,
        ),
      /current brief fingerprint/,
    );
    // Keep feedback handled so the later refusal specifically exercises the Beads revision fence.
    await store.saveEvent({ ...event, delivery: "handled" });
    const latest = briefFingerprint(await store.get(value.taskId));
    const raced = t.mock.method(
      globalThis,
      "fetch",
      async (request: Request, init?: RequestInit) => {
        if (
          request.method === "PATCH" &&
          new URL(request.url).pathname.endsWith(id)
        ) {
          raced.mock.restore();
          await bd("update", id, "--title", "Changed before the guarded write");
        }
        return await remoteFetch(request, init);
      },
    );
    await assert.rejects(
      () =>
        store!.workerUpdate(
          value.taskId,
          "worker-a",
          { status: "complete", evidence: ["Latest evidence"] },
          latest,
        ),
      /409: precondition_failed/,
    );
    const leftOpen = (await bd("show", id))[0];
    assert.equal(leftOpen.title, "Changed before the guarded write");
    assert.equal(leftOpen.status, "in_progress");
    await store.workerUpdate(
      value.taskId,
      "worker-a",
      { status: "complete", evidence: ["Verified edited criteria"] },
      briefFingerprint(await store.get(value.taskId)),
    );
    assert.equal((await bd("show", id))[0].status, "closed");
    await assert.rejects(
      () => store!.claim(value.taskId, "worker-a"),
      /not active/,
    );
  } finally {
    store?.close();
    for (const child of processes.reverse()) {
      if (child.exitCode === null) {
        child.kill("SIGTERM");
        await Promise.race([
          new Promise((resolve) => child.once("exit", resolve)),
          delay(5000),
        ]);
        if (child.exitCode === null) child.kill("SIGKILL");
      }
    }
    await rm(root, { recursive: true, force: true });
  }
});
