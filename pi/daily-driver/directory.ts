import {
  SessionManager,
  type ExtensionAPI,
  type ExtensionCommandContext,
} from "@earendil-works/pi-coding-agent";
import { constants } from "node:fs";
import { access, realpath, stat, unlink, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import { isAbsolute, join, resolve } from "node:path";
import { processFailure } from "./process.ts";
import type { DriverProfile } from "./config.ts";
import { PiMode, piModeSchema } from "./runtime.ts";

export const directoryProfileType = "pi-driver:directory-profile";

async function destination(argument: string, cwd: string): Promise<string> {
  let path = argument.trim();
  if (
    (path.startsWith('"') && path.endsWith('"')) ||
    (path.startsWith("'") && path.endsWith("'"))
  )
    path = path.slice(1, -1);
  if (path === "" || path === "~") path = homedir();
  else if (path.startsWith("~/")) path = join(homedir(), path.slice(2));
  const target = await realpath(isAbsolute(path) ? path : resolve(cwd, path));
  if (!(await stat(target)).isDirectory())
    throw new Error(`Not a directory: ${target}`);
  await access(target, constants.R_OK | constants.X_OK);
  return target;
}

export function registerDirectory(
  pi: ExtensionAPI,
  hasChildWork: (sessionId: string) => boolean,
  selectedProfile: () => DriverProfile | undefined = () => undefined,
): void {
  const blocked = (ctx: ExtensionCommandContext): string | undefined => {
    if (process.env["PI_DRIVER_ATTEMPT"] !== undefined)
      return "Managed tasks stay in their assigned checkout.";
    if (piModeSchema.parse(ctx.mode) !== PiMode.Tui)
      return "Use /cd in an interactive Pi terminal.";
    if (ctx.sessionManager.getSessionFile() === undefined)
      return "Directory switching requires a saved session; /cd is unavailable with --no-session.";
    if (!ctx.isIdle() || ctx.hasPendingMessages())
      return "Wait for the conversation and queued messages to settle before changing directories.";
    if (hasChildWork(ctx.sessionManager.getSessionId()))
      return "Settle delegated work before changing directories.";
    return undefined;
  };
  pi.registerCommand("cd", {
    description:
      "Change directory with the current conversation (default: home)",
    handler: async (argument, ctx) => {
      let reason = blocked(ctx);
      if (reason !== undefined) {
        ctx.ui.notify(reason, "warning");
        return;
      }
      let sessionFile: string;
      try {
        const target = await destination(argument, ctx.cwd);
        reason = blocked(ctx);
        if (reason !== undefined) {
          ctx.ui.notify(reason, "warning");
          return;
        }
        if (target === (await realpath(ctx.cwd))) {
          ctx.ui.notify(`Already in ${target}`, "info");
          return;
        }
        const parentSession = ctx.sessionManager.getSessionFile();
        const allocation = SessionManager.create(target, undefined, {
          ...(parentSession === undefined ? {} : { parentSession }),
        });
        const header = allocation.getHeader();
        const file = allocation.getSessionFile();
        if (header === null || file === undefined)
          throw new Error("Pi did not allocate a session");
        const manager = SessionManager.inMemory(target, undefined, [
          header,
          ...ctx.sessionManager.getEntries(),
        ]);
        // Reopening a tree selects its last stored entry. Anchor the continuation
        // to the user's selected branch, which may precede newer abandoned work.
        const leaf = ctx.sessionManager.getLeafId();
        if (leaf === null) manager.resetLeaf();
        else manager.branch(leaf);
        if (ctx.model !== undefined)
          manager.appendModelChange(ctx.model.provider, ctx.model.id);
        manager.appendThinkingLevelChange(pi.getThinkingLevel());
        manager.appendCustomMessageEntry(
          "pi-driver:directory",
          `Working directory changed from ${ctx.cwd} to ${target}.`,
          false,
        );
        manager.appendCustomEntry(
          directoryProfileType,
          selectedProfile() ?? null,
        );
        await writeFile(
          file,
          `${[manager.getHeader(), ...manager.getEntries()]
            .map((entry) => JSON.stringify(entry))
            .join("\n")}\n`,
          { flag: "wx", mode: 0o600 },
        );
        sessionFile = file;
      } catch (error) {
        ctx.ui.notify(processFailure(error).message, "error");
        return;
      }
      const result = await ctx.switchSession(sessionFile, {
        withSession: (next) => {
          next.ui.notify(`Working directory: ${next.cwd}`, "info");
          return Promise.resolve();
        },
      });
      if (result.cancelled) await unlink(sessionFile);
    },
  });
}
