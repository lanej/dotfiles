import { readdir, readFile, rename, mkdir, stat } from "node:fs/promises";
import { join, resolve } from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { z } from "zod";
import { createHash } from "node:crypto";
import type { Store } from "./store";
import type { Brief } from "../shared/contracts";
import { digest, githubObject } from "./github";
import { sessionEntries } from "./pi-session";

const legacyId = z.string().regex(/^[A-Za-z0-9][A-Za-z0-9_.-]*$/);
export const candidate = z.object({
  home: z.string(), legacyId, generation: z.string().max(200).regex(/^[A-Za-z0-9_.-]*$/), metadataHash: z.string(),
  worktree: z.string(), branch: z.string(), harness: z.string(), brief: z.string(),
  sessionFile: z.string().nullable(), sessionId: z.string().nullable(), ownerPid: z.number().int().nullable(),
  github: z.array(z.string()), pendingFeedback: z.number().int(),
});
export type Candidate = z.infer<typeof candidate>;
const hash = (value: string) => createHash("sha256").update(value).digest("hex");
const parseMeta = (text: string) => Object.fromEntries(text.split("\n").filter(line => line.includes("=")).map(line => {
  const index = line.indexOf("="); return [line.slice(0, index), line.slice(index + 1)];
}));
const read = async (path: string, fallback: string | null = null) => {
  try { return await readFile(path, "utf8"); } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return fallback;
    throw error;
  }
};
const alive = (pid: number) => {
  try { process.kill(pid, 0); return true; } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ESRCH") return false;
    throw error;
  }
};
const sessionOwner = z.object({
  schema: z.literal("firstmate-github-session.v1"), task: legacyId,
  generation: z.string(), worktree: z.string().min(1), branch: z.string().min(1),
  sessionFile: z.string().min(1), sessionId: z.uuid(), pid: z.number().int().positive(),
});
async function recordedOwner(home: string, id: string, meta: Record<string, string>) {
  const text = await read(join(home, "data", id, "github-session.json"));
  if (!text) return null;
  const owner = sessionOwner.parse(JSON.parse(text));
  if (owner.task !== id || owner.generation !== meta.spawn_gen || owner.worktree !== meta.worktree || owner.branch !== meta.branch) {
    throw new Error(`Firstmate session ownership differs from the current metadata for ${id}`);
  }
  await sessionEntries(owner.sessionFile, owner.sessionId, owner.worktree);
  return owner;
}
async function assertReleased(source: Candidate) {
  if (source.ownerPid && alive(source.ownerPid)) throw new Error("Recorded Firstmate Pi owner is still alive; preserve its session and stop old ownership first");
  const lock = await read(join(source.home, "state", ".lock"));
  if (lock) {
    const pid = Number(lock.trim());
    if (!Number.isSafeInteger(pid) || pid <= 0 || alive(pid)) throw new Error("Firstmate captain ownership is active or unreadable");
  }
  const processes = (await promisify(execFile)("ps", ["-axo", "pid=,command="], { timeout: 10000 })).stdout;
  if (processes.split("\n").some(line => line.includes(source.home) &&
    /fm-(watch|supervision|primary|branch-dispatch)|firstmate.*(?:rpc|start)/.test(line))) {
    throw new Error("Firstmate supervision still owns this home; stop it before activating replacement ownership");
  }
}
export async function inventory(homeInput: string): Promise<Candidate[]> {
  const home = resolve(homeInput);
  const directory = join(home, "state");
  const entries = await readdir(directory);
  const values = [];
  for (const filename of entries.filter(name => name.endsWith(".meta"))) {
    const id = legacyId.parse(filename.slice(0, -5));
    const text = (await read(join(directory, filename)))!;
    const meta = parseMeta(text);
    const session = await recordedOwner(home, id, meta);
    let pending: string[] = [];
    try { pending = (await readdir(join(directory, `${id}.inbox`))).filter(name => /^[0-9]+\.msg$/.test(name)); }
    catch (error) { if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error; }
    values.push(candidate.parse({
      home, legacyId: id, generation: meta.spawn_gen ?? "", metadataHash: hash(text),
      worktree: meta.worktree ?? "", branch: meta.branch ?? "", harness: meta.harness ?? "unknown",
      brief: await read(join(home, "data", id, "brief.md"), "") ?? "",
      sessionFile: session?.sessionFile ?? null, sessionId: session?.sessionId ?? null, ownerPid: session?.pid ?? null,
      github: meta.pr ? [meta.pr] : [], pendingFeedback: pending.length,
    }));
  }
  return values;
}
export async function stage(store: Store, source: Candidate, brief: Brief, id: string) {
  if (source.harness !== "pi" || !source.generation || !source.sessionId || !source.sessionFile || !source.ownerPid) {
    throw new Error("This Firstmate worker has no recorded resumable Pi session; preserve it under its old owner");
  }
  const existing = store.list().find(value => value.taskId === id);
  if (existing) {
    if (existing.migration?.home !== source.home || existing.migration.legacyId !== source.legacyId ||
      existing.migration.generation !== source.generation) throw new Error("Migration request ID belongs to another task");
    return existing;
  }
  const current = (await inventory(source.home)).find(value => value.legacyId === source.legacyId);
  if (!current || current.metadataHash !== source.metadataHash || current.sessionId !== source.sessionId ||
    current.ownerPid !== source.ownerPid || current.sessionFile !== source.sessionFile ||
    current.worktree !== source.worktree || current.branch !== source.branch || current.harness !== source.harness ||
    JSON.stringify(current.github) !== JSON.stringify(source.github)) {
    throw new Error("Firstmate ownership changed; refresh the migration inventory");
  }
  return store.transaction(() => {
    if (store.list().some(value => value.migration &&
      ((value.migration.home === source.home && value.migration.legacyId === source.legacyId) ||
        value.migration.sessionId === source.sessionId || value.migration.sessionFile === source.sessionFile))) {
      throw new Error("This Firstmate task or Pi session already has a staged owner");
    }
    for (const url of source.github) {
      githubObject(url);
      if (store.list().some(value => value.github.includes(url))) throw new Error("GitHub discussion already belongs to another task");
    }
    const value = store.create(brief, null, id, "paused", {
      migration: { home: source.home, legacyId: source.legacyId, generation: source.generation,
        sessionFile: source.sessionFile, sessionId: source.sessionId, ownership: "firstmate" },
      github: source.github, nextAction: "Verify session import and stop Firstmate ownership before activation",
    });
    store.addEvent(id, "feedback", "Retained Firstmate ownership inventory", {
      id: `migration:${id}`, payload: { source }, source: join(source.home, "data", source.legacyId, "brief.md"),
    });
    return value;
  });
}
export async function releaseAndImport(store: Store, id: string, importSession: (source: Candidate, taskId: string) =>
  Promise<{ agentId: string; workspaceId: string; cwd: string; sessionId: string | null }>) {
  const value = store.get(id);
  if (!value.migration) throw new Error("Task is not a staged Firstmate migration");
  if (value.migration.ownership === "tasks" && value.worker && value.control === "running") return value;
  const source = candidate.parse(store.events(id).find(item => item.id === `migration:${id}`)?.payload.source);
  const path = join(source.home, "state", `${source.legacyId}.meta`);
  const archive = join(source.home, "state", "paseo-handoff", `${source.legacyId}.${source.generation}.meta`);
  const original = await read(path);
  const retained = original ?? await read(archive);
  if (hash(retained ?? "") !== source.metadataHash) throw new Error("Firstmate task generation or metadata changed; refresh the migration inventory");
  const owner = await recordedOwner(source.home, source.legacyId, parseMeta(retained!));
  if (!owner || owner.pid !== source.ownerPid || owner.sessionId !== source.sessionId || owner.sessionFile !== source.sessionFile) {
    throw new Error("Firstmate session ownership changed; refresh the migration inventory");
  }
  await assertReleased(source);
  if (original !== null) {
    if (hash(original) !== source.metadataHash) throw new Error("Firstmate task generation or metadata changed; refresh the migration inventory");
    await mkdir(join(source.home, "state", "paseo-handoff"), { recursive: true, mode: 0o700 });
    if (await stat(archive).catch(() => null)) throw new Error("Ownership archive already exists; reconcile it before proceeding");
    if (hash((await read(path)) ?? "") !== source.metadataHash) throw new Error("Firstmate metadata changed during handoff");
    await rename(path, archive);
  } else if (hash((await read(archive)) ?? "") !== source.metadataHash) {
    throw new Error("Retained Firstmate ownership archive does not match the staged generation");
  }
  store.change(id, current => {
    current.migration!.ownership = "released"; current.launch = "reserved"; current.control = "paused";
  });
  await assertReleased(source);
  const imported = await importSession(source, id);
  if (imported.sessionId !== source.sessionId || resolve(imported.cwd) !== resolve(source.worktree)) {
    throw new Error("Paseo import did not confirm the original session and checkout; migration remains paused");
  }
  store.bind(id, imported.agentId, imported.workspaceId, imported.cwd);
  for (const url of source.github) {
    const objectText = await read(join(source.home, "state", "github-feedback", "objects", `${digest(url)}.json`));
    if (objectText) {
      const object = JSON.parse(objectText);
      store.write("objects", url, { seen: object.seen, state: null, version: object.stateVersion ?? 0 });
      for (const pending of object.pending ?? []) {
        store.addEvent(id, "github", pending.body ?? "GitHub observation", { id: pending.id, source: pending.source, payload: pending });
      }
    }
  }
  const inbox = join(source.home, "state", `${source.legacyId}.inbox`);
  let filenames: string[] = [];
  try { filenames = (await readdir(inbox)).filter(name => /^[0-9]+\.msg$/.test(name)).sort(); }
  catch (error) { if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error; }
  for (const filename of filenames) {
    const raw = (await read(join(inbox, filename)))!;
    if (!raw.startsWith("schema=fm-task-inbox.v1\n") || !raw.includes("\n--\n")) throw new Error("Unsupported retained Firstmate inbox envelope; migration remains paused");
    const body = raw.slice(raw.indexOf("\n--\n") + 4).replace(/\n$/, "");
    if (body.startsWith("FIRSTMATE_GITHUB_EVENT v1\n")) {
      const pending = JSON.parse(body.slice("FIRSTMATE_GITHUB_EVENT v1\n".length));
      store.addEvent(id, "github", pending.body ?? "GitHub observation", { id: pending.id, source: pending.source, payload: pending });
    } else store.addEvent(id, "feedback", body, { id: digest([source.home, source.legacyId, filename, body]) });
  }
  const replies = join(source.home, "state", "github-feedback", "replies");
  let replyFiles: string[] = [];
  try { replyFiles = await readdir(replies); } catch (error) { if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error; }
  for (const filename of replyFiles.filter(name => /^[a-f0-9]{64}\.json$/.test(name))) {
    const record = JSON.parse((await read(join(replies, filename)))!);
    store.write("replies", filename.slice(0, -5), { ...record, state: record.source ? "confirmed" : "unknown", source: record.source ?? null });
  }
  store.saveEvent({ ...store.events(id).find(item => item.id === `migration:${id}`)!, delivery: "handled" });
  store.addEvent(id, "continue", "Your existing Firstmate task was transferred with its Pi history, checkout, pending feedback, and reply reconciliation. Read task_context and task_inbox before continuing.");
  return store.change(id, current => { current.control = "running"; current.error = null; });
}
