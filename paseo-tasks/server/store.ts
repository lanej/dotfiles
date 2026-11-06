import { DatabaseSync } from "node:sqlite";
import { mkdirSync, chmodSync } from "node:fs";
import { dirname } from "node:path";
import { randomUUID } from "node:crypto";
import { task, event, ready, type Brief, type Task, type TaskEvent, type Update } from "../shared/contracts";

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
    initial: Partial<Pick<Task, "migration" | "github" | "nextAction">> = {}): Task {
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
      task.parse(value);
      this.db.prepare("UPDATE tasks SET revision=?,record=? WHERE id=?")
        .run(value.revision, JSON.stringify(value), id);
      return value;
    });
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
