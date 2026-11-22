import assert from "node:assert/strict";
import {
  access,
  mkdir,
  mkdtemp,
  readFile,
  realpath,
  rm,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { delimiter, join } from "node:path";
import { test } from "node:test";
import {
  createAgentSessionFromServices,
  createAgentSessionServices,
  SessionManager,
  SettingsManager,
  ProjectTrustStore,
} from "@earendil-works/pi-coding-agent";
import {
  lspTool,
  registerCodeIntelligence,
  renameTool,
} from "../code-intelligence/extension.ts";

await test("native Pi trust gates automatic diagnostics, LSP queries and rename before server startup", async () => {
  const root = await realpath(await mkdtemp(join(tmpdir(), "pi-lsp-trust-")));
  const previousPath = process.env["PATH"];
  const previousConfig = process.env["PI_DRIVER_CONFIG"];
  const previousAgentDir = process.env["PI_CODING_AGENT_DIR"];
  const marker = join(root, "server-executed");
  const agentDir = join(root, "agent");
  const executableDirectory = join(root, "bin");
  await mkdir(agentDir);
  await mkdir(executableDirectory);
  await writeFile(join(root, "config.json"), "{}");
  await writeFile(
    join(root, "Cargo.toml"),
    '[package]\nname = "untrusted"\nversion = "0.1.0"\n',
  );
  await writeFile(
    join(executableDirectory, "rust-analyzer"),
    `#!${process.execPath}\nrequire("node:fs").writeFileSync(${JSON.stringify(marker)}, "executed");\nprocess.exit(1);\n`,
    { mode: 0o755 },
  );
  process.env["PATH"] =
    `${executableDirectory}${delimiter}${previousPath ?? ""}`;
  process.env["PI_DRIVER_CONFIG"] = join(root, "config.json");
  process.env["PI_CODING_AGENT_DIR"] = agentDir;
  const settings = SettingsManager.inMemory({}, { projectTrusted: false });
  try {
    const services = await createAgentSessionServices({
      cwd: root,
      agentDir,
      settingsManager: settings,
      resourceLoaderOptions: {
        noExtensions: true,
        noSkills: true,
        noPromptTemplates: true,
        noThemes: true,
        extensionFactories: [
          (pi) => {
            registerCodeIntelligence(pi);
          },
        ],
      },
    });
    const { session } = await createAgentSessionFromServices({
      services,
      sessionManager: SessionManager.inMemory(root),
    });
    try {
      let confirm = false;
      await session.bindExtensions({
        mode: "rpc",
        uiContext: {
          ...session.extensionRunner.getUIContext(),
          confirm: () => Promise.resolve(confirm),
        },
      });
      session.agent.state.messages.push({
        role: "assistant",
        content: [
          {
            type: "toolCall",
            id: "trust-fixture",
            name: "trust-fixture",
            arguments: {},
          },
        ],
        api: "openai-completions",
        provider: "fixture",
        model: "fixture",
        stopReason: "toolUse",
        timestamp: Date.now(),
        usage: {
          input: 0,
          output: 0,
          cacheRead: 0,
          cacheWrite: 0,
          totalTokens: 0,
          cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
        },
      });
      const context = session.extensionRunner.createToolContext(
        "trust-fixture",
        undefined,
      );
      assert.equal(context.isProjectTrusted(), false);
      const written = await context.executeTool("write", {
        path: "main.rs",
        content: "fn main() {}\n",
      });
      assert.equal(
        written.isError,
        false,
        "untrusted LSP must not prevent an authorized edit",
      );
      assert.match(JSON.stringify(written.result.content), /project trust/u);
      const edited = await context.executeTool("edit", {
        path: "main.rs",
        oldText: "fn main() {}",
        newText: "fn main() { let _value = 1; }",
      });
      assert.equal(edited.isError, false);
      assert.match(JSON.stringify(edited.result.content), /project trust/u);
      for (const [name, input] of [
        [lspTool, { action: "diagnostics", path: "main.rs" }],
        [
          renameTool,
          {
            action: "preview",
            path: "main.rs",
            line: 1,
            column: 16,
            newName: "value",
          },
        ],
        [renameTool, { action: "apply", token: "untrusted-token" }],
      ] satisfies [string, unknown][]) {
        const result = await context.executeTool(name, input);
        assert.equal(result.isError, true);
        assert.match(JSON.stringify(result.result.content), /project trust/u);
      }
      await assert.rejects(
        access(marker),
        /ENOENT/u,
        "untrusted operations must never launch the executable",
      );
      // Native implicit trust alone must not authorize execution; an operator approval enables the same executable.
      settings.setProjectTrusted(true);
      assert.equal(context.isProjectTrusted(), true);
      const implicit = await context.executeTool(lspTool, {
        action: "diagnostics",
        path: "main.rs",
      });
      assert.equal(
        implicit.isError,
        true,
        "native implicit trust is not project execution approval",
      );
      await assert.rejects(access(marker), /ENOENT/u);
      const approval = session.extensionRunner.getCommand("lsp-trust");
      assert.ok(approval !== undefined);
      await approval.handler(
        "",
        session.extensionRunner.createCommandContext(),
      );
      await assert.rejects(
        access(marker),
        /ENOENT/u,
        "declining approval must not start a server",
      );
      confirm = true;
      await approval.handler(
        "",
        session.extensionRunner.createCommandContext(),
      );
      assert.equal(
        new ProjectTrustStore(agentDir).get(root),
        null,
        "session approval must not change native saved trust",
      );
      await context.executeTool(lspTool, {
        action: "diagnostics",
        path: "main.rs",
      });
      assert.equal(await readFile(marker, "utf8"), "executed");
      await session.extensionRunner.emit({
        type: "session_start",
        reason: "reload",
      });
      await rm(marker);
      const reloaded = await context.executeTool(lspTool, {
        action: "diagnostics",
        path: "main.rs",
      });
      assert.equal(
        reloaded.isError,
        true,
        "session approval must not survive a reload",
      );
      await assert.rejects(access(marker), /ENOENT/u);
      new ProjectTrustStore(agentDir).set(root, true);
      await context.executeTool(lspTool, {
        action: "diagnostics",
        path: "main.rs",
      });
      assert.equal(
        await readFile(marker, "utf8"),
        "executed",
        "recorded native approval must enable server startup",
      );
      settings.setProjectTrusted(false);
      await rm(marker);
      const revoked = await context.executeTool(lspTool, {
        action: "diagnostics",
        path: "main.rs",
      });
      assert.equal(revoked.isError, true);
      assert.match(JSON.stringify(revoked.result.content), /project trust/u);
      await assert.rejects(access(marker), /ENOENT/u);
    } finally {
      await session.extensionRunner.emit({
        type: "session_shutdown",
        reason: "quit",
      });
      session.dispose();
    }
  } finally {
    if (previousPath === undefined) delete process.env["PATH"];
    else process.env["PATH"] = previousPath;
    if (previousConfig === undefined) delete process.env["PI_DRIVER_CONFIG"];
    else process.env["PI_DRIVER_CONFIG"] = previousConfig;
    if (previousAgentDir === undefined)
      delete process.env["PI_CODING_AGENT_DIR"];
    else process.env["PI_CODING_AGENT_DIR"] = previousAgentDir;
    await rm(root, { recursive: true, force: true });
  }
});
