import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { z } from "zod";
import type { PaseoAgentHandle } from "@getpaseo/client";

const header = z.object({ type: z.literal("session"), version: z.literal(3), id: z.uuid(), cwd: z.string().min(1) });
export async function sessionEntries(file: string, id: string | null, cwd: string) {
  const entries = (await readFile(file, "utf8")).trim().split("\n").map(line => JSON.parse(line));
  const identity = header.parse(entries[0]);
  if ((id && identity.id !== id) || resolve(identity.cwd) !== resolve(cwd)) {
    throw new Error("Pi session header does not match the recorded session and checkout");
  }
  return { identity, entries: entries.slice(1) };
}
export async function completedPiTurn(handle: PaseoAgentHandle): Promise<string | null> {
  const snapshot = handle.current();
  const file = snapshot?.persistence?.nativeHandle;
  if (snapshot?.provider !== "pi" || !file || !snapshot.cwd) return null;
  const session = await sessionEntries(file, handle.runtimeInfo?.sessionId ?? null, snapshot.cwd).catch(async error => {
    // WHY: Pi reserves an unwritten path; imported history may still have a null last-message timestamp.
    if (error.code === "ENOENT" && !snapshot.lastUserMessageAt) {
      const history = await handle.timeline.refetch({ direction: "tail", limit: 1 });
      if (!history.entries.length) return null;
    }
    throw error;
  });
  if (!session) return null;
  const { identity, entries } = session;
  const byId = new Map(entries.filter(entry => typeof entry.id === "string").map(entry => [entry.id, entry]));
  let current = entries.at(-1);
  const visited = new Set<string>();
  while (current) {
    if (typeof current.id !== "string" || visited.has(current.id)) throw new Error("Pi session ancestry is unreadable");
    visited.add(current.id);
    if (current.type === "message") {
      // WHY: Idle alone cannot distinguish a completed turn from cancellation or a pending tool call.
      return current.message?.role === "assistant" && current.message.stopReason === "stop" ?
        `pi:${identity.id}:${current.id}` : null;
    }
    current = current.parentId ? byId.get(current.parentId) : undefined;
  }
  return null;
}
