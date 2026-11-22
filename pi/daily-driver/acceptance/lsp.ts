import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import {
  mkdir,
  mkdtemp,
  readFile,
  realpath,
  rm,
  symlink,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { setTimeout as delay } from "node:timers/promises";
import { promisify } from "node:util";
import { z } from "zod";
import {
  createAgentSessionFromServices,
  createAgentSessionServices,
  SessionManager,
  SettingsManager,
} from "@earendil-works/pi-coding-agent";
import {
  registerCodeIntelligence,
  lspTool,
  renameTool,
} from "../code-intelligence/extension.ts";

const root = await realpath(await mkdtemp(join(tmpdir(), "pi-lsp-native-")));
const agentDir = join(root, "agent");
await mkdir(agentDir);
await mkdir(join(root, "node_modules"));
await symlink(
  fileURLToPath(new URL("../node_modules/typescript", import.meta.url)),
  join(root, "node_modules/typescript"),
);
await writeFile(
  join(root, "tsconfig.json"),
  JSON.stringify({
    compilerOptions: { strict: true, noEmit: true, skipLibCheck: true },
    files: ["a.ts", "b.ts"],
  }),
);
await writeFile(
  join(root, "a.ts"),
  "export function greet(name: string): string { return name; }\n",
);
const valid =
  'import { greet } from "./a";\nexport const answer: string = greet("hello");\n';
await writeFile(join(root, "b.ts"), valid);
let blockWrites = false;
const services = await createAgentSessionServices({
  cwd: root,
  agentDir,
  settingsManager: SettingsManager.inMemory({}, { projectTrusted: true }),
  resourceLoaderOptions: {
    noExtensions: true,
    noSkills: true,
    noPromptTemplates: true,
    noThemes: true,
    extensionFactories: [
      (pi) => {
        registerCodeIntelligence(pi);
        pi.on("tool_call", (event) => {
          if (
            blockWrites &&
            event.toolName === "write" &&
            typeof event.input["path"] === "string" &&
            event.input["path"].endsWith("b.ts")
          )
            return { block: true, reason: "Fixture approval revoked" };
          return undefined;
        });
      },
    ],
  },
});
const { session } = await createAgentSessionFromServices({
  services,
  sessionManager: SessionManager.inMemory(root),
});
await session.bindExtensions({ mode: "rpc" });
session.agent.state.messages.push({
  role: "assistant",
  content: [
    { type: "toolCall", id: "acceptance", name: "acceptance", arguments: {} },
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
const tool = session.extensionRunner.createToolContext("acceptance", undefined);
const call = async (name: string, args: unknown) => {
  const outcome = await tool.executeTool(name, args);
  assert.equal(outcome.isError, false, JSON.stringify(outcome.result));
  return outcome.result.content
    .filter((item) => item.type === "text")
    .map((item) => item.text)
    .join("\n");
};
async function eventually(
  operation: () => Promise<string>,
  expected: RegExp,
): Promise<void> {
  const deadline = Date.now() + 30_000;
  let observed = "";
  do {
    observed = await operation();
    if (expected.test(observed)) return;
    await delay(100);
  } while (Date.now() < deadline);
  assert.match(
    observed,
    expected,
    "Language-server result did not settle before the acceptance deadline",
  );
}
try {
  // Initialization can precede project indexing; assert the semantic result when it settles.
  await eventually(
    () =>
      call(lspTool, {
        action: "definition",
        path: "b.ts",
        line: 2,
        column: 31,
      }),
    /a\.ts/u,
  );
  const references = await call(lspTool, {
    action: "references",
    path: "a.ts",
    line: 1,
    column: 18,
  });
  assert.match(references, /b\.ts/u);
  const introduced = await call("write", {
    path: "b.ts",
    content: valid.replace("answer: string", "answer: number"),
  });
  // The server may publish after the bounded automatic feedback window.
  assert.match(introduced, /lsp/u);
  await eventually(
    () => call(lspTool, { action: "diagnostics", path: "b.ts" }),
    /2322/u,
  );
  await call("write", { path: "b.ts", content: valid });
  await eventually(
    () => call(lspTool, { action: "diagnostics", path: "b.ts" }),
    /"total": 0/u,
  );
  const preview = z
    .object({
      token: z.string(),
      files: z.array(z.object({ path: z.string() })),
    })
    .parse(
      JSON.parse(
        await call(renameTool, {
          action: "preview",
          path: "a.ts",
          line: 1,
          column: 18,
          newName: "welcome",
        }),
      ),
    );
  assert.equal(preview.files.length, 2);
  await writeFile(join(root, "b.ts"), `${valid}// operator edit\n`);
  const stale = await tool.executeTool(renameTool, {
    action: "apply",
    token: preview.token,
  });
  assert.equal(stale.isError, true);
  assert.match(JSON.stringify(stale.result), /stale/u);
  assert.match(await readFile(join(root, "a.ts"), "utf8"), /function greet/u);
  await call("write", { path: "b.ts", content: valid });
  const blockedPreview = z.object({ token: z.string() }).parse(
    JSON.parse(
      await call(renameTool, {
        action: "preview",
        path: "a.ts",
        line: 1,
        column: 18,
        newName: "welcome",
      }),
    ),
  );
  blockWrites = true;
  const blocked = await tool.executeTool(renameTool, {
    action: "apply",
    token: blockedPreview.token,
  });
  assert.equal(
    blocked.isError,
    true,
    "nested rename writes must honor Pi's tool hooks",
  );
  assert.match(JSON.stringify(blocked.result), /Fixture approval revoked/u);
  assert.match(await readFile(join(root, "b.ts"), "utf8"), /greet/u);
  assert.ok(
    session.sessionManager
      .getBranch()
      .some(
        (entry) =>
          entry.type === "custom" &&
          entry.customType === "pi-driver:rename-recovery",
      ),
  );
  blockWrites = false;
  await call("write", {
    path: "a.ts",
    content: "export function greet(name: string): string { return name; }\n",
  });
  const finalPreview = z.object({ token: z.string() }).parse(
    JSON.parse(
      await call(renameTool, {
        action: "preview",
        path: "a.ts",
        line: 1,
        column: 18,
        newName: "welcome",
      }),
    ),
  );
  await call(renameTool, { action: "apply", token: finalPreview.token });
  assert.match(await readFile(join(root, "a.ts"), "utf8"), /function welcome/u);
  assert.match(
    await readFile(join(root, "b.ts"), "utf8"),
    /welcome\("hello"\)/u,
  );
  await promisify(execFile)(
    process.execPath,
    [
      fileURLToPath(
        new URL("../node_modules/typescript/bin/tsc", import.meta.url),
      ),
      "--project",
      join(root, "tsconfig.json"),
    ],
    { timeout: 15_000 },
  );
  console.log(
    "Native Pi + TypeScript LSP: definitions, references, edit diagnostics, semantic rename and compiler verification passed.",
  );
} finally {
  await session.extensionRunner.emit({
    type: "session_shutdown",
    reason: "quit",
  });
  session.dispose();
  await rm(root, { recursive: true, force: true });
}
