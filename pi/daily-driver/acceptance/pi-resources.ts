import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createInterface } from "node:readline";
import { fileURLToPath } from "node:url";
import { z } from "zod";
import { run } from "../process.ts";

const root = fileURLToPath(new URL("../", import.meta.url));
const temporary = await mkdtemp(join(tmpdir(), "pi-driver-resources-"));
const agent = join(temporary, ".pi/agent");
await mkdir(agent, { recursive: true });
await run(
  "python3",
  [join(root, "../../scripts/configure-pi-driver.py"), root, agent],
  { env: { ...process.env, PI_CODING_AGENT_DIR: agent } },
);
await writeFile(join(temporary, "config.json"), "{}");
await writeFile(
  join(agent, "models.json"),
  JSON.stringify({
    providers: {
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
  process.execPath,
  [
    join(
      root,
      "node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js",
    ),
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
  for await (const line of createInterface({ input: pi.stdout })) {
    const envelope = z
      .looseObject({ id: z.string().optional() })
      .parse(JSON.parse(line));
    if (envelope.id !== "resources") continue;
    const event = z
      .object({
        success: z.literal(true),
        data: z.object({ commands: z.array(z.object({ name: z.string() })) }),
      })
      .parse(envelope);
    for (const name of ["tasks", "archives", "driver-profile", "driver-status"])
      assert.ok(
        event.data.commands.some(
          (command: { name: string }) => command.name === name,
        ),
        name,
      );
    found = true;
    break;
  }
  assert.ok(found, errors);
  assert.doesNotMatch(
    errors,
    /Failed to load|Error loading|Cannot load|Warning: Extension package/,
  );
  console.log(
    "Pi 1.4.0 loaded the daily-driver extension and discovered its commands without a provider request.",
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
