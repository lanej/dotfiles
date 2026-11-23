import { requireIntegration } from "./integrations.ts";
import { createHash } from "node:crypto";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { z } from "zod";
import { Attempts, Phase, stateDirectory, type Attempt } from "./attempts.ts";
import { LeadMode } from "./lead-plan.ts";
import { loadConfig } from "./config.ts";
import { run } from "./process.ts";
import { TaskBeads } from "./task-service.ts";

import { identifier, prUrl, sha } from "./delivery-record.ts";

const receipt = z.object({
  id: identifier,
  state: z.enum(["pending", "published", "failed", "uncertain"]),
  url: prUrl.optional(),
  tracking: z.string().optional(),
});
const tracked = z.object({
  pr: z.object({
    id: identifier,
    url: prUrl,
    ownerAgentId: identifier,
    observation: z.object({ headSha: sha, lifecycle: z.string() }).optional(),
  }),
});
const registration = z.object({
  agent: z.object({
    id: identifier,
    harness: z.literal("pi"),
    endpoint: z.literal("local"),
    sessionId: identifier,
  }),
});
const mailbox = z.object({
  messages: z.array(
    z.object({
      id: identifier,
      actionId: z.string(),
      workflowPrId: identifier.optional(),
      readyHead: sha.optional(),
      acknowledgedAtMs: z.number().optional(),
      recipientAgentId: identifier,
      body: z.string(),
      applicable: z.boolean(),
    }),
  ),
  nextSequence: z.number().int().nonnegative(),
  hasMore: z.boolean(),
});

export async function octo(cwd: string, ...args: string[]): Promise<unknown> {
  const executable = await requireIntegration(await loadConfig(), "octo");
  return JSON.parse(
    await run(executable, [...args, "--json"], {
      cwd,
      env: {
        ...process.env,
        OCTO_MANAGER_AGENT: "0",
        CODEX_THREAD_ID: undefined,
        OCTO_MANAGER_AGENT_ID: undefined,
      },
      timeout: 15_000,
    }),
  );
}

export async function refreshPublication(
  db: Attempts,
  record: Attempt,
): Promise<Attempt> {
  const delivery = record.delivery;
  if (delivery === undefined || record.checkout === null)
    throw new Error("No Octo publication is recorded");
  if (delivery.octoSubmission === undefined)
    throw new Error(
      "Retry the same publish request to retrieve its Octo receipt",
    );
  const cwd = record.checkout.path;
  const current = receipt.parse(
    await octo(cwd, "submission", delivery.octoSubmission),
  );
  if (current.id !== delivery.octoSubmission)
    throw new Error("Octo returned a different publication");
  if (
    current.state !== "published" ||
    current.tracking !== "active" ||
    current.url === undefined
  )
    return record;
  const url = current.url;
  const { agent } = registration.parse(
    await octo(
      cwd,
      "agent",
      "register",
      "--harness",
      "pi",
      "--endpoint",
      "local",
      "--thread-id",
      record.id,
    ),
  );
  if (agent.sessionId !== record.id)
    throw new Error("Octo registered a different Pi session");
  const { pr } = tracked.parse(await octo(cwd, "pr", "show", url));
  if (pr.url !== url || pr.ownerAgentId !== agent.id)
    throw new Error("Octo publication and lead ownership do not match");
  return db.change(record.id, (row) => {
    const saved = row.delivery;
    if (saved?.requestId !== delivery.requestId)
      throw new Error("The Octo publication changed during reconciliation");
    if (
      (saved.url !== undefined && saved.url !== url) ||
      (saved.pr !== undefined && saved.pr !== pr.id) ||
      (saved.agent !== undefined && saved.agent !== agent.id)
    )
      throw new Error("Octo returned a different delivery binding");
    row.delivery = { ...saved, url, pr: pr.id, agent: agent.id };
    row.message = `Octo is tracking ${url}`;
  });
}

export async function publishLead(
  bead: string,
  title: string,
  bodyFile: string,
  base: string,
): Promise<Attempt> {
  const config = await loadConfig();
  await requireIntegration(config, "octo");
  if (config.beadsService === undefined)
    throw new Error("Configure the Beads service");
  const db = new Attempts(stateDirectory());
  try {
    const record = db.latest(config.beadsService.projectId, bead);
    if (
      record?.leadPlan?.mode !== LeadMode.Implementing ||
      record.checkout === null ||
      record.revision === null ||
      record.phase !== Phase.Verified ||
      record.verification?.exitCode !== 0
    )
      throw new Error("Verify the managed lead result before publishing");
    await new TaskBeads(record.source).requireCurrent(
      record.bead,
      record.revision,
      record.id,
    );
    const cwd = record.checkout.path;
    const output = async (...args: string[]) =>
      (await run("git", args, { cwd })).trim();
    const head = sha.parse(await output("rev-parse", "HEAD"));
    if (
      head !== record.verification.gitHead ||
      (await output("rev-parse", "HEAD^{tree}")) !==
        record.verification.gitState ||
      (await output("symbolic-ref", "--short", "HEAD")) !==
        record.checkout.branch ||
      (await output("status", "--porcelain", "--untracked-files=all")) !== ""
    )
      throw new Error(
        "Publish requires the clean, committed revision verified by this lead",
      );
    const body = await readFile(resolve(bodyFile));
    const digest = createHash("sha256")
      .update(JSON.stringify([head, title, base]))
      .update(body)
      .digest("hex");
    const requestId = `pi:${record.id}:${head}`;
    db.change(record.id, (row) => {
      if (
        row.leadPlan?.mode !== LeadMode.Implementing ||
        row.phase !== Phase.Verified ||
        row.revision !== record.revision ||
        row.verification?.gitHead !== head
      )
        throw new Error("The verified lead changed before publication");
      if (row.delivery !== undefined && row.delivery.requestDigest !== digest)
        throw new Error(
          "Inspect the existing Octo publication before supplying a different draft",
        );
      row.delivery ??= { requestId, requestDigest: digest, head, inbox: {} };
    });
    const directory = await mkdtemp(join(stateDirectory(), "publication-"));
    const path = join(directory, "draft.md");
    let created: z.infer<typeof receipt>;
    try {
      await writeFile(path, body, { mode: 0o600, flag: "wx" });
      created = receipt.parse(
        await octo(
          cwd,
          "submit-pr",
          "--title",
          title,
          "--body-file",
          path,
          "--base",
          base,
          "--head",
          record.checkout.branch,
          "--expected-head",
          head,
          "--track",
          "--harness",
          "pi",
          "--endpoint",
          "local",
          "--thread-id",
          record.id,
          "--request-id",
          requestId,
        ),
      );
    } finally {
      await rm(directory, { recursive: true });
    }
    const current = db.change(record.id, (row) => {
      if (
        row.delivery?.requestId !== requestId ||
        (row.delivery.octoSubmission !== undefined &&
          row.delivery.octoSubmission !== created.id)
      )
        throw new Error("The Octo submission no longer matches this lead");
      row.delivery.octoSubmission = created.id;
      row.message = `Octo publication ${created.state}`;
    });
    return await refreshPublication(db, current);
  } finally {
    db.close();
  }
}

export async function leadDeliveryDecision(
  bead: string,
  head: string,
  notice: string | undefined,
): Promise<unknown> {
  sha.parse(head);
  const config = await loadConfig();
  await requireIntegration(config, "octo");
  if (config.beadsService === undefined)
    throw new Error("Configure the Beads service");
  const db = new Attempts(stateDirectory());
  try {
    const record = db.latest(config.beadsService.projectId, bead);
    if (
      record === null ||
      record.leadPlan?.mode !== LeadMode.Implementing ||
      record.checkout === null ||
      record.revision === null ||
      record.phase !== Phase.Verified ||
      record.verification?.exitCode !== 0 ||
      record.verification.gitHead !== head ||
      (
        await run("git", ["status", "--porcelain", "--untracked-files=all"], {
          cwd: record.checkout.path,
        })
      ).trim() !== "" ||
      (
        await run("git", ["rev-parse", "HEAD"], { cwd: record.checkout.path })
      ).trim() !== head
    )
      throw new Error(
        "Verify and commit the current clean lead revision first",
      );
    await new TaskBeads(record.source).requireCurrent(
      record.bead,
      record.revision,
      record.id,
    );
    const { delivery } = await refreshPublication(db, record);
    if (delivery?.url === undefined || delivery.agent === undefined)
      throw new Error("Wait for Octo to enroll the lead pull request");
    const cwd = record.checkout.path;
    if (notice === undefined)
      return await octo(
        cwd,
        "pr",
        "ready",
        delivery.url,
        "--head",
        head,
        "--agent-id",
        delivery.agent,
      );
    z.uuid().parse(notice);
    if (delivery.inbox[notice]?.id !== notice)
      throw new Error("Inspect this PR's Ready notice in /octo-inbox first");
    const result = z
      .looseObject({
        state: z.string(),
        pr: prUrl,
        chain: identifier.optional(),
        entry: identifier.optional(),
      })
      .parse(
        await octo(
          cwd,
          "merge",
          notice,
          "--expected-pr",
          delivery.url,
          "--expected-head",
          head,
          "--agent-id",
          delivery.agent,
        ),
      );
    if (result.pr !== delivery.url)
      throw new Error("Octo returned a different merge subject");
    if (result.chain !== undefined && result.entry !== undefined) {
      const binding = {
        notice,
        head,
        chain: result.chain,
        entry: result.entry,
      };
      db.change(record.id, (row) => {
        if (row.delivery?.pr !== delivery.pr || row.delivery === undefined)
          throw new Error(
            "The delivery binding changed during the merge request",
          );
        row.delivery.merge = binding;
      });
    }
    return result;
  } finally {
    db.close();
  }
}

export async function readDeliveryInbox(
  db: Attempts,
  attempt: Attempt,
): Promise<{
  text: string;
  url?: string;
  receipts: { id: string; body: string }[];
}> {
  const record = await refreshPublication(db, attempt);
  const delivery = record.delivery;
  if (
    record.checkout === null ||
    delivery?.agent === undefined ||
    delivery.pr === undefined ||
    delivery.url === undefined
  )
    return { text: record.message, receipts: [] };
  const cwd = record.checkout.path;
  const { pr } = tracked.parse(await octo(cwd, "pr", "show", delivery.pr));
  if (
    pr.id !== delivery.pr ||
    pr.url !== delivery.url ||
    pr.ownerAgentId !== delivery.agent
  )
    throw new Error("This Pi session no longer owns the tracked pull request");
  const ready = new Map<string, string>();
  let after = 0;
  for (;;) {
    const page = mailbox.parse(
      await octo(
        cwd,
        "agent",
        "inbox",
        "--agent-id",
        delivery.agent,
        "--applicable-only",
        "--include-acknowledged",
        "--after",
        String(after),
      ),
    );
    for (const message of page.messages) {
      if (!message.applicable || message.recipientAgentId !== delivery.agent)
        continue;
      let prId = message.workflowPrId;
      if (prId === undefined && message.actionId !== "") {
        const { action } = z
          .object({ action: z.object({ prId: identifier }) })
          .parse(await octo(cwd, "action", "show", message.actionId));
        prId = action.prId;
      }
      if (prId !== delivery.pr) continue;
      if (message.readyHead !== undefined)
        ready.set(message.id, message.readyHead);
      if (db.get(record.id).delivery?.inbox[message.id]?.acknowledged === true)
        continue;
      db.change(record.id, (row) => {
        const saved = row.delivery;
        if (
          saved === undefined ||
          saved.pr !== delivery.pr ||
          saved.agent !== delivery.agent
        )
          throw new Error("The delivery binding changed");
        const previous = saved.inbox[message.id];
        if (previous !== undefined && previous.body !== message.body)
          throw new Error(
            "Octo returned different text for an existing notice",
          );
        saved.inbox[message.id] ??= {
          id: message.id,
          body: message.body,
          acknowledged: false,
        };
      });
      if (message.acknowledgedAtMs === undefined)
        await octo(
          cwd,
          "acknowledge-message",
          message.id,
          "--agent-id",
          delivery.agent,
        );
      db.change(record.id, (row) => {
        const saved = row.delivery?.inbox[message.id];
        if (saved !== undefined) saved.acknowledged = true;
      });
    }
    if (!page.hasMore) break;
    if (page.nextSequence <= after)
      throw new Error("Octo inbox cursor did not advance");
    after = page.nextSequence;
  }
  const notices = Object.values(db.get(record.id).delivery?.inbox ?? {});
  const text = notices
    .map((notice) => {
      const head = ready.get(notice.id);
      return head === undefined
        ? `${notice.id}\n${notice.body}`
        : `Ready · ${head}\n${notice.id}\n${notice.body}`;
    })
    .join("\n\n");
  return {
    text,
    url: delivery.url,
    receipts: notices.filter((notice) => notice.acknowledged),
  };
}
