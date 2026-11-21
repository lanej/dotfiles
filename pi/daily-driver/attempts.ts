import {
  worktreeAllocation,
  worktreeReservation,
} from "@lanej/task-runtime/worktree-contracts";
import { mkdirSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";
import { DatabaseSync } from "node:sqlite";
import { z } from "zod";
import { configSchema, driverProfileSchema, selection } from "./config.ts";
import { leadPlanSchema } from "./lead-plan.ts";
import { beadSchema, verificationSchema } from "./task-service.ts";

export enum Phase {
  Admitting = "admitting",
  Allocating = "allocating",
  Launching = "launching",
  Running = "running",
  Checking = "checking",
  Verified = "verified",
  CheckFailed = "check_failed",
  NeedsReview = "needs_review",
  Closed = "closed",
  Reconcile = "reconcile",
  Rejected = "rejected",
}

export const attemptSchema = z.object({
  id: z.uuid(),
  source: configSchema.shape.beadsService.unwrap(),
  bead: beadSchema,
  revision: z.string().nullable(),
  check: z.array(z.string()),
  profile: driverProfileSchema,
  model: selection,
  live: z.boolean(),
  leadPlan: leadPlanSchema.optional(),
  processStarted: z.string().nullable(),
  reservation: worktreeReservation,
  checkout: worktreeAllocation.nullable(),
  session: z.string().min(1),
  zellijSocket: z.string().min(1).optional(),
  pane: z.number().int().nonnegative().nullable(),
  pid: z.number().int().positive().nullable(),
  transcript: z.string().nullable(),
  phase: z.enum(Phase),
  verification: verificationSchema.nullable(),
  message: z.string(),
});
export type Attempt = z.infer<typeof attemptSchema>;
const row = z.object({ record: z.string() });
const decode = (value: unknown): Attempt =>
  attemptSchema.parse(JSON.parse(row.parse(value).record));

export function stateDirectory(): string {
  return resolve(
    process.env["PI_DRIVER_STATE_DIR"] ??
      join(
        process.env["XDG_STATE_HOME"] ?? join(homedir(), ".local", "state"),
        "pi-driver",
      ),
  );
}

/** Each transaction records one local transition; external operations run after the transaction commits. */
export class Attempts {
  private readonly db: DatabaseSync;
  constructor(
    readonly directory: string,
    readOnly = false,
  ) {
    if (!readOnly) mkdirSync(directory, { recursive: true, mode: 0o700 });
    this.db = new DatabaseSync(join(directory, "attempts.sqlite"), {
      readOnly,
    });
    this.db.exec("PRAGMA busy_timeout=5000");
    if (!readOnly)
      this.db
        .exec(`CREATE TABLE IF NOT EXISTS attempts (id TEXT PRIMARY KEY, project TEXT NOT NULL, bead TEXT NOT NULL, active INTEGER NOT NULL, record TEXT NOT NULL);
      CREATE UNIQUE INDEX IF NOT EXISTS active_attempt ON attempts(project,bead) WHERE active=1;`);
  }
  close(): void {
    this.db.close();
  }
  get(id: string): Attempt {
    return decode(
      this.db.prepare("SELECT record FROM attempts WHERE id=?").get(id),
    );
  }
  latest(project: string, bead: string): Attempt | null {
    const raw = this.db
      .prepare(
        "SELECT record FROM attempts WHERE project=? AND bead=? ORDER BY active DESC,rowid DESC LIMIT 1",
      )
      .get(project, bead);
    return raw === undefined ? null : decode(raw);
  }
  reserve(attempt: Attempt): boolean {
    const result = this.db
      .prepare(
        "INSERT OR IGNORE INTO attempts(id,project,bead,active,record) VALUES(?,?,?,1,?)",
      )
      .run(
        attempt.id,
        attempt.source.projectId,
        attempt.bead.id,
        JSON.stringify(attempt),
      );
    return Number(result.changes) === 1;
  }
  change(id: string, update: (record: Attempt) => void): Attempt {
    this.db.exec("BEGIN IMMEDIATE");
    try {
      const current = this.get(id);
      update(current);
      const active =
        current.phase !== Phase.Closed && current.phase !== Phase.Rejected;
      this.db
        .prepare("UPDATE attempts SET record=?,active=? WHERE id=?")
        .run(JSON.stringify(current), Number(active), id);
      this.db.exec("COMMIT");
      return current;
    } catch (cause) {
      this.db.exec("ROLLBACK");
      throw cause;
    }
  }
}
