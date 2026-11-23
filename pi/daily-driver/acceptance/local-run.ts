import { execFile } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import { z } from "zod";
import { withBeadsHttp } from "./beads-http-fixture.ts";

const execute = promisify(execFile);
const root = fileURLToPath(new URL("../", import.meta.url));
const runtime = z.object({ bd: z.string(), dolt: z.string() }).parse(
  process.env["PI_DRIVER_NATIVE_BD"] !== undefined &&
    process.env["PI_DRIVER_NATIVE_DOLT"] !== undefined
    ? {
        bd: process.env["PI_DRIVER_NATIVE_BD"],
        dolt: process.env["PI_DRIVER_NATIVE_DOLT"],
      }
    : JSON.parse(
        await readFile(
          process.env["PI_DRIVER_NATIVE_RUNTIME"] ??
            join(homedir(), ".local/share/beads-service/runtime.json"),
          "utf8",
        ),
      ),
);
const bd = process.env["PI_DRIVER_NATIVE_BD"] ?? runtime.bd;
const dolt = process.env["PI_DRIVER_NATIVE_DOLT"] ?? runtime.dolt;

await withBeadsHttp(bd, dolt, async (fixture, source) => {
  const env: NodeJS.ProcessEnv = {
    ...Object.fromEntries(
      Object.entries(process.env).filter(
        ([key]) =>
          !/^(BEADS_|BD_|DOLT_|GIT_|WORKTREE_|ZELLIJ|TMUX|PI_|PASEO_)/.test(
            key,
          ),
      ),
    ),
    PI_DRIVER_USE_SOURCE: process.env["PI_DRIVER_USE_SOURCE"],
    HOME: fixture.directory,
    DOLT_ROOT_PATH: join(fixture.directory, "dolt-home"),
    DOLT_CLI_NO_UPDATE_CHECK: "1",
    BD_DISABLE_METRICS: "1",
    PATH: `${dirname(dolt)}:${process.env["PATH"] ?? ""}`,
    GIT_CONFIG_GLOBAL: "/dev/null",
    GIT_CONFIG_NOSYSTEM: "1",
  };
  const input = join(fixture.directory, "local-run.json");
  await writeFile(
    input,
    JSON.stringify({
      root,
      directory: fixture.directory,
      workspace: fixture.workspace,
      bd,
      beadsService: source,
      output: process.env["PI_DRIVER_ACCEPTANCE_OUTPUT"],
      scenario: process.env["PI_DRIVER_ACCEPTANCE_CASE"],
    }),
  );
  const result = await execute(
    process.env["PI_DRIVER_NATIVE_PYTHON"] ?? "python3",
    [fileURLToPath(new URL("./local-run.py", import.meta.url)), input],
    { env, encoding: "utf8", timeout: 240_000, maxBuffer: 4 * 1024 * 1024 },
  );
  process.stdout.write(result.stdout);
  process.stderr.write(result.stderr);
});
