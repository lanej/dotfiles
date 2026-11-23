import { requireIntegration } from "./integrations.ts";
import { createHash, randomUUID } from "node:crypto";
import {
  link,
  lstat,
  mkdir,
  readFile,
  unlink,
  writeFile,
} from "node:fs/promises";
import { isAbsolute, join } from "node:path";
import { z } from "zod";
import { Attempts, Phase, stateDirectory, type Attempt } from "./attempts.ts";
import { loadConfig } from "./config.ts";
import { sha } from "./delivery-record.ts";
import { octo } from "./delivery.ts";
import { settledDelegates } from "./delegation.ts";
import { LeadMode } from "./lead-plan.ts";
import { processFailure, run } from "./process.ts";
import { processIsGone } from "./task-run.ts";
import { TaskBeads } from "./task-service.ts";

const chain = z.object({
  entries: z.array(
    z.object({
      id: z.string(),
      chainId: z.string(),
      prId: z.string(),
      state: z.string(),
      receiptId: z.string().optional(),
      ready: z.object({ head: sha }).optional(),
      mergeCommit: sha.optional(),
    }),
  ),
});
const observation = z.object({
  pr: z.object({
    id: z.string(),
    ownerAgentId: z.string(),
    observation: z.object({
      headSha: sha,
      lifecycle: z.string(),
      targetBase: z.object({ ref: z.string().min(1) }),
    }),
  }),
});
const manager = z.object({
  result: z.object({
    id: z.string(),
    owner_id: z.string(),
    path: z.string(),
    branch: z.string(),
    state: z.literal("finished"),
  }),
});
const hash = (bytes: Buffer) =>
  createHash("sha256").update(bytes).digest("hex");

async function retain(path: string, bytes: Buffer): Promise<string> {
  const candidate = `${path}.${randomUUID()}`;
  await writeFile(candidate, bytes, { flag: "wx", mode: 0o600, flush: true });
  try {
    await link(candidate, path);
  } catch (error) {
    if (processFailure(error).code !== "EEXIST") throw error;
  } finally {
    await unlink(candidate);
  }
  const digest = hash(await readFile(path));
  if (digest !== hash(bytes))
    throw new Error(`Archive content differs at ${path}`);
  return digest;
}

async function removed(primary: string, checkout: string): Promise<boolean> {
  const list = await run("git", ["worktree", "list", "--porcelain", "-z"], {
    cwd: primary,
  });
  if (list.split("\0").includes(`worktree ${checkout}`)) return false;
  try {
    await lstat(checkout);
    throw new Error("The checkout path exists without its Git registration");
  } catch (error) {
    if (processFailure(error).code !== "ENOENT") throw error;
  }
  return true;
}

export async function archiveLead(bead: string): Promise<Attempt> {
  const config = await loadConfig();
  const managerExecutable = await requireIntegration(config, "worktrees");
  await requireIntegration(config, "octo");
  if (config.beadsService === undefined)
    throw new Error("Configure the Beads service");
  const db = new Attempts(stateDirectory());
  try {
    const record = db.latest(config.beadsService.projectId, bead);
    if (record?.phase === Phase.Archived) return record;
    if (
      record === null ||
      record.leadPlan?.mode !== LeadMode.Implementing ||
      record.checkout === null ||
      record.transcript === null ||
      record.revision === null ||
      record.verification === null ||
      record.verification.exitCode !== 0 ||
      record.delivery?.merge === undefined ||
      record.delivery.pr === undefined ||
      record.delivery.agent === undefined ||
      (record.phase !== Phase.Verified && record.phase !== Phase.Archiving)
    )
      throw new Error(
        "A verified lead with a recorded Octo merge request is required",
      );
    if (record.pid === null || !processIsGone(record.pid))
      throw new Error("Exit the lead Pi session before archiving");
    const service = new TaskBeads(record.source);
    const children = await Promise.all(
      Object.values(record.leadPlan.children).map((id) => service.get(id)),
    );
    const open = children.filter((child) => child.status !== "closed");
    if (open.length > 0)
      throw new Error(
        `Settle child beads before archiving: ${open.map((child) => child.id).join(", ")}`,
      );

    const { checkout, delivery, verification } = record;
    const merge = record.delivery.merge;
    const { primary, path } = checkout;
    const { pr } = observation.parse(
      await octo(primary, "pr", "show", record.delivery.pr),
    );
    const { entries } = chain.parse(
      await octo(primary, "chain", "show", merge.chain),
    );
    const matching = entries.filter((entry) =>
      entry.id.startsWith(merge.entry),
    );
    const entry = matching.length === 1 ? matching[0] : undefined;
    if (
      entry?.mergeCommit === undefined ||
      entry.state !== "merged" ||
      entry.receiptId !== `pi-inbox:${merge.notice}:${merge.head}` ||
      !entry.chainId.startsWith(merge.chain) ||
      entry.prId !== delivery.pr ||
      entry.ready?.head !== merge.head ||
      verification.gitHead !== merge.head ||
      pr.id !== delivery.pr ||
      pr.ownerAgentId !== delivery.agent ||
      pr.observation.lifecycle !== "merged" ||
      pr.observation.headSha !== merge.head
    )
      throw new Error(
        "Octo has not confirmed this exact lead revision as merged",
      );

    const delegates = settledDelegates(record.id);
    const archive = join(db.directory, "archives", record.id);
    await mkdir(archive, { recursive: true, mode: 0o700 });
    const transcripts = await Promise.all(
      [{ id: record.id, path: record.transcript }, ...delegates].map(
        async ({ id, path: transcript }) => {
          if (!isAbsolute(transcript) || !(await lstat(transcript)).isFile())
            throw new Error(
              "A native transcript is missing or is not a regular file",
            );
          const bytes = await readFile(transcript);
          if (bytes.length === 0)
            throw new Error("An archived native transcript is empty");
          const name = `${id}.jsonl`;
          const digest = await retain(join(archive, name), bytes);
          return { id, transcript, name, digest };
        },
      ),
    );

    const git = async (...args: string[]) =>
      (await run("git", args, { cwd: primary, timeout: 90_000 })).trim();
    const base = `refs/heads/${pr.observation.targetBase.ref}`;
    await git("check-ref-format", base);
    const observed = `refs/pi-driver/archive-bases/${record.id}`;
    await git("fetch", "--no-tags", "origin", `+${base}:${observed}`);
    await git("merge-base", "--is-ancestor", entry.mergeCommit, observed);
    const retained = `refs/pi-driver/archives/${record.id}`;
    await git("update-ref", retained, entry.mergeCommit);
    if (
      (await git(
        "rev-parse",
        "--verify",
        `refs/heads/${checkout.branch}^{commit}`,
      )) !== merge.head
    )
      throw new Error("The verified source branch moved before cleanup");

    const manifest = join(archive, "manifest.json");
    const metadata = {
      id: record.id,
      bead: record.bead.id,
      revision: record.revision,
      summary: record.bead.title,
      checkout,
      verification,
      delivery: {
        url: delivery.url,
        pr: delivery.pr,
        submission: delivery.octoSubmission,
        merge,
      },
      mergedAs: entry.mergeCommit,
      retained,
      transcripts,
    };
    await retain(
      manifest,
      Buffer.from(`${JSON.stringify(metadata, null, 2)}\n`),
    );
    const claim = db.change(record.id, (row) => {
      if (row.phase === Phase.Archived) return;
      if (
        (row.phase !== Phase.Verified && row.phase !== Phase.Archiving) ||
        row.pid !== record.pid ||
        row.revision !== record.revision ||
        row.verification?.gitHead !== merge.head ||
        row.delivery?.merge?.notice !== merge.notice ||
        !processIsGone(record.pid ?? -1)
      )
        throw new Error("The lead attempt changed before finalization");
      row.phase = Phase.Archiving;
      row.message =
        "Transcript retained. Confirming Beads closure and checkout removal";
    });
    if (claim.phase === Phase.Archived) return claim;
    if (!(await service.closedWith(record.bead.id, record.id, verification)))
      await service.complete(
        record.bead,
        record.revision,
        record.id,
        verification,
      );

    if (!(await removed(primary, path))) {
      const finished = manager.parse(
        JSON.parse(
          await run(managerExecutable, ["finish", checkout.task_id, "--json"], {
            cwd: primary,
          }),
        ),
      ).result;
      if (
        finished.id !== checkout.task_id ||
        finished.owner_id !== checkout.owner_id ||
        finished.path !== path ||
        finished.branch !== checkout.branch
      )
        throw new Error("The worktree manager returned a different allocation");
      const options = [
        "prune",
        "--worktree",
        path,
        "--integrated",
        "--accept-recent",
        "-b",
        entry.mergeCommit,
      ];
      const preview = z
        .object({
          result: z.object({
            worktrees: z.array(
              z.object({ path: z.string(), action: z.string() }),
            ),
          }),
        })
        .parse(
          JSON.parse(
            await run(managerExecutable, [...options, "--json"], {
              cwd: primary,
              timeout: 180_000,
            }),
          ),
        );
      const candidate = preview.result.worktrees.find(
        (row) => row.path === path,
      );
      if (
        candidate?.action !== "remove" &&
        candidate?.action !== "force-remove"
      )
        throw new Error(
          `Worktree retained by the manager (${candidate?.action ?? "no removal candidate"})`,
        );
      await run(managerExecutable, [...options, "--apply", "--json"], {
        cwd: primary,
        timeout: 180_000,
      });
    }
    if (!(await removed(primary, path)))
      throw new Error("The worktree manager has not confirmed removal");
    return db.change(record.id, (row) => {
      row.phase = Phase.Archived;
      row.archiveManifest = manifest;
      row.message = `Archived · ${delivery.url ?? delivery.pr ?? record.bead.id}`;
    });
  } finally {
    db.close();
  }
}
