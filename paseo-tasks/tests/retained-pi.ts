import assert from "node:assert/strict";
import { writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import { join } from "node:path";
import {
  createAgentSession,
  DefaultResourceLoader,
  ModelRuntime,
  SessionManager,
  SettingsManager,
} from "@earendil-works/pi-coding-agent";
import turnOwner from "../pi/turn-owner";

// Use Pi's real input and run lifecycle. Only its model endpoint and the Paseo RPC transport are fixtures.
export async function checkRetainedPi(
  root: string,
  env: Record<string, string>,
  setWorkerOwnership: (owned: boolean) => Promise<void>,
) {
  const requests: string[] = [];
  const provider = createServer((request, response) => {
    let body = "";
    request.setEncoding("utf8");
    request.on("data", (chunk: string) => {
      body += chunk;
    });
    request.on("end", () => {
      requests.push(body);
      response.writeHead(200, { "content-type": "text/event-stream" });
      const reply = {
        id: "fixture",
        model: "fixture",
        choices: [
          {
            index: 0,
            delta: { role: "assistant", content: "Confirmed" },
            finish_reason: "stop",
          },
        ],
      };
      response.end(`data: ${JSON.stringify(reply)}\n\ndata: [DONE]\n\n`);
    });
  });
  const previous = Object.fromEntries(
    Object.keys(env).map((key) => [key, process.env[key]]),
  );
  Object.assign(process.env, env);
  let session:
    | Awaited<ReturnType<typeof createAgentSession>>["session"]
    | undefined;
  try {
    await new Promise<void>((resolve, reject) => {
      provider.once("error", reject);
      provider.listen(0, "127.0.0.1", resolve);
    });
    const address = provider.address();
    assert(address && typeof address !== "string");
    const modelsPath = join(root, "models.json");
    await writeFile(
      modelsPath,
      JSON.stringify({
        providers: {
          fixture: {
            api: "openai-completions",
            apiKey: "fixture",
            baseUrl: `http://127.0.0.1:${address.port}/v1`,
            models: [{ id: "fixture" }],
          },
        },
      }),
    );
    const modelRuntime = await ModelRuntime.create({
      modelsPath,
      authPath: join(root, "auth.json"),
      modelsStorePath: join(root, "catalog.json"),
    });
    const model = modelRuntime.getModel("fixture", "fixture");
    assert(model);
    const settingsManager = SettingsManager.inMemory();
    let transferAfterInput = false;
    const resourceLoader = new DefaultResourceLoader({
      cwd: root,
      agentDir: root,
      settingsManager,
      noExtensions: true,
      noContextFiles: true,
      noSkills: true,
      noThemes: true,
      noPromptTemplates: true,
      extensionFactories: [
        turnOwner,
        (pi) => {
          pi.on("input", async () => {
            if (transferAfterInput) {
              transferAfterInput = false;
              await setWorkerOwnership(false);
            }
          });
        },
      ],
    });
    await resourceLoader.reload();
    assert.deepEqual(resourceLoader.getExtensions().errors, []);
    ({ session } = await createAgentSession({
      cwd: root,
      agentDir: root,
      modelRuntime,
      model,
      noTools: "all",
      resourceLoader,
      settingsManager,
      sessionManager: SessionManager.inMemory(root),
    }));
    await session.bindExtensions({ mode: "rpc" });
    await session.prompt("Input after the task transfer");
    assert.equal(
      await session.steer("Steering after the task transfer"),
      "handled",
    );
    assert.equal(
      requests.length,
      0,
      "Transferred work must never reach the provider",
    );
    await setWorkerOwnership(true);
    await session.prompt("Previously authorized context");
    assert.equal(requests.length, 1);
    transferAfterInput = true;
    await session.prompt("Input admitted before transfer at run start");
    await session.sendCustomMessage(
      {
        customType: "fixture",
        content: "Custom input during transfer at run start",
        display: true,
        details: { note: "Private details during transfer at run start" },
      },
      { triggerTurn: true },
    );
    assert.equal(
      requests.length,
      1,
      "A run-start denial must prevent the model request",
    );
    assert.doesNotMatch(
      JSON.stringify(session.sessionManager.getBranch()),
      /transfer at run start/,
    );
    await setWorkerOwnership(true);
    await session.prompt("Input after ownership was restored");
    assert.equal(
      requests.length,
      2,
      "The same Pi conversation can run again after reconciliation",
    );
    assert.match(requests[1], /Previously authorized context/);
    assert.match(requests[1], /Input after ownership was restored/);
    assert.doesNotMatch(
      requests[1],
      /after the task transfer|transfer at run start/,
    );
  } finally {
    session?.dispose();
    provider.closeAllConnections();
    if (provider.listening)
      await new Promise<void>((resolve) => provider.close(() => resolve()));
    for (const [key, saved] of Object.entries(previous))
      if (saved === undefined) delete process.env[key];
      else process.env[key] = saved;
  }
}
