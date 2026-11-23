import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { isAbsolute, join } from "node:path";
import { pathToFileURL } from "node:url";

const studio = process.env["STUDIO_TEST_SOURCE"];
assert(
  studio && isAbsolute(studio),
  "Set STUDIO_TEST_SOURCE to an absolute Studio checkout with its locked dependencies installed",
);
const { TaskBeads, BeadChanged } = await import(
  pathToFileURL(join(studio, "task-service.ts")).href
);
const { withBeadsHttp } = await import(
  pathToFileURL(join(studio, "acceptance/beads-http-fixture.ts")).href
);
const execute = promisify(execFile);
const bd = process.env["BEADS_TEST_BD"];
const dolt = process.env["BEADS_TEST_DOLT"];
if (!bd || !dolt)
  throw new Error(
    "Set BEADS_TEST_BD and BEADS_TEST_DOLT to the pinned test binaries",
  );
await withBeadsHttp(bd, dolt, async (fixture, source) => {
  const { stdout, stderr } = await execute(
    "nvim",
    [
      "--headless",
      "-u",
      "NONE",
      "-i",
      "NONE",
      "-n",
      "-l",
      "nvim/tests/beads-native.lua",
    ],
    {
      cwd: process.cwd(),
      env: {
        ...process.env,
        BEADS_TEST_RESULT: join(fixture.directory, "result.json"),
        BEADS_TEST_SETTINGS: JSON.stringify({
          url: source.url,
          project_id: source.projectId,
          prefix: "trial",
          state_dir: join(fixture.directory, "editor"),
        }),
      },
      timeout: 60000,
      maxBuffer: 2 * 1024 * 1024,
    },
  );
  process.stdout.write(stdout + stderr);
  const record = JSON.parse(
    await readFile(join(fixture.directory, "result.json"), "utf8"),
  );
  const service = new TaskBeads({
    url: source.url,
    projectId: source.projectId,
  });
  await assert.rejects(
    () =>
      service.requireCurrent(record.accepted, record.revision, record.attempt),
    BeadChanged,
  );
  console.log(
    "Existing runtime rejected the superseded accepted brief/revision",
  );
});
