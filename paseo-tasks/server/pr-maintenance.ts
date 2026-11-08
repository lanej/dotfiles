import { join } from "node:path";
import { digest, githubObject, type GitHubPort } from "./github";
import type { Store } from "./store";
import type { Task, TaskEvent } from "../shared/contracts";
import { readMaintenancePolicy, type RepositoryPolicy } from "./maintenance-policy";
import { GitConflictResolver, StaleRevision, type Candidate, type ConflictResolver, type RepairRequest } from "./conflict-resolver";

export type MaintenanceRecord = {
  id: string; taskId: string; url: string; head: string; base: string;
  state: "preparing" | "publishing" | "published" | "needs_agent" | "superseded";
  policyDigest: string; candidate: Candidate | null; reason: string; updatedAt: string;
  request: RepairRequest | null;
};
export interface Maintainer {
  handle(value: Task, entry: TaskEvent, idle: () => Promise<boolean>): Promise<boolean>;
  records(taskId: string): MaintenanceRecord[];
  close?(): Promise<void>;
}
const message = (error: unknown) => error instanceof Error ? error.message : String(error);

export class PRMaintenance implements Maintainer {
  private running = new Set<string>();
  readonly resolver: ConflictResolver;
  constructor(readonly store: Store, readonly github: GitHubPort, readonly root: string,
    readonly policy: (directory: string | null) => RepositoryPolicy | null =
      directory => readMaintenancePolicy(join(root, "pr-maintenance.json"), directory),
    resolver?: ConflictResolver,
  ) { this.resolver = resolver ?? new GitConflictResolver(join(root, "pr-maintenance")); }
  records(taskId: string): MaintenanceRecord[] {
    return this.store.db.prepare("SELECT record FROM cache WHERE host LIKE ? ORDER BY rowid")
      .all("pr-maintenance:" + taskId + ":%").map(row => JSON.parse(row.record as string));
  }
  private save(record: MaintenanceRecord) {
    record.updatedAt = this.store.now();
    this.store.write("cache", "pr-maintenance:" + record.taskId + ":" + record.id, record);
  }
  private handled(value: Task, entry: TaskEvent, record: MaintenanceRecord) {
    const status = this.store.get(value.taskId);
    this.store.change(value.taskId, current => {
      const source = this.store.events(value.taskId).find(event => event.id === entry.id)!;
      this.store.saveEvent({ ...source, delivery: "handled", payload: { ...source.payload, maintenance: record } });
      if (current.status === "active" && ["complete", "decision"].includes(String(entry.payload.previousStatus)) &&
        !this.store.events(value.taskId).some(event =>
        event.delivery !== "handled" && event.kind !== "continue" && event.payload.type !== "state")) {
        for (const queued of this.store.events(value.taskId).filter(event => event.kind === "continue" && event.delivery === "queued")) {
          this.store.saveEvent({ ...queued, delivery: "handled" });
        }
        current.status = "decision";
        current.nextAction = record.state === "published" ? "Program updated the PR branch; wait for checks and review" :
          "PR revisions changed; wait for a current observation";
        current.evidence = [...new Set([...current.evidence, record.url + " " + (record.candidate?.head ?? record.head)])].slice(-50);
      }
    }, undefined, { notifyCoordinator: ["question", "blocked"].includes(status.status) || status.activity === "failed" });
  }
  async handle(value: Task, entry: TaskEvent, idle: () => Promise<boolean>): Promise<boolean> {
    if (value.kind !== "coding" || !value.worker || entry.payload.type !== "repair" ||
      !(entry.payload.repair as { conflict?: boolean } | undefined)?.conflict) return false;
    const url = String(entry.payload.url);
    const target = githubObject(url);
    const head = String(entry.payload.revision), base = String(entry.payload.baseRevision);
    const id = digest([value.taskId, url, head, base]);
    if (this.running.has(id)) return true;
    this.running.add(id);
    let record = this.store.read<MaintenanceRecord>("cache", "pr-maintenance:" + value.taskId + ":" + id);
    try {
      for (const pending of this.records(value.taskId).filter(other =>
        other.url === url && other.id !== id && other.state === "publishing")) {
        if (!pending.request || !pending.candidate?.head ||
          await this.resolver.remoteHead(pending.request) !== pending.candidate.head) return this.escalate(entry, pending);
        pending.state = "published"; pending.reason = "Publication confirmed before admitting another repair"; this.save(pending);
      }
      // WHY: Reconcile admitted effects even if policy was removed or GitHub now reports another revision.
      if (record?.state === "publishing") {
        if (record.request && record.candidate?.head &&
          await this.resolver.remoteHead(record.request) === record.candidate.head) {
          record.state = "published"; record.reason = "Publication confirmed after interruption"; this.save(record);
          this.handled(value, entry, record); return true;
        }
        record.reason = "Publication outcome remains unknown; reconcile the recorded candidate before any further push";
        this.save(record); return this.escalate(entry, record);
      }
      const policy = this.policy(value.repository);
      if (!policy) return false;
      if (policy.github.toLowerCase() !== (target.owner + "/" + target.repo).toLowerCase()) return false;
      if (!record) {
        record = { id, taskId: value.taskId, url, head, base, state: "preparing",
          policyDigest: digest(policy), candidate: null, reason: "", updatedAt: this.store.now(), request: null };
        this.save(record);
      }
      if (record.state === "published" || record.state === "superseded") { this.handled(value, entry, record); return true; }
      if (record.state === "needs_agent") return this.escalate(entry, record);
      const observation = (await this.github.observe(url)).pullRequest;
      if (!observation || observation.state !== "open" || observation.merged ||
        observation.head !== head || observation.base !== base || observation.mergeable !== false) {
        if (observation?.mergeable === null && observation.head === head && observation.base === base) return true;
        throw new StaleRevision("PR no longer has this conflict at these revisions");
      }
      if (!observation.headRef || !observation.baseRef || observation.headRepository?.toLowerCase() !== policy.github.toLowerCase() ||
        observation.baseRepository?.toLowerCase() !== policy.github.toLowerCase()) throw new Error("Automatic repair requires matching branch identities in the allowed repository");
      const request: RepairRequest = { id, directory: value.worker.cwd, head, base,
        headRef: observation.headRef, baseRef: observation.baseRef, policy };
      if (record.policyDigest !== digest(policy)) throw new Error("Maintenance policy changed during an unfinished attempt");
      record.request = request; this.save(record);
      if (!await idle() || this.store.get(value.taskId).control !== "running") return true;
      const candidate = record.candidate?.head ? record.candidate : await this.resolver.prepare(request);
      record.candidate = candidate; this.save(record);
      if (!candidate.head || candidate.conflicts.length || candidate.checks.length !== policy.checks.length ||
        candidate.checks.some(check => !check.passed) || candidate.confidence === null ||
        candidate.confidence < policy.minimumConfidence) throw new Error(candidate.reason);
      const current = (await this.github.observe(url)).pullRequest;
      if (!current || current.state !== "open" || current.merged || current.head !== head || current.base !== base) {
        throw new StaleRevision("PR changed while the program validated its candidate");
      }
      if (!await idle()) return true;
      const control = this.store.get(value.taskId);
      if (control.control !== "running" || !control.github.includes(url) || control.worker?.agentId !== value.worker?.agentId) return true;
      if (digest(this.policy(value.repository)) !== record.policyDigest) throw new Error("Maintenance policy changed before publication");
      record.state = "publishing"; this.save(record);
      try { await this.resolver.publish(request, candidate); }
      catch (error) {
        if (error instanceof StaleRevision) {
          record.state = "superseded"; record.reason = message(error); this.save(record);
          this.handled(value, entry, record); return true;
        }
        record.reason = "Publication needs reconciliation: " + message(error); this.save(record);
        return this.escalate(entry, record);
      }
      if (await this.resolver.remoteHead(request) !== candidate.head) {
        record.reason = "Published branch readback differs; reconcile before retrying"; this.save(record);
        return this.escalate(entry, record);
      }
      record.state = "published"; record.reason = candidate.reason; this.save(record);
      this.handled(value, entry, record); return true;
    } catch (error) {
      if (!record) {
        record = { id, taskId: value.taskId, url, head, base, state: "needs_agent", policyDigest: "",
          candidate: null, reason: message(error), updatedAt: this.store.now(), request: null };
      }
      if (record.state === "publishing") {
        record.reason = message(error); this.save(record);
        return this.escalate(entry, record);
      }
      record.state = error instanceof StaleRevision ? "superseded" : "needs_agent";
      record.reason = message(error); this.save(record);
      if (record.state === "superseded") { this.handled(value, entry, record); return true; }
      return this.escalate(entry, record);
    } finally { this.running.delete(id); }
  }
  private escalate(entry: TaskEvent, record: MaintenanceRecord) {
    this.store.saveEvent({ ...entry, payload: { ...entry.payload, maintenance: record } });
    return false;
  }
}

// Long-running Git and validation commands must not block polling or other tasks.
export class MaintenanceQueue implements Maintainer {
  private jobs = new Map<string, Promise<void>>();
  private outcomes = new Map<string, boolean>();
  private stopping = false;
  constructor(readonly program: PRMaintenance) {}
  records(taskId: string) { return this.program.records(taskId); }
  async handle(value: Task, entry: TaskEvent, idle: () => Promise<boolean>) {
    if (this.stopping) return true;
    const outcome = this.outcomes.get(entry.id);
    if (outcome !== undefined) { this.outcomes.delete(entry.id); return outcome; }
    if (!this.jobs.has(entry.id)) {
      if (this.jobs.size >= 2) return true;
      const job = this.program.handle(value, entry, async () => !this.stopping && await idle())
        .then(result => {
          if (this.program.store.events(value.taskId).find(event => event.id === entry.id)?.delivery !== "handled") {
            this.outcomes.set(entry.id, result);
          }
        })
        .catch(error => {
          this.program.store.change(value.taskId, current => { current.error = message(error); });
          this.outcomes.set(entry.id, false);
        }).finally(() => { this.jobs.delete(entry.id); });
      this.jobs.set(entry.id, job);
    }
    return true;
  }
  async drain() { await Promise.all(this.jobs.values()); }
  async close() { this.stopping = true; await this.drain(); }
}
