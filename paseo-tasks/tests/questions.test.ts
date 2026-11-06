import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
// @ts-expect-error The existing Pi extension is intentionally plain JavaScript.
import questions from "../../pi/extensions/paseo-questions.mjs";
// @ts-expect-error Configuration entrypoint is plain JavaScript.
import { configureQuestions, configureModels } from "../../scripts/paseo-tasks-config.mjs";

test("managers and workers use the same native question bridge, including typed answers and cancellation", async () => {
  const previous = process.env.PASEO_TASK_ROLE;
  try {
    for (const role of ["manager", "worker"]) {
      process.env.PASEO_TASK_ROLE = role;
      const hooks = new Map<string, Function>();
      let tool: any;
      questions({ on: (name: string, fn: Function) => hooks.set(name, fn), registerTool: (value: any) => { tool = value; } });
      hooks.get("session_start")!({}, { mode: "rpc" });
      const input = { questions: [{ header: "Approach", question: "Which approach should I use?",
        options: [{ label: "Measure", description: "Collect evidence" }, { label: "Wait", description: "Defer" }] }] };
      const output = await tool.execute("id", input, undefined, undefined,
        { hasUI: true, ui: { select: async () => "3. Type something.", input: async () => "Investigate both" } });
      assert.equal(output.details.answers[0].answer, "Investigate both");
      const cancelled = await tool.execute("id", input, undefined, undefined,
        { hasUI: true, ui: { select: async () => undefined } });
      assert.equal(cancelled.details.cancelled, true);
      assert.deepEqual(cancelled.details.answers, []);
      hooks.get("session_shutdown")!();
      await assert.rejects(() => tool.execute("id", input, undefined, undefined, { hasUI: true }), /Open this conversation/);
    }
  } finally {
    if (previous === undefined) delete process.env.PASEO_TASK_ROLE;
    else process.env.PASEO_TASK_ROLE = previous;
  }
});

test("question configuration is idempotent and preserves model selection, AWS settings and unrelated extensions", async () => {
  const directory = await mkdtemp(join(tmpdir(), "questions-test-"));
  const file = join(directory, "settings.json");
  try {
    const original = { extensions: ["/existing.mjs"], defaultProvider: "amazon-bedrock",
      defaultModel: "us.anthropic.claude-sonnet-5-5", defaultThinkingLevel: "medium", custom: { awsProfile: "keep" } };
    await writeFile(file, JSON.stringify(original));
    await configureQuestions(file);
    await configureQuestions(file);
    const saved = JSON.parse(await readFile(file, "utf8"));
    assert.equal(saved.extensions.length, 3);
    assert.deepEqual({ ...saved, extensions: original.extensions }, original);
    const models = join(directory, "models.json");
    const other = { providers: { existing: { api: "openai-responses", models: [{ id: "retained" }] } } };
    await writeFile(models, JSON.stringify(other));
    await configureModels(models); await configureModels(models);
    const configured = JSON.parse(await readFile(models, "utf8"));
    assert.deepEqual(configured.providers.existing, other.providers.existing);
    assert.equal(configured.providers["bedrock-sonnet-router"].api, "anthropic-messages");
  } finally { await rm(directory, { recursive: true, force: true }); }
});
