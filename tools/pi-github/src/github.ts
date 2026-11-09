import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { cleanText, parseTask } from "./domain.js";
const exec = promisify(execFile);
export async function readPullRequest(url: string, signal?: AbortSignal): Promise<unknown> {
  const task = parseTask({ kind: "summarize_pr", url });
  if (task.kind !== "summarize_pr") throw new Error("Expected PR task");
  const parts = new URL(task.url).pathname.split("/");
  let stdout: string;
  try { ({ stdout } = await exec("gh", ["api", "--hostname", "github.com", "--method", "GET", `repos/${parts[1]}/${parts[2]}/pulls/${parts[4]}`], { signal, timeout: 30000, maxBuffer: 1024 * 1024 })); }
  catch (error) {
    const stderr = String((error as { stderr?: string }).stderr ?? "");
    if (/401|403|auth|login|token/i.test(stderr)) throw new Error("GitHub authentication required: run gh auth login -h github.com");
    if (/429|rate.limit/i.test(stderr)) throw new Error("GitHub rate limit (429)");
    if (/50[0-4]/.test(stderr)) throw new Error("GitHub temporarily unavailable (503)");
    throw new Error(signal?.aborted ? "Operation aborted" : "GitHub PR read failed; check repository access and connectivity");
  }
  return publicPullRequest(JSON.parse(stdout));
}
export function publicPullRequest(pr: Record<string, any>): unknown {
  if (pr.base?.repo?.private !== false) throw new Error("Only confirmed public repository PRs may be sent to the model");
  return { url: pr.html_url, title: cleanText(String(pr.title), 2000), body: cleanText(String(pr.body ?? ""), 16000), bodyTruncated: String(pr.body ?? "").length > 16000, state: pr.state, merged: pr.merged, headSha: pr.head?.sha, base: pr.base?.ref };
}
