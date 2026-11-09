import { DatabaseSync } from "node:sqlite";
import { chmodSync, mkdirSync, lstatSync } from "node:fs";
import { join } from "node:path";
import { randomUUID } from "node:crypto";
import { digest, type Job, type JobEvent, type Task } from "./domain.js";

export function privateDirectory(path: string): void {
  mkdirSync(path, { recursive: true, mode: 0o700 });
  if (lstatSync(path).isSymbolicLink()) throw new Error("State directory must not be a symlink");
  chmodSync(path, 0o700);
}
export class Store {
  private db: DatabaseSync;
  private ownership: DatabaseSync;
  private closed = false;
  constructor(readonly directory: string, private now: () => number = Date.now) {
    privateDirectory(directory);
    this.ownership = new DatabaseSync(join(directory, "coordinator-lock.sqlite"));
    try {
      // WHY: Simultaneous first opens can briefly hold shared locks; allow one contender to finish before rejecting ownership.
      this.ownership.exec("PRAGMA busy_timeout=250; BEGIN EXCLUSIVE");
    } catch {
      this.ownership.close();
      throw new Error("Another coordinator owns this state directory");
    }
    try {
      this.db = new DatabaseSync(join(directory, "jobs.sqlite"));
      this.db.exec("PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, request_id TEXT UNIQUE NOT NULL, data TEXT NOT NULL); CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL, at INTEGER NOT NULL, kind TEXT NOT NULL, detail TEXT NOT NULL); CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)");
      for (const name of ["coordinator-lock.sqlite", "jobs.sqlite"]) chmodSync(join(directory, name), 0o600);
    } catch (error) { this.ownership.close(); throw error; }
  }
  jobs(): Job[] { return this.db.prepare("SELECT data FROM jobs ORDER BY rowid").all().map(r => JSON.parse(r.data as string) as Job); }
  get(id: string): Job {
    const row = this.db.prepare("SELECT data FROM jobs WHERE id=?").get(id);
    if (!row) throw new Error("Job not found");
    return JSON.parse(row.data as string) as Job;
  }
  submit(task: Task, requestId: string): Job {
    if (!requestId || requestId.length > 200) throw new Error("Invalid request ID");
    const row = this.db.prepare("SELECT data FROM jobs WHERE request_id=?").get(requestId);
    if (row) {
      const existing = JSON.parse(row.data as string) as Job;
      if (existing.digest !== digest(task)) throw new Error("Request ID already used with a different task");
      return existing;
    }
    const now = this.now();
    const job: Job = { id: randomUUID(), requestId, task, digest: digest(task), status: "queued", createdAt: now, updatedAt: now, availableAt: now, attempts: [], retryCount: 0 };
    this.save(job, "queued", task.kind);
    return job;
  }
  save(job: Job, kind: string, detail = ""): void {
    this.db.exec("BEGIN IMMEDIATE");
    try {
      this.db.prepare("INSERT INTO jobs(id,request_id,data) VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data").run(job.id, job.requestId, JSON.stringify(job));
      this.db.prepare("INSERT INTO events(job_id,at,kind,detail) VALUES (?,?,?,?)").run(job.id, this.now(), kind, detail.slice(0, 16000));
      this.db.exec("COMMIT");
    } catch (error) { this.db.exec("ROLLBACK"); throw error; }
  }
  event(jobId: string, kind: string, detail: string): void {
    this.db.prepare("INSERT INTO events(job_id,at,kind,detail) VALUES (?,?,?,?)").run(jobId, this.now(), kind, detail.slice(0, 16000));
  }
  events(after = 0, jobId?: string): JobEvent[] {
    const rows = jobId
      ? this.db.prepare("SELECT * FROM events WHERE seq>? AND job_id=? ORDER BY seq LIMIT 200").all(after, jobId)
      : this.db.prepare("SELECT * FROM (SELECT * FROM events ORDER BY seq DESC LIMIT 100) ORDER BY seq").all();
    return rows.map(r => ({ seq: Number(r.seq), jobId: r.job_id as string, at: Number(r.at), kind: r.kind as string, detail: r.detail as string }));
  }
  paused(): boolean { return this.db.prepare("SELECT value FROM settings WHERE key='paused'").get()?.value === "true"; }
  setPaused(value: boolean): void { this.db.prepare("INSERT INTO settings VALUES ('paused',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value").run(String(value)); }
  close(): void { if (this.closed) return; this.closed = true; this.db.close(); this.ownership.close(); }
}
