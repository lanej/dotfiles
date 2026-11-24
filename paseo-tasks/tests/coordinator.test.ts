import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import {
  mkdtempSync,
  readdirSync,
  readlinkSync,
  realpathSync,
  rmSync,
  symlinkSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";

await test("coordinator setup links the tracked guides and refreshes them on rerun", (t) => {
  const root = mkdtempSync(join(tmpdir(), "coordinator-"));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const source = realpathSync(join(import.meta.dirname, "../coordinator"));
  const setup = join(source, "init.sh");
  const dest = join(root, "installed");
  const env = { ...process.env, PATH: root, PASEO_COORDINATOR_DIR: dest };

  symlinkSync("/bin/bash", join(root, "bash"));
  const missing = spawnSync(setup, [], { env, encoding: "utf8" });
  assert.equal(missing.status, 1, missing.stderr);
  assert.match(missing.stderr, /octo-manager is required/);

  writeFileSync(join(root, "octo-manager"), "#!/bin/sh\nexit 1\n", {
    mode: 0o755,
  });
  env.PATH = `${root}:/usr/bin:/bin`;
  execFileSync(setup, [], { env });
  const guides = [
    "INSTRUCTIONS.md",
    "LESSONS.md",
    "PR-WORKFLOW.md",
    "README.md",
  ];
  assert.deepEqual(readdirSync(dest).sort(), guides);
  const lesson = join(dest, "LESSONS.md");
  assert.equal(readlinkSync(lesson), join(source, "guides", "LESSONS.md"));
  unlinkSync(lesson);
  writeFileSync(lesson, "old installed copy\n");
  execFileSync(setup, [dest], { env: { ...env, PASEO_COORDINATOR_DIR: root } });
  for (const guide of guides) {
    const installed = join(dest, guide);
    const canonical = join(source, "guides", guide);
    assert.equal(readlinkSync(installed), canonical);
    assert.equal(realpathSync(installed), canonical);
  }
});
