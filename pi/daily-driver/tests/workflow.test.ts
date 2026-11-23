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
import { Attempts } from "../attempts.ts";
import { taskDetails, taskLabel, taskSchema, taskTree } from "../beads.ts";

import { githubLink, renderReferences } from "../github-links.ts";
import { footerModelLabel } from "../footer.ts";
import { highlightSearchOutput } from "../search-renderer.ts";

const execute = promisify(execFile);
const root = fileURLToPath(new URL("../", import.meta.url));

await test("a fresh worker journal has no previous attempt for a bead", async () => {
  const directory = await mkdtemp(join(tmpdir(), "pi-driver-journal-"));
  const journal = new Attempts(directory);
  try {
    assert.equal(journal.latest("project", "bead"), null);
  } finally {
    journal.close();
    await rm(directory, { recursive: true, force: true });
  }
});

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

await test("search rendering highlights only identifiable source, preserving prefixes", () => {
  const color = (text: string, language: string) => [`[${language}]${text}`];
  assert.equal(
    highlightSearchOutput(
      "bash",
      { command: "sed -n '1,4p' 'src/a file.ts'" },
      "const a = 1;",
      color,
    ),
    "[typescript]const a = 1;",
  );
  const hits = "src/a.ts:9:const a = 1;\nsrc/b.py-8-print(a)\nunknown:2:plain";
  assert.equal(
    highlightSearchOutput("bash", { command: "rg -n needle src" }, hits, color),
    "src/a.ts:9:[typescript]const a = 1;\nsrc/b.py-8-[python]print(a)\nunknown:2:plain",
  );
  assert.equal(
    highlightSearchOutput("grep", {}, hits, color),
    "src/a.ts:9:[typescript]const a = 1;\nsrc/b.py-8-[python]print(a)\nunknown:2:plain",
  );
  assert.equal(
    highlightSearchOutput(
      "bash",
      { command: "rg --json needle src" },
      hits,
      color,
    ),
    hits,
  );
  assert.equal(
    highlightSearchOutput(
      "bash",
      { command: "sed -n '1,4p' a.ts | wc" },
      "4",
      color,
    ),
    "4",
  );
});

await test("compact model names preserve versions, variants, and unknown IDs", () => {
  assert.equal(footerModelLabel("gpt-6.1-sol"), "⊛ 6.1 \uE30D");
  assert.equal(footerModelLabel("openai.gpt-6.1-terra"), "⊛ 6.1 \uF0AC");
  assert.equal(footerModelLabel("gpt-6.1-luna"), "⊛ 6.1 \uF186");
  assert.equal(footerModelLabel("gpt-6.1-astra"), "⊛ 6.1 \uF005");
  assert.equal(footerModelLabel("gpt-7-nova"), "⊛ 7 Nova");
  assert.equal(footerModelLabel("gpt-4o-2024-11-20"), "⊛ 4o 2024-11-20");
  assert.equal(footerModelLabel("o3-mini"), "⊛ o3 Mini");
  assert.equal(footerModelLabel("claude-sonnet-4"), "claude-sonnet-4");
});

await test("inline GitHub references retain their exact destinations and line anchors", () => {
  const code = "https://github.com/owner/repo/blob/main/src/driver.ts#L4-L9";
  const issue = "https://github.com/owner/repo/issues/12";
  const rendered = renderReferences(
    `See [source](${code}) and ${issue}. Local src/driver.ts:4.`,
    (text) => text,
  );
  assert.ok(rendered.includes(`\x1b]8;;${code}\x1b\\‹› driver.ts:4–9`));
  assert.ok(rendered.includes(`\x1b]8;;${issue}\x1b\\! owner/repo#12`));
  assert.ok(rendered.endsWith("Local src/driver.ts:4."));
  assert.equal(
    githubLink("https://github.com.example.test/owner/repo/pull/1"),
    undefined,
  );
  assert.equal(
    githubLink("https://github.com/owner/repo/pull/1\x1b]8;;malicious"),
    undefined,
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
      `#!/usr/bin/env bun\nimport fs from 'node:fs';\nconst args=process.argv.slice(2); fs.appendFileSync(${JSON.stringify(capture)},JSON.stringify(args)+'\\n');\nif (!args.includes('--readonly') || !args.includes('--sandbox')) process.exit(31);\nif(process.env.BEADS_DIR || process.env.BEADS_DOLT_SERVER_PORT) process.exit(32);\nif(args.includes('sql')) console.log(JSON.stringify([{branch:'main'}]));\nelse if(args.includes('list')) console.log(JSON.stringify([{id:'fixture-1',title:'Task tree',status:'open'}]));\nelse if(args.includes('show')) console.log(JSON.stringify([{id:'fixture-1',title:'Task tree',status:'open',description:'Keep state'}]));\nelse process.exit(33);\n`,
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
      execute(join(root, "../../bin/pi-driver"), args, {
        cwd: workspace,
        env,
        timeout: 10_000,
      });
    const compiledConfig = await driver("config", "--example");
    const sourceConfig = await execute(
      join(root, "../../bin/pi-driver"),
      ["config", "--example"],
      {
        cwd: workspace,
        env: { ...env, PI_DRIVER_USE_SOURCE: "1" },
        timeout: 10_000,
      },
    );
    assert.equal(compiledConfig.stdout, sourceConfig.stdout);
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
    const install = (path = process.env["PATH"]) =>
      execute(
        "python3",
        [join(root, "../../scripts/configure-pi-driver.py"), root, agent],
        { env: { ...process.env, PATH: path, PI_CODING_AGENT_DIR: agent } },
      );
    const legacy = join(temporary, "pi");
    await writeFile(legacy, "#!/bin/sh\nexit 99\n", { mode: 0o755 });
    const before = await readFile(join(agent, "settings.json"), "utf8");
    await assert.rejects(
      install(`${temporary}:${process.env["PATH"] ?? ""}`),
      /Put standalone Pi ahead of script-based Pi launchers/,
    );
    assert.equal(await readFile(join(agent, "settings.json"), "utf8"), before);
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
