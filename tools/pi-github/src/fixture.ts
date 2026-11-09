import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { mkdir, mkdtemp, writeFile, readFile, lstat, rm } from "node:fs/promises";
import { join, resolve, dirname } from "node:path";

const exec = promisify(execFile);
const expected = { maxAttempts: 3, timeoutSeconds: 60, retryDelaySeconds: 1 };
const policyFile = "retry-policy.json";
export const conflictBrief = "Resolve the Git merge conflict in retry-policy.json. Preserve the target branch's maxAttempts of 3, take the source branch's timeoutSeconds of 60, and preserve retryDelaySeconds of 1. Read the conflict, write a combined policy, and validate it. Do not choose either branch unchanged.";
async function git(cwd: string, args: string[], signal?: AbortSignal): Promise<string> {
  const { stdout } = await exec("git", ["-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", "-c", "user.name=Pi Fixture", "-c", "user.email=fixture@localhost", ...args], {
    cwd, signal, timeout: 15000, maxBuffer: 65536,
    env: { PATH: process.env.PATH, LANG: "C", GIT_CONFIG_NOSYSTEM: "1", GIT_CONFIG_GLOBAL: "/dev/null", GIT_TERMINAL_PROMPT: "0" },
  });
  return stdout.trim();
}
async function safeFile(path: string): Promise<string> {
  const file = join(path, policyFile);
  const info = await lstat(file);
  if (!info.isFile() || info.isSymbolicLink() || info.size > 4096) throw new Error("Invalid fixture policy file");
  return file;
}
export async function createFixture(directory: string): Promise<{ path: string; conflict: string }> {
  const parent = join(directory, "fixtures");
  await mkdir(parent, { recursive: true, mode: 0o700 });
  if ((await lstat(parent)).isSymbolicLink()) throw new Error("Fixture directory must not be a symlink");
  const path = await mkdtemp(join(parent, "attempt-"));
  try {
    await git(path, ["init", "-b", "main"]);
    await writeFile(join(path, policyFile), JSON.stringify({ maxAttempts: 1, timeoutSeconds: 30, retryDelaySeconds: 1 }) + "\n");
    await git(path, ["add", policyFile]); await git(path, ["commit", "-m", "base"]);
    await git(path, ["branch", "source"]);
    await writeFile(join(path, policyFile), JSON.stringify({ maxAttempts: 3, timeoutSeconds: 30, retryDelaySeconds: 1 }) + "\n");
    await git(path, ["commit", "-am", "target attempt limit"]);
    await git(path, ["checkout", "source"]);
    await writeFile(join(path, policyFile), JSON.stringify({ maxAttempts: 5, timeoutSeconds: 60, retryDelaySeconds: 1 }) + "\n");
    await git(path, ["commit", "-am", "source timeout"]);
    await git(path, ["checkout", "main"]);
    try { await git(path, ["merge", "--no-commit", "source"]); } catch (error) {
      if ((error as { code?: number }).code !== 1) throw error;
    }
    const unmerged = await git(path, ["diff", "--name-only", "--diff-filter=U"]);
    if (unmerged !== policyFile) throw new Error("Fixture did not produce the expected Git conflict");
    return { path, conflict: await readFile(join(path, policyFile), "utf8") };
  } catch (error) { await rm(path, { recursive: true, force: true }); throw error; }
}
export async function readConflict(path: string): Promise<{ brief: string; content: string }> {
  return { brief: conflictBrief, content: await readFile(await safeFile(path), "utf8") };
}
export async function writeResolution(path: string, policy: unknown): Promise<string> {
  if (!policy || typeof policy !== "object" || Array.isArray(policy)) throw new Error("Policy must be a JSON object");
  const bytes = JSON.stringify(policy);
  if (bytes.length > 2048) throw new Error("Policy is too large");
  await writeFile(await safeFile(path), bytes + "\n");
  return "Policy written. Run validate_resolution before finishing.";
}
export async function validateResolution(path: string): Promise<{ valid: boolean; reason: string }> {
  try {
    const value = JSON.parse(await readFile(await safeFile(path), "utf8")) as Record<string, unknown>;
    const valid = Object.keys(value).sort().join() === Object.keys(expected).sort().join() && Object.entries(expected).every(([key, v]) => value[key] === v);
    const changed = await git(path, ["status", "--porcelain", "--untracked-files=all"]);
    const paths = changed.split("\n").filter(Boolean).map(line => line.slice(3));
    if (paths.some(file => file !== policyFile)) return { valid: false, reason: "Unrelated fixture paths changed" };
    return { valid, reason: valid ? "Combined policy satisfies the job brief" : "Expected maxAttempts=3, timeoutSeconds=60, retryDelaySeconds=1 and no other keys" };
  } catch { return { valid: false, reason: "Resolution must be valid JSON without conflict markers" }; }
}
export async function finishFixture(path: string, signal?: AbortSignal): Promise<string> {
  const validation = await validateResolution(path);
  if (!validation.valid) throw new Error(validation.reason);
  signal?.throwIfAborted();
  await git(path, ["add", policyFile], signal);
  await git(path, ["commit", "-m", "resolve retry policy conflict"], signal);
  if (await git(path, ["status", "--porcelain"], signal)) throw new Error("Fixture is not clean after merge");
  const parents = (await git(path, ["rev-list", "--parents", "-n", "1", "HEAD"], signal)).split(" ");
  if (parents.length !== 3) throw new Error("Resolution did not create a merge commit");
  return JSON.stringify({ policy: expected, mergeCommit: parents[0], clean: true });
}
export async function removeFixture(directory: string, path: string): Promise<void> {
  if (dirname(resolve(path)) !== resolve(directory, "fixtures") || !path.split("/").at(-1)?.startsWith("attempt-")) throw new Error("Refusing cleanup outside owned fixtures");
  await rm(path, { recursive: true, force: true });
}
