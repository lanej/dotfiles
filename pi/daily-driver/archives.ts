import { readFile, stat } from "node:fs/promises";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import type {
  ExtensionAPI,
  ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import { getSelectListTheme } from "@earendil-works/pi-coding-agent";
import { Input, matchesKey, SelectList, Text } from "@earendil-works/pi-tui";
import { z } from "zod";
import { Attempts, stateDirectory } from "./attempts.ts";
import { loadConfig } from "./config.ts";
import { processFailure } from "./process.ts";
import { NavigationKey } from "./runtime.ts";
import { showTask } from "./ui.ts";

// Session Snap archive schema and searchable picker adapted from tomsej/pi-ext (MIT).
const entry = z.object({
  id: z.string(),
  name: z.string().nullable(),
  cwd: z.string().nullable(),
  first_message: z.string().nullable(),
});
const previewEntry = z.object({
  type: z.literal("message"),
  message: z.object({
    role: z.enum(["user", "assistant"]),
    content: z.union([
      z.string(),
      z.array(z.looseObject({ type: z.string(), text: z.string().optional() })),
    ]),
  }),
});
const inline = (value: string) => value.replace(/\p{Cc}/gu, " ");
const clean = (value: string) => value.replace(/(?!\n)\p{Cc}/gu, "");
const caption = (row: z.infer<typeof entry>) =>
  inline(row.name ?? row.first_message ?? row.id);

async function pick(
  ctx: ExtensionContext,
  rows: z.infer<typeof entry>[],
  initial: string,
) {
  return ctx.ui.custom<{ id: string; query: string } | undefined>(
    (tui, theme, _keys, done) => {
      const input = new Input({ placeholder: "Search archives" });
      input.setValue(initial);
      const title = new Text(theme.fg("accent", "Archives"), 0, 0);
      function makeList() {
        const term = input.getValue().trim().toLowerCase();
        const list = new SelectList(
          rows
            .filter((row) =>
              [caption(row), row.cwd, row.first_message].some(
                (value) => value?.toLowerCase().includes(term) === true,
              ),
            )
            .map((row) => ({ value: row.id, label: caption(row) })),
          Math.max(2, Math.min(tui.terminal.rows - 8, 12)),
          getSelectListTheme(),
        );
        list.onSelect = (item) => {
          done({ id: item.value, query: input.getValue() });
        };
        return list;
      }
      let list = makeList();
      return {
        focused: false,
        invalidate() {
          title.invalidate();
          list.invalidate();
          input.invalidate();
        },
        render(width) {
          return [
            ...title.render(width),
            ...input.render(width),
            "",
            ...list.render(width),
          ];
        },
        handleInput(data) {
          if (
            matchesKey(data, NavigationKey.Escape) ||
            matchesKey(data, NavigationKey.Cancel)
          )
            done(undefined);
          else if (
            matchesKey(data, NavigationKey.Up) ||
            matchesKey(data, NavigationKey.Down) ||
            matchesKey(data, NavigationKey.Enter)
          )
            list.handleInput(data);
          else {
            input.handleInput(data);
            list = makeList();
          }
          tui.requestRender();
        },
      };
    },
  );
}

export function registerArchives(pi: ExtensionAPI): void {
  pi.registerCommand("archives", {
    description: "Browse archived Pi and Session Snap transcripts",
    async handler(argument, ctx) {
      if (!ctx.hasUI) throw new Error("Archive browsing requires the Pi TUI");
      const config = await loadConfig();
      const path =
        config.archives.database ??
        join(homedir(), ".pi/agent/session-archive.db");
      const { Database } = await import("bun:sqlite");
      const { gunzipSync } = await import("node:zlib");
      let query = argument;
      try {
        for (;;) {
          const managed = new Map<string, string>();
          const rows: z.infer<typeof entry>[] = [];
          const database = join(stateDirectory(), "attempts.sqlite");
          if (
            (await stat(database).catch((error: unknown) => {
              if (processFailure(error).code === "ENOENT") return undefined;
              throw error;
            })) !== undefined
          ) {
            const driver = new Attempts(stateDirectory(), true);
            try {
              for (const attempt of driver.archives()) {
                if (attempt.archiveManifest === undefined) continue;
                const id = `managed:${attempt.id}`;
                managed.set(
                  id,
                  join(dirname(attempt.archiveManifest), `${attempt.id}.jsonl`),
                );
                rows.push({
                  id,
                  name: attempt.bead.title,
                  cwd: attempt.checkout?.path ?? null,
                  first_message: attempt.bead.description,
                });
              }
            } finally {
              driver.close();
            }
          }
          if (
            (await stat(path).catch((error: unknown) => {
              if (processFailure(error).code === "ENOENT") return undefined;
              throw error;
            })) !== undefined
          ) {
            const db = new Database(path, { readonly: true });
            try {
              rows.push(
                ...z
                  .array(entry)
                  .parse(
                    db
                      .prepare(
                        "SELECT id, substr(name, 1, 256) AS name, substr(cwd, 1, 1024) AS cwd, substr(first_message, 1, 1024) AS first_message FROM sessions ORDER BY archived_at DESC, id LIMIT 1000",
                      )
                      .all(),
                  ),
              );
            } finally {
              db.close();
            }
          }
          if (rows.length === 0) {
            ctx.ui.notify("No archived sessions", "info");
            return;
          }
          const selected = await pick(ctx, rows, query);
          if (selected === undefined) return;
          query = selected.query;
          try {
            const file = managed.get(selected.id);
            let transcript: string;
            if (file !== undefined) {
              if ((await stat(file)).size > 4 * 1024 * 1024)
                throw new Error("Archive exceeds preview size");
              transcript = await readFile(file, "utf8");
            } else {
              const archive = new Database(path, { readonly: true });
              try {
                const raw = z
                  .object({ jsonl_gzip: z.instanceof(Uint8Array) })
                  .parse(
                    archive
                      .prepare(
                        "SELECT jsonl_gzip FROM session_data WHERE session_id = ? AND length(jsonl_gzip) <= 4194304",
                      )
                      .get(selected.id),
                  ).jsonl_gzip;
                transcript = gunzipSync(raw, {
                  maxOutputLength: 4 * 1024 * 1024,
                }).toString("utf8");
              } finally {
                archive.close();
              }
            }
            const lines: string[] = [];
            for (const line of transcript.split("\n")) {
              if (line.length === 0) continue;
              const parsed = previewEntry.safeParse(JSON.parse(line));
              if (!parsed.success) continue;
              const { role, content } = parsed.data.message;
              const body =
                typeof content === "string"
                  ? content
                  : content
                      .filter((part) => part.type === "text")
                      .map((part) => part.text ?? "")
                      .join("\n");
              lines.push(`${role}\n${clean(body).slice(0, 4000)}`);
              if (lines.length === 40) break;
            }
            const title = rows.find((row) => row.id === selected.id);
            await showTask(
              ctx,
              (title === undefined ? selected.id : caption(title)) +
                "\n\n" +
                (lines.length === 0
                  ? "No user or assistant messages"
                  : lines.join("\n\n")),
            );
          } catch {
            await showTask(
              ctx,
              "Archive transcript is missing, corrupt, or exceeds the preview limit.",
            );
          }
        }
      } catch (error) {
        const failure = processFailure(error);
        ctx.ui.notify(
          failure.message.includes("unable to open database")
            ? `Archive database unavailable: ${path}`
            : "Archive database is unreadable or has an unsupported schema",
          "warning",
        );
      }
    },
  });
}
