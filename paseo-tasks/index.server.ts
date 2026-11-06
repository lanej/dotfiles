import type { PluginServerContext } from "@getpaseo/plugin/server";
import { defineRpc } from "@getpaseo/plugin";
import { z } from "zod";
import { homedir, hostname } from "node:os";
import { join } from "node:path";
import { readFileSync, writeFileSync, mkdirSync, unlinkSync } from "node:fs";
import {
  address, brief, task, conversationAddress, coordinatorReport, incomingReport,
  listRpc, createRpc, bulkRpc, discoverRpc, adoptRpc, acceptRpc, managerRpc, event, migrateRpc,
} from "./shared/contracts";
import { Connection } from "./server/connection";
import { Store } from "./server/store";
import { Feedback, GitHub } from "./server/github";
import { TaskService, taskWorkspaceId } from "./server/service";
import { managerTools, workerTools } from "./server/tools";
import { candidate, inventory, stage, releaseAndImport } from "./server/migration";
import { reportVerification } from "./server/reports";

export default function contribute(server: PluginServerContext) {
  const home = process.env.PASEO_HOME ?? join(homedir(), ".paseo");
  const state = process.env.PASEO_TASKS_STATE ?? join(home, "tasks");
  mkdirSync(state, { recursive: true, mode: 0o700 });
  const lock = join(state, "service.json");
  try {
    const saved = JSON.parse(readFileSync(lock, "utf8"));
    try { process.kill(saved.pid, 0); throw new Error("Another task service is active on this host"); }
    catch (error) { if ((error as NodeJS.ErrnoException).code !== "ESRCH") throw error; }
    unlinkSync(lock);
  } catch (error) { if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error; }
  writeFileSync(lock, JSON.stringify({ pid: process.pid }), { flag: "wx", mode: 0o600 });
  const connection = new Connection(home);
  let service: TaskService | undefined;
  let stopped = false;
  let pending: Promise<void> | null = null;
  const ready = connection.open().then(({ serverId, paseo }) => {
    const store = new Store(join(state, "tasks.sqlite"), serverId);
    service = new TaskService(store, paseo, connection, new Feedback(store, new GitHub(), "lanej"),
      process.env.PASEO_TASK_LABEL ?? hostname());
    return service;
  });
  // NOTE: A load failure remains visible in RPCs and logs without losing the durable records.
  ready.catch(error => console.error("Task service initialization failed:", error.message));
  const timer = setInterval(() => {
    if (stopped || pending) return;
    pending = ready.then(value => value.tick()).catch(error => console.error("Task service recovery failed:", error.message))
      .finally(() => { pending = null; });
  }, 10000);
  server.handle(listRpc, async ({ aggregate }) => (await ready).list(aggregate));
  server.handle(createRpc, async input => (await ready).create(input));
  server.handle(bulkRpc, async input => (await ready).bulk(input));
  server.handle(discoverRpc, async input => (await ready).discover(input.serverId));
  server.handle(adoptRpc, async input => (await ready).adopt(input));
  server.handle(acceptRpc, async input => (await ready).accept(input));
  server.handle(managerRpc, async input => (await ready).newManager(input.cwd));
  server.handle(defineRpc({
    name: "tasks.coordinator", input: address.extend({ coordinator: conversationAddress.nullable() }), output: task,
  }), async input => {
    const value = await ready; value.assertHost(input.serverId);
    return value.assignCoordinator(input, input.coordinator);
  });
  server.handle(defineRpc({ name: "tasks.coordinator_validate", input: conversationAddress, output: z.object({ valid: z.literal(true) }) }),
    async input => {
      const value = await ready; value.assertHost(input.serverId);
      await value.reports.validate(input);
      return { valid: true as const };
    });
  server.handle(defineRpc({ name: "tasks.report_verify", input: z.object({ serverId: z.string(), id: z.uuid() }), output: reportVerification }),
    async input => {
      const value = await ready; value.assertHost(input.serverId);
      return value.reports.verification(input.id);
    });
  server.handle(defineRpc({
    name: "tasks.report_receive", input: coordinatorReport, output: z.object({ delivery: z.enum(["received", "superseded"]) }),
  }), async input => (await ready).reports.receive(input));
  server.handle(defineRpc({
    name: "tasks.report_collect",
    input: z.object({ serverId: z.string(), coordinatorHost: z.string(), receipts: z.array(z.uuid()) }),
    output: z.array(coordinatorReport),
  }), async input => {
    const value = await ready; value.assertHost(input.serverId);
    return value.reports.collect(input.coordinatorHost, input.receipts);
  });
  server.handle(defineRpc({
    name: "tasks.reports", input: conversationAddress, output: z.array(incomingReport),
  }), async input => {
    const value = await ready; value.assertHost(input.serverId);
    return value.store.incomingReports().filter(entry => entry.report.coordinator.agentId === input.agentId);
  });
  server.handle(defineRpc({ name: "tasks.firstmate_inventory", input: z.object({ home: z.string() }), output: z.array(candidate) }),
    async input => inventory(input.home));
  server.handle(defineRpc({ name: "tasks.firstmate_stage", input: z.object({ source: candidate, brief, requestId: z.uuid() }), output: task }),
    async input => stage((await ready).store, input.source, input.brief, input.requestId));
  server.handle(migrateRpc, async input => {
    const value = await ready;
    value.assertHost(input.serverId);
    return releaseAndImport(value.store, input.taskId, async (source, taskId) => {
      let agentId = value.store.get(taskId).worker?.agentId;
      if (!agentId) {
        const matches = (await value.conversations()).filter(agent => agent.provider === "pi" &&
          agent.labels["tasks.id"] === taskId && agent.persistence?.nativeHandle === source.sessionFile);
        if (matches.length > 1) throw new Error("Multiple imported workers claim this session; reconcile ownership before activation");
        agentId = matches[0]?.id;
      }
      if (!agentId) {
        const imported = await connection.raw.importAgent({
          providerId: "pi", providerHandleId: source.sessionFile!, cwd: source.worktree,
          labels: { "tasks.id": taskId, "tasks.role": "worker" },
        });
        agentId = imported.id;
      }
      const handle = value.paseo.agents.ref(agentId);
      await handle.refresh();
      if (handle.activeTurn || handle.status === "running") throw new Error("Imported worker is active; wait for its turn boundary before reconciliation");
      await handle.reload();
      await connection.raw.setAgentModel(handle.id, "bedrock-sonnet-router/us.anthropic.claude-sonnet-5-5");
      await connection.raw.setAgentThinkingOption(handle.id, "medium");
      await handle.refresh();
      return { agentId: handle.id, workspaceId: handle.workspaceId!, cwd: handle.cwd!,
        sessionId: handle.runtimeInfo?.sessionId ?? null };
    });
  });
  server.handle(defineRpc({ name: "tasks.feedback", input: address.extend({ text: z.string().min(1).max(20000) }), output: event }), async input => {
    const value = await ready; value.assertHost(input.serverId);
    return value.store.addEvent(input.taskId, "feedback", input.text);
  });
  server.handle(defineRpc({ name: "tasks.propose", input: address.extend({ brief }), output: task }), async input => {
    const value = await ready; value.assertHost(input.serverId); return value.propose(input.taskId, input.brief);
  });
  server.handle(defineRpc({ name: "tasks.link", input: address.extend({ url: z.string() }), output: task }), async input => {
    const value = await ready; value.assertHost(input.serverId); return value.link(input.taskId, input.url);
  });
  server.addHook("agent.open.before", async ({ request }) => {
    const value = await ready;
    let assigned = value.store.forAgent(request.agentId);
    const id = request.labels["tasks.id"];
    if (!assigned && id) {
      const reserved = value.store.get(id);
      if (!["reserved", "creating"].includes(reserved.launch) || !request.workspaceId) throw new Error("Worker has no matching task reservation");
      if (!reserved.migration && (request.agentId !== id || request.workspaceId !== taskWorkspaceId(id))) throw new Error("Worker identity differs from its stable reservation");
      // WHY: Provider startup can still fail; inject the scope now and bind only after confirmed creation/import.
      assigned = reserved;
    }
    if (request.purpose !== "interactive") return request;
    if (assigned) {
      request.tools.push(...workerTools(value, assigned.taskId, request.agentId));
      request.env.PASEO_TASK_ROLE = "worker";
      value.sessionOpened(request.agentId, "worker");
    } else if (request.labels["tasks.role"] === "manager") {
      request.tools.push(...managerTools(value));
      request.env.PASEO_TASK_ROLE = "manager";
      value.sessionOpened(request.agentId, "manager");
    }
    return request;
  });
  server.addHook("agent.turn.before", async ({ agent }) => {
    const value = await ready; const assigned = value.store.forAgent(agent.id);
    if (assigned) value.store.change(assigned.taskId, current => {
      current.activity = "running"; current.observedAt = value.store.now();
    });
  });
  server.addHook("agent.turn.after", async ({ agent, outcome, turnId }) => (await ready).turnEnded(agent.id, outcome, turnId));
  server.addHook("agent.permission.before", async ({ agent }) => {
    const value = await ready; const assigned = value.store.forAgent(agent.id);
    if (assigned) value.store.change(assigned.taskId, current => { current.activity = "question"; });
  });
  server.addHook("agent.archive.after", async ({ agent }) => {
    const value = await ready; const assigned = value.store.forAgent(agent.id);
    if (assigned) value.store.change(assigned.taskId, current => { current.activity = "closed"; current.control = "archived"; });
  });
  return async () => {
    stopped = true; clearInterval(timer);
    await pending;
    await ready.catch(() => {});
    await connection.close();
    if (service) { await service.paseo.dispose(); service.store.close(); }
    try {
      if (JSON.parse(readFileSync(lock, "utf8")).pid === process.pid) unlinkSync(lock);
    } catch (error) { if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error; }
  };
}
