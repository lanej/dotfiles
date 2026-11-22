import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import {
  buildContextEntries,
  CURRENT_SESSION_VERSION,
  parseSessionEntries,
  type SessionEntry,
} from "@earendil-works/pi-coding-agent";
import type { PaseoAgentHandle } from "@getpaseo/client";
import { z } from "zod";

const header = z.object({
  type: z.literal("session"),
  version: z.literal(CURRENT_SESSION_VERSION),
  id: z.uuid(),
  cwd: z.string().min(1),
});
export async function sessionEntries(
  file: string,
  id: string | null,
  cwd: string,
) {
  const content = await readFile(file, "utf8");
  // WHY: Pi tolerates malformed JSONL; ownership and completion checks must fail closed.
  const entries = parseSessionEntries(content);
  if (
    entries.length !== content.split("\n").filter((line) => line.trim()).length
  )
    throw new SyntaxError("Pi session contains malformed JSONL records");
  const identity = header.parse(entries[0]);
  if ((id && identity.id !== id) || resolve(identity.cwd) !== resolve(cwd)) {
    throw new Error(
      "Pi session header does not match the recorded session and checkout",
    );
  }
  return { identity, entries: entries.slice(1) as SessionEntry[] };
}
export async function completedPiTurn(
  handle: PaseoAgentHandle,
): Promise<string | null> {
  const snapshot = handle.current();
  const file = snapshot?.persistence?.nativeHandle;
  if (snapshot?.provider !== "pi" || !file || !snapshot.cwd) return null;
  const session = await sessionEntries(
    file,
    handle.runtimeInfo?.sessionId ?? null,
    snapshot.cwd,
  ).catch(async (error) => {
    // WHY: Pi reserves an unwritten path; imported history may still have a null last-message timestamp.
    if (error.code === "ENOENT" && !snapshot.lastUserMessageAt) {
      const history = await handle.timeline.refetch({
        direction: "tail",
        limit: 1,
      });
      if (!history.entries.length) return null;
    }
    throw error;
  });
  if (!session) return null;
  const { identity, entries } = session;
  const byId = new Map(
    entries
      .filter((entry) => typeof entry.id === "string")
      .map((entry) => [entry.id, entry]),
  );
  let current = entries.at(-1);
  const visited = new Set<string>();
  while (current) {
    if (typeof current.id !== "string" || visited.has(current.id))
      throw new Error("Pi session ancestry is unreadable");
    visited.add(current.id);
    current = current.parentId ? byId.get(current.parentId) : undefined;
  }
  const latest = buildContextEntries(entries).findLast(
    (entry) => entry.type === "message",
  );
  // WHY: Idle alone cannot distinguish a completed turn from cancellation or a pending tool call.
  return latest?.type === "message" &&
    latest.message.role === "assistant" &&
    latest.message.stopReason === "stop"
    ? `pi:${identity.id}:${latest.id}`
    : null;
}
