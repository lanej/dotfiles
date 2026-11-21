import { WorktreeManager } from "@lanej/task-runtime/worktrees";
import { randomUUID } from "node:crypto";
import { constants } from "node:fs";
import { access, realpath } from "node:fs/promises";
import { delimiter, join } from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { fileURLToPath } from "node:url";
import { isDeepStrictEqual } from "node:util";
import { z } from "zod";
import { Attempts, Phase, stateDirectory, type Attempt } from "./attempts.ts";
import {
  AgentRole,
  DefaultProvider,
  DriverProfile,
  knownProvider,
  loadConfig,
} from "./config.ts";
import { processStart } from "./process.ts";
import { ClaimRefused, TaskBeads } from "./task-service.ts";
import { Zellij } from "./zellij.ts";

const extension = fileURLToPath(
  new URL("./worker-extension.ts", import.meta.url),
);
async function piExecutable(): Promise<string> {
  const dirs = (process.env["PATH"] ?? "")
    .split(delimiter)
    .filter((dir) => dir.length > 0);
  const candidates = [
    ...dirs.map((dir) => join(dir, "pi")),
    fileURLToPath(new URL("./node_modules/.bin/pi", import.meta.url)),
  ];
  for (const candidate of candidates) {
    try {
      await access(candidate, constants.X_OK);
      return await realpath(candidate);
    } catch {
      // Keep searching the executable path.
    }
  }
  throw new Error("Install the configured Pi runtime before starting a bead");
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
    !matchesAttempt(pane?.terminal_command, record.id) ||
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

function matchesAttempt(
  command: string | null | undefined,
  attempt: string,
): boolean {
  const argv = command?.split(/\s+/u) ?? [];
  const marker = argv.indexOf("--session-id");
  return marker >= 0 && argv[marker + 1] === attempt;
}

export async function startTask(
  id: string,
  profile: DriverProfile,
  check: string[],
  targetTab?: number,
): Promise<Attempt> {
  const config = await loadConfig();
  const source = config.beadsService;
  if (source === undefined)
    throw new Error(
      "Configure beadsService.url and beadsService.projectId to start a native bead",
    );
  const model = config.profiles[profile]?.[AgentRole.Worker];
  if (model === undefined)
    throw new Error(`Configure the worker model for the ${profile} profile`);
  const expectedProvider =
    profile === DriverProfile.Personal
      ? DefaultProvider.ChatGPTSubscription
      : DefaultProvider.BedrockMantle;
  if (knownProvider(model.provider) !== expectedProvider)
    throw new Error(`The ${profile} worker must use ${expectedProvider}`);
  const session = z
    .string()
    .min(1, "Start from the target Zellij session")
    .parse(process.env["ZELLIJ_SESSION_NAME"]);
  const zellij = new Zellij(session);
  const attempt = randomUUID();
  const manager = new WorktreeManager();
  const service = new TaskBeads(source);
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
    if (!db.reserve(initial)) {
      const existing = db.latest(source.projectId, id);
      if (existing === null)
        throw new Error("The active attempt could not be identified");
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
      const environment = [
        `PI_DRIVER_STATE_DIR=${db.directory}`,
        `PI_DRIVER_ATTEMPT=${attempt}`,
      ];
      for (const key of ["PI_CODING_AGENT_DIR", "PI_DRIVER_CONFIG", "PATH"]) {
        const value = process.env[key];
        if (value !== undefined) environment.push(`${key}=${value}`);
      }
      const args = [
        ...environment,
        binary,
        "--session-id",
        attempt,
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
            matchesAttempt(candidate.terminal_command, attempt),
        );
        const [recovered] = matching;
        if (matching.length !== 1 || recovered === undefined) throw error;
        pane = recovered.id;
      }
      const deadline = Date.now() + 15000;
      do {
        const observed = db.get(attempt);
        if (observed.phase === Phase.Reconcile)
          throw new Error(observed.message);
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
