import assert from "node:assert/strict";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import type {
  ExtensionAPI,
  ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import dailyDriver from "../extension.ts";

test("Pi lifecycle adapter compacts settled history once and restores its native marker", async (t) => {
  const temporary = await mkdtemp(join(tmpdir(), "pi-driver-extension-"));
  const previous = process.env.PI_DRIVER_CONFIG;
  process.env.PI_DRIVER_CONFIG = join(temporary, "config.json");
  await writeFile(process.env.PI_DRIVER_CONFIG, "{}");
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const handlers = new Map<
    string,
    (event: object, context: ExtensionContext) => unknown
  >();
  const entries: {
    type: string;
    id: string;
    customType?: string;
    data?: unknown;
  }[] = [{ type: "message", id: "turn" }];
  let requests = 0;
  let draft = "";
  let terminalInput: (() => void) | undefined;
  const api = {
    on: (
      name: string,
      handler: (event: object, context: ExtensionContext) => unknown,
    ) => {
      handlers.set(name, handler);
    },
    registerCommand: () => {},
    appendEntry: (customType: string, data: unknown) => {
      entries.push({ type: "custom", id: "attempt", customType, data });
    },
  } as unknown as ExtensionAPI;
  const context = {
    mode: "tui",
    hasUI: true,
    isIdle: () => true,
    hasPendingMessages: () => false,
    getContextUsage: () => ({ percent: 60 }),
    sessionManager: {
      getBranch: () => entries,
      getSessionId: () => "session",
      getLeafId: () => entries.at(-1)?.id,
    },
    compact: (options: { onComplete(): void }) => {
      requests++;
      options.onComplete();
    },
    ui: {
      setStatus: () => {},
      notify: () => {},
      getEditorText: () => draft,
      onTerminalInput: (handler: () => void) => {
        terminalInput = handler;
        return () => {
          terminalInput = undefined;
        };
      },
    },
  } as unknown as ExtensionContext;
  const emit = async (name: string) => {
    await handlers.get(name)?.({}, context);
  };
  try {
    dailyDriver(api);
    await emit("session_start");
    t.mock.timers.tick(299_999);
    assert.equal(requests, 0);
    t.mock.timers.tick(1);
    assert.equal(requests, 1);
    assert.equal(entries.at(-1)?.customType, "pi-driver:idle-attempt");
    await emit("session_shutdown");
    await emit("session_start");
    t.mock.timers.tick(300_000);
    assert.equal(requests, 1, "resumed history must not compact again");
    entries.push({ type: "message", id: "next-turn" });
    await emit("agent_settled");
    draft = "unfinished";
    t.mock.timers.tick(300_000);
    assert.equal(requests, 1);
    draft = "";
    terminalInput?.();
    t.mock.timers.tick(300_000);
    assert.equal(requests, 2);
    await emit("session_shutdown");
    assert.equal(terminalInput, undefined);
  } finally {
    t.mock.timers.reset();
    if (previous === undefined) delete process.env.PI_DRIVER_CONFIG;
    else process.env.PI_DRIVER_CONFIG = previous;
    await rm(temporary, { recursive: true, force: true });
  }
});
