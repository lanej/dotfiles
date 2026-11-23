import assert from "node:assert/strict";
import {
  mkdtemp,
  mkdir,
  readFile,
  readdir,
  realpath,
  rm,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import {
  createAgentSessionFromServices,
  createAgentSessionRuntime,
  createAgentSessionServices,
  SessionManager,
  SettingsManager,
  type AgentSession,
  type CreateAgentSessionRuntimeFactory,
  type ExtensionCommandContext,
} from "@earendil-works/pi-coding-agent";
import { registerDirectory } from "../directory.ts";
import dailyDriver from "../extension.ts";
import { delegateTool } from "../delegation.ts";
import { AgentRole } from "../config.ts";
import { PiMode } from "../runtime.ts";

await test("/cd carries the active conversation and tree into rebuilt native Pi tools and project context", async (t) => {
  const root = await realpath(await mkdtemp(join(tmpdir(), "pi-driver-cd-")));
  const oldAgentDir = process.env["PI_CODING_AGENT_DIR"];
  const oldAttempt = process.env["PI_DRIVER_ATTEMPT"];
  const oldConfig = process.env["PI_DRIVER_CONFIG"];
  t.after(async () => {
    if (oldAgentDir === undefined) delete process.env["PI_CODING_AGENT_DIR"];
    else process.env["PI_CODING_AGENT_DIR"] = oldAgentDir;
    if (oldAttempt === undefined) delete process.env["PI_DRIVER_ATTEMPT"];
    else process.env["PI_DRIVER_ATTEMPT"] = oldAttempt;
    if (oldConfig === undefined) delete process.env["PI_DRIVER_CONFIG"];
    else process.env["PI_DRIVER_CONFIG"] = oldConfig;
    await rm(root, { recursive: true, force: true });
  });
  const source = join(root, "source");
  const target = join(root, "other project");
  const agentDir = join(root, "agent");
  for (const directory of [source, target, agentDir])
    await mkdir(directory, { recursive: true });
  process.env["PI_CODING_AGENT_DIR"] = agentDir;
  const configFile = join(root, "config.json");
  process.env["PI_DRIVER_CONFIG"] = configFile;
  const managerExecutable = join(root, "worktree-fixture");
  await writeFile(managerExecutable, "#!/bin/sh\nexit 97\n", { mode: 0o755 });
  const config = {
    integrations: {
      worktrees: { enabled: true, executable: managerExecutable },
    },
    idleCompaction: { enabled: false },
    delegation: { enabled: true },
    profiles: {
      work: Object.fromEntries(
        Object.values(AgentRole).map((role) => [
          role,
          { provider: "fixture", model: "tiny", reasoning: "low" },
        ]),
      ),
    },
  };
  await writeFile(configFile, JSON.stringify(config));
  delete process.env["PI_DRIVER_ATTEMPT"];
  await writeFile(join(source, "AGENTS.md"), "SOURCE_PROJECT_INSTRUCTIONS");
  await writeFile(join(target, "AGENTS.md"), "TARGET_PROJECT_INSTRUCTIONS");
  await writeFile(join(target, "marker.txt"), "destination contents");
  await writeFile(
    join(agentDir, "models.json"),
    JSON.stringify({
      providers: {
        fixture: {
          baseUrl: "https://bedrock-mantle.us-east-1.api.aws/v1",
          api: "openai-completions",
          apiKey: "fixture",
          models: [{ id: "tiny", reasoning: true }],
        },
      },
    }),
  );
  const notifications: string[] = [];
  let children = false;
  let cancel = false;
  let fullDriver = false;
  const factory: CreateAgentSessionRuntimeFactory = async (options) => {
    const services = await createAgentSessionServices({
      cwd: options.cwd,
      agentDir,
      settingsManager: SettingsManager.inMemory(
        {
          defaultProvider: "fixture",
          defaultModel: "tiny",
          defaultThinkingLevel: "low",
        },
        { projectTrusted: true },
      ),
      resourceLoaderOptions: {
        noExtensions: true,
        noSkills: true,
        noPromptTemplates: true,
        noThemes: true,
        extensionFactories: [
          (pi) => {
            if (fullDriver) dailyDriver(pi);
            else registerDirectory(pi, () => children);
            pi.on("session_before_switch", () => ({ cancel }));
          },
        ],
      },
    });
    const result = await createAgentSessionFromServices({
      services,
      sessionManager: options.sessionManager,
      ...(options.sessionStartEvent === undefined
        ? {}
        : { sessionStartEvent: options.sessionStartEvent }),
    });
    return { ...result, services, diagnostics: services.diagnostics };
  };
  const manager = SessionManager.create(source);
  const firstMessage = manager.appendMessage({
    role: "user",
    content: "Remember our deployment target is cobalt.",
    timestamp: Date.now(),
  });
  manager.appendCompaction(
    "The deployment target is cobalt.",
    firstMessage,
    100,
  );
  manager.appendSessionInfo("Moving conversation");
  const originalFile = manager.getSessionFile();
  assert.ok(originalFile !== undefined);
  const runtime = await createAgentSessionRuntime(factory, {
    cwd: source,
    agentDir,
    sessionManager: manager,
  });
  const bind = async (session: AgentSession): Promise<void> => {
    await session.bindExtensions({
      mode: PiMode.Tui,
      uiContext: {
        ...session.extensionRunner.getUIContext(),
        notify: (message) => notifications.push(message),
      },
      commandContextActions: {
        waitForIdle: () => session.waitForIdle(),
        newSession: (options) => runtime.newSession(options),
        fork: (entry, options) => runtime.fork(entry, options),
        navigateTree: (entry, options) => session.navigateTree(entry, options),
        switchSession: (path, options) => runtime.switchSession(path, options),
        reload: () => Promise.reject(new Error("Unexpected reload")),
      },
    });
  };
  runtime.setRebindSession(bind);
  await bind(runtime.session);
  const selected = manager.getLeafId();
  assert.ok(selected !== null);
  const inactive = manager.appendMessage({
    role: "user",
    content: "This abandoned branch must not become the active conversation.",
    timestamp: Date.now(),
  });
  manager.branch(selected);
  runtime.session.refreshContext();
  const conversation = manager.buildSessionProjection().messages;
  const branch = manager.getBranch();
  const original = await readFile(originalFile, "utf8");
  const cd = async (
    path: string,
    overrides: Partial<ExtensionCommandContext> = {},
  ): Promise<void> => {
    const runner = runtime.session.extensionRunner;
    const command = runner.getCommand("cd");
    assert.ok(command !== undefined);
    await command.handler(path, {
      ...runner.createCommandContext(),
      ...overrides,
    });
  };
  try {
    const model = runtime.session.model;
    assert.equal(model?.id, "tiny");
    const thinking = runtime.session.thinkingLevel;
    assert.match(runtime.session.systemPrompt, /SOURCE_PROJECT_INSTRUCTIONS/u);
    await cd(target, { sessionManager: SessionManager.inMemory(source) });
    assert.match(notifications.at(-1) ?? "", /unavailable with --no-session/u);
    await cd("missing");
    assert.equal(runtime.cwd, source);
    await cd(join(target, "marker.txt"));
    assert.match(notifications.at(-1) ?? "", /Not a directory/u);
    await cd(target, { hasPendingMessages: () => true });
    assert.match(notifications.at(-1) ?? "", /queued messages/u);
    children = true;
    await cd(target);
    assert.match(notifications.at(-1) ?? "", /delegated work/u);
    children = false;
    process.env["PI_DRIVER_ATTEMPT"] = "managed-task";
    await cd(target);
    assert.match(notifications.at(-1) ?? "", /assigned checkout/u);
    delete process.env["PI_DRIVER_ATTEMPT"];
    assert.equal(runtime.cwd, source);
    cancel = true;
    await cd(target);
    assert.equal(runtime.cwd, source);
    const targetManager = SessionManager.create(target);
    assert.deepEqual(await readdir(targetManager.getSessionDir()), []);
    cancel = false;
    await cd('"../other project"');
    assert.equal(runtime.cwd, target);
    assert.equal(runtime.session.sessionManager.getCwd(), target);
    const continued = runtime.session.sessionManager;
    assert.deepEqual(
      continued.buildSessionProjection().messages.slice(0, conversation.length),
      conversation,
    );
    assert.equal(
      JSON.stringify(continued.getBranch().slice(0, branch.length)),
      JSON.stringify(branch),
    );
    assert.ok(continued.getEntry(inactive) !== undefined);
    assert.equal(
      continued.getBranch().some((entry) => entry.id === inactive),
      false,
    );
    assert.equal(continued.getSessionName(), "Moving conversation");
    const modelContext = JSON.stringify(runtime.session.agent.state.messages);
    assert.match(modelContext, /deployment target is cobalt/u);
    assert.match(modelContext, /Working directory changed/u);
    assert.doesNotMatch(modelContext, /abandoned branch/u);
    assert.match(runtime.session.systemPrompt, /TARGET_PROJECT_INSTRUCTIONS/u);
    assert.doesNotMatch(
      runtime.session.systemPrompt,
      /SOURCE_PROJECT_INSTRUCTIONS/u,
    );
    const switchedModel = runtime.session.model;
    assert.ok(switchedModel !== undefined);
    assert.equal(switchedModel.id, model.id);
    assert.equal(switchedModel.provider, model.provider);
    assert.equal(runtime.session.thinkingLevel, thinking);
    assert.equal(
      runtime.session.sessionManager.getHeader()?.parentSession,
      originalFile,
    );
    assert.equal(await readFile(originalFile, "utf8"), original);
    const output = await runtime.session.executeBash("pwd; cat marker.txt");
    assert.match(output.output, /other project\ndestination contents/u);
    const read = runtime.session.agent.state.tools.find(
      (tool) => tool.name === "read",
    );
    assert.ok(read !== undefined);
    const result = await read.execute("native-read", { path: "marker.txt" });
    assert.match(JSON.stringify(result), /destination contents/u);
    const sessionId = runtime.session.sessionId;
    await cd(".");
    assert.equal(runtime.session.sessionId, sessionId);
    await cd(source);
    assert.equal(runtime.cwd, source);
    assert.match(runtime.session.systemPrompt, /SOURCE_PROJECT_INSTRUCTIONS/u);
    assert.deepEqual(
      runtime.session.sessionManager
        .buildSessionProjection()
        .messages.slice(0, conversation.length),
      conversation,
    );
    fullDriver = true;
    await runtime.switchSession(originalFile);
    const driver = runtime.session.extensionRunner;
    const profileCommand = driver.getCommand("driver-profile");
    assert.ok(profileCommand !== undefined);
    await profileCommand.handler("work", driver.createCommandContext());
    assert.ok(runtime.session.getActiveToolNames().includes(delegateTool));
    runtime.session.setThinkingLevel("high");
    await cd(target);
    assert.ok(runtime.session.getActiveToolNames().includes(delegateTool));
    assert.equal(runtime.session.thinkingLevel, "high");
    await writeFile(configFile, JSON.stringify({ ...config, profiles: {} }));
    await cd(source);
    assert.equal(
      runtime.session.getActiveToolNames().includes(delegateTool),
      false,
    );
    assert.ok(
      notifications.some((message) =>
        message.includes("Configure the work profile first"),
      ),
    );
  } finally {
    await runtime.dispose();
  }
});
