import { diffExtension, packageRoot } from "./package-resources.ts";
import { integrationStatus, requireIntegration } from "./integrations.ts";
import { getAgentDir, ModelRuntime } from "@earendil-works/pi-coding-agent";
import { WorktreeManager } from "@lanej/task-runtime/worktrees";
import { randomUUID } from "node:crypto";
import { constants } from "node:fs";
import { access, realpath, stat } from "node:fs/promises";
import { join } from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { isDeepStrictEqual } from "node:util";
import { z } from "zod";
import { Attempts, Phase, stateDirectory, type Attempt } from "./attempts.ts";
import {
  AgentRole,
  DefaultProvider,
  DriverProfile,
  type DriverConfig,
  knownProvider,
  loadConfig,
} from "./config.ts";
import { LeadMode } from "./lead-plan.ts";
import { processFailure, processStart, run } from "./process.ts";
import { ClaimRefused, TaskBeads } from "./task-service.ts";
import { Zellij } from "./zellij.ts";

const extension = join(packageRoot, "worker-extension.ts");
export async function piExecutable(): Promise<string> {
  const executable = join(packageRoot, "scripts/pi");
  await access(executable, constants.X_OK);
  return executable;
}

async function focus(
  record: Attempt,
  zellij: Zellij,
  service: TaskBeads,
  primary: string,
  profile: DriverProfile,
  check: string[],
): Promise<Attempt> {
  if (
    record.reservation.primary !== primary ||
    record.profile !== profile ||
    !isDeepStrictEqual(record.check, check)
  ) {
    throw new Error(
      "The existing attempt has a different repository, profile or verification command",
    );
  }
  return focusRegisteredPane(record, zellij, service);
}

export async function taskPaneBeads(project: string): Promise<Set<string>> {
  if (!(await integrationStatus(await loadConfig(), "zellij")).available)
    return new Set();
  const session = process.env["ZELLIJ_SESSION_NAME"];
  if (session === undefined || session === "") return new Set();
  const directory = stateDirectory();
  try {
    await stat(join(directory, "attempts.sqlite"));
  } catch (error) {
    if (processFailure(error).code === "ENOENT") return new Set();
    throw error;
  }
  const db = new Attempts(directory, true);
  try {
    return db.livePaneBeads(project, session);
  } finally {
    db.close();
  }
}

export async function focusTaskPane(
  source: Attempt["source"],
  bead: string,
): Promise<void> {
  await requireIntegration(await loadConfig(), "zellij");
  const session = z
    .string()
    .min(1, "Open the task tree inside Zellij to focus a pane")
    .parse(process.env["ZELLIJ_SESSION_NAME"]);
  const db = new Attempts(stateDirectory(), true);
  try {
    const record = db.latest(source.projectId, bead);
    if (record === null || record.session !== session)
      throw new Error(
        "This task has no registered Pi pane in the current Zellij session",
      );
    await focusRegisteredPane(
      record,
      new Zellij(session),
      new TaskBeads(source),
    );
  } finally {
    db.close();
  }
}

async function focusRegisteredPane(
  record: Attempt,
  zellij: Zellij,
  service: TaskBeads,
): Promise<Attempt> {
  if (record.pid === null || record.pane === null || record.revision === null) {
    throw new Error(
      `Attempt ${record.id} is ${record.phase}. ${record.message}. Inspect pi-driver tasks ${record.bead.id} --json`,
    );
  }
  await service.requireCurrent(record.bead, record.revision, record.id);
  if (record.zellijSocket !== zellij.identity)
    throw new Error(
      "This attempt has no binding to the current Zellij server. Inspect the retained attempt before resuming",
    );
  const panes = await zellij.panes();
  const pane = panes.find(
    (candidate) =>
      candidate.id === record.pane && !candidate.is_plugin && !candidate.exited,
  );
  if (
    !record.live ||
    record.checkout === null ||
    !matchesAttempt(pane?.terminal_command, record.id, record.transcript) ||
    pane?.pane_cwd == null ||
    (await realpath(pane.pane_cwd)) !==
      (await realpath(record.checkout.path)) ||
    (await processStart(record.pid)) !== record.processStarted
  ) {
    throw new Error(
      "The registered Pi process or pane has exited or changed. Inspect the retained attempt before resuming",
    );
  }
  await zellij.focus(record.pane);
  return record;
}

async function assertLeadProfile(
  config: DriverConfig,
  profile: DriverProfile,
): Promise<void> {
  const agent = getAgentDir();
  const runtime = await ModelRuntime.create({
    authPath: join(agent, "auth.json"),
    modelsPath: join(agent, "models.json"),
  });
  for (const role of [AgentRole.Lead, AgentRole.Explorer, AgentRole.Reviewer]) {
    const selection = config.profiles[profile]?.[role];
    const model =
      selection === undefined
        ? undefined
        : runtime.getModel(selection.provider, selection.model);
    if (
      model === undefined ||
      !runtime.hasConfiguredAuth(model.provider) ||
      (profile === DriverProfile.Personal &&
        knownProvider(model.provider) !==
          DefaultProvider.ChatGPTSubscription) ||
      (profile === DriverProfile.Work &&
        !/^https:\/\/bedrock-mantle\.[a-z0-9-]+\.api\.aws(?:\/|$)/u.test(
          model.baseUrl,
        ))
    )
      throw new Error(
        `Configure and authenticate the ${profile} ${role} model in Pi before claiming the task`,
      );
  }
}

function matchesAttempt(
  command: string | null | undefined,
  attempt: string,
  transcript: string | null,
): boolean {
  const argv = command?.split(/\s+/u) ?? [];
  const marker = argv.indexOf("--session-id");
  return (
    (marker >= 0 && argv[marker + 1] === attempt) ||
    (transcript !== null &&
      command?.includes(`--session ${transcript} --`) === true)
  );
}

async function launchPi(
  db: Attempts,
  zellij: Zellij,
  tab: number,
  binary: string,
  record: Attempt,
): Promise<Attempt> {
  const { id: attempt, checkout, model } = record;
  const id = record.bead.id;
  const lead = record.leadPlan !== undefined;
  if (checkout === null) throw new Error("Missing managed checkout");
  const environment = [
    `PI_DRIVER_STATE_DIR=${db.directory}`,
    `PI_DRIVER_ATTEMPT=${attempt}`,
    // Pi does not detect hyperlink support from the managed Zellij pane alone.
    ...(lead ? ["PI_HYPERLINKS=1"] : []),
  ];
  for (const key of ["PI_CODING_AGENT_DIR", "PI_DRIVER_CONFIG", "PATH"]) {
    const value = process.env[key];
    if (value !== undefined) environment.push(`${key}=${value}`);
  }
  const args = [
    ...environment,
    binary,
    ...(record.resumePhase === undefined || record.transcript === null
      ? ["--session-id", attempt]
      : ["--session", record.transcript]),
    ...(lead
      ? ["--no-extensions", "--no-mcp", "--extension", diffExtension()]
      : []),
    "--extension",
    extension,
    "--provider",
    model.provider,
    "--model",
    model.model,
    "--thinking",
    model.reasoning,
  ];
  let pane: number;
  try {
    pane = await zellij.launch(tab, id, checkout.path, args);
  } catch (error) {
    // The socket can disconnect after accepting a launch. Recover the existing
    // pane by attempt identity and never send another launch for this attempt.
    const candidates = await zellij.panes().catch(() => []);
    const matching = candidates.filter(
      (candidate) =>
        candidate.tab_id === tab &&
        !candidate.is_plugin &&
        !candidate.exited &&
        matchesAttempt(candidate.terminal_command, attempt, record.transcript),
    );
    const [recovered] = matching;
    if (matching.length !== 1 || recovered === undefined) throw error;
    pane = recovered.id;
  }
  const deadline = Date.now() + 15000;
  do {
    const observed = db.get(attempt);
    if (observed.phase === Phase.Reconcile) throw new Error(observed.message);
    if (observed.pid !== null) {
      if (observed.pane !== pane)
        throw new Error("Pi registered a different Zellij pane");
      return observed;
    }
    await delay(100);
  } while (Date.now() < deadline);
  throw new Error(
    "Native Pi registration is pending. Inspect the attempt before retrying",
  );
}

export function processIsGone(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return false;
  } catch (error) {
    if (z.object({ code: z.literal("ESRCH") }).safeParse(error).success)
      return true;
    throw error;
  }
}

export async function resumeLead(
  bead: string,
  targetTab?: number,
): Promise<Attempt> {
  const config = await loadConfig();
  await requireIntegration(config, "zellij");
  const managerExecutable = await requireIntegration(config, "worktrees");
  if (config.beadsService === undefined)
    throw new Error("Configure the Beads service before resuming");
  const db = new Attempts(stateDirectory());
  try {
    const record = db.latest(config.beadsService.projectId, bead);
    if (
      record === null ||
      record.leadPlan === undefined ||
      record.checkout === null ||
      record.revision === null ||
      record.transcript === null ||
      record.pid === null ||
      (record.phase !== Phase.Running &&
        record.phase !== Phase.Verified &&
        record.phase !== Phase.CheckFailed)
    )
      throw new Error("No settled, resumable lead attempt is recorded");
    const session = z
      .string()
      .min(1, "Resume from a live Zellij session")
      .parse(process.env["ZELLIJ_SESSION_NAME"]);
    const zellij = new Zellij(session);
    const service = new TaskBeads(record.source);
    if (!processIsGone(record.pid)) {
      return await focus(
        record,
        zellij,
        service,
        record.reservation.primary,
        record.profile,
        record.check,
      );
    }
    const checkout = record.checkout;
    if (
      (
        await run("git", ["rev-parse", "--show-toplevel"], {
          cwd: checkout.path,
        })
      ).trim() !== (await realpath(checkout.path)) ||
      (
        await run("git", ["branch", "--show-current"], { cwd: checkout.path })
      ).trim() !== checkout.branch ||
      !(await stat(record.transcript)).isFile()
    )
      throw new Error(
        "The managed checkout or Pi transcript no longer matches the attempt",
      );
    await new WorktreeManager(managerExecutable).requireAllocation(checkout);
    if (record.leadPlan.mode === LeadMode.Applying)
      throw new Error("The plan batch needs reconciliation before resuming");
    await service.requireCurrent(record.bead, record.revision, record.id);
    await assertLeadProfile(config, record.profile);
    const [binary, tab] = await Promise.all([
      piExecutable(),
      zellij.launchTab(targetTab),
    ]);
    const previousPid = record.pid;
    const phase = record.phase;
    const pending = db.change(record.id, (row) => {
      if (
        row.pid !== previousPid ||
        row.phase !== phase ||
        row.revision !== record.revision ||
        !processIsGone(previousPid)
      )
        throw new Error("The lead changed before resume admission");
      row.resumePhase = phase;
      row.phase = Phase.Launching;
      row.session = session;
      row.zellijSocket = zellij.identity;
      row.live = false;
      row.pid = null;
      row.pane = null;
      row.message = "Waiting for the existing Pi transcript to reopen";
    });
    try {
      return await launchPi(db, zellij, tab, binary, pending);
    } catch (error) {
      db.change(record.id, (row) => {
        if (row.pid !== null) return;
        row.phase = Phase.Reconcile;
        row.message =
          "Resume outcome uncertain. Inspect the Pi pane and transcript before retrying";
      });
      throw error;
    }
  } finally {
    db.close();
  }
}

export async function startTask(
  id: string,
  profile: DriverProfile,
  check: string[],
  targetTab?: number,
  lead = true,
): Promise<Attempt> {
  const config = await loadConfig();
  await requireIntegration(config, "zellij");
  const managerExecutable = await requireIntegration(config, "worktrees");
  const source = config.beadsService;
  if (source === undefined)
    throw new Error(
      "Configure beadsService.url and beadsService.projectId to start a native bead",
    );
  const model =
    config.profiles[profile]?.[lead ? AgentRole.Lead : AgentRole.Worker];
  if (model === undefined)
    throw new Error(`Configure the model for the ${profile} profile`);
  const expectedProvider =
    profile === DriverProfile.Personal
      ? DefaultProvider.ChatGPTSubscription
      : DefaultProvider.BedrockMantle;
  if (knownProvider(model.provider) !== expectedProvider)
    throw new Error(`The ${profile} profile must use ${expectedProvider}`);
  const session = z
    .string()
    .min(1, "Start from the target Zellij session")
    .parse(process.env["ZELLIJ_SESSION_NAME"]);
  const zellij = new Zellij(session);
  const attempt = randomUUID();
  const manager = new WorktreeManager(managerExecutable);
  const service = new TaskBeads(source);
  await access(extension, constants.R_OK);
  const [binary, reservation, bead, tab] = await Promise.all([
    piExecutable(),
    manager.prepare(process.cwd(), attempt, `pi/bead-${attempt}`, "HEAD", "pi"),
    service.get(id),
    zellij.launchTab(targetTab),
  ]);
  const db = new Attempts(stateDirectory());
  try {
    const initial: Attempt = {
      id: attempt,
      source,
      bead,
      revision: null,
      check,
      profile,
      model,
      live: false,
      leadPlan: lead ? { mode: LeadMode.Planning, draft: null } : undefined,
      processStarted: null,
      reservation,
      checkout: null,
      session,
      zellijSocket: zellij.identity,
      pane: null,
      pid: null,
      transcript: null,
      phase: Phase.Admitting,
      verification: null,
      message: "Claiming the accepted bead",
    };
    const last = db.latest(source.projectId, id);
    if (bead.status === "closed") {
      if (
        last?.verification?.exitCode === 0 &&
        (await service.closedWith(id, last.id, last.verification))
      ) {
        return db.change(last.id, (row) => {
          row.phase = Phase.Closed;
          row.message = "Beads confirmed the verified result";
        });
      }
      throw new Error("This bead is already closed");
    }
    if (last === null && (bead.status !== "open" || bead.assignee !== ""))
      throw new Error("The bead must be open and unclaimed");
    if (last === null && lead) await assertLeadProfile(config, profile);
    if (!db.reserve(initial)) {
      const existing = db.latest(source.projectId, id);
      if (existing === null)
        throw new Error("The active attempt could not be identified");
      if ((existing.leadPlan !== undefined) !== lead)
        throw new Error("The existing attempt has a different session role");
      return await focus(
        existing,
        zellij,
        service,
        reservation.primary,
        profile,
        check,
      );
    }
    try {
      const revision = await service.claim(bead, attempt);
      db.change(attempt, (row) => {
        row.revision = revision;
        row.phase = Phase.Allocating;
        row.message = "Allocating the managed checkout";
      });
      const checkout = await manager.acquire(reservation, () => {
        db.change(attempt, (row) => {
          row.reservation.attempted = true;
        });
      });
      db.change(attempt, (row) => {
        row.checkout = checkout;
        row.phase = Phase.Launching;
        row.message = "Waiting for native Pi to register";
      });
      await service.requireCurrent(bead, revision, attempt);
      return await launchPi(db, zellij, tab, binary, db.get(attempt));
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : String(cause);
      // A read immediately after a transport failure can outrun the original claim.
      db.change(attempt, (row) => {
        if (row.pid !== null) return;
        row.phase =
          cause instanceof ClaimRefused ? Phase.Rejected : Phase.Reconcile;
        row.message = message;
      });
      throw cause;
    }
  } finally {
    db.close();
  }
}
