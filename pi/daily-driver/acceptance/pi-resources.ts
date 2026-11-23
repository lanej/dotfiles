import { ModelRuntime } from "@earendil-works/pi-coding-agent";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createInterface } from "node:readline";
import { fileURLToPath } from "node:url";
import { z } from "zod";
import {
  AgentRole,
  DriverProfile,
  exampleConfig,
  ReasoningLevel,
} from "../config.ts";
import { run } from "../process.ts";
import { piExecutable } from "../task-run.ts";

const root = fileURLToPath(new URL("../", import.meta.url));
const temporary = await mkdtemp(join(tmpdir(), "pi-driver-resources-"));
const agent = join(temporary, ".pi/agent");
await mkdir(agent, { recursive: true });
const registry = await ModelRuntime.create({
  authPath: join(agent, "auth.json"),
  modelsPath: join(agent, "models.json"),
});
for (const [role, selection] of Object.entries(exampleConfig.profiles.personal))
  assert.ok(
    registry.getModel(selection.provider, selection.model) !== undefined,
    `The personal example's ${role} model is unavailable: ${selection.model}`,
  );

await run("python3", [join(root, "scripts/configure.py"), root, agent], {
  env: { ...process.env, PI_CODING_AGENT_DIR: agent },
});
const workModel = {
  provider: "fixture-mantle",
  model: "work-model",
  reasoning: ReasoningLevel.Low,
};
await writeFile(
  join(temporary, "config.json"),
  JSON.stringify({
    profiles: {
      [DriverProfile.Work]: Object.fromEntries(
        Object.values(AgentRole).map((role) => [role, workModel]),
      ),
    },
  }),
);
await writeFile(
  join(agent, "models.json"),
  JSON.stringify({
    providers: {
      [workModel.provider]: {
        baseUrl: "https://bedrock-mantle.us-east-1.api.aws/v1",
        api: "openai-completions",
        apiKey: "$PI_DRIVER_FIXTURE_NO_MANTLE_AUTH",
        models: [{ id: workModel.model }],
      },
      fixture: {
        baseUrl: "http://127.0.0.1:9/v1",
        api: "openai-completions",
        apiKey: "fixture",
        models: [{ id: "tiny" }],
      },
    },
  }),
);
const pi = spawn(
  await piExecutable(),
  [
    "--mode",
    "rpc",
    "--offline",
    "--no-session",
    "--no-mcp",
    "--model",
    "fixture/tiny",
  ],
  {
    cwd: temporary,
    env: {
      ...process.env,
      HOME: temporary,
      PI_CODING_AGENT_DIR: agent,
      PI_DRIVER_CONFIG: join(temporary, "config.json"),
      PI_SKIP_VERSION_CHECK: "1",
      PI_TELEMETRY: "0",
      PI_DRIVER_FIXTURE_NO_MANTLE_AUTH: "",
    },
    stdio: ["pipe", "pipe", "pipe"],
  },
);
let errors = "";
pi.stderr.on("data", (chunk: Buffer) => {
  errors += chunk.toString();
});
const timeout = setTimeout(() => pi.kill("SIGKILL"), 20_000);
try {
  pi.stdin.write('{"id":"resources","type":"get_commands"}\n');
  let found = false;
  let rejectedSwitch = false;
  let checkedModel = false;
  for await (const line of createInterface({ input: pi.stdout })) {
    const envelope = z
      .looseObject({
        id: z.string().optional(),
        method: z.string().optional(),
        type: z.string().optional(),
      })
      .parse(JSON.parse(line));
    if (envelope.id === "resources") {
      const event = z
        .object({
          success: z.literal(true),
          data: z.object({ commands: z.array(z.object({ name: z.string() })) }),
        })
        .parse(envelope);
      for (const name of [
        "tasks",
        "archives",
        "driver-profile",
        "driver-status",
      ])
        assert.ok(
          event.data.commands.some(
            (command: { name: string }) => command.name === name,
          ),
          name,
        );
      found = true;
      pi.stdin.write(
        '{"id":"profile","type":"prompt","message":"/driver-profile work"}\n',
      );
    }
    if (
      envelope.type === "extension_ui_request" &&
      envelope.method === "notify"
    ) {
      const notice = z
        .object({ message: z.string(), notifyType: z.literal("error") })
        .parse(envelope);
      assert.match(notice.message, /Cannot switch to work.*fixture-mantle/);
      assert.match(notice.message, /current model is still active/);
      rejectedSwitch = true;
    }
    if (envelope.id === "profile") {
      z.object({ success: z.literal(true) }).parse(envelope);
      pi.stdin.write('{"id":"model","type":"get_state"}\n');
    }
    if (envelope.id === "model") {
      const state = z
        .object({
          success: z.literal(true),
          data: z.object({
            model: z.object({ provider: z.string(), id: z.string() }),
          }),
        })
        .parse(envelope);
      assert.deepEqual(state.data.model, { provider: "fixture", id: "tiny" });
      checkedModel = true;
      break;
    }
  }
  assert.ok(found, errors);
  assert.ok(checkedModel, "Pi did not return the active model");
  assert.ok(rejectedSwitch, "Pi silently rejected the unauthenticated profile");
  assert.doesNotMatch(
    errors,
    /Failed to load|Error loading|Cannot load|Warning: Extension package/,
  );
  console.log(
    "Pi 1.4.0 discovered the daily-driver commands and kept the current model after a rejected profile switch.",
  );
} finally {
  clearTimeout(timeout);
  if (pi.exitCode === null) {
    pi.kill("SIGTERM");
    await new Promise<void>((resolve) => {
      pi.once("close", () => {
        resolve();
      });
    });
  }
  await rm(temporary, { recursive: true, force: true });
}
