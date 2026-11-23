import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import {
  mkdir,
  mkdtemp,
  readFile,
  readdir,
  realpath,
  rm,
  symlink,
  writeFile,
} from "node:fs/promises";
import {
  createServer,
  type IncomingMessage,
  type ServerResponse,
} from "node:http";
import { tmpdir } from "node:os";
import { delimiter, dirname, join } from "node:path";
import { createInterface } from "node:readline";
import { fileURLToPath } from "node:url";
import { z } from "zod";
import {
  AgentRole,
  DefaultProvider,
  DriverProfile,
  ReasoningLevel,
} from "../config.ts";
import { run } from "../process.ts";
import { PiEvent } from "../runtime.ts";

import { piExecutable } from "../task-run.ts";

enum Scenario {
  Complete = "complete",
  LostAllocation = "--lost-allocation",
  Cancel = "--cancel",
}
enum RpcCommand {
  Prompt = "prompt",
  Abort = "abort",
}
const root = fileURLToPath(new URL("../", import.meta.url));
const requestSchema = z.object({
  model: z.enum(AgentRole),
  messages: z.array(z.object({ role: z.string() })),
  tools: z
    .array(z.object({ function: z.object({ name: z.string() }) }))
    .default([]),
});
const eventSchema = z.looseObject({
  id: z.string().optional(),
  type: z.string(),
  success: z.boolean().optional(),
});
const attemptSchema = z.object({
  id: z.string(),
  state: z.string(),
  role: z.enum(AgentRole),
  reasoning: z.enum(ReasoningLevel),
  source: z.string(),
  worktree: z.object({ path: z.string(), owner_id: z.string() }),
  session: z.string().optional(),
  sessionFile: z.string().optional(),
});
type ModelRequest = z.infer<typeof requestSchema>;
const toolNames = (request: ModelRequest) =>
  request.tools.map((tool) => tool.function.name);
const settledEvent: string = PiEvent.AgentSettled;
const costs = { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 };

function bounded<T>(operation: Promise<T>, reason: string): Promise<T> {
  let timer: NodeJS.Timeout | undefined;
  const deadline = new Promise<never>((_resolve, reject) => {
    timer = setTimeout(() => {
      reject(new Error(reason));
    }, 30_000);
  });
  return Promise.race([operation, deadline]).finally(() => {
    clearTimeout(timer);
  });
}

function fixtureProvider(scenario: Scenario) {
  const requests: ModelRequest[] = [];
  let markChildStarted: (() => void) | undefined;
  const childStarted = new Promise<void>((resolve) => {
    markChildStarted = resolve;
  });
  let failure: unknown;
  async function reply(incoming: IncomingMessage, response: ServerResponse) {
    incoming.setEncoding("utf8");
    let body = "";
    for await (const chunk of incoming) body += z.string().parse(chunk);
    const request = requestSchema.parse(JSON.parse(body));
    requests.push(request);
    if (request.model === AgentRole.Explorer && scenario === Scenario.Cancel) {
      markChildStarted?.();
      // The RPC abort should disconnect this pending model request.
      return;
    }

    const hasResult = request.messages.some(
      (message) => message.role === "tool",
    );
    const call = hasResult
      ? undefined
      : request.model === AgentRole.Lead
        ? {
            name: "driver_delegate",
            arguments: JSON.stringify({
              role: AgentRole.Explorer,
              brief: "Read fixture.txt",
            }),
          }
        : { name: "read", arguments: JSON.stringify({ path: "fixture.txt" }) };
    const useTool =
      call !== undefined && toolNames(request).includes(call.name);
    const delta = useTool
      ? {
          role: "assistant",
          tool_calls: [
            {
              index: 0,
              id: `call_${request.model}`,
              type: "function",
              function: call,
            },
          ],
        }
      : { role: "assistant", content: "finished" };
    const chunk = {
      id: "fixture",
      object: "chat.completion.chunk",
      created: 1,
      model: request.model,
      choices: [
        { index: 0, delta, finish_reason: useTool ? "tool_calls" : "stop" },
      ],
    };
    response.writeHead(200, { "Content-Type": "text/event-stream" });
    response.end(`data: ${JSON.stringify(chunk)}\n\ndata: [DONE]\n\n`);
  }
  const server = createServer((incoming, response) => {
    reply(incoming, response).catch((error: unknown) => {
      failure = error;
      response.writeHead(400).end();
    });
  });
  return {
    server,
    requests,
    childStarted,
    get failure() {
      return failure;
    },
  };
}

async function exercise(scenario: Scenario, fixture: string) {
  const provider = fixtureProvider(scenario);
  try {
    await new Promise<void>((resolve, reject) => {
      provider.server.once("error", reject);
      provider.server.listen(0, "127.0.0.1", resolve);
    });
    const address = provider.server.address();
    assert.ok(address !== null && typeof address !== "string");
    const repo = join(fixture, "repo");
    const agent = join(fixture, "agent");
    const config = join(fixture, "config.json");
    const state = join(fixture, "state");
    const env = Object.assign(
      Object.fromEntries(
        Object.entries(process.env).filter(
          ([key]) => !/^(GIT_|PI_|WORKTREE_)/.test(key),
        ),
      ),
      {
        HOME: fixture,
        PI_CODING_AGENT_DIR: agent,
        PI_DRIVER_CONFIG: config,
        PI_TELEMETRY: "0",
        PI_SKIP_VERSION_CHECK: "1",
        XDG_STATE_HOME: state,
        XDG_CONFIG_HOME: join(fixture, "config"),
        XDG_CACHE_HOME: join(fixture, "cache"),
      },
    );
    await mkdir(repo);
    const command = (exe: string, args: string[]) =>
      run(exe, args, { cwd: repo, env, timeout: 30_000 });
    if (scenario === Scenario.LostAllocation) {
      const manager = (
        await command("sh", ["-c", "command -v worktree"])
      ).trim();
      assert.ok(manager.startsWith("/"));
      const bin = join(fixture, "bin");
      await mkdir(bin);
      await writeFile(
        join(bin, "worktree"),
        `#!/usr/bin/env bun
const { spawnSync } = require("node:child_process");
const args = process.argv.slice(2);
const lose = args[0] === "create";
const result = spawnSync(${JSON.stringify(manager)}, args, { stdio: ["inherit", lose ? "ignore" : "inherit", "inherit"] });
process.exit(lose ? 1 : (result.status ?? 1));
`,
        { mode: 0o755 },
      );
      env["PATH"] = `${bin}${delimiter}${env["PATH"] ?? ""}`;
    }
    await command("git", ["init", "-q"]);
    await writeFile(join(repo, ".gitignore"), ".worktrees/\n");
    await writeFile(join(repo, "fixture.txt"), "committed fixture evidence\n");
    await writeFile(join(fixture, "outside.txt"), "outside fixture\n");
    await symlink(join(fixture, "outside.txt"), join(repo, "outside"));
    await command("git", ["add", "."]);
    await command("git", [
      "-c",
      "user.name=Fixture",
      "-c",
      "user.email=fixture@example.invalid",
      "commit",
      "-qm",
      "Fixture",
    ]);
    const source = (await command("git", ["rev-parse", "HEAD"])).trim();
    await writeFile(join(repo, "fixture.txt"), "uncommitted change\n");
    await command("python3", [join(root, "scripts/configure.py"), root, agent]);

    const models = Object.values(AgentRole).map((id) => ({
      id,
      reasoning: true,
      cost: costs,
    }));
    const efforts = {
      [AgentRole.Lead]: ReasoningLevel.High,
      [AgentRole.Worker]: ReasoningLevel.Medium,
      [AgentRole.Reviewer]: ReasoningLevel.Medium,
      [AgentRole.Explorer]: ReasoningLevel.Low,
    };
    await writeFile(
      join(agent, "models.json"),
      JSON.stringify({
        providers: {
          "openai-codex": {
            baseUrl: `http://127.0.0.1:${String(address.port)}/v1`,
            api: "openai-completions",
            apiKey: "fixture",
            models,
          },
        },
      }),
    );
    await writeFile(
      config,
      JSON.stringify({
        delegation: { enabled: true },
        integrations: { worktrees: { enabled: true } },
        profiles: {
          [DriverProfile.Personal]: Object.fromEntries(
            Object.values(AgentRole).map((model) => [
              model,
              {
                provider: DefaultProvider.ChatGPTSubscription,
                model,
                reasoning: efforts[model],
              },
            ]),
          ),
        },
      }),
    );

    const pi = spawn(
      await piExecutable(),
      [
        "--mode",
        "rpc",
        "--offline",
        "--no-mcp",
        "--model",
        "openai-codex/lead",
      ],
      {
        env,
        cwd: repo,
        stdio: ["pipe", "pipe", "pipe"],
      },
    );
    let spawnError: Error | undefined;
    pi.once("error", (error) => {
      spawnError = error;
    });
    const closed = new Promise<void>((resolve) => {
      pi.once("close", () => {
        resolve();
      });
    });
    let stderr = "";
    pi.stderr.on("data", (chunk: Buffer) => {
      stderr = (stderr + chunk.toString()).slice(-8000);
    });
    const lines = createInterface({ input: pi.stdout });
    const events = lines[Symbol.asyncIterator]();
    const recent: unknown[] = [];
    const send = (id: string, type: RpcCommand, message?: string) => {
      pi.stdin.write(`${JSON.stringify({ id, type, message })}\n`);
    };
    const wait = async (
      predicate: (event: z.infer<typeof eventSchema>) => boolean,
    ) => {
      for (;;) {
        const line = await events.next();
        if (line.done === true)
          throw new Error("Pi closed its RPC stream", { cause: spawnError });
        const event = eventSchema.parse(JSON.parse(line.value));
        recent.push(event);
        if (recent.length > 12) recent.shift();
        if (predicate(event)) return event;
      }
    };
    const rpc = async (id: string, type: RpcCommand, message?: string) => {
      send(id, type, message);
      const response = await bounded(
        wait((event) => event.id === id),
        `Pi did not acknowledge ${id}`,
      );
      assert.equal(response.success, true, JSON.stringify(response));
    };
    try {
      await rpc("profile", RpcCommand.Prompt, "/driver-profile personal");
      await rpc("lead", RpcCommand.Prompt, "Delegate repository inspection");
      if (scenario === Scenario.Cancel) {
        await bounded(
          provider.childStarted,
          "The Explorer did not reach the fixture provider",
        );
        await rpc("cancel", RpcCommand.Abort);
      } else {
        await bounded(
          wait((event) => event.type === settledEvent),
          "The lead did not settle",
        );
      }
      assert.equal(provider.failure, undefined);
      const attemptsDir = join(state, "pi-driver", "attempts");
      const [filename, extra] = (await readdir(attemptsDir)).filter((file) =>
        file.endsWith(".json"),
      );
      assert.ok(filename !== undefined && extra === undefined);
      const attempt = attemptSchema.parse(
        JSON.parse(await readFile(join(attemptsDir, filename), "utf8")),
      );
      const expected =
        scenario === Scenario.LostAllocation
          ? "uncertain"
          : scenario === Scenario.Cancel
            ? "cancelled"
            : "complete";
      assert.equal(attempt.state, expected);
      assert.equal(attempt.source, source);
      assert.equal(attempt.role, AgentRole.Explorer);
      assert.equal(attempt.reasoning, ReasoningLevel.Low);
      const [lead] = provider.requests;
      assert.ok(lead !== undefined);
      assert.ok(toolNames(lead).includes("driver_delegate"));
      assert.ok(
        !toolNames(lead).some((name) =>
          ["Agent", "SubagentWorkflow", "subagent"].includes(name),
        ),
      );
      const checkout = attempt.worktree.path;
      assert.equal(dirname(checkout), join(repo, ".worktrees"));
      assert.equal(attempt.worktree.owner_id, attempt.id);
      assert.equal(
        await readFile(join(checkout, "fixture.txt"), "utf8"),
        "committed fixture evidence\n",
      );
      if (scenario === Scenario.LostAllocation) {
        assert.equal((await readdir(join(repo, ".worktrees"))).length, 1);
        assert.ok(
          provider.requests.every(
            (request) => request.model === AgentRole.Lead,
          ),
        );
        console.log(
          "Lost worktree response recovered by owner. One checkout, zero child launches.",
        );
      } else {
        assert.ok(
          attempt.session !== undefined && attempt.sessionFile !== undefined,
        );
        if (scenario === Scenario.Cancel) {
          console.log(
            "Native Pi abort settled the child and retained its session locator.",
          );
        } else {
          const transcript = await readFile(attempt.sessionFile, "utf8");
          const children = provider.requests.filter(
            (request) => request.model === AgentRole.Explorer,
          );
          const [child] = children;
          assert.ok(child !== undefined);
          assert.equal(children.length, 2);
          assert.deepEqual(
            new Set(toolNames(child)),
            new Set(["read", "ls", "find", "grep"]),
          );
          assert.match(transcript, /committed fixture evidence/);
          assert.doesNotMatch(transcript, /uncommitted change/);
          console.log(
            "Native Pi delegation, exact worktree and snapshot tools verified.",
          );
        }
      }
    } catch (error) {
      console.error(JSON.stringify(recent, null, 2), stderr);
      throw error;
    } finally {
      lines.close();
      pi.kill("SIGTERM");
      const kill = setTimeout(() => {
        pi.kill("SIGKILL");
      }, 5000);
      try {
        await closed;
      } finally {
        clearTimeout(kill);
      }
    }
  } finally {
    await new Promise<void>((resolve) => {
      provider.server.close(() => {
        resolve();
      });
      provider.server.closeAllConnections();
    });
  }
}

const [argument, extra] = process.argv.slice(2);
assert.equal(extra, undefined, "Choose at most one scenario");
const scenario = z.enum(Scenario).parse(argument ?? Scenario.Complete);
const fixture = await mkdtemp(join(tmpdir(), "pi-driver-delegation-"));
try {
  await exercise(scenario, await realpath(fixture));
} finally {
  await rm(fixture, { recursive: true, force: true });
}
