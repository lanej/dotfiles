import { DatabaseSync } from "node:sqlite";
import { mkdirSync, chmodSync } from "node:fs";
import { dirname } from "node:path";
import { createHash, randomUUID } from "node:crypto";
import {
  task, event, ready, outgoingReport, incomingReport,
  type Brief, type Task, type TaskEvent, type Update, type OutgoingReport, type IncomingReport,
} from "../shared/contracts";

export class Store {
  readonly db: DatabaseSync;
  constructor(file: string, readonly serverId: string, readonly now = () => new Date().toISOString()) {
    mkdirSync(dirname(file), { recursive: true, mode: 0o700 });
    this.db = new DatabaseSync(file);
    chmodSync(file, 0o600);
    this.db.exec(`
      PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; PRAGMA busy_timeout=5000;
      CREATE TABLE IF NOT EXISTS identity (id INTEGER PRIMARY KEY CHECK(id=1), server TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, revision INTEGER NOT NULL, record TEXT NOT NULL);
      CREATE UNIQUE INDEX IF NOT EXISTS worker_owner ON tasks(json_extract(record,'$.worker.agentId'))
        WHERE json_extract(record,'$.worker.agentId') IS NOT NULL;
      CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, task TEXT NOT NULL, record TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS objects (url TEXT PRIMARY KEY, record TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS replies (event TEXT PRIMARY KEY, record TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS cache (host TEXT PRIMARY KEY, record TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS report_outbox (id TEXT PRIMARY KEY, record TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS report_inbox (id TEXT PRIMARY KEY, record TEXT NOT NULL);
    `);
    this.db.prepare("INSERT OR IGNORE INTO identity VALUES (1,?)").run(serverId);
    if ((this.db.prepare("SELECT server FROM identity").get() as { server: string }).server !== serverId) {
      this.close();
      throw new Error("Task database belongs to another host; preserve it and reconcile the host identity");
    }
    // WHY: A crashed sender cannot establish whether Paseo accepted its prompt.
    for (const row of this.db.prepare("SELECT record FROM events").all()) {
      const value = event.parse(JSON.parse(row.record as string));
      if (value.delivery === "sending") this.saveEvent({ ...value, delivery: "unknown" });
    }
    for (const record of this.outgoingReports()) {
      if (record.delivery === "sending") this.saveOutgoingReport({ ...record, delivery: "unknown" });
    }
    for (const record of this.incomingReports()) {
      if (record.delivery === "sending") this.saveIncomingReport({ ...record, delivery: "unknown" });
    }
  }
  close() { this.db.close(); }
  transaction<T>(fn: () => T): T {
    this.db.exec("BEGIN IMMEDIATE");
    try { const result = fn(); this.db.exec("COMMIT"); return result; }
    catch (error) { this.db.exec("ROLLBACK"); throw error; }
  }
  list(): Task[] {
    return this.db.prepare("SELECT record FROM tasks ORDER BY json_extract(record,'$.priority') DESC").all()
      .map(row => task.parse(JSON.parse(row.record as string)));
  }
  get(id: string): Task {
    const row = this.db.prepare("SELECT record FROM tasks WHERE id=?").get(id);
    if (!row) throw new Error(`Unknown task ${id}`);
    return task.parse(JSON.parse(row.record as string));
  }
  forAgent(agentId: string): Task | undefined { return this.list().find(value => value.worker?.agentId === agentId); }
  create(value: Brief, group: string | null = null, id: string = randomUUID(), control: Task["control"] = "running",
    initial: Partial<Pick<Task, "migration" | "github" | "nextAction" | "coordinator">> = {}): Task {
    const at = this.now();
    const record = task.parse({ ...value, serverId: this.serverId, taskId: id, revision: 1,
      status: ready(value, !!initial.migration) ? "active" : "draft", control, priority: 50, group,
      worker: null, activity: "unknown", approach: "", progress: "", evidence: [], blocker: null,
      nextAction: ready(value) ? "Start worker" : "Clarify outcome and success criteria",
      github: [], proposals: [], launch: "none", createdAt: at, updatedAt: at, observedAt: null,
      error: null, migration: null, ...initial });
    this.db.prepare("INSERT INTO tasks VALUES (?,?,?)").run(id, 1, JSON.stringify(record));
    return record;
  }
  change(id: string, fn: (value: Task) => void, revision?: number): Task {
    return this.transaction(() => {
      const value = this.get(id);
      if (revision !== undefined && revision !== value.revision) throw new Error("Task changed; refresh before applying this instruction");
      fn(value);
      value.revision++; value.updatedAt = this.now();
      this.queueCoordinatorReport(value);
      task.parse(value);
      this.db.prepare("UPDATE tasks SET revision=?,record=? WHERE id=?")
        .run(value.revision, JSON.stringify(value), id);
      return value;
    });
  }
  private queueCoordinatorReport(value: Task) {
    const key = `coordinator-report:${value.taskId}`;
    const reportable = value.worker && value.coordinator && value.migration?.ownership !== "firstmate" &&
      (["complete", "decision", "question", "blocked"].includes(value.status) || value.activity === "failed");
    if (!reportable) {
      value.coordinatorReport = null;
      this.write("cache", key, null);
      for (const entry of this.outgoingReports().filter(entry => entry.report.task.taskId === value.taskId && entry.delivery === "queued")) {
        this.db.prepare("UPDATE report_outbox SET record=? WHERE id=?")
          .run(JSON.stringify({ ...entry, delivery: "superseded" }), entry.report.id);
      }
      return;
    }
    const signature = createHash("sha256").update(JSON.stringify({
      coordinator: value.coordinator, status: value.status, failed: value.activity === "failed",
      brief: [value.title, value.outcome, value.successCriteria, value.constraints],
      progress: value.progress, evidence: value.evidence, blocker: value.blocker, error: value.error, next: value.nextAction,
      github: value.github, worker: value.worker,
    })).digest("hex");
    if (this.read<string>("cache", key) === signature) return;
    // WHY: Coalesce unsent intermediate updates; confirmed or uncertain deliveries retain their own evidence.
    for (const entry of this.outgoingReports().filter(entry => entry.report.task.taskId === value.taskId && entry.delivery === "queued")) {
      this.db.prepare("UPDATE report_outbox SET record=? WHERE id=?")
        .run(JSON.stringify({ ...entry, delivery: "superseded" }), entry.report.id);
    }
    const id = randomUUID();
    value.coordinatorReport = { id, delivery: "queued", error: null };
    const entry = outgoingReport.parse({
      report: { id, coordinator: value.coordinator, task: value, createdAt: this.now() },
      delivery: "queued", error: null,
    });
    this.db.prepare("INSERT INTO report_outbox VALUES (?,?)").run(id, JSON.stringify(entry));
    this.write("cache", key, signature);
  }
  outgoingReports(): OutgoingReport[] {
    return this.db.prepare("SELECT record FROM report_outbox ORDER BY rowid").all()
      .map(row => outgoingReport.parse(JSON.parse(row.record as string)));
  }
  incomingReports(): IncomingReport[] {
    return this.db.prepare("SELECT record FROM report_inbox ORDER BY rowid").all()
      .map(row => incomingReport.parse(JSON.parse(row.record as string)));
  }
  reportDiagnostics() {
    return this.db.prepare("SELECT host,record FROM cache WHERE host='report-directory' OR host LIKE 'report-source:%'").all()
      .map(row => ({ source: row.host, ...JSON.parse(row.record as string) }));
  }
  saveOutgoingReport(entry: OutgoingReport) {
    outgoingReport.parse(entry);
    const save = () => {
      const existing = this.outgoingReports().find(value => value.report.id === entry.report.id);
      if (!existing) throw new Error("Unknown outgoing report");
      if (JSON.stringify(existing.report) !== JSON.stringify(entry.report)) throw new Error("Report identity belongs to another snapshot");
      if (["received", "superseded"].includes(existing.delivery) && entry.delivery !== existing.delivery) return;
      this.db.prepare("UPDATE report_outbox SET record=? WHERE id=?").run(JSON.stringify(entry), entry.report.id);
      const value = this.get(entry.report.task.taskId);
      if (value.coordinatorReport?.id === entry.report.id) {
        value.coordinatorReport = { id: entry.report.id, delivery: entry.delivery, error: entry.error };
        this.db.prepare("UPDATE tasks SET record=? WHERE id=?").run(JSON.stringify(task.parse(value)), value.taskId);
      }
    };
    if (this.db.isTransaction) save(); else this.transaction(save);
  }
  saveIncomingReport(entry: IncomingReport) {
    incomingReport.parse(entry);
    const existing = this.incomingReports().find(value => value.report.id === entry.report.id);
    if (existing && JSON.stringify(existing.report) !== JSON.stringify(entry.report)) throw new Error("Report identity belongs to another snapshot");
    if (existing && ["accepted", "superseded"].includes(existing.delivery) && entry.delivery !== existing.delivery) return;
    this.db.prepare("INSERT INTO report_inbox VALUES (?,?) ON CONFLICT(id) DO UPDATE SET record=excluded.record")
      .run(entry.report.id, JSON.stringify(entry));
  }
  workerUpdate(id: string, agentId: string, patch: Update): Task {
    return this.change(id, value => {
      if (value.worker?.agentId !== agentId) throw new Error("Worker is not assigned to this task");
      if (value.control === "archived") throw new Error("Task is archived");
      if (patch.status === "complete" && !(patch.evidence?.length || value.evidence.length)) {
        throw new Error("Completion requires evidence of the success criteria");
      }
      if (patch.status === "complete" && this.events(id).some(entry => entry.delivery !== "handled" &&
        (entry.kind === "feedback" || entry.kind === "github" && entry.payload.type !== "state"))) {
        throw new Error("Completion requires handling pending assigned feedback; inspect task_inbox and acknowledge it first");
      }
      Object.assign(value, patch);
    });
  }
  bind(id: string, agentId: string, workspaceId: string, cwd: string): Task {
    return this.change(id, value => {
      if (value.worker && value.worker.agentId !== agentId) throw new Error("Task already has a primary conversation");
      value.worker = { agentId, workspaceId, cwd }; value.launch = "bound";
      if (value.status === "draft" && ready(value, true)) {
        value.status = "active"; value.nextAction = "Continue on the retained checkout";
      }
      if (value.migration?.ownership === "released") value.migration.ownership = "tasks";
    });
  }
  addEvent(id: string, kind: TaskEvent["kind"], body: string, options: {
    id?: string; source?: string; payload?: Record<string, unknown>;
  } = {}): TaskEvent {
    const insert = () => {
      const value = this.get(id);
      const record = event.parse({ id: options.id ?? randomUUID(), taskId: id, kind, body,
        source: options.source ?? null, payload: options.payload ?? {}, delivery: "queued",
        createdAt: this.now(), receipt: null });
      const added = this.db.prepare("INSERT OR IGNORE INTO events VALUES (?,?,?)").run(record.id, id, JSON.stringify(record)).changes;
      // WHY: New assigned input reopens completed work; repeated input and state observations grant no new work.
      if (added && ["complete", "decision"].includes(value.status) && value.worker && !["archived", "archiving"].includes(value.control) &&
        value.migration?.ownership !== "firstmate" && (kind === "feedback" || kind === "github" && record.payload.type !== "state")) {
        value.status = "active"; value.nextAction = "Handle newly assigned feedback within the existing task brief";
        value.revision++; value.updatedAt = this.now();
        this.queueCoordinatorReport(value);
        task.parse(value);
        this.db.prepare("UPDATE tasks SET revision=?,record=? WHERE id=?").run(value.revision, JSON.stringify(value), id);
      }
      const saved = this.events(id).find(value => value.id === record.id);
      if (!saved) throw new Error("Event identity belongs to another task");
      return saved;
    };
    return this.db.isTransaction ? insert() : this.transaction(insert);
  }
  events(id: string): TaskEvent[] {
    return this.db.prepare("SELECT record FROM events WHERE task=? ORDER BY rowid").all(id)
      .map(row => event.parse(JSON.parse(row.record as string)));
  }
  saveEvent(value: TaskEvent) {
    event.parse(value);
    // WHY: A delayed send receipt cannot reopen feedback the worker already handled.
    this.db.prepare("UPDATE events SET record=? WHERE id=? AND (json_extract(record,'$.delivery')!='handled' OR ?='handled')")
      .run(JSON.stringify(value), value.id, value.delivery);
  }
  read<T>(table: "objects" | "replies" | "cache", id: string): T | null {
    const key = { objects: "url", replies: "event", cache: "host" }[table];
    const row = this.db.prepare(`SELECT record FROM ${table} WHERE ${key}=?`).get(id);
    return row ? JSON.parse(row.record as string) : null;
  }
  write(table: "objects" | "replies" | "cache", id: string, value: unknown) {
    this.db.prepare(`INSERT OR REPLACE INTO ${table} VALUES (?,?)`).run(id, JSON.stringify(value));
  }
  claimReply(id: string, value: unknown): boolean {
    return this.db.prepare("INSERT OR IGNORE INTO replies VALUES (?,?)").run(id, JSON.stringify(value)).changes === 1;
  }
}
