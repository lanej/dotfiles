import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { randomUUID } from "node:crypto";
import { Store } from "../server/store";
import { inventory, stage, releaseAndImport } from "../server/migration";
import { digest } from "../server/github";

test("Firstmate transfer refuses live ownership and drift, preserves checkout/session, and resumes from a failed import with pending feedback and reply intent", async () => {
  const directory = await mkdtemp(join(tmpdir(), "task-migration-"));
  const home = join(directory, "firstmate");
  const checkout = join(directory, "existing-checkout");
  const state = join(home, "state");
  const data = join(home, "data", "legacy-task");
  const sessionFile = join(directory, "original-session.jsonl");
  const store = new Store(join(directory, "tasks.sqlite"), "mac");
  const originalMeta = `worktree=${checkout}\nbranch=legacy-branch\nharness=pi\nspawn_gen=generation1\npr=https://github.com/o/r/pull/1\n`;
  const metadataPath = join(state, "legacy-task.meta");
  try {
    await mkdir(state, { recursive: true }); await mkdir(data, { recursive: true }); await mkdir(checkout);
    await writeFile(join(checkout, "wip.txt"), "Uncommitted work must survive");
    await writeFile(metadataPath, originalMeta);
    await writeFile(join(data, "brief.md"), "The original desired outcome");
    const sessionId = randomUUID();
    const history = `${JSON.stringify({ type: "session", version: 3, id: sessionId, cwd: checkout })}\n`;
    await writeFile(sessionFile, history);
    const session = { schema: "firstmate-github-session.v1", task: "legacy-task", branch: "legacy-branch",
      sessionFile, sessionId, pid: process.pid, generation: "generation1", worktree: checkout };
    await writeFile(join(data, "github-session.json"), JSON.stringify(session));
    await writeFile(join(data, "github-session.json"), JSON.stringify({ ...session, generation: "old-generation" }));
    await assert.rejects(() => inventory(home), /ownership differs/);
    await writeFile(join(data, "github-session.json"), JSON.stringify(session));
    const live = (await inventory(home))[0];
    const taskId = randomUUID();
    const brief = { title: "Retained task", outcome: "The original desired outcome", successCriteria: ["Deliver the original criteria"],
      constraints: ["Preserve work"], kind: "coding" as const, repository: checkout, baseRef: null };
    await stage(store, live, brief, taskId);
    assert.equal(store.get(taskId).status, "active", "Retained coding work requires no new checkout base");
    await assert.rejects(() => releaseAndImport(store, taskId, async () => { throw new Error("Must not import"); }), /still alive/);
    assert.equal(await readFile(metadataPath, "utf8"), originalMeta);
    assert.equal(store.get(taskId).migration!.ownership, "firstmate");
    await writeFile(join(data, "github-session.json"), JSON.stringify({ ...session, pid: 2147483647 }));
    const stopped = (await inventory(home))[0];
    const stagedId = randomUUID();
    await assert.rejects(() => stage(store, stopped, brief, stagedId), /staged owner/);
    store.db.prepare("DELETE FROM events WHERE task=?").run(taskId);
    store.db.prepare("DELETE FROM tasks WHERE id=?").run(taskId);
    await stage(store, stopped, brief, stagedId);
    await writeFile(metadataPath, originalMeta + "changed=yes\n");
    await assert.rejects(() => releaseAndImport(store, stagedId, async () => { throw new Error("Must not import"); }), /metadata changed/);
    await writeFile(metadataPath, originalMeta);
    const inbox = join(state, "legacy-task.inbox");
    await mkdir(inbox);
    const githubEvent = { id: "a".repeat(64), url: "https://github.com/o/r/pull/1", type: "inline",
      body: "Address the source feedback", source: "https://github.com/o/r/pull/1#discussion_r10", commentId: 10 };
    await writeFile(join(inbox, "001.msg"), `schema=fm-task-inbox.v1\nat=now\nbody-terminator=1\n--\nFIRSTMATE_GITHUB_EVENT v1\n${JSON.stringify(githubEvent)}\n`);
    await writeFile(join(inbox, "002.msg"), "schema=fm-task-inbox.v1\nat=now\nbody-terminator=1\n--\nQueued user correction\n");
    const objectDirectory = join(state, "github-feedback", "objects");
    const replyDirectory = join(state, "github-feedback", "replies");
    await mkdir(objectDirectory, { recursive: true }); await mkdir(replyDirectory, { recursive: true });
    await writeFile(join(objectDirectory, `${digest(githubEvent.url)}.json`), JSON.stringify({ seen: [githubEvent.id], pending: [], stateVersion: 4 }));
    await writeFile(join(replyDirectory, `${githubEvent.id}.json`), JSON.stringify({
      body: `Reply body\n\n<!-- firstmate-feedback:${githubEvent.id} -->`, login: "lanej",
    }));
    await assert.rejects(() => releaseAndImport(store, stagedId, async () => { throw new Error("Paseo import interrupted"); }), /interrupted/);
    assert.equal(store.get(stagedId).control, "paused");
    assert.equal(store.get(stagedId).migration!.ownership, "released");
    assert.equal(await readFile(join(state, "paseo-handoff", "legacy-task.generation1.meta"), "utf8"), originalMeta);
    let imports = 0;
    const ensureSession = async () => {
      if (!store.get(stagedId).worker) {
        imports++;
        store.bind(stagedId, "imported-worker", "original-workspace", checkout);
        throw new Error("Import accepted but response lost");
      }
      return { agentId: "imported-worker", workspaceId: "original-workspace", cwd: checkout, sessionId };
    };
    await assert.rejects(() => releaseAndImport(store, stagedId, ensureSession), /response lost/);
    assert.equal(store.get(stagedId).control, "paused");
    const resumed = await releaseAndImport(store, stagedId, ensureSession);
    assert.equal(imports, 1);
    assert.equal(resumed.control, "running");
    assert.equal(resumed.status, "active");
    assert.equal(resumed.worker!.cwd, checkout);
    assert.equal(resumed.migration!.ownership, "tasks");
    assert.ok(store.events(stagedId).some(event => event.id === githubEvent.id));
    assert.ok(store.events(stagedId).some(event => event.body === "Queued user correction"));
    assert.equal(store.read<{ state: string }>("replies", githubEvent.id)!.state, "unknown");
    assert.equal(await readFile(sessionFile, "utf8"), history);
    assert.equal(await readFile(join(checkout, "wip.txt"), "utf8"), "Uncommitted work must survive");
    assert.equal((await releaseAndImport(store, stagedId, async () => { throw new Error("Duplicate import"); })).worker!.agentId, "imported-worker");
  } finally { store.close(); await rm(directory, { recursive: true, force: true }); }
});
