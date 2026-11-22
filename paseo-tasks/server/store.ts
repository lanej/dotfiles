import { AsyncLocalStorage } from "node:async_hooks";
import { createHash, randomUUID } from "node:crypto";
import { chmodSync, existsSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";
import { DatabaseSync } from "node:sqlite";
import { type Beads, beadId, taskContent } from "./beads";
import {
  brief,
  type Brief,
  event,
  type IncomingReport,
  incomingReport,
  type OutgoingReport,
  outgoingReport,
  ready,
  type Task,
  type TaskEvent,
  task,
  type Update,
} from "../shared/contracts";
export const briefFingerprint = (value: Task): string =>
  createHash("sha256")
    .update(JSON.stringify(brief.strip().parse(value)))
    .digest("hex");

function workerTaskId(db: DatabaseSync, agentId: string): string | undefined {
  return db
    .prepare(
      "SELECT id FROM tasks WHERE json_extract(record,'$.worker.agentId')=?",
    )
    .get(agentId)?.id as string | undefined;
}

export class Store {
  static hasWorker(file: string, agentId: string): boolean {
    if (!existsSync(file)) return false;
    const db = new DatabaseSync(file, { readOnly: true });
    try {
      return workerTaskId(db, agentId) !== undefined;
    } finally {
      db.close();
    }
  }
  readonly db: DatabaseSync;
  private readonly context = new AsyncLocalStorage<boolean>();
  private tail: Promise<unknown> = Promise.resolve();
  constructor(
    readonly file: string,
    readonly serverId: string,
    readonly now = () => new Date().toISOString(),
    readonly beads: Beads | null = null,
  ) {
    mkdirSync(dirname(file), { recursive: true, mode: 0o700 });
    this.db = new DatabaseSync(file);
    chmodSync(file, 0o600);
    this.db.exec(`
      PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; PRAGMA busy_timeout=5000;
      CREATE TABLE IF NOT EXISTS identity (id INTEGER PRIMARY KEY CHECK(id=1), server TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, revision INTEGER NOT NULL, record TEXT NOT NULL);
      CREATE UNIQUE INDEX IF NOT EXISTS worker_owner ON tasks(json_extract(record,'$.worker.agentId'))
        WHERE json_extract(record,'$.worker.agentId') IS NOT NULL;
      CREATE TABLE IF NOT EXISTS beads_authority (id INTEGER PRIMARY KEY CHECK(id=1), project TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS beads_tasks (id TEXT PRIMARY KEY, bead TEXT NOT NULL UNIQUE);
      CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, task TEXT NOT NULL, record TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS objects (url TEXT PRIMARY KEY, record TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS replies (event TEXT PRIMARY KEY, record TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS cache (host TEXT PRIMARY KEY, record TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS report_outbox (id TEXT PRIMARY KEY, record TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS report_inbox (id TEXT PRIMARY KEY, record TEXT NOT NULL);
    `);
    this.db
      .prepare("INSERT OR IGNORE INTO identity VALUES (1,?)")
      .run(serverId);
    if (
      (
        this.db.prepare("SELECT server FROM identity").get() as {
          server: string;
        }
      ).server !== serverId
    ) {
      this.close();
      throw new Error(
        "Task database belongs to another host; preserve it and reconcile the host identity",
      );
    }
    if (beads) {
      const pin = this.db
        .prepare("SELECT project FROM beads_authority WHERE id=1")
        .get();
      const total = Number(
        this.db.prepare("SELECT COUNT(*) AS n FROM tasks").get()!.n,
      );
      const enrolled = Number(
        this.db.prepare("SELECT COUNT(*) AS n FROM beads_tasks").get()!.n,
      );
      if (
        (pin && pin.project !== beads.authority) ||
        (!pin && total > 0) ||
        total !== enrolled
      ) {
        this.close();
        throw new Error(
          "Existing local tasks belong to another or unrecorded authority; preserve them and reconcile explicitly. No automatic migration is supported.",
        );
      }
      this.db
        .prepare("INSERT OR IGNORE INTO beads_authority VALUES (1,?)")
        .run(beads.authority);
    }
    // WHY: A crashed sender cannot establish whether the receiver accepted its input.
    for (const table of ["events", "report_outbox", "report_inbox"]) {
      for (const row of this.db
        .prepare(`SELECT rowid,record FROM ${table}`)
        .all()) {
        const parser =
          table === "events"
            ? event
            : table === "report_outbox"
              ? outgoingReport
              : incomingReport;
        const value = parser.parse(JSON.parse(row.record as string));
        if (value.delivery === "sending") {
          value.delivery = "unknown";
          this.db
            .prepare(`UPDATE ${table} SET record=? WHERE rowid=?`)
            .run(JSON.stringify(value), row.rowid);
          if (table === "report_outbox" && "report" in value) {
            const saved = this.db
              .prepare("SELECT record FROM tasks WHERE id=?")
              .get(value.report.task.taskId);
            if (saved) {
              const current = task.parse(JSON.parse(saved.record as string));
              if (current.coordinatorReport?.id === value.report.id) {
                current.coordinatorReport = {
                  id: value.report.id,
                  delivery: "unknown",
                  error: value.error,
                };
                this.db
                  .prepare("UPDATE tasks SET record=? WHERE id=?")
                  .run(JSON.stringify(current), current.taskId);
              }
            }
          }
        }
      }
    }
  }
  close() {
    this.db.close();
  }
  async transaction<T>(fn: () => T | Promise<T>): Promise<T> {
    if (this.context.getStore()) return fn();
    const previous = this.tail;
    const result = previous
      .catch(() => {})
      .then(() =>
        this.context.run(true, async () => {
          this.db.exec("BEGIN IMMEDIATE");
          try {
            const value = await fn();
            this.db.exec("COMMIT");
            return value;
          } catch (error) {
            this.db.exec("ROLLBACK");
            throw error;
          }
        }),
      );
    this.tail = result;
    return result;
  }
  async list(): Promise<Task[]> {
    return await this.transaction(async () => {
      const records = this.db
        .prepare(
          "SELECT record FROM tasks ORDER BY json_extract(record,'$.priority') DESC",
        )
        .all();
      const values: Task[] = [];
      for (const row of records)
        values.push(
          await this.project(task.parse(JSON.parse(row.record as string))),
        );
      return values.sort((a, b) => b.priority - a.priority);
    });
  }
  async ids(): Promise<string[]> {
    return await this.transaction(() =>
      this.db
        .prepare("SELECT id FROM tasks")
        .all()
        .map((row) => row.id as string),
    );
  }
  async find(id: string): Promise<Task | undefined> {
    return await this.transaction(async () => {
      const row = this.db
        .prepare("SELECT record FROM tasks WHERE id=?")
        .get(id);
      return row
        ? await this.project(task.parse(JSON.parse(row.record as string)))
        : undefined;
    });
  }
  async get(id: string): Promise<Task> {
    const value = await this.find(id);
    if (!value) throw new Error(`Unknown task ${id}`);
    return value;
  }
  hasWorker(agentId: string): boolean {
    return workerTaskId(this.db, agentId) !== undefined;
  }
  private async enrolled(id: string): Promise<boolean> {
    return await this.transaction(async () => {
      return !!this.db.prepare("SELECT id FROM beads_tasks WHERE id=?").get(id);
    });
  }
  private async project(value: Task): Promise<Task> {
    return await this.transaction(async () => {
      if (!(await this.enrolled(value.taskId))) return value;
      if (!this.beads)
        throw new Error(
          "Beads authority unavailable for enrolled task; refusing stale SQLite content",
        );
      const observed = await this.beads.read(value);
      if (JSON.stringify(taskContent(value)) === JSON.stringify(observed))
        return value;
      const apply = async () => {
        Object.assign(value, observed);
        value.revision++;
        value.updatedAt = this.now();
        await this.queueCoordinatorReport(value);
        this.db
          .prepare("UPDATE tasks SET revision=?,record=? WHERE id=?")
          .run(value.revision, JSON.stringify(task.parse(value)), value.taskId);
        return value;
      };
      return this.db.isTransaction
        ? await apply()
        : await this.transaction(apply);
    });
  }
  async assertOwner(id: string, agentId?: string) {
    return await this.transaction(async () => {
      if (agentId !== undefined && workerTaskId(this.db, agentId) !== id)
        throw new Error("This conversation is not bound to the requested task");
      if (await this.enrolled(id)) {
        if (!this.beads) throw new Error("Beads authority unavailable");
        const worker = agentId ?? (await this.get(id)).worker?.agentId;
        if (worker)
          await this.beads.assertOwner(
            { serverId: this.serverId, taskId: id },
            worker,
          );
      } else if (agentId !== undefined)
        throw new Error("Worker turns require an enrolled Beads task");
    });
  }
  async claim(id: string, worker: string) {
    return await this.transaction(async () => {
      const value = await this.get(id);
      if (await this.enrolled(id)) {
        if (!this.beads) throw new Error("Beads authority unavailable");
        await this.beads.claim(value, worker);
      }
    });
  }
  async forAgent(agentId: string): Promise<Task | undefined> {
    return await this.transaction(async () => {
      const id = workerTaskId(this.db, agentId);
      return id === undefined ? undefined : await this.get(id);
    });
  }
  async create(
    value: Brief,
    group: string | null = null,
    id: string = randomUUID(),
    control: Task["control"] = "running",
    initial: Partial<
      Pick<Task, "migration" | "github" | "nextAction" | "coordinator">
    > = {},
  ): Promise<Task> {
    return await this.transaction(async () => {
      if (!this.db.isTransaction)
        return await this.transaction(
          async () => await this.create(value, group, id, control, initial),
        );
      const at = this.now();
      const record = task.parse({
        ...value,
        serverId: this.serverId,
        taskId: id,
        revision: 1,
        status: ready(value, !!initial.migration) ? "active" : "draft",
        control,
        priority: 50,
        group,
        worker: null,
        activity: "unknown",
        approach: "",
        progress: "",
        evidence: [],
        blocker: null,
        nextAction: ready(value)
          ? "Start worker"
          : "Clarify outcome and success criteria",
        github: [],
        proposals: [],
        launch: "none",
        createdAt: at,
        updatedAt: at,
        observedAt: null,
        error: null,
        migration: null,
        ...initial,
      });
      if (this.beads) await this.beads.create(record);
      this.db
        .prepare("INSERT INTO tasks VALUES (?,?,?)")
        .run(id, 1, JSON.stringify(record));
      if (this.beads)
        this.db
          .prepare("INSERT INTO beads_tasks VALUES (?,?)")
          .run(id, beadId(id));
      return record;
    });
  }
  async change(
    id: string,
    fn: (value: Task) => void | Promise<void>,
    revision?: number,
    options: {
      notifyCoordinator?: boolean;
    } = {},
  ): Promise<Task> {
    return await this.transaction(async () => {
      return await this.transaction(async () => {
        const value = await this.get(id);
        if (revision !== undefined && revision !== value.revision)
          throw new Error(
            "Task changed; refresh before applying this instruction",
          );
        const before = structuredClone(value);
        await fn(value);
        task.parse(value);
        if (await this.enrolled(id))
          Object.assign(value, await this.beads!.update(before, value));
        value.revision++;
        value.updatedAt = this.now();
        await this.queueCoordinatorReport(
          value,
          options.notifyCoordinator === false,
        );
        task.parse(value);
        this.db
          .prepare("UPDATE tasks SET revision=?,record=? WHERE id=?")
          .run(value.revision, JSON.stringify(value), id);
        return value;
      });
    });
  }
  private async queueCoordinatorReport(value: Task, silent = false) {
    return await this.transaction(async () => {
      const key = `coordinator-report:${value.taskId}`;
      const reportable =
        value.worker &&
        value.coordinator &&
        value.migration?.ownership !== "firstmate" &&
        (["complete", "decision", "question", "blocked"].includes(
          value.status,
        ) ||
          value.activity === "failed");
      if (!reportable) {
        value.coordinatorReport = null;
        await this.write("cache", key, null);
        for (const entry of (await this.outgoingReports()).filter(
          (entry) =>
            entry.report.task.taskId === value.taskId &&
            entry.delivery === "queued",
        )) {
          this.db
            .prepare("UPDATE report_outbox SET record=? WHERE id=?")
            .run(
              JSON.stringify({ ...entry, delivery: "superseded" }),
              entry.report.id,
            );
        }
        return;
      }
      const signature = createHash("sha256")
        .update(
          JSON.stringify({
            coordinator: value.coordinator,
            status: value.status,
            failed: value.activity === "failed",
            brief: [
              value.title,
              value.outcome,
              value.successCriteria,
              value.constraints,
            ],
            progress: value.progress,
            evidence: value.evidence,
            blocker: value.blocker,
            error: value.error,
            next: value.nextAction,
            github: value.github,
            worker: value.worker,
          }),
        )
        .digest("hex");
      if ((await this.read<string>("cache", key)) === signature) return;
      // WHY: Coalesce unsent intermediate updates; confirmed or uncertain deliveries retain their own evidence.
      for (const entry of (await this.outgoingReports()).filter(
        (entry) =>
          entry.report.task.taskId === value.taskId &&
          entry.delivery === "queued",
      )) {
        this.db
          .prepare("UPDATE report_outbox SET record=? WHERE id=?")
          .run(
            JSON.stringify({ ...entry, delivery: "superseded" }),
            entry.report.id,
          );
      }
      if (silent) {
        // WHY: Routine program progress must not wake a coordinator on the next passive task observation.
        value.coordinatorReport = null;
        await this.write("cache", key, signature);
        return;
      }
      const id = randomUUID();
      value.coordinatorReport = { id, delivery: "queued", error: null };
      const entry = outgoingReport.parse({
        report: {
          id,
          coordinator: value.coordinator,
          task: value,
          createdAt: this.now(),
        },
        delivery: "queued",
        error: null,
      });
      this.db
        .prepare("INSERT INTO report_outbox VALUES (?,?)")
        .run(id, JSON.stringify(entry));
      await this.write("cache", key, signature);
    });
  }
  async outgoingReports(): Promise<OutgoingReport[]> {
    return await this.transaction(async () => {
      return this.db
        .prepare("SELECT record FROM report_outbox ORDER BY rowid")
        .all()
        .map((row) => outgoingReport.parse(JSON.parse(row.record as string)));
    });
  }
  async incomingReports(): Promise<IncomingReport[]> {
    return await this.transaction(async () => {
      return this.db
        .prepare("SELECT record FROM report_inbox ORDER BY rowid")
        .all()
        .map((row) => incomingReport.parse(JSON.parse(row.record as string)));
    });
  }
  async reportDiagnostics() {
    return await this.transaction(async () => {
      return this.db
        .prepare(
          "SELECT host,record FROM cache WHERE host='report-directory' OR host LIKE 'report-source:%'",
        )
        .all()
        .map((row) => ({
          source: row.host,
          ...JSON.parse(row.record as string),
        }));
    });
  }
  async saveOutgoingReport(entry: OutgoingReport) {
    return await this.transaction(async () => {
      outgoingReport.parse(entry);
      const save = async () => {
        const existing = (await this.outgoingReports()).find(
          (value) => value.report.id === entry.report.id,
        );
        if (!existing) throw new Error("Unknown outgoing report");
        if (JSON.stringify(existing.report) !== JSON.stringify(entry.report))
          throw new Error("Report identity belongs to another snapshot");
        if (
          ["received", "superseded"].includes(existing.delivery) &&
          entry.delivery !== existing.delivery
        )
          return;
        this.db
          .prepare("UPDATE report_outbox SET record=? WHERE id=?")
          .run(JSON.stringify(entry), entry.report.id);
        const value = await this.get(entry.report.task.taskId);
        if (value.coordinatorReport?.id === entry.report.id) {
          value.coordinatorReport = {
            id: entry.report.id,
            delivery: entry.delivery,
            error: entry.error,
          };
          this.db
            .prepare("UPDATE tasks SET record=? WHERE id=?")
            .run(JSON.stringify(task.parse(value)), value.taskId);
        }
      };
      if (this.db.isTransaction) await save();
      else await this.transaction(save);
    });
  }
  async saveIncomingReport(entry: IncomingReport) {
    return await this.transaction(async () => {
      incomingReport.parse(entry);
      const existing = (await this.incomingReports()).find(
        (value) => value.report.id === entry.report.id,
      );
      if (
        existing &&
        JSON.stringify(existing.report) !== JSON.stringify(entry.report)
      )
        throw new Error("Report identity belongs to another snapshot");
      if (
        existing &&
        ["accepted", "superseded"].includes(existing.delivery) &&
        entry.delivery !== existing.delivery
      )
        return;
      this.db
        .prepare(
          "INSERT INTO report_inbox VALUES (?,?) ON CONFLICT(id) DO UPDATE SET record=excluded.record",
        )
        .run(entry.report.id, JSON.stringify(entry));
    });
  }
  async workerUpdate(
    id: string,
    agentId: string,
    patch: Update,
    evaluatedBrief?: string,
  ): Promise<Task> {
    return await this.transaction(async () => {
      await this.assertOwner(id);
      const enrolled = await this.enrolled(id);
      return await this.change(id, async (value) => {
        if (value.worker?.agentId !== agentId)
          throw new Error("Worker is not assigned to this task");
        if (value.control === "archived") throw new Error("Task is archived");
        if (patch.status === "complete" && enrolled) {
          if (evaluatedBrief !== briefFingerprint(value))
            throw new Error(
              "Completion requires the current brief fingerprint from task_context; review the latest brief and verify its success criteria",
            );
          if (!patch.evidence?.length)
            throw new Error("Submit evidence for the brief you evaluated");
        }
        if (
          patch.status === "complete" &&
          !(patch.evidence?.length || value.evidence.length)
        ) {
          throw new Error(
            "Completion requires evidence of the success criteria",
          );
        }
        if (
          patch.status === "complete" &&
          (await this.events(id)).some(
            (entry) =>
              entry.delivery !== "handled" &&
              (entry.kind === "feedback" ||
                (entry.kind === "github" && entry.payload.type !== "state")),
          )
        ) {
          throw new Error(
            "Completion requires handling pending assigned feedback; inspect task_inbox and acknowledge it first",
          );
        }
        Object.assign(value, patch);
      });
    });
  }
  async bind(
    id: string,
    agentId: string,
    workspaceId: string,
    cwd: string,
  ): Promise<Task> {
    return await this.transaction(async () => {
      const existing = await this.get(id);
      if (existing.worker && existing.worker.agentId !== agentId)
        throw new Error("Task already has a primary conversation");
      if (!existing.worker) {
        if (existing.status === "draft" && ready(existing, true))
          await this.change(id, (value) => {
            value.status = "active";
          });
        await this.claim(id, agentId);
      }
      await this.assertOwner(id);
      return await this.change(id, (value) => {
        if (value.worker && value.worker.agentId !== agentId)
          throw new Error("Task already has a primary conversation");
        value.worker = { agentId, workspaceId, cwd };
        value.launch = "bound";
        if (value.status === "draft" && ready(value, true)) {
          value.status = "active";
          value.nextAction = "Continue on the retained checkout";
        }
        if (value.migration?.ownership === "released")
          value.migration.ownership = "tasks";
      });
    });
  }
  async addEvent(
    id: string,
    kind: TaskEvent["kind"],
    body: string,
    options: {
      id?: string;
      source?: string;
      payload?: Record<string, unknown>;
    } = {},
  ): Promise<TaskEvent> {
    return await this.transaction(async () => {
      const insert = async () => {
        const value = await this.get(id);
        const record = event.parse({
          id: options.id ?? randomUUID(),
          taskId: id,
          kind,
          body,
          source: options.source ?? null,
          payload: options.payload ?? {},
          delivery: "queued",
          createdAt: this.now(),
          receipt: null,
        });
        const added = this.db
          .prepare("INSERT OR IGNORE INTO events VALUES (?,?,?)")
          .run(record.id, id, JSON.stringify(record)).changes;
        // WHY: New assigned input reopens completed work; repeated input and state observations grant no new work.
        if (
          added &&
          ["complete", "decision"].includes(value.status) &&
          value.worker &&
          !["archived", "archiving"].includes(value.control) &&
          value.migration?.ownership !== "firstmate" &&
          (kind === "feedback" ||
            (kind === "github" && record.payload.type !== "state"))
        ) {
          const before = structuredClone(value);
          value.status = "active";
          value.nextAction =
            "Handle newly assigned feedback within the existing task brief";
          if (await this.enrolled(id))
            Object.assign(value, await this.beads!.update(before, value));
          value.revision++;
          value.updatedAt = this.now();
          await this.queueCoordinatorReport(value);
          task.parse(value);
          this.db
            .prepare("UPDATE tasks SET revision=?,record=? WHERE id=?")
            .run(value.revision, JSON.stringify(value), id);
        }
        const saved = (await this.events(id)).find(
          (value) => value.id === record.id,
        );
        if (!saved) throw new Error("Event identity belongs to another task");
        return saved;
      };
      return this.db.isTransaction
        ? await insert()
        : await this.transaction(insert);
    });
  }
  async events(id: string): Promise<TaskEvent[]> {
    return await this.transaction(async () => {
      return this.db
        .prepare("SELECT record FROM events WHERE task=? ORDER BY rowid")
        .all(id)
        .map((row) => event.parse(JSON.parse(row.record as string)));
    });
  }
  async saveEvent(value: TaskEvent) {
    return await this.transaction(async () => {
      event.parse(value);
      // WHY: A delayed send receipt cannot reopen feedback the worker already handled.
      this.db
        .prepare(
          "UPDATE events SET record=? WHERE id=? AND (json_extract(record,'$.delivery')!='handled' OR ?='handled')",
        )
        .run(JSON.stringify(value), value.id, value.delivery);
    });
  }
  async read<T>(
    table: "objects" | "replies" | "cache",
    id: string,
  ): Promise<T | null> {
    return await this.transaction(async () => {
      const key = { objects: "url", replies: "event", cache: "host" }[table];
      const row = this.db
        .prepare(`SELECT record FROM ${table} WHERE ${key}=?`)
        .get(id);
      return row ? JSON.parse(row.record as string) : null;
    });
  }
  async write(
    table: "objects" | "replies" | "cache",
    id: string,
    value: unknown,
  ) {
    return await this.transaction(async () => {
      this.db
        .prepare(`INSERT OR REPLACE INTO ${table} VALUES (?,?)`)
        .run(id, JSON.stringify(value));
    });
  }
  async claimReply(id: string, value: unknown): Promise<boolean> {
    return await this.transaction(async () => {
      return (
        this.db
          .prepare("INSERT OR IGNORE INTO replies VALUES (?,?)")
          .run(id, JSON.stringify(value)).changes === 1
      );
    });
  }
}
