import assert from "node:assert/strict";
import { Command } from "commander";
import { BeadsHttp, type components } from "@lanej/task-runtime/beads";
import { writeFile } from "node:fs/promises";
import { join } from "node:path";
import { z } from "zod";
import { BeadsReader, parentId, taskSchema } from "../beads.ts";
import { run } from "../process.ts";
import { beadSchema, type NativeBead } from "../task-service.ts";
import { withBeadsHttp } from "./beads-http-fixture.ts";
import { verificationControl } from "./verification-control.ts";

class ContractProbe extends BeadsHttp {
  async read(id: string): Promise<NativeBead> {
    return beadSchema.parse(
      await this.result(
        this.client.GET("/v0/beads/issues/{id}", {
          params: { path: { id } },
        }),
      ),
    );
  }

  patch(
    before: NativeBead,
    actor: string,
    patch: components["schemas"]["IssuePatchBody"],
  ) {
    return this.client.PATCH("/v0/beads/issues/{id}", {
      params: { path: { id: before.id } },
      body: {
        actor,
        expected_version: before.revision,
        expected_status: before.status,
        expected_assignee: before.assignee,
        force_close_policy: false,
        force_assignee_transfer: false,
        patch,
      },
    });
  }
}

const program = new Command()
  .requiredOption("--bd <path>", "Absolute path to the evaluated bd binary")
  .requiredOption(
    "--dolt <path>",
    "Absolute path to the evaluated Dolt binary",
  );
program.parse();
const options = program.opts<{ bd: string; dolt: string }>();
const version = (await run(options.bd, ["--version"])).trim();
await withBeadsHttp(
  options.bd,
  options.dolt,
  async ({ workspace, directory, command }, source) => {
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
      guardedHttpClaim: false,
      updateBumpsRevision: false,
      editorBumpsRevision: false,
      atomicCurrentScopeClosure: false,
      dispatchReady: false,
    };
    const http = new ContractProbe(source.url, source.projectId);
    await http.verifyAuthority();
    const createdHttp = await command([
      "create",
      "--title",
      "HTTP scope fence",
      "--type",
      "task",
      "--description",
      "HTTP accepted scope A",
      "--acceptance",
      "HTTP accepted criteria A",
      "--json",
    ]);
    assert.equal(createdHttp.code, 0, createdHttp.stderr);
    const httpId = taskSchema.parse(JSON.parse(createdHttp.stdout)).id;
    const original = await http.read(httpId);
    const claims = await Promise.all(
      ["http-a", "http-b"].map((actor) =>
        http.patch(original, actor, { assignee: actor, status: "in_progress" }),
      ),
    );
    assert.equal(claims.filter((result) => result.response.ok).length, 1);
    const loser = claims.find((result) => !result.response.ok);
    assert(loser !== undefined);
    assert.equal(loser.response.status, 409);
    z.object({ code: z.literal("precondition_failed") }).parse(loser.error);
    report.guardedHttpClaim = true;
    const admitted = await http.read(httpId);
    assert.equal(admitted.status, "in_progress");
    assert.equal(admitted.description, original.description);
    assert.equal(admitted.acceptance_criteria, original.acceptance_criteria);
    assert(["http-a", "http-b"].includes(admitted.assignee));

    const rejectStale = async (before: NativeBead, field: string) => {
      const rejected = await http.patch(before, before.assignee, {
        status: "closed",
        metadata: { merge: { "contract.stale": field } },
      });
      assert.equal(
        rejected.response.status,
        409,
        JSON.stringify(rejected.error),
      );
      z.object({ code: z.literal("precondition_failed") }).parse(
        rejected.error,
      );
      const preserved = await http.read(before.id);
      assert.equal(preserved.status, "in_progress");
      assert.equal(preserved.metadata["contract.stale"], undefined);
    };
    const changedDescription = await command(
      ["update", httpId, "--description", "HTTP human scope B", "--json"],
      "operator",
    );
    assert.equal(changedDescription.code, 0, changedDescription.stderr);
    const updated = await http.read(httpId);
    assert.equal(updated.description, "HTTP human scope B");
    assert.equal(updated.status, admitted.status);
    assert.equal(updated.assignee, admitted.assignee);
    assert.notEqual(
      updated.revision,
      admitted.revision,
      "bd update changed the description without changing its opaque revision",
    );
    await rejectStale(admitted, "description");
    report.updateBumpsRevision = true;

    const editor = join(directory, "fixture-editor.sh");
    await writeFile(
      editor,
      '#!/bin/sh\nprintf "%s\\n" "HTTP human criteria B" > "$1"\n',
      { mode: 0o700 },
    );
    const edited = await command(["edit", httpId, "--acceptance"], "operator", {
      EDITOR: editor,
      VISUAL: editor,
    });
    assert.equal(edited.code, 0, edited.stderr);
    const currentScope = await http.read(httpId);
    assert.equal(currentScope.acceptance_criteria, "HTTP human criteria B");
    assert.equal(currentScope.status, updated.status);
    assert.equal(currentScope.assignee, updated.assignee);
    assert.notEqual(
      currentScope.revision,
      updated.revision,
      "bd edit --acceptance changed criteria without changing its opaque revision",
    );
    await rejectStale(updated, "acceptance_criteria");
    report.editorBumpsRevision = true;

    const evidence = {
      kind: "native-contract-probe",
      acceptedRevision: currentScope.revision,
      description: currentScope.description,
      acceptance_criteria: currentScope.acceptance_criteria,
    };
    const completed = await http.patch(currentScope, currentScope.assignee, {
      status: "closed",
      metadata: { merge: { "contract.result": evidence } },
    });
    assert.equal(
      completed.response.status,
      200,
      JSON.stringify(completed.error),
    );
    const closed = await http.read(httpId);
    assert.equal(closed.status, "closed");
    assert.deepEqual(closed.metadata["contract.result"], evidence);
    assert.equal(closed.description, currentScope.description);
    assert.equal(closed.acceptance_criteria, currentScope.acceptance_criteria);
    report.atomicCurrentScopeClosure = true;
    report.dispatchReady = true;
    const verification = await verificationControl(
      { workspace, directory, command },
      source,
    );
    console.log(JSON.stringify({ ...report, ...verification }, null, 2));
  },
);
