export type Check = {
  id: number; name: string; app: number | null; status: string; conclusion: string | null;
  completedAt: string | null; url: string | null;
};
export type CommitStatus = { id: number; context: string; state: string; url: string | null };
export type PullRequest = {
  head: string; base: string; state: string; merged: boolean; draft: boolean;
  mergeable: boolean | null; mergeableState: string; checks: Check[]; statuses: CommitStatus[];
};
export function latestChecks(values: Check[]): Check[] {
  const latest = new Map<string, Check>();
  for (const value of values) {
    const key = JSON.stringify([value.app, value.name]);
    if (!latest.has(key) || latest.get(key)!.id < value.id) latest.set(key, value);
  }
  return [...latest.values()].sort((a, b) => a.id - b.id);
}
export function latestStatuses(values: CommitStatus[]): CommitStatus[] {
  const latest = new Map<string, CommitStatus>();
  for (const value of values) if (!latest.has(value.context) || latest.get(value.context)!.id < value.id) latest.set(value.context, value);
  return [...latest.values()].sort((a, b) => a.id - b.id);
}
export function watchPR(value: PullRequest) {
  const failures = value.checks.filter(check => check.status === "completed" &&
    check.conclusion !== null && !["success", "neutral", "skipped"].includes(check.conclusion));
  const statuses = value.statuses.filter(status => ["failure", "error"].includes(status.state));
  const conflict = value.mergeable === false;
  const pending = value.checks.some(check => check.status !== "completed" || check.conclusion === null) ||
    value.statuses.some(status => status.state === "pending");
  const repair = { conflict, checks: failures, statuses };
  if (value.state !== "open" || value.merged) return { phase: "closed" as const, detail: "PR is closed; no automatic repairs", repair: null };
  if (conflict || failures.length || statuses.length) return {
    phase: "repair" as const, detail: [conflict ? "Merge conflict" : "", ...failures.map(check => `${check.name}: ${check.conclusion}`),
      ...statuses.map(status => `${status.context}: ${status.state}`)].filter(Boolean).join("; "), repair,
  };
  if (pending || !value.checks.length && !value.statuses.length) return {
    phase: "checks" as const, detail: pending ? "Waiting for reported checks" : "No checks reported yet; passing CI is unverified", repair: null,
  };
  if (value.mergeable === null) return { phase: "unknown" as const, detail: "Reported checks passed; GitHub is still computing mergeability", repair: null };
  return { phase: "review" as const,
    detail: `Reported checks passed; watching review feedback${value.draft ? " on a draft PR" : ""}. Merge requires explicit authority`, repair: null };
}
