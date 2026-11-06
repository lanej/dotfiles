import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { randomUUID } from "node:crypto";
import type { PaseoApi } from "@getpaseo/client";
import type { AgentToolContext, AgentToolDefinition } from "@getpaseo/plugin/server";
import { WorkspaceCreateRequestSchema, FetchAgentsRequestMessageSchema } from "@getpaseo/protocol/messages";
import { Store } from "../server/store";
import { Feedback, type GitHubPort, type Observation } from "../server/github";
import { TaskService, taskWorkspaceId, type Router } from "../server/service";
import { managerTools, workerTools } from "../server/tools";
import { createInput, brief, type Brief } from "../shared/contracts";
import { completedPiTurn } from "../server/pi-session";
import type { Worktrees } from "../server/treehouse";
import type { PullRequest } from "../server/pr-watch";

const specified: Brief = { title: "Investigate latency", outcome: "Explain the latency regression",
  successCriteria: ["Identify the changed component with measurements"], constraints: ["Do not deploy"],
  kind: "investigation", repository: "/repo", baseRef: null };
class FakeGitHub implements GitHubPort {
  observation: Observation = { head: "revision-a", state: { head: "revision-a" }, events: [] };
  rows: { id: number; body: string; html_url: string; user: { login: string } }[] = [];
  uncertain = false;
  submitted = 0;
  async observe() { return this.observation; }
  async login() { return "lanej"; }
  async comments() { return this.rows; }
  async submit(_url: string, _inline: boolean, _id: number | null, body: string) {
    this.submitted++;
    const result = { id: 42, body, html_url: "https://github.com/o/r/pull/1#discussion_r42", user: { login: "lanej" } };
    this.rows.push(result);
    if (this.uncertain) throw new Error("Response lost after GitHub accepted the reply");
    return result;
  }
}
class FakePaseo {
  agentsById = new Map<string, any>();
  workspacesById = new Map<string, any>();
  connectedHosts: any[] = [];
  loseSend = false;
  historyVisible = true;
  creates = 0;
  sources: any[] = [];
  readonly agents = {
    create: async (input: any) => this.createAgent(input, randomUUID(), input.cwd),
    ref: (id: string) => this.agentsById.get(id),
    list: async (input: any) => {
      FetchAgentsRequestMessageSchema.parse({ ...input, type: "fetch_agents_request", requestId: randomUUID() });
      const offset = Number(input.page.cursor ?? 0);
      const values = [...this.agentsById.values()];
      const next = offset + input.page.limit;
      return { entries: values.slice(offset, next).map(value => ({ agent: value.current() })),
        pageInfo: { nextCursor: next < values.length ? String(next) : null, prevCursor: null, hasMore: next < values.length } };
    },
  };
  readonly workspaces = {
    create: async (input: any) => {
      WorkspaceCreateRequestSchema.parse({ ...input, type: "workspace.create.request", requestId: randomUUID() });
      const previous = this.workspacesById.get(input.workspaceId);
      if (previous) return previous;
      this.sources.push(input.source);
      const id = input.workspaceId ?? randomUUID();
      const cwd = input.source.kind === "worktree" ? `/isolated/${input.source.worktreeSlug}` : input.source.path;
      const workspace = { id, directory: cwd, agents: { create: async (request: any) => this.createAgent(request, id, cwd) } };
      this.workspacesById.set(id, workspace);
      return workspace;
    },
  };
  readonly hosts = { list: async () => ({ self: { serverId: "mac" }, hosts: this.connectedHosts }) };
  async dispose() {}
  createAgent(input: any, workspaceId: string, cwd: string) {
    const id = input.agentId ?? randomUUID();
    const existing = this.agentsById.get(id);
    if (existing) return existing;
    this.creates++;
    const record = { id, provider: "pi", title: input.title, cwd, workspaceId, status: "idle", archivedAt: null, activeTurn: null,
      labels: input.labels ?? {} };
    const handle: any = {
      ...record, activeTurn: null, lastError: null, pendingPermissions: [], input,
      current: () => ({ ...record, status: handle.status, activeTurn: handle.activeTurn }),
      refresh: async () => ({ agent: handle.current() }),
      reloads: 0,
      reload: async () => { handle.reloads++; handle.status = "idle"; handle.lastError = null; return { agent: handle.current() }; },
      send: async (body: string) => {
        handle.messages.push(body); handle.activeTurn = { id: randomUUID() }; handle.status = "running";
        if (this.loseSend) throw new Error("Paseo acknowledgment lost");
      },
      messages: [] as string[],
      timeline: { refetch: async () => ({ entries: this.historyVisible ? handle.messages : [] }) },
    };
    this.agentsById.set(id, handle);
    return handle;
  }
  finish(id: string) { const handle = this.agentsById.get(id); handle.activeTurn = null; handle.status = "idle"; }
  closeManager() {
    for (const [id, value] of this.agentsById) if (value.input.parent) this.agentsById.delete(id);
  }
}
function fixture() {
  const directory = mkdtempSync(join(tmpdir(), "tasks-test-"));
  const file = join(directory, "tasks.sqlite");
  const store = new Store(file, "mac");
  const github = new FakeGitHub();
  const paseo = new FakePaseo();
  const router: Router = { call: async () => { throw new Error("Remote host unavailable"); } };
  const feedback = new Feedback(store, github, "lanej", { checks: 0, review: 0 });
  let acquisitions = 0;
  const leases = new Map<string, any>();
  const worktrees: Worktrees = {
    prepare: async (primary, holder, branch, baseRef) => ({ primary, root: `${primary}/.worktrees`, holder, branch, baseRef,
      baseCommit: "a".repeat(40), treehouseBase: branch.replace(/^task\//, "task-base/"), attempted: false }),
    acquire: async (reserved, attempting) => {
      if (!leases.has(reserved.holder)) {
        attempting(); acquisitions++;
        leases.set(reserved.holder, { path: `/isolated/${reserved.branch}`, lease_id: randomUUID(), lease_holder: reserved.holder,
          leased_at: "2026-11-06T00:00:00Z", base_branch: reserved.baseRef, primary: reserved.primary,
          root: reserved.root, branch: reserved.branch });
      }
      return leases.get(reserved.holder);
    },
  };
  const service = new TaskService(store, paseo as unknown as PaseoApi, router, feedback, "Mac", undefined, worktrees);
  return { directory, file, store, github, paseo, router, feedback, service, worktrees, leases, acquisitions: () => acquisitions,
    cleanup: () => { store.close(); rmSync(directory, { recursive: true, force: true }); } };
}
const managerContext = { agent: { id: "manager" } } as AgentToolContext;
async function tool(tools: AgentToolDefinition[], name: string, input: unknown, context = managerContext) {
  const selected = tools.find(value => value.name === name)!;
  assert.ok(selected, `Tool ${name} is available`);
  return selected.execute(selected.input.parse(input), context);
}
async function create(f: ReturnType<typeof fixture>, extra: Partial<Brief> = {}) {
  const input = createInput.parse({ serverId: "mac", brief: { ...specified, ...extra }, requestId: randomUUID() });
  await tool(managerTools(f.service), "task_create", input);
  return f.store.get(input.requestId);
}

test("typed task creation retains drafts, isolates coding work, and starts one directly accessible independent conversation", async () => {
  const f = fixture();
  try {
    const draft = await create(f, { outcome: "", successCriteria: [] });
    assert.equal(draft.status, "draft");
    assert.equal(draft.worker, null);
    assert.equal(f.paseo.creates, 0);
    const codingDraft = await create(f, { kind: "coding", baseRef: null });
    assert.equal(codingDraft.status, "draft");
    assert.equal(codingDraft.worker, null);
    assert.equal(f.paseo.sources.length, 0, "Fresh coding work still requires an explicit base before checkout creation");
    const input = createInput.parse({ serverId: "mac", brief: { ...specified, kind: "coding", baseRef: "origin/main" }, requestId: randomUUID() });
    await tool(managerTools(f.service), "task_create", input);
    await tool(managerTools(f.service), "task_create", input);
    await assert.rejects(() => f.service.create({ ...input, brief: { ...input.brief, outcome: "Another outcome" } }), /different brief/);
    const coding = f.store.get(input.requestId);
    assert.equal(f.paseo.creates, 1);
    assert.ok(coding.worker?.cwd.startsWith("/isolated/"));
    assert.equal(f.paseo.sources[0].kind, "directory");
    assert.equal(f.paseo.sources[0].path, coding.treehouseLease!.path);
    assert.equal(coding.treehouseLease!.base_branch, "origin/main");
    assert.equal(coding.treehouseLease!.branch, `task/${coding.taskId}`);
    assert.equal(coding.treehouseLease!.lease_holder, `paseo-task:mac:${coding.taskId}`);
    assert.equal(f.acquisitions(), 1);
    const handle = f.paseo.agentsById.get(coding.worker!.agentId);
    assert.equal(handle.input.config.provider, "pi/bedrock-sonnet-router/us.anthropic.claude-sonnet-5-5");
    assert.equal(handle.input.config.thinkingOptionId, "medium");
    f.paseo.closeManager();
    await f.service.tick();
    assert.equal(handle.messages.length, 1, "worker keeps running after manager closes");
    assert.match(handle.messages[0], /Desired outcome/);
    assert.ok(f.paseo.agents.ref(coding.worker!.agentId), "recorded conversation can be entered directly");
  } finally { f.cleanup(); }
});

test("lost Treehouse allocation replies recover the owned lease before workspace creation without allocating twice", async () => {
  const f = fixture();
  try {
    const acquire = f.worktrees.acquire;
    let loseResponse = true;
    f.worktrees.acquire = async (reserved, attempting) => {
      const leased = await acquire(reserved, attempting);
      if (loseResponse) { loseResponse = false; throw new Error("Lease reply lost"); }
      return leased;
    };
    const value = await create(f, { kind: "coding", baseRef: "origin/main" });
    assert.equal(value.worker, null);
    assert.equal(value.treehouseReservation!.attempted, true);
    assert.equal(f.paseo.sources.length, 0);
    assert.match(value.error!, /Lease reply lost/);
    const recovered = new TaskService(f.store, f.paseo as unknown as PaseoApi, f.router, f.feedback, "Mac", undefined, f.worktrees);
    await recovered.start(value.taskId);
    assert.equal(f.acquisitions(), 1);
    assert.equal(f.store.get(value.taskId).worker!.cwd, [...f.leases.values()][0].path);
    assert.equal(f.store.get(value.taskId).treehouseLease!.lease_id, [...f.leases.values()][0].lease_id);
    assert.equal(f.paseo.sources[0].kind, "directory");
    await recovered.bulk({ tasks: [value], action: "archive" });
    assert.equal(f.store.get(value.taskId).treehouseLease!.lease_id, [...f.leases.values()][0].lease_id,
      "A retained conversation keeps its lease; archive does not return the checkout");
  } finally { f.cleanup(); }
});

test("execution context cannot change during checkout preparation, and a concurrent pause prevents acquisition", async () => {
  const f = fixture();
  try {
    const prepare = f.worktrees.prepare;
    let release!: () => void;
    const barrier = new Promise<void>(resolve => { release = resolve; });
    f.worktrees.prepare = async (...args) => { await barrier; return prepare(...args); };
    const id = randomUUID();
    const creation = f.service.create(createInput.parse({ serverId: "mac", requestId: id,
      brief: { ...specified, kind: "coding", baseRef: "origin/main" } }));
    const proposed = f.service.propose(id, { ...specified, kind: "coding", repository: "/another", baseRef: "origin/main" });
    await assert.rejects(() => f.service.accept({ serverId: "mac", taskId: id,
      proposalId: proposed.proposals[0].id, revision: proposed.revision }), /execution context/);
    await f.service.bulk({ tasks: [{ serverId: "mac", taskId: id }], action: "pause" });
    release();
    await creation;
    assert.equal(f.acquisitions(), 0);
    assert.equal(f.paseo.creates, 0);
    assert.equal(f.store.get(id).repository, specified.repository);
    await f.service.bulk({ tasks: [{ serverId: "mac", taskId: id }], action: "resume" });
    assert.equal(f.store.get(id).worker!.cwd, [...f.leases.values()][0].path);
    assert.equal(f.acquisitions(), 1);
  } finally { f.cleanup(); }
});

test("passive GitHub observations cannot become worker input after a crash or a legacy queued receipt", async () => {
  const f = fixture();
  try {
    const value = await create(f);
    for (const entry of f.store.events(value.taskId)) f.feedback.acknowledge(entry, "Done");
    f.store.workerUpdate(value.taskId, value.worker!.agentId, { status: "decision" });
    f.service.link(value.taskId, "https://github.com/o/r/pull/1");
    const save = f.store.saveEvent.bind(f.store);
    f.store.saveEvent = () => { throw new Error("Interrupted passive receipt"); };
    await assert.rejects(() => f.feedback.poll(f.store.get(value.taskId)), /Interrupted/);
    f.store.saveEvent = save;
    assert.equal(f.store.events(value.taskId).filter(entry => entry.payload.type === "state").length, 0,
      "Passive insertion and handled receipt roll back together");
    const legacy = f.store.addEvent(value.taskId, "github", "Legacy passive observation", { payload: { type: "state" } });
    await f.service.deliver(f.store.get(value.taskId));
    assert.equal(f.paseo.agents.ref(value.worker!.agentId).messages.length, 0);
    assert.equal(f.store.events(value.taskId).find(entry => entry.id === legacy.id)!.delivery, "handled");
  } finally { f.cleanup(); }
});

test("PR polling repairs new failures and conflicts in the retained worker, then waits for review through pause and restart", async () => {
  const f = fixture();
  try {
    const value = await create(f);
    const url = "https://github.com/o/r/pull/1";
    f.service.link(value.taskId, url);
    for (const entry of f.store.events(value.taskId)) f.feedback.acknowledge(entry, "Initial work done");
    f.store.workerUpdate(value.taskId, value.worker!.agentId, { status: "complete", evidence: ["Initial PR pushed"] });
    const pr: PullRequest = {
      state: "open", head: "revision-a", base: "base-a", merged: false, draft: false, mergeable: true, mergeableState: "clean",
      checks: [{ id: 11, name: "tests", app: 1, status: "in_progress", conclusion: null, completedAt: null, url }],
      statuses: [],
    };
    const observe = () => { f.github.observation = { head: pr.head, pullRequest: structuredClone(pr), state: structuredClone(pr), events: [] }; };
    observe();
    await f.feedback.poll(f.store.get(value.taskId));
    assert.equal(f.store.get(value.taskId).prWatches[0].phase, "checks");
    assert.equal(f.store.get(value.taskId).status, "complete");
    await f.service.deliver(f.store.get(value.taskId));
    assert.equal(f.paseo.agents.ref(value.worker!.agentId).messages.length, 0, "Pending CI does not spin the worker");
    pr.checks[0] = { ...pr.checks[0], status: "completed", conclusion: "failure", completedAt: "later" };
    observe();
    await f.service.bulk({ tasks: [value], action: "pause" });
    await f.feedback.poll(f.store.get(value.taskId));
    assert.equal(f.store.get(value.taskId).status, "active");
    const failed = f.store.events(value.taskId).find(entry => entry.payload.type === "repair")!;
    assert.ok(failed);
    assert.throws(() => f.store.workerUpdate(value.taskId, value.worker!.agentId,
      { status: "complete", evidence: ["Earlier work"] }), /pending assigned feedback/);
    const resumed = new Feedback(f.store, f.github, "lanej", { checks: 0, review: 0 });
    await resumed.poll(f.store.get(value.taskId));
    assert.equal(f.store.events(value.taskId).filter(entry => entry.payload.type === "repair").length, 1);
    await f.service.deliver(f.store.get(value.taskId));
    assert.equal(f.paseo.agents.ref(value.worker!.agentId).messages.length, 0);
    await f.service.bulk({ tasks: [value], action: "resume" });
    await f.service.deliver(f.store.get(value.taskId));
    const handle = f.paseo.agents.ref(value.worker!.agentId);
    assert.match(handle.messages[0], /failing checks or a merge conflict/);
    assert.equal(f.store.get(value.taskId).worker!.agentId, value.worker!.agentId);
    assert.equal(f.paseo.creates, 1);
    await assert.rejects(() => resumed.reply(f.store.get(value.taskId), failed.id, "Repairing", pr.head), /source feedback/);
    f.paseo.finish(handle.id);
    for (const entry of f.store.events(value.taskId)) f.feedback.acknowledge(entry, "Repair pushed");
    f.store.workerUpdate(value.taskId, handle.id, { status: "decision", nextAction: "Await checks and review" });
    pr.head = "revision-b"; pr.checks[0] = { ...pr.checks[0], id: 12, conclusion: "success" };
    observe();
    await resumed.poll(f.store.get(value.taskId));
    assert.equal(f.store.get(value.taskId).prWatches[0].phase, "review");
    await f.service.deliver(f.store.get(value.taskId));
    assert.equal(handle.messages.length, 1, "Passing CI waits for review without another agent turn");
    f.github.observation.events.push({ type: "inline", item: { id: 90, body: "Correct this edge case",
      html_url: `${url}#discussion_r90`, user: { login: "reviewer" }, commit_id: pr.head } });
    await resumed.poll(f.store.get(value.taskId));
    assert.equal(f.store.get(value.taskId).status, "active", "New review input reopens the waiting worker");
    await f.service.deliver(f.store.get(value.taskId));
    assert.match(handle.messages[1], /Handle review comments in this checkout/);
    f.paseo.finish(handle.id);
    for (const entry of f.store.events(value.taskId)) f.feedback.acknowledge(entry, "Review handled");
    f.store.workerUpdate(value.taskId, handle.id, { status: "decision" });
    pr.base = "base-b"; pr.mergeable = false; pr.mergeableState = "dirty"; observe();
    await resumed.poll(f.store.get(value.taskId));
    assert.equal(f.store.get(value.taskId).prWatches[0].phase, "repair");
    await f.service.deliver(f.store.get(value.taskId));
    assert.equal(handle.messages.length, 3);
    assert.equal(f.paseo.creates, 1, "Checks, conflicts and review all use one primary Pi conversation");
  } finally { f.cleanup(); }
});

test("polling cadence survives restart and slows once reported checks pass", async () => {
  const f = fixture();
  try {
    let now = "2026-11-06T00:00:00Z";
    const store = new Store(f.file, "mac", () => now);
    const value = await create(f);
    f.service.link(value.taskId, "https://github.com/o/r/pull/1");
    let observations = 0;
    const original = f.github.observe.bind(f.github);
    f.github.observe = async () => { observations++; return original(); };
    f.github.observation.pullRequest = {
      state: "open", head: "revision-a", base: "base-a", merged: false, draft: false, mergeable: true, mergeableState: "clean",
      checks: [{ id: 1, name: "tests", app: 1, status: "completed", conclusion: "success", completedAt: now, url: null }],
      statuses: [],
    };
    await new Feedback(store, f.github, "lanej").poll(store.get(value.taskId));
    assert.equal(observations, 1);
    now = "2026-11-06T00:01:59Z";
    await new Feedback(store, f.github, "lanej").poll(store.get(value.taskId));
    assert.equal(observations, 1);
    now = "2026-11-06T00:02:00Z";
    await new Feedback(store, f.github, "lanej").poll(store.get(value.taskId));
    assert.equal(observations, 2);
    store.close();
  } finally { f.cleanup(); }
});

test("a closed or already repaired PR supersedes queued repairs without waking the worker or discarding source feedback", async () => {
  for (const close of [true, false]) {
    const f = fixture();
    try {
      const value = await create(f);
      const url = "https://github.com/o/r/pull/1";
      f.service.link(value.taskId, url);
      for (const entry of f.store.events(value.taskId)) f.feedback.acknowledge(entry, "Initial work done");
      f.store.workerUpdate(value.taskId, value.worker!.agentId, { status: "decision" });
      await f.service.tick();
      f.github.observation.pullRequest = {
        state: "open", head: "revision-a", base: "base-a", merged: false, draft: false, mergeable: false, mergeableState: "dirty",
        checks: [{ id: 1, name: "tests", app: 1, status: "completed", conclusion: "success", completedAt: "now", url }], statuses: [],
      };
      await f.feedback.poll(f.store.get(value.taskId));
      const repair = f.store.events(value.taskId).find(entry => entry.payload.type === "repair")!;
      f.github.observation.pullRequest.mergeable = null;
      await f.feedback.poll(f.store.get(value.taskId));
      await f.service.deliver(f.store.get(value.taskId));
      assert.equal(f.paseo.agents.ref(value.worker!.agentId).messages.length, 0, "Unknown mergeability defers the same-revision repair");
      assert.equal(f.store.events(value.taskId).find(entry => entry.id === repair.id)!.delivery, "queued");
      f.github.observation.pullRequest.mergeable = false;
      await f.feedback.poll(f.store.get(value.taskId));
      assert.equal(f.store.events(value.taskId).find(entry => entry.id === repair.id)!.delivery, "queued",
        "A confirmed conflict retains its original repair after an unknown observation");
      f.github.observation.pullRequest.checks[0] = { ...f.github.observation.pullRequest.checks[0], id: 2, conclusion: "failure" };
      await f.feedback.poll(f.store.get(value.taskId));
      assert.equal(f.store.events(value.taskId).find(entry => entry.id === repair.id)!.delivery, "handled");
      const replacement = f.store.events(value.taskId).find(entry => entry.payload.type === "repair" && entry.delivery === "queued")!;
      assert.equal(replacement.payload.previousStatus, "decision", "Replacement repairs retain their original waiting baseline");
      f.github.observation.pullRequest.state = close ? "closed" : "open";
      f.github.observation.pullRequest.mergeable = true;
      f.github.observation.pullRequest.checks[0].conclusion = "success";
      await f.feedback.poll(f.store.get(value.taskId));
      await f.service.deliver(f.store.get(value.taskId));
      assert.equal(f.paseo.agents.ref(value.worker!.agentId).messages.length, 0);
      const skipped = f.store.events(value.taskId).find(entry => entry.id === replacement.id)!;
      assert.equal(skipped.delivery, "handled");
      assert.ok(skipped.payload.superseded);
      assert.equal(f.store.get(value.taskId).status, "decision", "Superseded automatic work restores its prior waiting state");
      f.github.observation.events = [{ type: "comment", item: { id: 7, body: "Please explain the outcome", user: { login: "reviewer" } } }];
      await f.feedback.poll(f.store.get(value.taskId));
      await f.service.deliver(f.store.get(value.taskId));
      assert.equal(f.paseo.agents.ref(value.worker!.agentId).messages.length, 1, "Source discussion feedback is retained");
    } finally { f.cleanup(); }
  }
});

test("GitHub rate limits preserve retry time through restart and recover without erasing other failures", async () => {
  const f = fixture();
  try {
    let now = "2026-11-06T00:00:00Z";
    const store = new Store(f.file, "mac", () => now);
    const value = await create(f);
    f.service.link(value.taskId, "https://github.com/o/r/pull/1");
    let attempts = 0;
    f.github.observe = async () => {
      if (++attempts === 1) throw Object.assign(new Error("API rate limit exceeded"), { status: 403,
        response: { headers: { "x-ratelimit-remaining": "0", "x-ratelimit-reset": String(Date.parse("2026-11-06T00:10:00Z") / 1000) } } });
      return f.github.observation;
    };
    const failure = await new Feedback(store, f.github, "lanej").poll(store.get(value.taskId)).catch(error => error.message);
    store.change(value.taskId, task => { task.error = failure; });
    now = "2026-11-06T00:09:59Z";
    await new Feedback(store, f.github, "lanej").poll(store.get(value.taskId));
    assert.equal(attempts, 1);
    now = "2026-11-06T00:10:01Z";
    await new Feedback(store, f.github, "lanej").poll(store.get(value.taskId));
    assert.equal(attempts, 2);
    assert.equal(store.get(value.taskId).error, null);
    store.change(value.taskId, task => { task.error = "Provider execution failed"; });
    now = "2026-11-06T00:12:01Z";
    await new Feedback(store, f.github, "lanej").poll(store.get(value.taskId));
    assert.equal(store.get(value.taskId).error, "Provider execution failed");
    store.close();
  } finally { f.cleanup(); }
});

test("plugin recovery restores scoped tools once at idle without interrupting turns, questions, or unassigned conversations", async () => {
  const f = fixture();
  try {
    const value = await create(f);
    const worker = f.paseo.agentsById.get(value.worker!.agentId);
    const managerAddress = await f.service.newManager("/repo");
    const manager = f.paseo.agentsById.get(managerAddress.agentId);
    const unrelated = f.paseo.createAgent({ title: "Unassigned Pi" }, "workspace", "/repo");
    worker.activeTurn = { id: "retained-turn" }; worker.status = "running";
    manager.pendingPermissions = [{ id: "native-question" }];
    const event = f.store.addEvent(value.taskId, "feedback", "Retained feedback");
    f.store.change(value.taskId, current => { current.control = "paused"; });
    await f.service.tick();
    assert.equal(worker.reloads, 0);
    assert.equal(manager.reloads, 0);
    assert.equal(unrelated.reloads, 0);
    assert.equal(f.store.events(value.taskId).find(entry => entry.id === event.id)!.delivery, "queued");
    f.paseo.finish(worker.id);
    manager.pendingPermissions = [];
    await f.service.tick();
    assert.equal(worker.reloads, 1);
    assert.equal(manager.reloads, 1);
    assert.equal(unrelated.reloads, 0);
    assert.equal(f.store.get(value.taskId).worker?.agentId, worker.id);
    assert.equal(f.store.get(value.taskId).control, "paused");
    await f.service.tick();
    assert.equal(worker.reloads, 1);
    assert.equal(manager.reloads, 1);
    const replacement = new TaskService(f.store, f.paseo as unknown as PaseoApi, f.router, f.feedback, "Mac");
    await replacement.tick();
    assert.equal(worker.reloads, 2, "A new plugin generation restores the retained worker");
    assert.equal(manager.reloads, 2, "A new plugin generation restores the retained manager");
    assert.equal(unrelated.reloads, 0);
    assert.equal(f.store.events(value.taskId).find(entry => entry.id === event.id)!.delivery, "queued");
  } finally { f.cleanup(); }
});

test("failed tool recovery remains retryable and cannot dispatch retained feedback", async () => {
  const f = fixture();
  try {
    const value = await create(f);
    const worker = f.paseo.agentsById.get(value.worker!.agentId);
    const original = worker.reload;
    worker.reload = async () => {
      f.service.sessionOpened(worker.id, "worker");
      throw new Error("Provider failed after tool injection");
    };
    await f.service.tick();
    assert.equal(worker.messages.length, 0);
    assert.match(f.store.get(value.taskId).error!, /Provider failed/);
    assert.equal(f.store.events(value.taskId)[0].delivery, "queued");
    worker.reload = original;
    await f.service.tick();
    assert.equal(worker.reloads, 1);
    assert.equal(worker.messages.length, 1);
    assert.equal(f.store.events(value.taskId)[0].delivery, "accepted");
  } finally { f.cleanup(); }
});

test("a turn or question clearing during refresh cannot dispatch before tool recovery", async () => {
  for (const permission of [false, true]) {
    const f = fixture();
    try {
      const value = await create(f);
      const worker = f.paseo.agentsById.get(value.worker!.agentId);
      const refresh = worker.refresh;
      let calls = 0;
      worker.refresh = async () => {
        const observed = await refresh();
        if (calls++ === 0) {
          worker.activeTurn = permission ? null : { id: "ending-turn" };
          worker.status = permission ? "idle" : "running";
          worker.pendingPermissions = permission ? [{ id: "answering-question" }] : [];
        } else {
          worker.activeTurn = null; worker.status = "idle"; worker.pendingPermissions = [];
        }
        return observed;
      };
      await f.service.deliver(value);
      assert.equal(worker.messages.length, 0);
      assert.equal(worker.reloads, 0);
      assert.equal(calls, 1, "Deferred repair cannot proceed to a dispatch refresh");
      await f.service.deliver(value);
      assert.equal(worker.reloads, 1);
      assert.equal(worker.messages.length, 1);
    } finally { f.cleanup(); }
  }
});

test("adoption preserves only the selected existing conversation and checkout; scoped worker tools reject foreign identities and brief mutation", async () => {
  const f = fixture();
  try {
    const selected = f.paseo.createAgent({ title: "Existing investigation" }, "existing-workspace", "/existing/wip");
    const other = f.paseo.createAgent({ title: "Other conversation" }, "another-workspace", "/other");
    const discovered = await f.service.discover("mac");
    assert.equal(discovered.length, 2);
    const input = createInput.parse({ serverId: "mac", brief: specified, requestId: randomUUID(), start: false });
    await tool(managerTools(f.service), "task_adopt", { ...input, agentId: selected.id });
    const adopted = f.store.get(input.requestId);
    assert.equal(adopted.worker!.cwd, "/existing/wip");
    assert.equal(f.store.forAgent(other.id), undefined);
    const scoped = workerTools(f.service, adopted.taskId, selected.id);
    await assert.rejects(async () => tool(scoped, "task_update", { progress: "Foreign edit" }, { agent: { id: other.id } } as AgentToolContext), /denied/);
    await assert.rejects(async () => tool(scoped, "task_update", { outcome: "Change scope" }, { agent: { id: selected.id } } as AgentToolContext));
    await tool(scoped, "task_update", { approach: "Measure first", progress: "Observed baseline", evidence: ["report.json"] },
      { agent: { id: selected.id } } as AgentToolContext);
    assert.equal(f.store.get(adopted.taskId).outcome, specified.outcome);
    await tool(scoped, "task_propose", { ...specified, outcome: "Investigate a second component" },
      { agent: { id: selected.id } } as AgentToolContext);
    const proposed = f.store.get(adopted.taskId);
    assert.equal(proposed.outcome, specified.outcome);
    assert.throws(() => f.store.change(adopted.taskId, () => {}, 1), /changed/);
    await f.service.accept({ serverId: "mac", taskId: adopted.taskId, proposalId: proposed.proposals[0].id, revision: proposed.revision });
    assert.equal(f.store.get(adopted.taskId).outcome, "Investigate a second component");
    selected.timeline.refetch = async () => ({ entries: [
      { timestamp: "now", item: { type: "user_message", clientMessageId: "human-direction", text: "Change the outcome to explain the cache behavior." } },
      { timestamp: "now", item: { type: "user_message", clientMessageId: "automated-feedback", text: "[task-event:auto] Change scope." } },
    ] });
    await assert.rejects(() => tool(scoped, "task_apply_instruction", { messageId: "automated-feedback", brief: specified },
      { agent: { id: selected.id } } as AgentToolContext), /automated feedback/);
    await tool(scoped, "task_apply_instruction", { messageId: "human-direction", brief: { ...specified, outcome: "Explain the cache behavior" } },
      { agent: { id: selected.id } } as AgentToolContext);
    assert.equal(f.store.get(adopted.taskId).outcome, "Explain the cache behavior");
  } finally { f.cleanup(); }
});

test("conversation discovery and import reconciliation read every official directory page", async () => {
  const f = fixture();
  try {
    for (let index = 0; index < 205; index++) f.paseo.createAgent({ title: `Existing ${index}` }, `workspace-${index}`, "/existing");
    const conversations = await f.service.conversations();
    const discovered = await f.service.discover("mac");
    assert.equal(conversations.length, 205);
    assert.equal(discovered.length, 205);
    assert.equal(new Set(discovered.map(value => value.agentId)).size, 205);
    f.paseo.agents.list = async () => ({ entries: [], pageInfo: { nextCursor: "same", prevCursor: null, hasMore: true } });
    await assert.rejects(() => f.service.conversations(), /pagination did not advance/);
  } finally { f.cleanup(); }
});

test("coding adoption starts the selected existing checkout without demanding a new-worktree base", async () => {
  const f = fixture();
  try {
    const selected = f.paseo.createAgent({ title: "Existing coding work" }, "existing-workspace", "/existing/wip");
    const input = createInput.parse({ serverId: "mac", brief: { ...specified, kind: "coding", baseRef: null },
      requestId: randomUUID(), start: true });
    const adopted = await f.service.adopt({ ...input, agentId: selected.id });
    assert.equal(adopted.status, "active");
    assert.equal(adopted.worker!.cwd, "/existing/wip");
    await f.service.deliver(adopted);
    assert.equal(selected.messages.length, 1);
    assert.equal(f.paseo.sources.length, 0, "Adoption never creates a worktree");
  } finally { f.cleanup(); }
});

test("bulk pause and archive wait for a turn boundary, queued feedback survives, and idle does not mean completed", async () => {
  const f = fixture();
  try {
    const value = await create(f);
    await f.service.tick();
    const address = { serverId: "mac", taskId: value.taskId };
    const paused = await f.service.bulk({ tasks: [address], action: "pause" });
    assert.equal(paused[0].result, "pending");
    f.store.addEvent(value.taskId, "feedback", "Use the new measurement");
    f.paseo.finish(value.worker!.agentId);
    await f.service.turnEnded(value.worker!.agentId, { kind: "completed" });
    assert.equal(f.store.get(value.taskId).control, "paused");
    assert.equal(f.store.get(value.taskId).status, "active");
    await f.service.tick();
    assert.equal(f.paseo.agents.ref(value.worker!.agentId).messages.length, 1);
    await f.service.bulk({ tasks: [address, { serverId: "dev2", taskId: randomUUID() }], action: "resume" });
    await f.service.tick();
    assert.match(f.paseo.agents.ref(value.worker!.agentId).messages[1], /new measurement/);
    const archived = await f.service.bulk({ tasks: [address], action: "archive" });
    assert.equal(archived[0].result, "pending");
    f.paseo.finish(value.worker!.agentId);
    await f.service.turnEnded(value.worker!.agentId, { kind: "completed" });
    assert.equal(f.store.get(value.taskId).control, "archived");
    const draft = await create(f, { outcome: "", successCriteria: [] });
    assert.equal((await f.service.bulk({ tasks: [{ serverId: "mac", taskId: draft.taskId }], action: "archive" }))[0].result, "applied");
    assert.equal(f.store.get(draft.taskId).control, "archived");
  } finally { f.cleanup(); }
});

test("host disconnect retains last observation, verifies destination identity, and never routes an action to the local worker", async () => {
  const f = fixture();
  try {
    const value = await create(f);
    f.paseo.connectedHosts = [{ serverId: "dev", registrationId: "dev-registration", label: "dev", status: "online" }];
    f.router.call = async () => [{ serverId: "dev", label: "dev", connection: "online", observedAt: "2026-11-05T00:00:00Z",
      error: null, tasks: [{ ...value, serverId: "dev" }] }];
    await f.service.list();
    f.router.call = async () => { throw new Error("host_offline"); };
    const offline = (await f.service.list())[1];
    assert.equal(offline.connection, "unavailable");
    assert.equal(offline.tasks[0].serverId, "dev");
    assert.equal(offline.observedAt, "2026-11-05T00:00:00Z");
    const result = await f.service.bulk({ tasks: [{ serverId: "dev", taskId: value.taskId }], action: "pause" });
    assert.equal(result[0].result, "unknown");
    assert.equal(f.store.get(value.taskId).control, "running");
    f.router.call = async () => [{ serverId: "wrong-host", tasks: [] }];
    assert.match((await f.service.list())[1].error!, /identity/);
    assert.throws(() => new Store(f.file, "wrong-host"), /another host/);
  } finally { f.cleanup(); }
});

test("uncertain Paseo delivery is durable and reconciles from the source conversation without duplicate prompts", async () => {
  const f = fixture();
  try {
    const value = await create(f);
    f.paseo.loseSend = true;
    await f.service.tick();
    assert.equal(f.store.events(value.taskId)[0].delivery, "unknown");
    f.paseo.finish(value.worker!.agentId);
    f.paseo.historyVisible = false;
    await f.service.tick();
    assert.equal(f.paseo.agents.ref(value.worker!.agentId).messages.length, 1);
    f.paseo.historyVisible = true;
    await f.service.tick();
    assert.equal(f.store.events(value.taskId)[0].delivery, "accepted");
    assert.equal(f.paseo.agents.ref(value.worker!.agentId).messages.length, 1);
    f.store.saveEvent({ ...f.store.events(value.taskId)[0], delivery: "sending" });
    const persisted = new Store(f.file, "mac");
    assert.equal(persisted.events(value.taskId)[0].delivery, "unknown");
    persisted.close();
  } finally { f.cleanup(); }
});

test("pause during refresh leaves feedback queued; pause during an already reserved send waits for its turn boundary", async () => {
  const f = fixture();
  try {
    const value = await create(f);
    const handle = f.paseo.agents.ref(value.worker!.agentId);
    let release!: () => void;
    const barrier = new Promise<void>(resolve => { release = resolve; });
    let reads = 0;
    handle.refresh = async () => {
      if (++reads === 1) await barrier;
      return { agent: handle.current() };
    };
    const delivery = f.service.deliver(value);
    const result = await f.service.bulk({ tasks: [{ serverId: "mac", taskId: value.taskId }], action: "pause" });
    assert.equal(result[0].result, "applied");
    release(); await delivery;
    assert.equal(handle.messages.length, 0);
    assert.equal(f.store.events(value.taskId)[0].delivery, "queued");
    await f.service.bulk({ tasks: [{ serverId: "mac", taskId: value.taskId }], action: "resume" });
    const originalSend = handle.send;
    let sendReached!: () => void;
    const reached = new Promise<void>(resolve => { sendReached = resolve; });
    let finishSend!: () => void;
    const waiting = new Promise<void>(resolve => { finishSend = resolve; });
    handle.send = async (body: string) => { sendReached(); await waiting; return originalSend(body); };
    const reserved = f.service.deliver(f.store.get(value.taskId));
    await reached;
    assert.equal((await f.service.bulk({ tasks: [{ serverId: "mac", taskId: value.taskId }], action: "pause" }))[0].result, "pending");
    finishSend(); await reserved;
    assert.equal(handle.messages.length, 1);
    f.paseo.finish(handle.id);
    await f.service.turnEnded(handle.id, { kind: "completed" });
    assert.equal(f.store.get(value.taskId).control, "paused");
  } finally { f.cleanup(); }
});

test("worker creation reconciles the same workspace and conversation after a lost creation response and restart", async () => {
  const f = fixture();
  try {
    const original = f.paseo.workspaces.create;
    let loseResponse = true;
    f.paseo.workspaces.create = async input => {
      const created = await original(input);
      if (loseResponse) throw new Error("Workspace acknowledgment lost");
      return created;
    };
    const value = await create(f, { kind: "coding", baseRef: "origin/main" });
    assert.equal(value.launch, "unknown");
    assert.equal(value.worker, null);
    loseResponse = false;
    const resumed = new TaskService(f.store, f.paseo as unknown as PaseoApi, f.router, f.feedback, "Mac", undefined, f.worktrees);
    await resumed.tick();
    assert.equal(f.store.get(value.taskId).worker!.workspaceId, taskWorkspaceId(value.taskId));
    assert.equal(f.paseo.sources.length, 1);
    assert.equal(f.paseo.creates, 1);
    assert.equal(f.paseo.agents.ref(value.taskId).messages.length, 1);
  } finally { f.cleanup(); }
});

test("resume reopens the same closed or failed worker and respects native archive state", async () => {
  const f = fixture();
  try {
    const value = await create(f);
    await f.service.tick();
    const handle = f.paseo.agents.ref(value.worker!.agentId);
    f.paseo.finish(handle.id);
    handle.status = "closed";
    const result = await f.service.bulk({ tasks: [{ serverId: "mac", taskId: value.taskId }], action: "resume" });
    assert.equal(result[0].result, "applied");
    await f.service.tick();
    assert.equal(handle.messages.length, 2);
    assert.equal(f.paseo.creates, 1);
    f.paseo.finish(handle.id);
    handle.status = "error"; handle.lastError = "Provider disconnected";
    await f.service.bulk({ tasks: [{ serverId: "mac", taskId: value.taskId }], action: "resume" });
    assert.equal(handle.lastError, null);
    handle.archivedAt = "now";
    f.paseo.finish(handle.id);
    await f.service.tick();
    assert.equal(f.store.get(value.taskId).control, "archived");
  } finally { f.cleanup(); }
});

test("restart continues a completed Pi turn once, while cancellation and GitHub outages preserve their separate outcomes", async () => {
  const f = fixture();
  try {
    const value = await create(f);
    await f.service.tick();
    const handle = f.paseo.agents.ref(value.worker!.agentId);
    const file = join(f.directory, "pi-session.jsonl");
    const current = handle.current;
    const timeline = handle.timeline.refetch;
    handle.timeline.refetch = async () => ({ entries: [] });
    handle.current = () => ({ ...current(), persistence: { nativeHandle: file }, lastUserMessageAt: null });
    assert.equal(await completedPiTurn(handle), null, "An unstarted Pi session has no completion checkpoint");
    handle.timeline.refetch = timeline;
    await assert.rejects(() => completedPiTurn(handle), /ENOENT/, "Imported history with no Paseo message timestamp still requires its native file");
    handle.current = () => ({ ...current(), persistence: { nativeHandle: file }, lastUserMessageAt: "now" });
    await assert.rejects(() => completedPiTurn(handle), /ENOENT/, "Missing previously started history remains visible");
    const sessionId = randomUUID();
    const header = JSON.stringify({ type: "session", version: 3, id: sessionId, cwd: handle.cwd });
    writeFileSync(file, `${header}\n${JSON.stringify({ type: "message", id: "completed", parentId: null,
      message: { role: "assistant", stopReason: "stop", content: [{ type: "text", text: "Measured one component" }] } })}\n`);
    handle.current = () => ({ ...current(), persistence: { nativeHandle: file } });
    f.paseo.finish(handle.id);
    const resumed = new TaskService(f.store, f.paseo as unknown as PaseoApi, f.router, f.feedback, "Mac");
    await resumed.tick();
    assert.equal(handle.messages.length, 2);
    f.paseo.finish(handle.id);
    await resumed.tick();
    assert.equal(handle.messages.length, 2, "one observed completed turn creates one continuation");
    writeFileSync(file, `${header}\n${JSON.stringify({ type: "message", id: "canceled", parentId: null,
      message: { role: "assistant", stopReason: "aborted" } })}\n`);
    await resumed.tick();
    assert.equal(handle.messages.length, 2, "an aborted turn is not automatically continued");
    f.service.link(value.taskId, "https://github.com/o/r/issues/1");
    f.github.observe = async () => { throw new Error("GitHub unavailable"); };
    f.store.addEvent(value.taskId, "feedback", "Human instruction remains deliverable");
    await resumed.tick();
    assert.equal(handle.messages.length, 3);
    assert.match(f.store.get(value.taskId).error!, /GitHub unavailable/);
  } finally { f.cleanup(); }
});

test("concurrent GitHub reply tools reserve one durable source-thread submission", async () => {
  const f = fixture();
  try {
    const value = await create(f);
    const url = "https://github.com/o/r/pull/1";
    f.service.link(value.taskId, url);
    const entry = f.store.addEvent(value.taskId, "github", "Please fix", {
      id: "c".repeat(64), source: `${url}#discussion_r12`, payload: { url, type: "inline", commentId: 12 },
    });
    let release!: () => void;
    const barrier = new Promise<void>(resolve => { release = resolve; });
    f.github.comments = async () => { await barrier; return []; };
    const calls = [f.feedback.reply(f.store.get(value.taskId), entry.id, "Fixed", "revision-a"),
      f.feedback.reply(f.store.get(value.taskId), entry.id, "Fixed", "revision-a")];
    release();
    const results = await Promise.allSettled(calls);
    assert.equal(f.github.submitted, 1);
    assert.equal(results.filter(result => result.status === "fulfilled").length, 1);
    assert.equal(f.store.read<{ state: string }>("replies", entry.id)!.state, "confirmed");
  } finally { f.cleanup(); }
});

test("worker acknowledgment before the send receipt keeps feedback handled", async () => {
  const f = fixture();
  try {
    const value = await create(f);
    const handle = f.paseo.agents.ref(value.worker!.agentId);
    const entry = f.store.events(value.taskId)[0];
    handle.send = async () => { f.feedback.acknowledge(entry, "Handled the instruction"); };
    await f.service.deliver(value);
    assert.equal(f.store.events(value.taskId)[0].delivery, "handled");
    f.store.saveEvent({ ...entry, delivery: "unknown" });
    assert.equal(f.store.events(value.taskId)[0].delivery, "handled");
  } finally { f.cleanup(); }
});
test("completed work reopens only for new assigned feedback or explicit resume, preserving control and conversation ownership", async () => {
  const f = fixture();
  try {
    const value = await create(f);
    await f.service.deliver(value);
    f.paseo.finish(value.worker!.agentId);
    const complete = () => f.store.workerUpdate(value.taskId, value.worker!.agentId,
      { status: "complete", evidence: ["Original success criteria verified"] });
    complete();
    await f.service.turnEnded(value.worker!.agentId, { kind: "completed" }, "initial-completion");
    assert.equal(f.store.events(value.taskId).filter(entry => entry.kind === "continue").length, 0);
    f.service.link(value.taskId, "https://github.com/o/r/pull/1");
    await f.feedback.poll(f.store.get(value.taskId));
    assert.equal(f.store.get(value.taskId).status, "complete", "Checks and revision observations do not reopen work");
    for (const entry of f.store.events(value.taskId)) f.feedback.acknowledge(entry, "Observed");
    f.github.observation.events = [{ type: "inline", item: {
      id: 91, body: "Please correct this within the original scope", user: { login: "reviewer" },
      html_url: "https://github.com/o/r/pull/1#discussion_r91", commit_id: "revision-a",
    } }];
    await f.feedback.poll(f.store.get(value.taskId));
    assert.equal(f.store.get(value.taskId).status, "active");
    assert.deepEqual(f.store.get(value.taskId).worker, value.worker);
    assert.deepEqual(brief.strip().parse(f.store.get(value.taskId)), brief.strip().parse(value));
    await f.service.deliver(f.store.get(value.taskId));
    assert.equal(f.paseo.agents.ref(value.worker!.agentId).messages.length, 2);
    f.paseo.finish(value.worker!.agentId);
    for (const entry of f.store.events(value.taskId)) f.feedback.acknowledge(entry, "Handled within original scope");
    complete();
    await f.feedback.poll(f.store.get(value.taskId));
    assert.equal(f.store.get(value.taskId).status, "complete", "Reobserved feedback does not resurrect completion");

    await f.service.bulk({ tasks: [value], action: "pause" });
    const input = f.store.addEvent(value.taskId, "feedback", "New manager instruction", { id: "new-manager-input" });
    assert.equal(f.store.get(value.taskId).status, "active");
    assert.equal(f.store.get(value.taskId).control, "paused");
    await f.service.deliver(f.store.get(value.taskId));
    assert.equal(f.paseo.agents.ref(value.worker!.agentId).messages.length, 2);
    assert.throws(complete, /pending assigned feedback/);
    f.feedback.acknowledge(input, "Handled during the paused turn");
    complete();
    f.store.addEvent(value.taskId, "feedback", input.body, { id: input.id });
    assert.equal(f.store.get(value.taskId).status, "complete", "Replayed durable manager input does not reopen work");
    assert.throws(() => f.store.transaction(() => {
      f.store.addEvent(value.taskId, "feedback", "Rolled back", { id: "rolled-back-input" });
      throw new Error("Insertion interrupted");
    }), /interrupted/);
    assert.equal(f.store.get(value.taskId).status, "complete");
    assert.ok(!f.store.events(value.taskId).some(entry => entry.id === "rolled-back-input"));
    f.store.addEvent(value.taskId, "feedback", "Legacy retained input", { id: "legacy-backlog" });
    f.store.change(value.taskId, task => { task.status = "complete"; });
    const resumed = await f.service.bulk({ tasks: [value], action: "resume" });
    assert.equal(resumed[0].result, "applied");
    assert.equal(f.store.get(value.taskId).status, "active", "Explicit resume recovers retained completed-task backlog");
    await f.service.deliver(f.store.get(value.taskId));
    assert.equal(f.paseo.agents.ref(value.worker!.agentId).messages.length, 3);
    f.paseo.finish(value.worker!.agentId);
    for (const entry of f.store.events(value.taskId)) f.feedback.acknowledge(entry, "Handled");
    complete();
    await f.service.bulk({ tasks: [value], action: "archive" });
    f.store.addEvent(value.taskId, "feedback", "Archived input");
    assert.equal(f.store.get(value.taskId).status, "complete");
    assert.equal(f.store.get(value.taskId).control, "archived");
    await f.service.deliver(f.store.get(value.taskId));
    assert.equal(f.paseo.agents.ref(value.worker!.agentId).messages.length, 3);
  } finally { f.cleanup(); }
});

test("feedback arriving before the final completion update remains dispatchable until the worker handles it", async () => {
  const f = fixture();
  try {
    const value = await create(f);
    await f.service.deliver(value);
    const input = f.store.addEvent(value.taskId, "feedback", "Inspect this input before declaring completion");
    assert.throws(() => f.store.workerUpdate(value.taskId, value.worker!.agentId,
      { status: "complete", evidence: ["Earlier work verified"] }), /pending assigned feedback/);
    assert.equal(f.store.get(value.taskId).status, "active");
    f.paseo.finish(value.worker!.agentId);
    await f.service.deliver(f.store.get(value.taskId));
    assert.equal(f.paseo.agents.ref(value.worker!.agentId).messages.length, 2);
    assert.equal(f.store.events(value.taskId).find(entry => entry.id === input.id)!.delivery, "accepted");
    assert.throws(() => f.store.workerUpdate(value.taskId, value.worker!.agentId,
      { status: "complete", evidence: ["Earlier work verified"] }), /pending assigned feedback/);
    f.feedback.acknowledge(input, "Input handled");
    assert.equal(f.store.workerUpdate(value.taskId, value.worker!.agentId,
      { status: "complete", evidence: ["Work and new input verified"] }).status, "complete");
  } finally { f.cleanup(); }
});

test("GitHub feedback survives restart, source replies reconcile uncertain submissions, and stale revisions prevent posting", async () => {
  const f = fixture();
  try {
    const value = await create(f);
    const url = "https://github.com/o/r/pull/1";
    f.service.link(value.taskId, url);
    f.github.observation.events = [{ type: "inline", item: { id: 12, body: "Please measure the old path",
      html_url: `${url}#discussion_r12`, user: { login: "reviewer" }, updated_at: "now", commit_id: "revision-a" } }];
    await f.feedback.poll(f.store.get(value.taskId));
    const pending = f.store.events(value.taskId).find(item => item.payload.type === "inline")!;
    assert.equal(pending.payload.authority, "review-input");
    assert.equal(pending.source, `${url}#discussion_r12`);
    f.github.uncertain = true;
    await assert.rejects(() => f.feedback.reply(f.store.get(value.taskId), pending.id, "Measured and fixed", "revision-a"), /lost/);
    const persisted = new Store(f.file, "mac");
    const resumed = new Feedback(persisted, f.github, "lanej");
    const receipt = await resumed.reply(persisted.get(value.taskId), pending.id, "Measured and fixed", "revision-a");
    assert.match(receipt, /discussion_r42/);
    assert.equal(f.github.submitted, 1);
    await assert.rejects(() => resumed.reply(persisted.get(value.taskId), pending.id, "Another reply", "revision-a"), /differs/);
    await assert.rejects(() => resumed.reply(persisted.get(value.taskId), pending.id, "Measured and fixed", "revision-b"), /revision/);
    persisted.close();
    assert.equal(f.github.submitted, 1);
    const tools = workerTools(f.service, value.taskId, value.worker!.agentId);
    assert.ok(!tools.some(item => item.name.includes("merge")), "review approval has no automatic merge operation");
  } finally { f.cleanup(); }
});

test("durable database refuses corrupt records instead of reporting an empty or successful board", () => {
  const f = fixture();
  try {
    const value = f.store.create(specified);
    f.store.db.prepare("UPDATE tasks SET record=? WHERE id=?").run(JSON.stringify({ taskId: value.taskId, priority: "corrupt" }), value.taskId);
    assert.throws(() => f.store.list());
  } finally { f.cleanup(); }
});
