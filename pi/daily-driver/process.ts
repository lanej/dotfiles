import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { z } from "zod";

const execute = promisify(execFile);
const failureSchema = z.object({
  code: z.union([z.string(), z.number()]).optional(),
  stdout: z.string().optional(),
  stderr: z.string().optional(),
  message: z.string(),
});

export function processFailure(error: unknown): z.infer<typeof failureSchema> {
  if (error instanceof CommandError) return error.failure;
  const parsed = failureSchema.safeParse(error);
  return parsed.success
    ? parsed.data
    : { message: error instanceof Error ? error.message : String(error) };
}

class CommandError extends Error {
  constructor(
    message: string,
    readonly failure: z.infer<typeof failureSchema>,
  ) {
    super(message);
  }
}

export async function run(
  executable: string,
  args: string[],
  options: { cwd?: string; env?: NodeJS.ProcessEnv; timeout?: number } = {},
): Promise<string> {
  try {
    const result = await execute(executable, args, {
      timeout: 15_000,
      ...options,
      maxBuffer: 4 * 1024 * 1024,
      encoding: "utf8",
      windowsHide: true,
    });
    return result.stdout;
  } catch (error) {
    const failure = processFailure(error);
    const stderr = failure.stderr?.trim();
    throw new CommandError(
      `${executable} failed (${String(failure.code ?? "unknown")}): ${stderr !== undefined && stderr.length > 0 ? stderr : failure.message}`,
      failure,
    );
  }
}

export async function processStart(pid: number): Promise<string> {
  return (
    await run("ps", ["-p", String(pid), "-o", "lstart="], {
      env: { ...process.env, LC_ALL: "C", TZ: "UTC" },
    })
  ).trim();
}
