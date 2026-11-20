import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execute = promisify(execFile);

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
    const failure = error as Error & {
      stderr?: string;
      code?: string | number;
    };
    throw new Error(
      `${executable} failed (${failure.code ?? "unknown"}): ${failure.stderr?.trim() || failure.message}`,
    );
  }
}
