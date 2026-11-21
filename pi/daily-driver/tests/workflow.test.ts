import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import {
  mkdir,
  mkdtemp,
  readFile,
  readlink,
  rm,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import { z } from "zod";
import { taskDetails, taskLabel, taskSchema, taskTree } from "../beads.ts";

const execute = promisify(execFile);
const root = fileURLToPath(new URL("../", import.meta.url));

await test("task containment stays separate from blockers, including missing parents and cycles", () => {
  const rows = taskTree([
    {
      id: "child",
      title: "Inspect",
      status: "open",
      dependencies: [
        { id: "root", dependency_type: "parent-child" },
        { id: "blocker", dependency_type: "blocks" },
      ],
    },
    { id: "root", title: "Driver", status: "in_progress" },
    { id: "blocker", title: "Scope fence", status: "open" },
    { id: "orphan", title: "Other branch", status: "open", parent: "missing" },
    { id: "cycle-a", title: "Cycle A", status: "open", parent: "cycle-b" },
    { id: "cycle-b", title: "Cycle B", status: "open", parent: "cycle-a" },
  ]);
  assert.deepEqual(
    rows.slice(0, 3).map((row) => [row.task.id, row.depth]),
    [
      ["root", 0],
      ["child", 1],
      ["blocker", 0],
    ],
  );
  assert.equal(rows.length, 6);
  assert.match(rows[3]?.warning ?? "", /outside/);
  assert.match(rows[4]?.warning ?? "", /Cyclic/);
  assert.match(
    taskDetails(
      rows[1]?.task ?? { id: "", title: "", status: "" },
      "/authority",
    ),
    /Blocked by: blocker/,
  );
  assert.doesNotMatch(
    taskLabel({
      task: { id: "bad", title: "escape\x1b[31m\nnewline", status: "open" },
      depth: 0,
    }),
    /\p{Cc}/u,
  );
});

await test("CLI reads the explicitly configured source and dispatch never allocates", async () => {
  const temporary = await mkdtemp(join(tmpdir(), "pi-driver-workflow-"));
  try {
    const workspace = join(temporary, "authority with spaces");
    await mkdir(join(workspace, ".beads"), { recursive: true });
    await writeFile(
      join(workspace, ".beads/metadata.json"),
      JSON.stringify({ dolt_mode: "server", dolt_database: "fixture" }),
    );
    const capture = join(temporary, "calls.jsonl");
    const boundary = join(temporary, "native-bd");
    await writeFile(
      boundary,
      `#!/usr/bin/env node\nimport fs from 'node:fs';\nconst args=process.argv.slice(2); fs.appendFileSync(${JSON.stringify(capture)},JSON.stringify(args)+'\\n');\nif (!args.includes('--readonly') || !args.includes('--sandbox')) process.exit(31);\nif(process.env.BEADS_DIR || process.env.BEADS_DOLT_SERVER_PORT) process.exit(32);\nif(args.includes('sql')) console.log(JSON.stringify([{branch:'main'}]));\nelse if(args.includes('list')) console.log(JSON.stringify([{id:'fixture-1',title:'Task tree',status:'open'}]));\nelse if(args.includes('show')) console.log(JSON.stringify([{id:'fixture-1',title:'Task tree',status:'open',description:'Keep state'}]));\nelse process.exit(33);\n`,
      { mode: 0o755 },
    );
    const config = join(temporary, "config.json");
    await writeFile(
      config,
      JSON.stringify({
        beads: {
          workspace,
          database: "fixture",
          branch: "main",
          executable: boundary,
        },
      }),
    );
    const env = {
      ...process.env,
      PI_DRIVER_CONFIG: config,
      BEADS_DIR: "/wrong-workspace",
      BEADS_DOLT_SERVER_PORT: "1",
    };
    const driver = (...args: string[]) =>
      execute(
        process.execPath,
        ["--import", "tsx", join(root, "cli.ts"), ...args],
        { cwd: root, env, timeout: 10_000 },
      );
    const listing = z
      .object({ workspace: z.string(), tasks: z.array(taskSchema) })
      .parse(JSON.parse((await driver("tasks", "--json")).stdout));
    assert.equal(listing.workspace, workspace);
    assert.equal(listing.tasks[0]?.id, "fixture-1");
    assert.match((await driver("tasks", "fixture-1")).stdout, /Keep state/);
    const before = await readFile(capture, "utf8");
    await assert.rejects(
      driver("start", "--profile", "personal"),
      /missing required argument/,
    );
    assert.equal(
      await readFile(capture, "utf8"),
      before,
      "gated start must not call Beads",
    );
    await writeFile(config, "invalid config");
    assert.match((await driver("skill")).stdout, /daily driver/);
    await assert.rejects(driver("tasks"), /Cannot load/);
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});

await test("opt-in registration preserves local settings and is idempotent", async () => {
  const temporary = await mkdtemp(join(tmpdir(), "pi-driver-install-"));
  try {
    const agent = join(temporary, "agent");
    await mkdir(agent);
    await writeFile(
      join(agent, "settings.json"),
      JSON.stringify({
        theme: "dark",
        defaultModel: "keep-model",
        packages: ["keep-package"],
      }),
    );
    const install = () =>
      execute(
        "python3",
        [join(root, "../../scripts/configure-pi-driver.py"), root, agent],
        { env: { ...process.env, PI_CODING_AGENT_DIR: agent } },
      );
    await install();
    await install();
    const settings = z
      .object({
        theme: z.string(),
        quietStartup: z.boolean(),
        defaultModel: z.string(),
        packages: z.array(z.string()),
      })
      .parse(JSON.parse(await readFile(join(agent, "settings.json"), "utf8")));
    assert.equal(settings.theme, "dotfiles");
    assert.equal(settings.quietStartup, true);
    assert.equal(
      await readlink(join(agent, "themes/dotfiles.json")),
      join(root, "../../design-system/generated/pi.json"),
    );
    assert.equal(settings.defaultModel, "keep-model");
    assert.deepEqual(settings.packages, [
      "keep-package",
      root.replace(/\/$/, ""),
    ]);
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});
