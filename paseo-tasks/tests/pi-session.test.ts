import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type { PaseoAgentHandle } from "@getpaseo/client";
import { test } from "node:test";
import { completedPiTurn, sessionEntries } from "../server/pi-session";

await test("Pi context follows the active branch without rewriting history or accepting corrupt ancestry", async () => {
  const cwd = await mkdtemp(join(tmpdir(), "pi-context-"));
  const file = join(cwd, "session.jsonl");
  const id = randomUUID();
  const header = { type: "session", version: 3, id, cwd };
  const message = (
    entryId: string,
    parentId: string | null,
    stopReason: string,
  ) => ({
    type: "message",
    id: entryId,
    parentId,
    message: {
      role: "assistant",
      stopReason,
      content: [{ type: "text", text: entryId }],
    },
  });
  const handle = {
    current: () => ({
      provider: "pi",
      cwd,
      persistence: { nativeHandle: file },
      lastUserMessageAt: "now",
    }),
    runtimeInfo: { sessionId: id },
  } as unknown as PaseoAgentHandle;
  const save = async (...entries: unknown[]) => {
    const content =
      [header, ...entries].map((entry) => JSON.stringify(entry)).join("\n") +
      "\n";
    await writeFile(file, content);
    return content;
  };
  try {
    const history = await save(
      message("completed", null, "stop"),
      message("abandoned", "completed", "aborted"),
      {
        type: "custom",
        id: "active",
        parentId: "completed",
        customType: "status",
        data: {},
      },
    );
    assert.equal(await completedPiTurn(handle), `pi:${id}:completed`);
    assert.equal(
      await readFile(file, "utf8"),
      history,
      "Inspection must not migrate or rewrite Pi's live session",
    );
    await save(
      message("completed", null, "stop"),
      message("abandoned", "completed", "aborted"),
      {
        type: "compaction",
        id: "compacted",
        parentId: "completed",
        firstKeptEntryId: "completed",
        summary: "Earlier context summarized",
        tokensBefore: 100,
      },
    );
    assert.equal(await completedPiTurn(handle), `pi:${id}:completed`);
    await save(message("pending", null, "toolUse"));
    assert.equal(await completedPiTurn(handle), null);
    await assert.rejects(
      () => sessionEntries(file, randomUUID(), cwd),
      /does not match/,
    );
    await assert.rejects(
      () => sessionEntries(file, id, join(cwd, "other")),
      /does not match/,
    );
    await save(message("cycle", "cycle", "stop"));
    await assert.rejects(
      () => completedPiTurn(handle),
      /ancestry is unreadable/,
    );
    await writeFile(file, `${history}{broken\n`);
    await assert.rejects(() => completedPiTurn(handle), SyntaxError);
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});
