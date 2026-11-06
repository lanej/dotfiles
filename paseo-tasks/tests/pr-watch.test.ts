import { test } from "node:test";
import assert from "node:assert/strict";
import { latestChecks, latestStatuses, watchPR, type PullRequest } from "../server/pr-watch";

test("current check attempts and commit status contexts replace historical failures without hiding other apps", () => {
  const checks = latestChecks([
    { id: 1, name: "test", app: 10, status: "completed", conclusion: "failure", completedAt: "earlier", url: null },
    { id: 3, name: "test", app: 10, status: "completed", conclusion: "success", completedAt: "later", url: null },
    { id: 2, name: "test", app: 11, status: "completed", conclusion: "failure", completedAt: "earlier", url: null },
  ]);
  assert.deepEqual(checks.map(value => value.id), [2, 3]);
  const statuses = latestStatuses([
    { id: 30, context: "build", state: "success", url: null }, { id: 20, context: "build", state: "failure", url: null },
  ]);
  assert.deepEqual(statuses.map(value => value.id), [30]);
  const clean: PullRequest = { state: "open", merged: false, draft: false, head: "h", base: "b",
    mergeable: true, mergeableState: "clean", checks: [checks[1]], statuses };
  assert.equal(watchPR(clean).phase, "review");
  assert.equal(watchPR({ ...clean, checks }).phase, "repair");
  assert.equal(watchPR({ ...clean, mergeable: null }).phase, "unknown");
  assert.equal(watchPR({ ...clean, mergeable: false }).repair!.conflict, true);
  assert.equal(watchPR({ ...clean, checks: [], statuses: [] }).phase, "checks");
  assert.equal(watchPR({ ...clean, state: "closed", mergeable: false, checks }).phase, "closed");
});
