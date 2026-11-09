#!/usr/bin/env bun
import { parseArgs } from "node:util";
import { homedir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { randomUUID } from "node:crypto";
import { spawn } from "node:child_process";
import { Coordinator } from "./coordinator.js";
import { request } from "./client.js";
import { dashboard } from "./dashboard.js";
import { terminalStates, type JobEvent } from "./domain.js";

process.umask(0o077);
async function main(): Promise<void> {
  const { values, positionals } = parseArgs({ allowPositionals: true, options: { state: { type: "string" }, model: { type: "string" }, url: { type: "string" }, "request-id": { type: "string" }, json: { type: "boolean" }, after: { type: "string" }, watch: { type: "boolean" }, help: { type: "boolean", short: "h" } } });
  const directory = resolve(values.state ?? process.env.PI_GITHUB_STATE ?? join(homedir(), ".local", "state", "pi-github"));
  const [command, argument] = positionals;
  if (!command || values.help) {
    console.log("pi-github dashboard | serve | login | demo | submit summarize-pr --url URL | get ID | events ID [--watch] [--after N] | cancel ID | retry ID | pause | resume\nOptions: --state DIR --model MODEL --request-id ID --json\nDefault model: openai-codex/gpt-6.1-terra. Only public PR inspection and disposable fixture writes are supported."); return;
  }
  if (command === "login") {
    console.log("Pi uses a separate ChatGPT login. In Pi, run /login openai-codex, complete the browser flow, then /quit. Credentials are managed by Pi and are never copied from Codex.");
    const child = spawn(process.execPath, [fileURLToPath(new URL("../node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js", import.meta.url)), "--no-tools", "--no-extensions", "--no-skills", "--no-context-files", "--no-session"], { stdio: "inherit" });
    process.exitCode = await new Promise<number>((resolve, reject) => { child.on("error", reject); child.on("exit", code => resolve(code ?? 1)); }); return;
  }
  if (command === "dashboard" || command === "serve") {
    if (command === "dashboard" && !process.stdin.isTTY) throw new Error("Dashboard needs a terminal; use serve for foreground headless operation");
    const coordinator = new Coordinator(directory, { model: values.model });
    await coordinator.start();
    if (command === "dashboard") await dashboard(coordinator);
    else {
      console.log(JSON.stringify({ ready: true, state: directory }));
      await new Promise<void>(resolve => { const stop = () => { void coordinator.close().then(resolve); }; process.once("SIGINT", stop); process.once("SIGTERM", stop); });
    }
    return;
  }
  const id = argument;
  let result: unknown;
  if (command === "submit" && argument === "summarize-pr" && values.url) result = await request(directory, { op: "submit", requestId: values["request-id"] ?? randomUUID(), task: { kind: "summarize_pr", url: values.url } });
  else if (command === "demo") {
    const requestId = values["request-id"] ?? randomUUID();
    const conflict = await request(directory, { op: "submit", requestId: `${requestId}:conflict`, task: { kind: "resolve_conflict" } });
    const github = await request(directory, { op: "submit", requestId: `${requestId}:github`, task: { kind: "summarize_pr", url: values.url ?? "https://github.com/earendil-works/pi/pull/11546" } });
    result = { conflict, github };
  } else if (["get", "cancel", "retry"].includes(command) && id) result = await request(directory, { op: command, id });
  else if (["pause", "resume"].includes(command)) result = await request(directory, { op: command });
  else if (command === "events" && id) {
    let cursor = Number(values.after ?? 0);
    do {
      const events: JobEvent[] = await request(directory, { op: "events", id, after: cursor });
      for (const event of events) { console.log(JSON.stringify(event)); cursor = event.seq; }
      if (!values.watch) break;
      const job = await request(directory, { op: "get", id });
      if (terminalStates.includes(job.status) && events.length < 200) break;
      await new Promise(resolve => setTimeout(resolve, 250));
    } while (true);
    return;
  } else throw new Error("Unsupported command; see --help");
  console.log(JSON.stringify(result, null, values.json ? undefined : 2));
}
main().catch(error => { console.error((error as Error).message); process.exitCode = 1; });
