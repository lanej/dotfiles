import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import {
  chmod,
  copyFile,
  realpath,
  stat,
  mkdir,
  mkdtemp,
  readFile,
  readlink,
  rm,
  symlink,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import { z } from "zod";
import { taskDetails, taskLabel, taskSchema, taskTree } from "../beads.ts";

import { githubLink, renderReferences } from "../github-links.ts";
import { footerModelLabel } from "../footer.ts";
import { highlightSearchOutput } from "../search-renderer.ts";

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
      execute(join(root, "scripts/pi-driver"), args, {
        cwd: workspace,
        env,
        timeout: 10_000,
      });
    const compiledConfig = await driver("config", "--example");
    const sourceConfig = await execute(
      join(root, "scripts/pi-driver"),
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
    await chmod(join(agent, "settings.json"), 0o600);
    const install = () =>
      execute("python3", [join(root, "scripts/configure.py"), root, agent], {
        env: { ...process.env, PI_CODING_AGENT_DIR: agent },
      });
    await install();
    await install();
    assert.equal(
      (await stat(join(agent, "settings.json"))).mode & 0o777,
      0o600,
    );
    const settings = z
      .object({
        theme: z.string(),
        quietStartup: z.boolean(),
        defaultModel: z.string(),
        packages: z.array(z.string()),
      })
      .parse(JSON.parse(await readFile(join(agent, "settings.json"), "utf8")));
    assert.equal(settings.theme, "dark");
    assert.equal(settings.quietStartup, true);
    assert.equal(
      await readlink(join(agent, "themes/dotfiles.json")),
      join(root, "resources/theme.json"),
    );
    assert.equal(settings.defaultModel, "keep-model");
    assert.deepEqual(settings.packages, [
      "keep-package",
      root.replace(/\/$/, ""),
    ]);
    const saved = await readFile(join(agent, "settings.json"), "utf8");
    const linked = join(temporary, "linked-settings.json");
    await writeFile(linked, saved);
    await rm(join(agent, "settings.json"));
    await symlink(linked, join(agent, "settings.json"));
    await assert.rejects(install(), /Preserving linked Pi settings/);
    assert.equal(await readFile(linked, "utf8"), saved);
    await rm(join(agent, "settings.json"));
    await writeFile(join(agent, "settings.json"), saved);
    const theme = join(agent, "themes/dotfiles.json");
    await rm(theme);
    await symlink(linked, theme);
    await assert.rejects(install(), /Preserving the existing dotfiles.json/);
    assert.equal(await readlink(theme), linked);
    assert.equal(await readFile(join(agent, "settings.json"), "utf8"), saved);
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});

await test("optional integrations stay inactive until enabled and fail before effects when absent", async () => {
  const temporary = await mkdtemp(join(tmpdir(), "pi-driver-optional-"));
  try {
    const config = join(temporary, "config.json");
    const marker = join(temporary, "unexpected-effect");
    const executable = join(temporary, "integration");
    await writeFile(
      executable,
      `#!/bin/sh\nprintf called >> "${marker}"\nexit 99\n`,
      { mode: 0o755 },
    );
    const invoke = (...args: string[]) =>
      execute(join(root, "scripts/pi-driver"), args, {
        cwd: temporary,
        env: {
          ...process.env,
          PI_DRIVER_CONFIG: config,
          PI_DRIVER_STATE_DIR: join(temporary, "state"),
        },
      });
    await writeFile(
      config,
      JSON.stringify({
        integrations: {
          zellij: { executable },
          worktrees: { executable },
          octo: { executable },
        },
      }),
    );
    const report = z
      .object({
        integrations: z.record(
          z.string(),
          z.object({ enabled: z.boolean(), available: z.boolean() }),
        ),
      })
      .parse(JSON.parse((await invoke("doctor")).stdout));
    assert.ok(
      Object.values(report.integrations).every(
        (integration) => !integration.enabled && !integration.available,
      ),
    );
    await assert.rejects(
      invoke("start", "fixture", "--profile", "personal"),
      /Enable integrations.zellij.enabled/,
    );
    await writeFile(
      config,
      JSON.stringify({
        integrations: {
          zellij: { enabled: true, executable: join(temporary, "missing") },
        },
      }),
    );
    await assert.rejects(
      invoke("start", "fixture", "--profile", "personal"),
      /Install .*missing or configure integrations.zellij.executable/,
    );
    await assert.rejects(invoke("doctor"));
    await assert.rejects(readFile(marker), /ENOENT/);
    await assert.rejects(
      readFile(join(temporary, "state/attempts.sqlite")),
      /ENOENT/,
    );
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});

await test("configuration upgrades the exact legacy dotfiles package and theme pair", async () => {
  const temporary = await mkdtemp(join(tmpdir(), "pi-driver-legacy-config-"));
  try {
    const agent = join(temporary, "agent");
    const previous = join(temporary, "dotfiles/pi/daily-driver");
    const legacyTheme = join(
      temporary,
      "dotfiles/design-system/generated/pi.json",
    );
    await mkdir(previous, { recursive: true });
    await mkdir(join(temporary, "dotfiles/design-system/generated"), {
      recursive: true,
    });
    await mkdir(join(agent, "themes"), { recursive: true });
    await writeFile(
      join(previous, "package.json"),
      JSON.stringify({ name: "@lanej/pi-daily-driver" }),
    );
    await writeFile(legacyTheme, "{}");
    await symlink(legacyTheme, join(agent, "themes/dotfiles.json"));
    await writeFile(
      join(agent, "settings.json"),
      JSON.stringify({
        theme: "dotfiles",
        packages: ["keep-package", previous],
      }),
    );
    await execute(
      "python3",
      [join(root, "scripts/configure.py"), root, agent],
      { env: { ...process.env, PI_CODING_AGENT_DIR: agent } },
    );
    const settings = z
      .object({ packages: z.array(z.string()), theme: z.string() })
      .parse(JSON.parse(await readFile(join(agent, "settings.json"), "utf8")));
    assert.deepEqual(settings.packages, [
      "keep-package",
      root.replace(/\/$/, ""),
    ]);
    assert.equal(settings.theme, "dotfiles");
    assert.equal(
      await readlink(join(agent, "themes/dotfiles.json")),
      join(root, "resources/theme.json"),
    );
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});

await test("launchers ignore checkout Bun preloads and dotenv before the host entrypoint", async () => {
  const temporary = await realpath(
    await mkdtemp(join(tmpdir(), "pi-driver-bootstrap-")),
  );
  try {
    const checkout = join(temporary, "untrusted checkout");
    const home = join(temporary, "home");
    const bundle = join(temporary, "bundle");
    const marker = join(temporary, "preload-executed");
    const hostDirectory = join(
      bundle,
      "node_modules/@earendil-works/pi-coding-agent/dist/bundle",
    );
    for (const path of [
      checkout,
      home,
      hostDirectory,
      join(bundle, "scripts"),
      join(bundle, "resources"),
      join(bundle, "runtime"),
      join(temporary, "bin"),
    ])
      await mkdir(path, { recursive: true });
    const preload = join(checkout, "preload.ts");
    await writeFile(
      preload,
      `import { appendFileSync } from "node:fs"; appendFileSync(${JSON.stringify(marker)}, "executed\\n"); process.env["PI_DRIVER_BOOTSTRAP_PRELOAD"] = "executed";`,
    );
    await writeFile(
      join(checkout, "bunfig.toml"),
      `preload = [${JSON.stringify(preload)}]\n`,
    );
    await writeFile(
      join(home, ".bunfig.toml"),
      `preload = [${JSON.stringify(preload)}]\n`,
    );
    await writeFile(
      join(checkout, ".env"),
      "PI_DRIVER_BOOTSTRAP_UNTRUSTED=dotenv\n",
    );
    await writeFile(join(bundle, "resources/bunfig.toml"), "preload = []\n");
    const entry = `console.log(JSON.stringify({ cwd: process.cwd(), args: process.argv.slice(2), inherited: process.env["PI_DRIVER_BOOTSTRAP_INHERITED"], dotenv: process.env["PI_DRIVER_BOOTSTRAP_UNTRUSTED"] ?? null, preload: process.env["PI_DRIVER_BOOTSTRAP_PRELOAD"] ?? null }));`;
    await writeFile(join(hostDirectory, "cli.js"), entry);
    await writeFile(join(bundle, "cli.ts"), entry);
    await symlink(process.execPath, join(bundle, "runtime/bun"));
    await symlink(process.execPath, join(temporary, "bin/bun"));
    const args = ["argument with spaces", "--no-extensions", "--resume"];
    for (const mode of ["embedded", "path"]) {
      if (mode === "path") await rm(join(bundle, "runtime/bun"));
      for (const name of ["pi", "pi-driver"]) {
        const launcher = join(bundle, "scripts", name);
        await copyFile(join(root, "scripts", name), launcher);
        await chmod(launcher, 0o755);
        const result = await execute(launcher, args, {
          cwd: checkout,
          env: {
            ...process.env,
            HOME: home,
            XDG_CONFIG_HOME: join(home, ".config"),
            PATH: `${join(temporary, "bin")}:${process.env["PATH"] ?? ""}`,
            PI_DRIVER_USE_SOURCE: "1",
            PI_DRIVER_BOOTSTRAP_INHERITED: "preserve",
          },
          timeout: 10_000,
        });
        assert.ok(
          result.stdout.length > 0,
          `${mode}/${name}: ${result.stderr}`,
        );
        const observed = z
          .object({
            cwd: z.string(),
            args: z.array(z.string()),
            inherited: z.string(),
            dotenv: z.string().nullable(),
            preload: z.string().nullable(),
          })
          .parse(JSON.parse(result.stdout));
        assert.deepEqual(observed, {
          cwd: checkout,
          args,
          inherited: "preserve",
          dotenv: null,
          preload: null,
        });
        await assert.rejects(readFile(marker), /ENOENT/);
      }
    }
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});
