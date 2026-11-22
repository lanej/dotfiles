import { mkdirSync, readFileSync, unlinkSync, writeFileSync } from "node:fs";
import { homedir, hostname } from "node:os";
import { join } from "node:path";
import { defineRpc } from "@getpaseo/plugin";
import type { PluginServerContext } from "@getpaseo/plugin/server";
import { z } from "zod";
import { Connection } from "./server/connection";
import { Beads } from "./server/beads";
import { Feedback, GitHub } from "./server/github";
import {
  candidate,
  inventory,
  releaseAndImport,
  stage,
} from "./server/migration";
import { MaintenanceQueue, PRMaintenance } from "./server/pr-maintenance";
import { reportVerification } from "./server/reports";
import { TaskService, taskWorkspaceId } from "./server/service";
import { Store } from "./server/store";
import { managerTools, workerTools } from "./server/tools";
import {
  acceptRpc,
  address,
  adoptRpc,
  authorizeTurnRpc,
  brief,
  bulkRpc,
  conversationAddress,
  coordinatorReport,
  createRpc,
  discoverRpc,
  event,
  incomingReport,
  listRpc,
  managerRpc,
  migrateRpc,
  task,
} from "./shared/contracts";
export default function contribute(server: PluginServerContext) {
  const home = process.env.PASEO_HOME ?? join(homedir(), ".paseo");
  const state = process.env.PASEO_TASKS_STATE ?? join(home, "tasks");
  mkdirSync(state, { recursive: true, mode: 0o700 });
  const lock = join(state, "service.json");
  try {
    const saved = JSON.parse(readFileSync(lock, "utf8"));
    try {
      process.kill(saved.pid, 0);
      throw new Error("Another task service is active on this host");
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ESRCH") throw error;
    }
    unlinkSync(lock);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
  }
  writeFileSync(lock, JSON.stringify({ pid: process.pid }), {
    flag: "wx",
    mode: 0o600,
  });
  const file = join(state, "tasks.sqlite");
  let connection: Connection | undefined;
  const taskConnection = () => (connection ??= new Connection(home));
  let initialization: Promise<TaskService> | undefined;
  let service: TaskService | undefined;
  let stopped = false;
  let pending: Promise<void> | null = null;
  const initialize = async () => {
    if (
      process.env.PASEO_TASKS_BEADS_DIR ||
      process.env.PASEO_TASKS_BEADS_AUTHORITY ||
      process.env.PASEO_TASKS_BEADS_SSH_HOST
    )
      throw new Error(
        "Embedded/SSH Beads settings are retired; configure PASEO_TASKS_BEADS_URL and PASEO_TASKS_BEADS_PROJECT_ID explicitly. Existing data is preserved.",
      );
    const url = process.env.PASEO_TASKS_BEADS_URL;
    const project = process.env.PASEO_TASKS_BEADS_PROJECT_ID;
    if (!url || !project)
      throw new Error(
        "Set PASEO_TASKS_BEADS_URL and PASEO_TASKS_BEADS_PROJECT_ID for the shared Beads service",
      );
    const tokenFile = process.env.PASEO_TASKS_BEADS_TOKEN_FILE;
    const records = new Beads(
      url,
      project,
      tokenFile ? readFileSync(tokenFile, "utf8").trim() : undefined,
    );
    await records.verifyAuthority();
    const router = taskConnection();
    const { serverId, paseo } = await router.open();
    const store = new Store(file, serverId, undefined, records);
    const github = new GitHub();
    service = new TaskService(
      store,
      paseo,
      router,
      new Feedback(store, github, "lanej"),
      process.env.PASEO_TASK_LABEL ?? hostname(),
      undefined,
      undefined,
      new MaintenanceQueue(new PRMaintenance(store, github, state)),
    );
    return service;
  };
  function ready(): Promise<TaskService> {
    initialization ??= initialize().catch((error: unknown) => {
      initialization = undefined;
      throw error;
    });
    return initialization;
  }
  function hasWorker(agentId: string): boolean {
    return service?.store.hasWorker(agentId) ?? Store.hasWorker(file, agentId);
  }
  const timer = setInterval(() => {
    if (stopped || pending) return;
    pending = ready()
      .then(async (value) => await value.tick())
      .catch((error) =>
        console.error("Task service recovery failed:", error.message),
      )
      .finally(() => {
        pending = null;
      });
  }, 10000);
  server.handle(
    listRpc,
    async ({ aggregate }) => await (await ready()).list(aggregate),
  );
  server.handle(
    createRpc,
    async (input) => await (await ready()).create(input),
  );
  server.handle(bulkRpc, async (input) => await (await ready()).bulk(input));
  server.handle(
    discoverRpc,
    async (input) => await (await ready()).discover(input.serverId),
  );
  server.handle(adoptRpc, async (input) => await (await ready()).adopt(input));
  server.handle(authorizeTurnRpc, async ({ serverId, taskId, agentId }) => {
    const value = await ready();
    value.assertHost(serverId);
    await value.store.assertOwner(taskId, agentId);
    return true as const;
  });
  server.handle(
    acceptRpc,
    async (input) => await (await ready()).accept(input),
  );
  server.handle(
    managerRpc,
    async (input) => await (await ready()).newManager(input.cwd),
  );
  server.handle(
    defineRpc({
      name: "tasks.coordinator",
      input: address.extend({ coordinator: conversationAddress.nullable() }),
      output: task,
    }),
    async (input) => {
      const value = await ready();
      value.assertHost(input.serverId);
      return await value.assignCoordinator(input, input.coordinator);
    },
  );
  server.handle(
    defineRpc({
      name: "tasks.coordinator_validate",
      input: conversationAddress,
      output: z.object({ valid: z.literal(true) }),
    }),
    async (input) => {
      const value = await ready();
      value.assertHost(input.serverId);
      await value.reports.validate(input);
      return { valid: true as const };
    },
  );
  server.handle(
    defineRpc({
      name: "tasks.report_verify",
      input: z.object({ serverId: z.string(), id: z.uuid() }),
      output: reportVerification,
    }),
    async (input) => {
      const value = await ready();
      value.assertHost(input.serverId);
      return await value.reports.verification(input.id);
    },
  );
  server.handle(
    defineRpc({
      name: "tasks.report_receive",
      input: coordinatorReport,
      output: z.object({ delivery: z.enum(["received", "superseded"]) }),
    }),
    async (input) => await (await ready()).reports.receive(input),
  );
  server.handle(
    defineRpc({
      name: "tasks.report_collect",
      input: z.object({
        serverId: z.string(),
        coordinatorHost: z.string(),
        receipts: z.array(z.uuid()),
      }),
      output: z.array(coordinatorReport),
    }),
    async (input) => {
      const value = await ready();
      value.assertHost(input.serverId);
      return await value.reports.collect(input.coordinatorHost, input.receipts);
    },
  );
  server.handle(
    defineRpc({
      name: "tasks.reports",
      input: conversationAddress,
      output: z.array(incomingReport),
    }),
    async (input) => {
      const value = await ready();
      value.assertHost(input.serverId);
      return (await value.store.incomingReports()).filter(
        (entry) => entry.report.coordinator.agentId === input.agentId,
      );
    },
  );
  server.handle(
    defineRpc({
      name: "tasks.firstmate_inventory",
      input: z.object({ home: z.string() }),
      output: z.array(candidate),
    }),
    async (input) => await inventory(input.home),
  );
  server.handle(
    defineRpc({
      name: "tasks.firstmate_stage",
      input: z.object({ source: candidate, brief, requestId: z.uuid() }),
      output: task,
    }),
    async (input) =>
      await stage(
        (await ready()).store,
        input.source,
        input.brief,
        input.requestId,
      ),
  );
  server.handle(migrateRpc, async (input) => {
    const value = await ready();
    value.assertHost(input.serverId);
    const raw = taskConnection().raw;
    return await releaseAndImport(
      value.store,
      input.taskId,
      async (source, taskId) => {
        let agentId = (await value.store.get(taskId)).worker?.agentId;
        if (!agentId) {
          const matches = (await value.conversations()).filter(
            (agent) =>
              agent.provider === "pi" &&
              agent.labels["tasks.id"] === taskId &&
              agent.persistence?.nativeHandle === source.sessionFile,
          );
          if (matches.length > 1)
            throw new Error(
              "Multiple imported workers claim this session; reconcile ownership before activation",
            );
          agentId = matches[0]?.id;
        }
        if (!agentId) {
          const imported = await raw.importAgent({
            providerId: "pi",
            providerHandleId: source.sessionFile!,
            cwd: source.worktree,
            labels: { "tasks.id": taskId, "tasks.role": "worker" },
          });
          agentId = imported.id;
        }
        const handle = value.paseo.agents.ref(agentId);
        await handle.refresh();
        if (handle.activeTurn || handle.status === "running")
          throw new Error(
            "Imported worker is active; wait for its turn boundary before reconciliation",
          );
        await handle.reload();
        await raw.setAgentModel(
          handle.id,
          "bedrock-sonnet-router/us.anthropic.claude-sonnet-5-5",
        );
        await raw.setAgentThinkingOption(handle.id, "medium");
        await handle.refresh();
        return {
          agentId: handle.id,
          workspaceId: handle.workspaceId!,
          cwd: handle.cwd!,
          sessionId: handle.runtimeInfo?.sessionId ?? null,
        };
      },
    );
  });
  server.handle(
    defineRpc({
      name: "tasks.feedback",
      input: address.extend({ text: z.string().min(1).max(20000) }),
      output: event,
    }),
    async (input) => {
      const value = await ready();
      value.assertHost(input.serverId);
      return await value.store.addEvent(input.taskId, "feedback", input.text);
    },
  );
  server.handle(
    defineRpc({
      name: "tasks.propose",
      input: address.extend({ brief }),
      output: task,
    }),
    async (input) => {
      const value = await ready();
      value.assertHost(input.serverId);
      return await value.propose(input.taskId, input.brief);
    },
  );
  server.handle(
    defineRpc({
      name: "tasks.link",
      input: address.extend({ url: z.string() }),
      output: task,
    }),
    async (input) => {
      const value = await ready();
      value.assertHost(input.serverId);
      return await value.link(input.taskId, input.url);
    },
  );
  server.handle(
    defineRpc({
      name: "tasks.pr_maintenance",
      input: address,
      output: z.array(z.unknown()),
    }),
    async (input) => {
      const value = await ready();
      value.assertHost(input.serverId);
      await value.store.get(input.taskId);
      return value.maintenance?.records(input.taskId) ?? [];
    },
  );
  server.addHook("agent.open.before", async ({ request }) => {
    const id = request.labels["tasks.id"];
    const manager = request.labels["tasks.role"] === "manager";
    const worker = hasWorker(request.agentId);
    if (!id && !manager && !worker) return request;
    const value = await ready();
    let assigned = worker
      ? await value.store.forAgent(request.agentId)
      : undefined;
    if (!assigned && id) {
      const reserved = await value.store.get(id);
      if (
        !["reserved", "creating"].includes(reserved.launch) ||
        !request.workspaceId
      )
        throw new Error("Worker has no matching task reservation");
      if (
        !reserved.migration &&
        (request.agentId !== id || request.workspaceId !== taskWorkspaceId(id))
      )
        throw new Error("Worker identity differs from its stable reservation");
      // WHY: Provider startup can still fail; inject the scope now and bind only after confirmed creation/import.
      assigned = reserved;
    }
    if (request.purpose !== "interactive") return request;
    if (assigned) {
      request.tools.push(
        ...workerTools(value, assigned.taskId, request.agentId),
      );
      request.env.PASEO_TASK_ROLE = "worker";
      request.env.PASEO_TASK_ID = assigned.taskId;
      request.env.PASEO_TASK_SERVER_ID = value.store.serverId;
      request.env.PASEO_HOME = home;
      value.sessionOpened(request.agentId, "worker");
    } else if (manager) {
      request.tools.push(...managerTools(value));
      request.env.PASEO_TASK_ROLE = "manager";
      value.sessionOpened(request.agentId, "manager");
    }
    return request;
  });
  server.addHook("agent.turn.before", async ({ agent }) => {
    if (!hasWorker(agent.id)) return;
    const value = await ready();
    const assigned = await value.store.forAgent(agent.id);
    if (assigned)
      await value.store.transaction(async () => {
        await value.store.assertOwner(assigned.taskId);
        await value.store.change(assigned.taskId, (current) => {
          current.activity = "running";
          current.observedAt = value.store.now();
        });
      });
  });
  server.addHook("agent.turn.after", async ({ agent, outcome, turnId }) => {
    if (hasWorker(agent.id))
      await (await ready()).turnEnded(agent.id, outcome, turnId);
  });
  server.addHook("agent.permission.before", async ({ agent }) => {
    if (!hasWorker(agent.id)) return;
    const value = await ready();
    const assigned = await value.store.forAgent(agent.id);
    if (assigned)
      await value.store.change(assigned.taskId, (current) => {
        current.activity = "question";
      });
  });
  server.addHook("agent.archive.after", async ({ agent }) => {
    if (!hasWorker(agent.id)) return;
    const value = await ready();
    const assigned = await value.store.forAgent(agent.id);
    if (assigned)
      await value.store.change(assigned.taskId, (current) => {
        current.activity = "closed";
        current.control = "archived";
      });
  });
  return async () => {
    stopped = true;
    clearInterval(timer);
    await pending;
    await initialization?.catch(() => {});
    await service?.maintenance?.close?.();
    await connection?.close();
    if (service) {
      await service.paseo.dispose();
      service.store.close();
    }
    try {
      if (JSON.parse(readFileSync(lock, "utf8")).pid === process.pid)
        unlinkSync(lock);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    }
  };
}
