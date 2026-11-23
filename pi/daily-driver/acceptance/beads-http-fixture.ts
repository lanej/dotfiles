import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { createServer } from "node:net";
import { dirname, join } from "node:path";
import { z } from "zod";
import { withBeads, type NativeBeads } from "./beads-fixture.ts";

export interface BeadsHttpSource {
  url: string;
  projectId: string;
}

export async function withBeadsHttp<T>(
  bd: string,
  dolt: string,
  use: (fixture: NativeBeads, source: BeadsHttpSource) => Promise<T>,
): Promise<T> {
  return withBeads(bd, dolt, async (fixture) => {
    const env: NodeJS.ProcessEnv = {
      ...Object.fromEntries(
        Object.entries(process.env).filter(
          ([key]) =>
            !/^(BEADS_|BD_|DOLT_|GIT_|WORKTREE_|ZELLIJ|TMUX|PI_|PASEO_)/.test(
              key,
            ),
        ),
      ),
      HOME: fixture.directory,
      DOLT_ROOT_PATH: join(fixture.directory, "dolt-home"),
      DOLT_CLI_NO_UPDATE_CHECK: "1",
      BD_DISABLE_METRICS: "1",
      PATH: `${dirname(dolt)}:${process.env["PATH"] ?? ""}`,
      GIT_CONFIG_GLOBAL: "/dev/null",
      GIT_CONFIG_NOSYSTEM: "1",
    };
    const listener = createServer();
    listener.listen(0, "127.0.0.1");
    await once(listener, "listening");
    const address = listener.address();
    assert(address !== null && typeof address !== "string");
    const port = address.port;
    await new Promise<void>((resolve, reject) => {
      listener.close((error) => {
        if (error !== undefined) reject(error);
        else resolve();
      });
    });
    const service = spawn(
      bd,
      ["serve", "--addr", `127.0.0.1:${String(port)}`],
      {
        cwd: fixture.workspace,
        env,
        stdio: ["ignore", "ignore", "pipe"],
      },
    );
    let diagnostics = "";
    service.stderr.on("data", (chunk: Buffer) => {
      diagnostics = (diagnostics + chunk.toString()).slice(-8000);
    });
    service.on("error", (error) => {
      diagnostics += error.message;
    });
    try {
      const url = `http://127.0.0.1:${String(port)}`;
      let projectId: string | undefined;
      const deadline = Date.now() + 20_000;
      while (Date.now() < deadline && projectId === undefined) {
        try {
          const response = await fetch(`${url}/v0/beads/context`, {
            signal: AbortSignal.timeout(1000),
          });
          if (response.ok) {
            projectId = z
              .object({ project_id: z.string().min(1) })
              .parse(await response.json()).project_id;
          }
        } catch {
          // rationale(acceptance): The private HTTP listener may not be bound yet.
        }
        assert.equal(service.exitCode, null, diagnostics);
        assert.equal(service.signalCode, null, diagnostics);
        assert(service.pid !== undefined, `Could not start ${bd} serve`);
        if (projectId === undefined)
          await new Promise((resolve) => setTimeout(resolve, 100));
      }
      assert(
        projectId !== undefined && projectId.length > 0,
        `Beads HTTP fixture did not start: ${diagnostics}`,
      );
      return await use(fixture, { url, projectId });
    } finally {
      if (
        service.exitCode === null &&
        service.signalCode === null &&
        service.pid !== undefined
      ) {
        service.kill("SIGTERM");
        const timer = setTimeout(() => service.kill("SIGKILL"), 5000);
        try {
          await once(service, "close");
        } finally {
          clearTimeout(timer);
        }
      }
    }
  });
}
