import { EventEmitter } from "node:events";
import { fork, type ChildProcess } from "node:child_process";
import { createServer, type Server, type Socket } from "node:net";
import { chmodSync, existsSync, lstatSync, unlinkSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { Store } from "./store.js";
import { activeStates, cleanText, nextReady, parseTask, retryDelay, transition, type Job, type Snapshot, type Status } from "./domain.js";
import { createFixture, readConflict, writeResolution, validateResolution, finishFixture, removeFixture } from "./fixture.js";
import { readPullRequest } from "./github.js";

interface Active { jobId: string; attempt: number; child?: ChildProcess; childExited?: boolean; abort: AbortController; exited: Promise<void>; killTimer?: NodeJS.Timeout }
export interface CoordinatorOptions { now?: () => number; workerPath?: string; model?: string; workerEnv?: NodeJS.ProcessEnv }
export function processAlive(pid: number): boolean {
  try { process.kill(pid, 0); return true; } catch (error) { return (error as NodeJS.ErrnoException).code !== "ESRCH"; }
}
function errorText(error: unknown): string {
  // WHY: Subprocess errors contain commands and output; persist a bounded diagnosis rather than raw error objects.
  const e = error as { name?: string; message?: string; code?: string | number; status?: number };
  if (e.name === "AbortError") return "Operation aborted";
  return cleanText(e.message ?? String(error), 2000);
}
export function transient(error: string): boolean {
  return /\b(429|500|502|503|504)\b|ECONNRESET|ETIMEDOUT|EAI_AGAIN|temporarily unavailable|rate limit/i.test(error) && !/auth|credential|login|401|403/i.test(error);
}
export class Coordinator extends EventEmitter {
  readonly store: Store;
  readonly socketPath: string;
  private server?: Server;
  private sockets = new Set<Socket>();
  private timer?: NodeJS.Timeout;
  private active?: Active;
  private stopping = false;
  private stopped = false;
  private recoveryPids = new Set<number>();
  private now: () => number;
  private closePromise?: Promise<void>;
  private finalSnapshot?: Snapshot;
  constructor(readonly directory: string, private options: CoordinatorOptions = {}) {
    super(); this.now = options.now ?? Date.now;
    this.store = new Store(directory, this.now);
    this.socketPath = join(directory, "run.sock");
    for (const job of this.store.jobs()) {
      let observedExit = false;
      for (const attempt of job.attempts) {
        if (!attempt.pid || attempt.exitObservedAt !== undefined) continue;
        if (processAlive(attempt.pid)) this.recoveryPids.add(attempt.pid);
        else { attempt.exitObservedAt = this.now(); observedExit = true; }
      }
      if (observedExit) this.store.save(job, "worker_exit_observed", "Previous worker no longer exists");
      if (!activeStates.includes(job.status)) continue;
      this.store.save({ ...transition(job, "interrupted", this.now()), attempts: job.attempts.map((a, i) => i === job.attempts.length - 1 ? { ...a, endedAt: this.now(), error: "Coordinator stopped before completion" } : a), error: "Previous attempt interrupted; retry explicitly after the previous worker exits" }, "interrupted", "Coordinator recovery");
    }
  }
  async start(): Promise<void> {
    try {
      // WHY: The SQLite ownership lock is held before inspecting or replacing a stale socket.
      if (existsSync(this.socketPath)) {
        if (!lstatSync(this.socketPath).isSocket()) throw new Error("Refusing to replace a non-socket control path");
        unlinkSync(this.socketPath);
      }
      this.server = createServer(socket => this.connection(socket));
      await new Promise<void>((resolve, reject) => { this.server!.once("error", reject); this.server!.listen(this.socketPath, () => { this.server!.off("error", reject); resolve(); }); });
      chmodSync(this.socketPath, 0o600);
      this.timer = setInterval(() => this.tick(), 100);
      this.tick();
    } catch (error) { this.store.close(); throw error; }
  }
  snapshot(): Snapshot {
    if (this.finalSnapshot) return this.finalSnapshot;
    const recoveryPid = [...this.recoveryPids][0];
    return { scheduler: this.stopped ? "stopped" : this.stopping ? "stopping" : this.store.paused() ? "paused" : "running", worker: recoveryPid ? "recovering" : this.active ? "busy" : "idle", jobs: this.store.jobs(), events: this.store.events(), ...(recoveryPid ? { recoveryPid } : {}) };
  }
  private notify(): void { this.emit("change"); }
  private change(id: string, status: Status, detail = "", patch: Partial<Job> = {}): Job {
    const job = { ...transition(this.store.get(id), status, this.now()), ...patch };
    this.store.save(job, status, detail); this.notify(); return job;
  }
  command(value: unknown): unknown {
    if (!value || typeof value !== "object") throw new Error("Expected command object");
    const v = value as Record<string, unknown>;
    if (v.op === "snapshot") return this.snapshot();
    if (v.op === "get" && typeof v.id === "string") return this.store.get(v.id);
    if (v.op === "events") {
      if (v.id !== undefined && typeof v.id !== "string") throw new Error("Invalid job ID");
      const after = v.after ?? 0;
      if (!Number.isSafeInteger(after) || (after as number) < 0) throw new Error("Invalid event cursor");
      return this.store.events(after as number, v.id as string | undefined);
    }
    if (this.stopping) throw new Error("Coordinator is stopping");
    if (v.op === "submit" && typeof v.requestId === "string") {
      const job = this.store.submit(parseTask(v.task), v.requestId); this.notify(); queueMicrotask(() => this.tick()); return job;
    }
    if (v.op === "pause" || v.op === "resume") { this.store.setPaused(v.op === "pause"); this.notify(); queueMicrotask(() => this.tick()); return { scheduler: v.op === "pause" ? "paused" : "running" }; }
    if (v.op === "cancel" && typeof v.id === "string") return this.cancel(v.id);
    if (v.op === "retry" && typeof v.id === "string") {
      if (this.recoveryPids.size || this.active?.jobId === v.id) throw new Error("Wait for the previous worker to exit before retrying");
      const job = this.store.get(v.id);
      if (job.status !== "failed" && job.status !== "interrupted") throw new Error("Only failed or interrupted jobs can be retried");
      return this.change(job.id, "queued", "Manual retry", { error: undefined, result: undefined, retryCount: 0, availableAt: this.now(), fixture: undefined });
    }
    throw new Error("Unsupported command or arguments");
  }
  private connection(socket: Socket): void {
    this.sockets.add(socket); socket.on("close", () => this.sockets.delete(socket)); socket.on("error", () => {});
    socket.setTimeout(5000, () => socket.destroy());
    let input = "";
    socket.on("data", chunk => {
      input += chunk.toString();
      if (Buffer.byteLength(input) > 16384) { socket.end(JSON.stringify({ ok: false, error: "Request too large" }) + "\n"); return; }
      if (!input.includes("\n")) return;
      try { socket.end(JSON.stringify({ ok: true, result: this.command(JSON.parse(input.slice(0, input.indexOf("\n")))) }) + "\n"); }
      catch (error) { socket.end(JSON.stringify({ ok: false, error: errorText(error) }) + "\n"); }
    });
  }
  tick(): void {
    for (const pid of this.recoveryPids) if (!processAlive(pid)) {
      this.recoveryPids.delete(pid);
      for (const job of this.store.jobs()) {
        if (job.attempts.some(a => a.pid === pid && a.exitObservedAt === undefined)) {
          job.attempts = job.attempts.map(a => a.pid === pid && a.exitObservedAt === undefined ? { ...a, exitObservedAt: this.now() } : a);
          this.store.save(job, "worker_exit_observed", "Previous worker no longer exists");
        }
      }
      this.notify();
    }
    if (this.stopping || this.active || this.recoveryPids.size || this.store.paused()) return;
    const now = this.now();
    for (const job of this.store.jobs()) if (job.status === "retry_wait" && job.availableAt <= now) this.change(job.id, "queued", "Retry delay elapsed");
    const job = nextReady(this.store.jobs(), now);
    if (!job) return;
    const claimed = this.change(job.id, "running", "Worker claimed", { error: undefined, result: undefined, attempts: [...job.attempts, { number: job.attempts.length + 1, startedAt: now }] });
    const active: Active = { jobId: job.id, attempt: claimed.attempts.length, abort: new AbortController(), exited: Promise.resolve() };
    this.active = active;
    active.exited = this.run(active).finally(() => { if (active.killTimer) clearTimeout(active.killTimer); if (this.active === active) this.active = undefined; this.notify(); if (!this.stopping) queueMicrotask(() => this.tick()); });
  }
  private cancel(id: string): Job {
    const job = this.store.get(id);
    if (job.status === "queued" || job.status === "retry_wait") return this.change(id, "cancelled", "Cancelled before dispatch");
    if (job.status === "cancelling") return job;
    if (!activeStates.includes(job.status)) return job;
    const next = this.change(id, "cancelling", "Cancellation requested");
    if (this.active?.jobId === id) this.abort(this.active);
    return next;
  }
  private abort(active: Active): void {
    active.abort.abort();
    if (active.child?.connected) active.child.send({ type: "abort" }, () => {});
    if (!active.killTimer) active.killTimer = setTimeout(() => active.child?.kill("SIGKILL"), 5000);
  }
  private async run(active: Active): Promise<void> {
    let failure: string | undefined;
    let result: string | undefined;
    let fixture: string | undefined;
    let readGithub = false;
    try {
      let job = this.store.get(active.jobId);
      if (job.task.kind === "resolve_conflict") {
        const created = await createFixture(this.directory); fixture = created.path;
        if (active.abort.signal.aborted) throw new Error("Operation aborted");
        job = this.change(job.id, "conflicted", created.conflict, { fixture });
      }
      active.abort.signal.throwIfAborted();
      const child = fork(this.options.workerPath ?? fileURLToPath(new URL("./worker.js", import.meta.url)), [], { stdio: ["ignore", "ignore", "pipe", "ipc"], env: { ...process.env, ...this.options.workerEnv }, execArgv: [] });
      active.child = child;
      let done = false;
      const pendingTools = new Set<Promise<void>>();
      let outputBytes = 0;
      const deadline = setTimeout(() => { failure = "Attempt deadline exceeded"; this.abort(active); }, 180000);
      const exit = new Promise<void>((resolve, reject) => { child.once("error", reject); child.once("exit", (code, signal) => { active.childExited = true; if (!done && !active.abort.signal.aborted) failure = `Worker exited before completion (${signal ?? code})`; resolve(); }); });
      child.stderr?.on("data", () => { /* WHY: SDK diagnostics can contain provider responses; the structured failure channel is authoritative. */ });
      child.on("message", (message: unknown) => {
        if (!message || typeof message !== "object") return;
        const m = message as Record<string, any>;
        if (m.attempt !== active.attempt || this.active !== active) return;
        if (m.type === "progress" && typeof m.text === "string" && outputBytes < 32000) {
          const text = cleanText(m.text, Math.min(2000, 32000 - outputBytes)); outputBytes += text.length;
          this.store.event(job.id, "progress", text); this.notify();
        } else if (m.type === "done" && typeof m.text === "string" && !done) { done = true; result = cleanText(m.text); }
        else if (m.type === "failure" && typeof m.error === "string" && !done) { done = true; failure = cleanText(m.error, 2000); }
        else if (m.type === "tool" && typeof m.id === "string" && typeof m.name === "string") {
          const work = (async () => {
            try {
              if (active.abort.signal.aborted || this.store.get(job.id).status === "cancelling") throw new Error("Job cancelled");
              let response: unknown;
              if (job.task.kind === "summarize_pr" && m.name === "read_pull_request") { response = await readPullRequest(job.task.url, active.abort.signal); readGithub = true; }
              else if (fixture && job.task.kind === "resolve_conflict") {
                if (m.name === "read_conflict") response = await readConflict(fixture);
                else if (m.name === "write_resolution") response = await writeResolution(fixture, m.args?.policy);
                else if (m.name === "validate_resolution") response = await validateResolution(fixture);
                else throw new Error("Tool not allowed for this job");
              } else throw new Error("Tool not allowed for this job");
              this.store.event(job.id, "tool", m.name); this.notify();
              if (child.connected) child.send({ type: "tool_result", id: m.id, result: response }, () => {});
            } catch (error) { if (child.connected) child.send({ type: "tool_result", id: m.id, error: errorText(error) }, () => {}); }
          })();
          pendingTools.add(work); void work.finally(() => pendingTools.delete(work));
        }
      });
      // WHY: A child cannot begin model/tool work until its PID is durable for crash recovery.
      job = this.store.get(job.id);
      job.attempts[job.attempts.length - 1]!.pid = child.pid;
      this.store.save(job, "worker_started", `Attempt ${active.attempt}`);
      if (job.status === "conflicted") job = this.change(job.id, "resolving", "Pi is resolving the conflict");
      child.send({ type: "start", attempt: active.attempt, task: job.task, model: this.options.model ?? "gpt-6.1-terra" }, () => {});
      try { await exit; await Promise.all(pendingTools); } finally { clearTimeout(deadline); }
      if (!active.abort.signal.aborted && !failure) {
        if (!done || !result?.trim()) throw new Error("Worker returned no result");
        if (fixture) result = `${result}\n\n${await finishFixture(fixture, active.abort.signal)}`;
        else if (!readGithub) throw new Error("Worker did not read the requested PR");
      }
    } catch (error) { failure = errorText(error); }
    finally {
      const job = this.store.get(active.jobId);
      const attempts = job.attempts.map((a, i) => i === job.attempts.length - 1 ? { ...a, endedAt: this.now(), ...(active.childExited ? { exitObservedAt: this.now() } : {}), ...(failure ? { error: failure } : {}) } : a);
      if (job.status === "cancelling") this.change(job.id, "cancelled", "Worker exited", { attempts });
      else if (this.stopping) this.change(job.id, "interrupted", "Coordinator shutdown", { attempts, error: "Interrupted during shutdown" });
      else if (failure || active.abort.signal.aborted) {
        const error = failure ?? "Attempt aborted";
        const delay = transient(error) ? retryDelay(job.retryCount) : undefined;
        if (delay !== undefined) this.change(job.id, "retry_wait", error, { attempts, error, retryCount: job.retryCount + 1, availableAt: this.now() + delay });
        else this.change(job.id, "failed", error, { attempts, error });
      } else this.change(job.id, "succeeded", "Job completed", { attempts, result });
      if (fixture) await removeFixture(this.directory, fixture).catch(() => {});
    }
  }
  close(): Promise<void> {
    if (this.closePromise) return this.closePromise;
    this.closePromise = (async () => {
      this.stopping = true; if (this.timer) clearInterval(this.timer); this.notify();
      if (this.active) { this.abort(this.active); await this.active.exited; }
      for (const socket of this.sockets) socket.destroy();
      if (this.server?.listening) await new Promise<void>(resolve => this.server!.close(() => resolve()));
      if (existsSync(this.socketPath)) unlinkSync(this.socketPath);
      this.finalSnapshot = { ...this.snapshot(), scheduler: "stopped" };
      this.stopped = true; this.store.close();
    })();
    return this.closePromise;
  }
}
