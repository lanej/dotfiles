import assert from "node:assert/strict";
import { Command } from "commander";
import { BeadsReader, parentId, taskSchema } from "../beads.ts";
import { run } from "../process.ts";
import { withBeads } from "./beads-fixture.ts";

const program = new Command()
  .requiredOption("--bd <path>", "Absolute path to the evaluated bd binary")
  .requiredOption(
    "--dolt <path>",
    "Absolute path to the evaluated Dolt binary",
  );
program.parse();
const options = program.opts<{ bd: string; dolt: string }>();
const version = (await run(options.bd, ["--version"])).trim();
await withBeads(options.bd, options.dolt, async ({ workspace, command }) => {
  const create = await command([
    "create",
    "--title",
    "Scope fence probe",
    "--type",
    "task",
    "--description",
    "Accepted scope A",
    "--acceptance",
    "Only one current attempt",
    "--json",
  ]);
  assert.equal(create.code, 0, create.stderr);
  const id = taskSchema.parse(JSON.parse(create.stdout)).id;
  const child = await command([
    "create",
    "--title",
    "Child probe",
    "--type",
    "task",
    "--parent",
    id,
    "--json",
  ]);
  assert.equal(child.code, 0, child.stderr);
  const childId = taskSchema.parse(JSON.parse(child.stdout)).id;
  const reader = new BeadsReader({
    workspace,
    database: "pi_driver_trial",
    branch: "main",
    executable: options.bd,
  });
  const listed = await reader.list().catch(async (error: unknown) => {
    throw new Error(
      `${String(error)}; native list: ${(await command(["list", "--all", "--json"])).stdout}`,
    );
  });
  assert.equal(listed.length, 2);
  const childTask = await reader.show(childId);
  assert.equal(
    parentId(childTask),
    id,
    "The browser must retain native containment identity",
  );
  // Also inspect list shape: a flat result must not silently look like a complete hierarchy.
  const listHasParent = listed.some(
    (task) => task.id === childId && parentId(task) === id,
  );
  const race = await Promise.all([
    command(["update", id, "--claim", "--json"], "attempt-a"),
    command(["update", id, "--claim", "--json"], "attempt-b"),
  ]);
  assert.equal(
    race.filter((result) => result.code === 0).length,
    1,
    JSON.stringify(race),
  );
  const current = await reader.show(id);
  const owner = String(current.assignee);
  const stale = owner === "attempt-a" ? "attempt-b" : "attempt-a";
  const staleUpdate = await command(
    [
      "update",
      id,
      "--if-assignee",
      stale,
      "--if-status",
      "in_progress",
      "--status",
      "open",
      "--json",
    ],
    stale,
  );
  assert.equal(staleUpdate.code, 13, staleUpdate.stderr);
  assert.equal(
    (await command(["update", id, "--claim", "--json"], owner)).code,
    0,
  );
  assert.equal(
    (
      await command(
        [
          "update",
          id,
          "--description",
          "Scope B changed after admission",
          "--json",
        ],
        "operator",
      )
    ).code,
    0,
  );
  const oldScope = await command(
    [
      "update",
      id,
      "--if-assignee",
      owner,
      "--if-status",
      "in_progress",
      "--status",
      "open",
      "--json",
    ],
    owner,
  );
  const report = {
    version,
    atomicClaim: true,
    staleOwnerRejected: true,
    repeatedClaimReconciled: true,
    listHasParent,
    staleAcceptedScopeRejected: oldScope.code !== 0,
    oldScopeExit: oldScope.code,
    dispatchReady: false,
  };
  console.log(JSON.stringify(report, null, 2));
  process.exitCode = 2;
});
