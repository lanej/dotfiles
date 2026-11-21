import assert from "node:assert/strict";
import { test } from "node:test";
import { IdleSession, type IdleSessionHost } from "../idle.ts";
import { PiEvent } from "../runtime.ts";

await test("idle session restores attempts and preserves unknown child work across reinitialization", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const idle = new IdleSession();
  let requests = 0;
  let draft = "";
  let sessionId = "session";
  let historyId = "turn";
  let recordedHistory: string | null = null;
  const host: IdleSessionHost = {
    snapshot: () => ({
      sessionId,
      branchId: historyId,
      historyId,
      settled: true,
      pendingInput: false,
      editorText: draft,
      percent: 60,
    }),
    recordAttempt: (id) => {
      recordedHistory = id;
    },
    compact: (callbacks) => {
      requests++;
      callbacks.complete();
    },
    notify: (error) => {
      throw error;
    },
    schedule: (callback, delay) => {
      const timer = setTimeout(callback, delay);
      return () => {
        clearTimeout(timer);
      };
    },
  };
  const initialize = () => {
    idle.initialize(host, 300_000, 60, recordedHistory);
  };
  try {
    idle.newSession();
    initialize();
    t.mock.timers.tick(299_999);
    assert.equal(requests, 0);
    t.mock.timers.tick(1);
    assert.equal(requests, 1);
    assert.equal(recordedHistory, "turn");
    idle.stop();
    idle.newSession();
    initialize();
    t.mock.timers.tick(300_000);
    assert.equal(requests, 1, "resumed history must not compact again");
    historyId = "next-turn";
    idle.agentSettled();
    draft = "unfinished";
    t.mock.timers.tick(300_000);
    assert.equal(requests, 1);
    draft = "";
    idle.terminalInput();
    t.mock.timers.tick(300_000);
    assert.equal(requests, 2);

    idle.toolStart("subagent");
    for (const event of [PiEvent.SessionTree, PiEvent.SessionCompact]) {
      initialize();
      historyId = `after-${event}`;
      idle.agentSettled();
      t.mock.timers.tick(300_000);
      assert.equal(
        requests,
        2,
        `${event} must not clear the unknown-child guard`,
      );
    }

    idle.stop();
    sessionId = "next-session";
    historyId = "fresh-session";
    idle.newSession();
    initialize();
    t.mock.timers.tick(300_000);
    assert.equal(
      requests,
      3,
      "new session startup resets the child-work guard",
    );
    historyId = "shutdown-turn";
    idle.agentSettled();
    idle.stop();
    t.mock.timers.tick(300_000);
    assert.equal(requests, 3, "shutdown cancels the pending timer");
  } finally {
    idle.stop();
    t.mock.timers.reset();
  }
});
