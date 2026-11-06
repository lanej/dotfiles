import { Octokit } from "@octokit/rest";
import { createHash } from "node:crypto";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import type { Store } from "./store";
import type { Task, TaskEvent } from "../shared/contracts";
import { latestChecks, latestStatuses, watchPR, type PullRequest } from "./pr-watch";

export const digest = (value: unknown) => createHash("sha256").update(JSON.stringify(value)).digest("hex");
export function githubObject(url: string) {
  const match = /^https:\/\/github\.com\/([A-Za-z0-9-]+)\/([A-Za-z0-9_.-]+)\/(issues|pull)\/([1-9][0-9]*)$/.exec(url);
  if (!match) throw new Error("Use an exact GitHub issue or pull request URL");
  return { owner: match[1], repo: match[2], kind: match[3], number: Number(match[4]) };
}
type Comment = {
  id: number; body?: string | null; html_url?: string; user?: { login: string } | null;
  updated_at?: string; submitted_at?: string | null; state?: string;
  commit_id?: string; in_reply_to_id?: number; path?: string; line?: number | null;
};
export type Observation = {
  head: string | null; state: unknown;
  pullRequest?: PullRequest;
  events: { type: string; item: Comment }[];
};
export interface GitHubPort {
  observe(url: string): Promise<Observation>;
  login(): Promise<string>;
  comments(url: string, inline: boolean): Promise<Comment[]>;
  submit(url: string, inline: boolean, commentId: number | null, body: string): Promise<{ html_url: string }>;
}
export class GitHub implements GitHubPort {
  private client?: Octokit;
  constructor(private readonly token?: string, private readonly baseUrl?: string) {}
  private async api() {
    if (!this.client) {
      const auth = this.token ?? process.env.GH_TOKEN ?? process.env.GITHUB_TOKEN ??
        (await promisify(execFile)("gh", ["auth", "token"], { timeout: 10000 })).stdout.trim();
      this.client = new Octokit({ auth, baseUrl: this.baseUrl, request: { timeout: 15000 } });
    }
    return this.client;
  }
  private async list(route: string, parameters: Record<string, unknown>): Promise<Comment[]> {
    const api = await this.api();
    const rows: Comment[] = [];
    let count = 0;
    for await (const page of api.paginate.iterator(route, { ...parameters, per_page: 100 })) {
      if (++count > 100) throw new Error("GitHub pagination bound reached; observation remains incomplete");
      rows.push(...page.data as Comment[]);
    }
    return rows;
  }
  async login() { return (await (await this.api()).users.getAuthenticated()).data.login; }
  async comments(url: string, inline: boolean) {
    const value = githubObject(url);
    return this.list(inline ? "GET /repos/{owner}/{repo}/pulls/{pull_number}/comments" :
      "GET /repos/{owner}/{repo}/issues/{issue_number}/comments",
    { ...value, pull_number: value.number, issue_number: value.number });
  }
  async observe(url: string): Promise<Observation> {
    const value = githubObject(url);
    const api = await this.api();
    const events = (await this.comments(url, false)).map(item => ({ type: "comment", item }));
    if (value.kind === "issues") {
      const core = (await api.issues.get({ ...value, issue_number: value.number })).data;
      return { head: null, events, state: { state: core.state, title: core.title, body: core.body, updatedAt: core.updated_at } };
    }
    const core = (await api.pulls.get({ ...value, pull_number: value.number })).data;
    const [reviews, inline, checks, statuses] = await Promise.all([
      this.list("GET /repos/{owner}/{repo}/pulls/{pull_number}/reviews", { ...value, pull_number: value.number }),
      this.comments(url, true),
      api.paginate(api.checks.listForRef, { ...value, ref: core.head.sha, filter: "latest", per_page: 100 }),
      api.paginate(api.repos.listCommitStatusesForRef, { ...value, ref: core.head.sha, per_page: 100 }),
    ]);
    events.push(...reviews.filter(item => item.state !== "PENDING").map(item => ({ type: "review", item })),
      ...inline.map(item => ({ type: "inline", item })));
    const threads: { id: string; resolved: boolean; commentId: number | null }[] = [];
    let cursor: string | null = null;
    for (let page = 0; page < 100; page++) {
      const result: any = await api.graphql(
        "query($owner:String!,$repo:String!,$number:Int!,$cursor:String){repository(owner:$owner,name:$repo){pullRequest(number:$number){reviewThreads(first:100,after:$cursor){nodes{id isResolved comments(first:1){nodes{databaseId}}}pageInfo{hasNextPage endCursor}}}}}",
        { owner: value.owner, repo: value.repo, number: value.number, cursor });
      const batch = result.repository?.pullRequest?.reviewThreads;
      if (!Array.isArray(batch?.nodes) || !batch.pageInfo) throw new Error("GitHub inline discussion observation is incomplete");
      threads.push(...batch.nodes.map((thread: any) => ({ id: thread.id, resolved: thread.isResolved,
        commentId: thread.comments?.nodes[0]?.databaseId ?? null })));
      if (!batch.pageInfo.hasNextPage) break;
      cursor = batch.pageInfo.endCursor;
      if (!cursor || page === 99) throw new Error("GitHub inline discussion pagination bound reached");
    }
    const closing = (await api.pulls.get({ ...value, pull_number: value.number })).data;
    if (closing.head.sha !== core.head.sha || closing.base.sha !== core.base.sha) throw new Error("GitHub revision changed during observation");
    const pullRequest: PullRequest = {
      state: closing.state, merged: closing.merged, draft: closing.draft ?? false, head: core.head.sha, base: core.base.sha,
      mergeable: closing.mergeable, mergeableState: closing.mergeable_state,
      checks: latestChecks(checks.map(item => ({ id: item.id, name: item.name, app: item.app?.id ?? null,
        status: item.status, conclusion: item.conclusion, completedAt: item.completed_at, url: item.html_url }))),
      statuses: latestStatuses(statuses.map(item => ({ id: item.id, context: item.context, state: item.state, url: item.target_url }))),
    };
    return { head: core.head.sha, events, pullRequest, state: {
      ...pullRequest, threads,
      reviews: reviews.map(item => ({ id: item.id, state: item.state, revision: item.commit_id })),
    } };
  }
  async submit(url: string, inline: boolean, commentId: number | null, body: string) {
    const value = githubObject(url);
    const api = await this.api();
    if (inline) {
      if (!Number.isSafeInteger(commentId) || !commentId) throw new Error("Inline feedback has no source comment");
      return (await api.pulls.createReplyForReviewComment({ ...value, pull_number: value.number, comment_id: commentId, body })).data;
    }
    return (await api.issues.createComment({ ...value, issue_number: value.number, body })).data;
  }
}
type ObjectState = { seen: string[]; state: string | null; version: number; nextPollAt?: string };
type Reply = { body: string; login: string; state: "intent" | "unknown" | "confirmed"; source: string | null };

export class Feedback {
  constructor(readonly store: Store, readonly github: GitHubPort, readonly owner: string,
    readonly intervals = { checks: 30000, review: 120000 }) {}
  async poll(value: Task) {
    for (const url of value.github) {
      const saved = this.store.read<ObjectState>("objects", url) ?? { seen: [], state: null, version: 0 };
      const now = this.store.now();
      if (saved.nextPollAt && saved.nextPollAt > now) continue;
      let observation: Observation;
      try { observation = await this.github.observe(url); }
      catch (error) {
        const failure = error as { status?: number; response?: { headers?: Record<string, string> } };
        const headers = failure.response?.headers ?? {};
        const retry = Number(headers["retry-after"]);
        const reset = Number(headers["x-ratelimit-reset"]);
        const delay = [403, 429].includes(failure.status ?? 0) ? this.intervals.review : this.intervals.checks;
        saved.nextPollAt = new Date(Math.max(Date.parse(now) + delay,
          Number.isFinite(retry) ? Date.parse(now) + retry * 1000 : 0,
          headers["x-ratelimit-remaining"] === "0" && Number.isFinite(reset) ? reset * 1000 + 1000 : 0)).toISOString();
        this.store.write("objects", url, saved);
        throw new Error(`GitHub polling failed for ${url}; retry after ${saved.nextPollAt}: ${error instanceof Error ? error.message : String(error)}`);
      }
      const previous = this.store.get(value.taskId).error;
      if (previous?.startsWith(`GitHub polling failed for ${url};`)) {
        this.store.change(value.taskId, current => { if (current.error === previous) current.error = null; });
      }
      const watch = observation.pullRequest ? watchPR(observation.pullRequest) : null;
      for (const { type, item } of observation.events) {
        const marker = /<!-- (?:paseo-task|firstmate)-feedback:([a-f0-9]{64}) -->/.exec(item.body ?? "");
        const reply = marker ? this.store.read<Reply>("replies", marker[1]) : null;
        if (reply && reply.body === item.body && reply.login === item.user?.login) continue;
        const id = digest([url, type, item.id, item.updated_at ?? item.submitted_at, item.body, item.state]);
        if (saved.seen.includes(id)) continue;
        this.store.addEvent(value.taskId, "github", item.body ?? "", {
          id, source: item.html_url ?? url, payload: {
            url, type, author: item.user?.login, authority: item.user?.login === this.owner ? "owner-direction" : "review-input",
            revision: item.commit_id ?? observation.head, state: item.state,
            commentId: item.in_reply_to_id ?? item.id, path: item.path, line: item.line,
          },
        });
        saved.seen.push(id);
      }
      if (watch && observation.pullRequest) {
        const pr = observation.pullRequest;
        const previousStatus = this.store.events(value.taskId).find(entry => entry.delivery === "queued" &&
          entry.payload.type === "repair" && entry.payload.url === url &&
          ["complete", "decision"].includes(String(entry.payload.previousStatus)))?.payload.previousStatus ?? this.store.get(value.taskId).status;
        if (watch.repair) this.store.addEvent(value.taskId, "github",
          `Repair the linked PR within the accepted task scope: ${watch.detail}`, {
            id: digest([value.taskId, url, "repair", pr.head, pr.base, watch.repair]), source: url,
            payload: { url, type: "repair", authority: "task-policy", revision: pr.head, baseRevision: pr.base,
              observation: pr, repair: watch.repair, previousStatus },
          });
        this.store.change(value.taskId, current => {
          const recorded = { url, head: pr.head, base: pr.base, phase: watch.phase, detail: watch.detail, observedAt: now };
          current.prWatches = [...current.prWatches.filter(item => item.url !== url), recorded];
        });
        const currentRepair = watch.repair ? digest([value.taskId, url, "repair", pr.head, pr.base, watch.repair]) : null;
        const superseded = this.store.events(value.taskId).filter(item => item.delivery === "queued" &&
          item.payload.type === "repair" && item.payload.url === url && item.id !== currentRepair &&
          (["closed", "review"].includes(watch.phase) || currentRepair !== null ||
            item.payload.revision !== pr.head || item.payload.baseRevision !== pr.base));
        for (const entry of superseded) {
          this.store.saveEvent({ ...entry, delivery: "handled", payload: { ...entry.payload,
            superseded: { phase: watch.phase, head: pr.head, base: pr.base, observedAt: now } } });
        }
        const waiting = superseded.find(entry => ["complete", "decision"].includes(String(entry.payload.previousStatus)))?.payload.previousStatus;
        if (!currentRepair && waiting && !this.store.events(value.taskId).some(entry => entry.delivery !== "handled" &&
          (entry.kind === "feedback" || entry.kind === "github" && entry.payload.type !== "state" ||
            ["queued", "sending", "unknown"].includes(entry.delivery)))) {
          this.store.change(value.taskId, current => {
            if (current.status === "active" && current.activity === "idle") current.status = waiting as "complete" | "decision";
          });
        }
      }
      const state = digest(observation.state);
      if (state !== saved.state) {
        saved.version++;
        this.store.transaction(() => {
          const passive = this.store.addEvent(value.taskId, "github", "GitHub revision and checks changed", {
            id: digest([url, saved.version, state]), source: url,
            payload: { url, type: "state", revision: observation.head, observation: observation.state },
          });
          this.store.saveEvent({ ...passive, delivery: "handled" });
        });
        saved.state = state;
      }
      saved.nextPollAt = new Date(Date.parse(now) + (watch && !["review", "closed"].includes(watch.phase) ?
        this.intervals.checks : this.intervals.review)).toISOString();
      this.store.write("objects", url, saved);
    }
  }
  async reply(value: Task, eventId: string, text: string, expectedHead: string | null) {
    const entry = this.store.events(value.taskId).find(item => item.id === eventId && item.kind === "github");
    if (!entry || !["comment", "review", "inline"].includes(String(entry.payload.type))) throw new Error("Select pending source feedback on this task");
    if (!text.trim() || text.length > 60000) throw new Error("Reply must contain 1..60000 characters");
    const url = String(entry.payload.url);
    if (!value.github.includes(url)) throw new Error("Feedback link is no longer owned by this task");
    const observed = await this.github.observe(url);
    if (observed.head !== expectedHead) throw new Error("GitHub revision changed; inspect the current revision before replying");
    const previous = this.store.read<Reply>("replies", eventId);
    const body = previous?.body ?? `${text}\n\n<!-- paseo-task-feedback:${eventId} -->`;
    if (previous && !previous.body.startsWith(`${text}\n\n<!--`)) throw new Error("Reply intent differs; reconcile the previous submission first");
    const login = await this.github.login();
    if (previous && previous.login !== login) throw new Error("GitHub identity changed; reconcile the original reply");
    const inline = entry.payload.type === "inline";
    const found = (await this.github.comments(url, inline)).find(item => item.body === body && item.user?.login === login);
    if (found?.html_url) {
      this.store.write("replies", eventId, { body, login, state: "confirmed", source: found.html_url });
      return found.html_url;
    }
    if (previous?.state === "unknown" || previous?.state === "intent" || previous?.state === "confirmed") {
      throw new Error("Previous GitHub submission is unresolved; no duplicate was sent. Retry reconciliation after GitHub exposes the reply");
    }
    // WHY: Concurrent tool calls must reserve one durable POST after their asynchronous reads.
    if (!this.store.claimReply(eventId, { body, login, state: "intent", source: null })) {
      throw new Error("Another GitHub submission already owns this event; reconcile its receipt before retrying");
    }
    try {
      const result = await this.github.submit(url, inline, Number(entry.payload.commentId), body);
      this.store.write("replies", eventId, { body, login, state: "confirmed", source: result.html_url });
      return result.html_url;
    } catch (error) {
      this.store.write("replies", eventId, { body, login, state: "unknown", source: null });
      throw error;
    }
  }
  acknowledge(entry: TaskEvent, summary: string) {
    if (!summary.trim()) throw new Error("Supply a feedback outcome");
    this.store.change(entry.taskId, value => { value.progress = summary; });
    this.store.saveEvent({ ...entry, delivery: "handled" });
  }
}
