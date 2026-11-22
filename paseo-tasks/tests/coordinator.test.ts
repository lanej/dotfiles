import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { test } from "node:test";
import { fileURLToPath, URL } from "node:url";

await test("coordinator installs guidance and preserves operator notes", () => {
  const result = spawnSync(
    "python3",
    [
      fileURLToPath(
        new URL("../coordinator/test_coordinator.py", import.meta.url),
      ),
    ],
    { encoding: "utf8", timeout: 120_000 },
  );
  assert.equal(
    result.status,
    0,
    [result.error?.message, result.stdout, result.stderr]
      .filter(Boolean)
      .join("\n"),
  );
});
