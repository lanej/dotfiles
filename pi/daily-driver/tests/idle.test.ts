import assert from "node:assert/strict";
import { test } from "node:test";
import { IdleCompactor, type IdleSnapshot } from "../idle.ts";

function fixture() {
  const snapshot: IdleSnapshot = {
    sessionId: "one",
    branchId: "leaf",
    historyId: "history",
    settled: true,
    pendingInput: false,
    editorText: "",
    dialogs: 0,
    children: 0,
    percent: 60,
  };
  let time = 0;
  let next = 0;
  const timers = new Map<number, { at: number; callback(): void }>();
  const attempts: string[] = [];
  const errors: Error[] = [];
  let requests = 0;
  let callbacks: { complete(): void; error(error: Error): void } | undefined;
  const controller = new IdleCompactor(
    {
      snapshot: () => ({ ...snapshot }),
      recordAttempt: (id) => {
        attempts.push(id);
      },
      notify: (error) => {
        errors.push(error);
      },
      compact: (value) => {
        requests++;
        callbacks = value;
      },
      schedule: (callback, delay) => {
        const id = ++next;
        timers.set(id, { at: time + delay, callback });
        return () => {
          timers.delete(id);
        };
      },
    },
    300_000,
    60,
  );
  const advance = (ms: number) => {
    time += ms;
    for (const [id, timer] of timers)
      if (timer.at <= time) {
        timers.delete(id);
        timer.callback();
      }
  };
  return {
    snapshot,
    controller,
    advance,
    attempts,
    errors,
    get requests() {
      return requests;
    },
    get callbacks() {
      return callbacks;
    },
  };
}

await test("five settled minutes AND 60 percent are required; one request per history", () => {
  const f = fixture();
  f.snapshot.percent = 59.9;
  f.controller.settled();
  f.advance(300_000);
  assert.equal(f.requests, 0);
  f.snapshot.percent = 60;
  f.controller.settled();
  f.advance(299_999);
  assert.equal(f.requests, 0);
  f.advance(1);
  assert.equal(f.requests, 1);
  f.callbacks?.complete();
  f.controller.settled();
  f.advance(300_000);
  assert.equal(f.requests, 1);
  f.snapshot.historyId = "next-turn";
  f.snapshot.branchId = "next-leaf";
  f.controller.settled();
  f.advance(300_000);
  assert.equal(f.requests, 2);
});

await test("new input restarts the idle window; drafts and unknown usage fail closed", () => {
  const f = fixture();
  f.controller.settled();
  f.advance(200_000);
  f.controller.activity();
  f.controller.settled();
  f.advance(200_000);
  assert.equal(f.requests, 0);
  f.snapshot.editorText = "unfinished instruction";
  f.advance(100_000);
  assert.equal(f.requests, 0);
  f.snapshot.editorText = "";
  f.snapshot.percent = null;
  f.controller.settled();
  f.advance(300_000);
  assert.equal(f.requests, 0);
});

await test("active work, queued input, dialogs, and children prevent requests", () => {
  for (const change of [
    { settled: false },
    { pendingInput: true },
    { dialogs: 1 },
    { children: 1 },
  ]) {
    const f = fixture();
    f.controller.settled();
    Object.assign(f.snapshot, change);
    f.advance(300_000);
    assert.equal(f.requests, 0, JSON.stringify(change));
  }
});

await test("replacement, branch changes, restore and failed requests do not replay stale timers", () => {
  const f = fixture();
  f.controller.settled();
  f.snapshot.sessionId = "replacement";
  f.advance(300_000);
  assert.equal(f.requests, 0);
  f.controller.settled();
  f.snapshot.branchId = "other-branch";
  f.advance(300_000);
  assert.equal(f.requests, 0);
  f.controller.restore("history");
  f.controller.settled();
  f.advance(300_000);
  assert.equal(f.requests, 0);
  f.snapshot.historyId = "fresh";
  f.controller.settled();
  f.advance(300_000);
  assert.equal(f.requests, 1);
  f.callbacks?.error(new Error("provider unavailable"));
  f.controller.settled();
  f.advance(300_000);
  assert.equal(f.requests, 1);
  assert.equal(f.errors[0]?.message, "provider unavailable");
  assert.deepEqual(f.attempts, ["fresh"]);
  f.snapshot.historyId = "later";
  f.controller.settled();
  f.controller.stop();
  f.advance(300_000);
  assert.equal(f.requests, 1);
});
