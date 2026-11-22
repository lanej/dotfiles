import {
  BeadsError,
  BeadsHttp,
  type components,
} from "@lanej/task-runtime/beads";
import { readFileSync } from "node:fs";
import { isDeepStrictEqual } from "node:util";
import { z } from "zod";
import type { DriverConfig } from "./config.ts";
import { orderedTasks, type LeadDraft } from "./lead-plan.ts";

export const beadSchema = z.looseObject({
  id: z.string().min(1),
  title: z.string(),
  description: z.string().default(""),
  acceptance_criteria: z.string().default(""),
  status: z.string(),
  assignee: z.string().default(""),
  revision: z.string().min(1),
  metadata: z.record(z.string(), z.unknown()).default({}),
});
export type NativeBead = z.infer<typeof beadSchema>;

export const verificationSchema = z.object({
  summary: z.string(),
  check: z.array(z.string()),
  exitCode: z.number().int().nullable(),
  gitHead: z.string(),
  gitState: z.string(),
  output: z.string(),
  reason: z.string().optional(),
});
export type Verification = z.infer<typeof verificationSchema>;

export const owner = (attempt: string): string => `pi:${attempt}`;
export class ClaimRefused extends Error {}
export class BeadChanged extends Error {}

export function sameBrief(left: NativeBead, right: NativeBead): boolean {
  return (
    left.id === right.id &&
    left.title === right.title &&
    left.description === right.description &&
    left.acceptance_criteria === right.acceptance_criteria
  );
}

export class TaskBeads extends BeadsHttp {
  private readonly reviewOnly: boolean;
  constructor(settings: NonNullable<DriverConfig["beadsService"]>) {
    super(
      settings.url,
      settings.projectId,
      settings.tokenFile === undefined
        ? undefined
        : readFileSync(settings.tokenFile, "utf8").trim(),
    );
    this.reviewOnly = settings.reviewOnly === true;
  }

  async get(id: string): Promise<NativeBead> {
    await this.verifyAuthority();
    const row = beadSchema.parse(
      await this.result(
        this.client.GET("/v0/beads/issues/{id}", { params: { path: { id } } }),
      ),
    );
    if (row.id !== id)
      throw new Error("Beads returned a different task identity");
    return row;
  }

  async list() {
    await this.verifyAuthority();
    const page = await this.result(
      this.client.GET("/v0/beads/issues", {
        params: { query: { limit: 1000, all: true } },
      }),
    );
    const relationships = new Map<
      string,
      components["schemas"]["Dependency"][]
    >();
    for (let offset = 0; offset < page.items.length; offset += 100) {
      const ids = page.items.slice(offset, offset + 100).map((task) => task.id);
      const batch = await this.result(
        this.client.GET("/v0/beads/dependencies", {
          params: { query: { issue_id: ids } },
        }),
      );
      if (batch.missing.length > 0)
        throw new Error(
          "The Beads graph changed while reading tasks. Refresh the tree",
        );
      for (const edge of batch.items) {
        const edges = relationships.get(edge.issue_id);
        if (edges === undefined) relationships.set(edge.issue_id, [edge]);
        else edges.push(edge);
      }
    }
    return {
      ...page,
      items: page.items.map((task) => ({
        ...task,
        dependencies: relationships.get(task.id) ?? [],
      })),
    };
  }

  private async write(
    before: NativeBead,
    attempt: string,
    patch: components["schemas"]["IssuePatchBody"],
  ) {
    return this.result(
      this.client.PATCH("/v0/beads/issues/{id}", {
        params: { path: { id: before.id } },
        body: {
          actor: owner(attempt),
          expected_version: before.revision,
          expected_status: before.status,
          expected_assignee: before.assignee,
          force_close_policy: false,
          force_assignee_transfer: false,
          patch,
        },
      }),
    );
  }

  private async requireReady(before: NativeBead): Promise<void> {
    if (before.status !== "open" || before.assignee !== "")
      throw new Error("The bead must be open and unclaimed");
    const list = (limit: number) =>
      this.result(
        this.client.GET("/v0/beads/ready", {
          params: { query: { unassigned: true, limit, brief: true } },
        }),
      );
    let ready = await list(1000);
    if (ready.has_more && !ready.items.some((item) => item.id === before.id)) {
      const count = await this.result(
        this.client.GET("/v0/beads/ready:count", {
          params: { query: { unassigned: true } },
        }),
      );
      ready = await list(Math.max(1, count.total));
    }
    if (!ready.items.some((item) => item.id === before.id)) {
      throw new Error(
        ready.has_more
          ? "Beads readiness could not be confirmed in this workspace"
          : "Beads reports that this task is not ready",
      );
    }
  }

  async claim(before: NativeBead, attempt: string): Promise<string> {
    try {
      await this.requireReady(before);
    } catch (cause) {
      throw new ClaimRefused(
        cause instanceof Error ? cause.message : String(cause),
        { cause },
      );
    }
    // Preserve the revision minted by the claim. A later detail read might already carry another writer's revision.
    const result = await this.write(before, attempt, {
      assignee: owner(attempt),
      status: "in_progress",
      metadata: { merge: { "pi.attempt": attempt } },
    }).catch((cause: unknown) => {
      if (
        cause instanceof BeadsError &&
        [400, 401, 403, 404, 409, 422].includes(cause.status)
      ) {
        throw new ClaimRefused(cause.message, { cause });
      }
      throw cause;
    });
    const confirmed = await this.get(before.id);
    if (
      confirmed.revision !== result.revision ||
      confirmed.assignee !== owner(attempt) ||
      confirmed.metadata["pi.attempt"] !== attempt ||
      !sameBrief(before, confirmed)
    ) {
      throw new Error(
        "The bead changed during admission. Inspect the recorded claim before dispatch",
      );
    }
    return result.revision;
  }

  async requireCurrent(
    accepted: NativeBead,
    revision: string,
    attempt: string,
  ): Promise<NativeBead> {
    const current = await this.get(accepted.id);
    if (
      !sameBrief(accepted, current) ||
      current.revision !== revision ||
      current.assignee !== owner(attempt) ||
      current.status !== "in_progress" ||
      current.metadata["pi.attempt"] !== attempt
    ) {
      throw new BeadChanged(
        "The accepted brief, revision or owner changed. Review the result against the current bead",
      );
    }
    return current;
  }

  async applyPlan(
    accepted: NativeBead,
    revision: string,
    attempt: string,
    digest: string,
    draft: LeadDraft,
  ): Promise<{ revision: string; children: Record<string, string> }> {
    if (this.reviewOnly)
      throw new Error("This Beads service requires operator-managed changes");
    const current = await this.requireCurrent(accepted, revision, attempt);
    if (draft.tasks.length === 0)
      return { revision: current.revision, children: {} };
    if (current.metadata["pi.plan"] !== undefined)
      throw new Error(
        "A task breakdown is already recorded. Inspect the Beads tree",
      );
    const items: components["schemas"]["ApplyItem"][] = [
      {
        kind: "update",
        update: {
          target: { id: current.id },
          expected_version: revision,
          expected_status: current.status,
          expected_assignee: owner(attempt),
          patch: { metadata: { merge: { "pi.plan": digest } } },
          force_close_policy: false,
          force_assignee_transfer: false,
        },
      },
    ];
    for (const task of orderedTasks(draft)) {
      items.push(
        {
          kind: "create",
          create: {
            key: task.key,
            title: task.title,
            description: task.description,
            acceptance_criteria: task.acceptance,
            issue_type: "task",
            ephemeral: false,
            no_history: false,
            metadata: { "pi.plan": digest, "pi.plan_key": task.key },
          },
        },
        {
          kind: "dep_add",
          dep_add: {
            source: { key: task.key },
            target: { id: current.id },
            type: "parent-child",
          },
        },
      );
      for (const blocker of task.blockedBy)
        items.push({
          kind: "dep_add",
          dep_add: {
            source: { key: task.key },
            target: { key: blocker },
            type: "blocks",
          },
        });
    }
    const result = await this.result(
      this.client.POST("/v0/beads/issues:batchApply", {
        body: {
          actor: owner(attempt),
          items,
          force_id_prefix: false,
          skip_per_edge_cycle_check: false,
        },
      }),
    );
    const patch = result.items[0];
    if (
      patch?.kind !== "update" ||
      patch.issue_id !== current.id ||
      draft.tasks.some((task) => !Object.hasOwn(result.keys, task.key))
    )
      throw new Error("Beads did not return a complete plan receipt");
    const confirmed = await this.requireCurrent(
      accepted,
      patch.revision,
      attempt,
    );
    if (confirmed.metadata["pi.plan"] !== digest)
      throw new Error("Beads did not confirm the approved plan");
    return { revision: confirmed.revision, children: result.keys };
  }

  async complete(
    accepted: NativeBead,
    revision: string,
    attempt: string,
    evidence: Verification,
    signal?: AbortSignal,
  ): Promise<void> {
    const current = await this.requireCurrent(accepted, revision, attempt);
    signal?.throwIfAborted();
    try {
      await this.write(current, attempt, {
        status: "closed",
        metadata: {
          merge: { "pi.result": evidence, "pi.result_attempt": attempt },
        },
      });
    } catch (cause) {
      if (cause instanceof BeadsError && cause.status === 409)
        throw new BeadChanged(cause.message, { cause });
      if (!(await this.closedWith(accepted.id, attempt, evidence))) throw cause;
      return;
    }
    if (!(await this.closedWith(accepted.id, attempt, evidence)))
      throw new Error(
        "Beads has not confirmed closure with this attempt's evidence",
      );
  }

  async closedWith(
    id: string,
    attempt: string,
    evidence: Verification,
  ): Promise<boolean> {
    const current = await this.get(id);
    return (
      current.status === "closed" &&
      current.metadata["pi.result_attempt"] === attempt &&
      isDeepStrictEqual(current.metadata["pi.result"], evidence)
    );
  }
}
