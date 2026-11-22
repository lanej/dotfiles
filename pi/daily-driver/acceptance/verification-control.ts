import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { randomUUID } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { promisify } from "node:util";
import { z } from "zod";
import { Attempts, Phase, type Attempt } from "../attempts.ts";
import { DriverProfile, ReasoningLevel } from "../config.ts";
import { processFailure } from "../process.ts";
import { TaskBeads } from "../task-service.ts";
import { submitResult } from "../task-verification.ts";
import type { NativeBeads } from "./beads-fixture.ts";
import type { BeadsHttpSource } from "./beads-http-fixture.ts";

const execute = promisify(execFile);
const pidsSchema = z.object({
  parent: z.number().int().positive(),
  child: z.number().int().positive(),
});

async function running(pid: number): Promise<boolean> {
  try {
    const result = await execute("ps", ["-p", String(pid), "-o", "stat="], {
      timeout: 2000,
    });
    return (
      result.stdout.trim().length > 0 && !result.stdout.trim().startsWith("Z")
    );
  } catch (cause) {
    if (processFailure(cause).code === 1) return false;
    throw cause;
  }
}

export async function verificationControl(
  fixture: NativeBeads,
  source: BeadsHttpSource,
) {
  const { directory, workspace, command } = fixture;
  const git = async (...args: string[]) =>
    (
      await execute("git", args, { cwd: workspace, timeout: 5000 })
    ).stdout.trim();
  await writeFile(join(workspace, ".gitignore"), ".beads/\n");
  await git("add", ".gitignore");
  await git(
    "-c",
    "user.name=Fixture",
    "-c",
    "user.email=fixture@example.invalid",
    "-c",
    "core.hooksPath=/dev/null",
    "commit",
    "-qm",
    "Verifier fixture",
  );
  await git("branch", "-M", "main");
  const service = new TaskBeads(source);
  const db = new Attempts(join(directory, "verification-journal"));
  const admitted = async (
    check: string[],
    reviewOnly = false,
  ): Promise<Attempt> => {
    const created = await command([
      "create",
      "--title",
      "Native verifier control",
      "--type",
      "task",
      "--description",
      "Keep scope and results guarded",
      "--acceptance",
      "Run the agreed fixture verifier",
      "--json",
    ]);
    assert.equal(created.code, 0, created.stderr);
    const id = z
      .object({ id: z.string() })
      .parse(JSON.parse(created.stdout)).id;
    const bead = await service.get(id);
    const attempt = randomUUID();
    const revision = await service.claim(bead, attempt);
    const record: Attempt = {
      id: attempt,
      source: { ...source, reviewOnly },
      bead,
      revision,
      check,
      profile: DriverProfile.Personal,
      model: {
        provider: "openai-codex",
        model: "fixture",
        reasoning: ReasoningLevel.Off,
      },
      live: false,
      processStarted: null,
      reservation: {
        primary: workspace,
        root: workspace,
        holder: attempt,
        agent: "pi",
        branch: "main",
        baseRef: "HEAD",
        baseCommit: await git("rev-parse", "HEAD"),
        attempted: false,
      },
      // This verifier-only fixture uses the primary Git working tree, not a manager allocation.
      checkout: {
        primary: workspace,
        root: workspace,
        path: workspace,
        task_id: "verification-fixture",
        owner_id: attempt,
        agent: "pi",
        branch: "main",
        created_at: new Date().toISOString(),
        base_ref: "HEAD",
      },
      session: "verification-fixture",
      pane: null,
      pid: null,
      transcript: null,
      phase: Phase.Running,
      verification: null,
      message: "Native verifier fixture",
    };
    assert(db.reserve(record));
    return record;
  };
  const controller = new AbortController();
  let pending: Promise<string> | undefined;
  let processes: z.infer<typeof pidsSchema> | undefined;
  const marker = join(directory, "verifier-started.json");
  const effects = join(directory, "verifier-effects.txt");
  const verifier = join(directory, "blocking-verifier.mjs");
  await writeFile(
    verifier,
    `import {spawn} from 'node:child_process';
import {appendFileSync,writeFileSync} from 'node:fs';
process.on('SIGTERM',()=>{});
const child=spawn(process.execPath,['-e',"process.on('SIGTERM',()=>{});setInterval(()=>{},1000)"],{stdio:'inherit'});
appendFileSync(${JSON.stringify(effects)},'started\\n');
writeFileSync(${JSON.stringify(marker)},JSON.stringify({parent:process.pid,child:child.pid}));
setInterval(()=>{},1000);
`,
  );
  try {
    const cancelled = await admitted([process.execPath, verifier]);
    pending = submitResult(
      db,
      cancelled.id,
      "Cancel the real blocking verifier",
      controller.signal,
    );
    const deadline = Date.now() + 5000;
    while (processes === undefined && Date.now() < deadline) {
      try {
        processes = pidsSchema.parse(
          JSON.parse(await readFile(marker, "utf8")),
        );
      } catch (cause) {
        const missing = z
          .object({ code: z.literal("ENOENT") })
          .safeParse(cause);
        if (!missing.success) throw cause;
        await delay(20);
      }
    }
    assert(
      processes !== undefined,
      "The actual verifier never signalled startup",
    );
    assert(await running(processes.parent));
    assert(await running(processes.child));
    const started = Date.now();
    controller.abort(new Error("Fixture operator cancelled verification"));
    assert.match(await pending, /cancel/i);
    assert(
      Date.now() - started < 5000,
      "Cancellation did not promptly finish the verifier process tree",
    );
    assert.equal(await running(processes.parent), false);
    assert.equal(await running(processes.child), false);
    const stored = db.get(cancelled.id);
    assert.notEqual(stored.phase, Phase.Checking);
    assert.notEqual(stored.phase, Phase.Closed);
    assert.match(stored.message, /cancel/i);
    assert.notEqual((await service.get(cancelled.bead.id)).status, "closed");
    assert.equal(
      (await service.get(cancelled.bead.id)).metadata["pi.result"],
      undefined,
    );
    await submitResult(
      db,
      cancelled.id,
      "Same cancelled submission",
      controller.signal,
    ).catch(() => undefined);
    assert.equal(
      await readFile(effects, "utf8"),
      "started\n",
      "An already cancelled submission restarted the verifier",
    );

    const reviewEffects = join(directory, "review-effects.txt");
    const review = await admitted(
      [
        process.execPath,
        "-e",
        `require('node:fs').appendFileSync(${JSON.stringify(reviewEffects)},'checked\\n')`,
      ],
      true,
    );
    assert.match(
      await submitResult(db, review.id, "Passing check requires review"),
      /human review/,
    );
    assert.equal(db.get(review.id).phase, Phase.NeedsReview);
    assert.equal(db.get(review.id).verification?.exitCode, 0);
    const reviewTask = await service.get(review.bead.id);
    assert.notEqual(reviewTask.status, "closed");
    assert.equal(reviewTask.metadata["pi.result"], undefined);
    await assert.rejects(
      () => submitResult(db, review.id, "Repeat review-only result"),
      /requires a running worker/,
    );
    assert.equal(await readFile(reviewEffects, "utf8"), "checked\n");
    return {
      cancellationStopsTree: true,
      cancelledSubmissionNotRepeated: true,
      reviewOnlyPreservesOpenTask: true,
    };
  } finally {
    controller.abort();
    if (processes !== undefined) {
      try {
        process.kill(-processes.parent, "SIGKILL");
      } catch (cause) {
        assert.equal(processFailure(cause).code, "ESRCH");
      }
    }
    if (pending !== undefined) await pending.catch(() => undefined);
    db.close();
  }
}
