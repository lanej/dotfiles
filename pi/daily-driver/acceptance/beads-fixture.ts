import { execFile, spawn } from "node:child_process";
import { once } from "node:events";
import { mkdir, mkdtemp, rm } from "node:fs/promises";
import { createConnection, createServer } from "node:net";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { promisify } from "node:util";
import { processFailure } from "../process.ts";

const execute = promisify(execFile);
export interface CommandResult {
  code: number;
  stdout: string;
  stderr: string;
}
export interface NativeBeads {
  workspace: string;
  directory: string;
  command: (
    args: string[],
    actor?: string,
    environment?: NodeJS.ProcessEnv,
  ) => Promise<CommandResult>;
}

export async function withBeads<T>(
  bd: string,
  dolt: string,
  use: (fixture: NativeBeads) => Promise<T>,
): Promise<T> {
  const directory = await mkdtemp(join(tmpdir(), "pi-driver-native-"));
  const workspace = join(directory, "workspace");
  const data = join(directory, "dolt");
  await mkdir(workspace);
  await mkdir(data);
  const env = Object.fromEntries(
    Object.entries(process.env).filter(
      ([key]) => !/^(BEADS_|BD_|DOLT_|GIT_)/.test(key),
    ),
  );
  Object.assign(env, {
    HOME: directory,
    DOLT_ROOT_PATH: join(directory, "dolt-home"),
    DOLT_CLI_NO_UPDATE_CHECK: "1",
    PATH: `${dirname(dolt)}:${process.env["PATH"] ?? ""}`,
  });
  await execute(
    "git",
    ["-c", "core.hooksPath=/dev/null", "init", "--quiet", workspace],
    { env },
  );
  const listener = createServer();
  listener.listen(0, "127.0.0.1");
  await once(listener, "listening");
  const address = listener.address();
  if (address === null || typeof address === "string")
    throw new Error("Cannot reserve fixture port");
  const port = address.port;
  await new Promise<void>((resolve, reject) => {
    listener.close((error) => {
      if (error !== undefined) reject(error);
      else resolve();
    });
  });
  const server = spawn(
    dolt,
    [
      "sql-server",
      "--host",
      "127.0.0.1",
      "--port",
      String(port),
      "--data-dir",
      data,
    ],
    { cwd: data, env, stdio: ["ignore", "ignore", "pipe"] },
  );
  let serverError = "";
  server.stderr.on("data", (chunk: Buffer) => {
    serverError = (serverError + chunk.toString()).slice(-4000);
  });
  server.on("error", (error) => {
    serverError = error.message;
  });
  const command = async (
    args: string[],
    actor = "trial",
    environment: NodeJS.ProcessEnv = {},
  ): Promise<CommandResult> => {
    try {
      const result = await execute(
        bd,
        ["--sandbox", "--actor", actor, ...args],
        {
          cwd: workspace,
          env: { ...env, ...environment },
          encoding: "utf8",
          timeout: 30_000,
          maxBuffer: 4 * 1024 * 1024,
        },
      );
      return { code: 0, ...result };
    } catch (error) {
      const failure = processFailure(error);
      return {
        code: typeof failure.code === "number" ? failure.code : -1,
        stdout: failure.stdout ?? "",
        stderr:
          failure.stderr !== undefined && failure.stderr.length > 0
            ? failure.stderr
            : failure.message,
      };
    }
  };
  try {
    const deadline = Date.now() + 20_000;
    for (;;) {
      const connected = await new Promise<boolean>((resolve) => {
        const socket = createConnection({ host: "127.0.0.1", port });
        socket.once("connect", () => {
          socket.destroy();
          resolve(true);
        });
        socket.once("error", () => {
          socket.destroy();
          resolve(false);
        });
      });
      if (connected) break;
      if (Date.now() >= deadline || server.exitCode !== null)
        throw new Error(`Dolt fixture did not start: ${serverError}`);
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    const initialized = await command([
      "init",
      "--server",
      "--external",
      "--server-host",
      "127.0.0.1",
      "--server-port",
      String(port),
      "--database",
      "pi_driver_trial",
      "--prefix",
      "trial",
      "--skip-agents",
      "--skip-hooks",
      "--non-interactive",
    ]);
    if (initialized.code !== 0) throw new Error(initialized.stderr);
    return await use({ workspace, directory, command });
  } finally {
    if (server.exitCode === null) {
      server.kill("SIGTERM");
      const timer = setTimeout(() => server.kill("SIGKILL"), 5000);
      try {
        await once(server, "close");
      } finally {
        clearTimeout(timer);
      }
    }
    await rm(directory, { recursive: true, force: true, maxRetries: 3 });
  }
}
