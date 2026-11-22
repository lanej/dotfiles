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
  const parsed = failureSchema.safeParse(error);
  return parsed.success
    ? parsed.data
    : { message: error instanceof Error ? error.message : String(error) };
}

export async function run(
  executable: string,
  args: string[],
  options: { cwd?: string; env?: NodeJS.ProcessEnv } = {},
): Promise<string> {
  try {
    const result = await execute(executable, args, {
      ...options,
      timeout: 15_000,
      maxBuffer: 4 * 1024 * 1024,
      encoding: "utf8",
      windowsHide: true,
    });
    return result.stdout;
  } catch (error) {
    const failure = processFailure(error);
    const stderr = failure.stderr?.trim();
    throw new Error(
      `${executable} failed (${String(failure.code ?? "unknown")}): ${stderr !== undefined && stderr.length > 0 ? stderr : failure.message}`,
    );
  }
}
