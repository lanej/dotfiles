import { execFileSync } from "node:child_process";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { repositoryPolicy } from "../server/maintenance-policy";
import type { PullRequest } from "../server/pr-watch";

export function maintenanceFixture(mode: "clean" | "recorded" | "structural" = "clean") {
  const recorded = mode === "recorded", structural = mode === "structural";
  const root = mkdtempSync(join(tmpdir(), "pr-maintenance-"));
  const remote = join(root, "remote.git"), repository = join(root, "repository");
  mkdirSync(repository);
  const git = (...args: string[]) => execFileSync("git", args, { cwd: repository, encoding: "utf8",
    env: { ...process.env, GIT_TERMINAL_PROMPT: "0" }, stdio: ["ignore", "pipe", "pipe"] }).trim();
  git("init", "--bare", remote);
  git("init", "-b", "main");
  git("config", "user.email", "fixture@example.test");
  git("config", "user.name", "Maintenance fixture");
  git("config", "commit.gpgsign", "false");
  git("config", "rerere.enabled", "true");
  const file = structural ? "value.json" : "value.txt";
  writeFileSync(join(repository, file), structural ? '{"base":true}\n' : "base\n");
  git("add", "."); git("commit", "-m", "Initial");
  git("checkout", "-b", "feature");
  writeFileSync(join(repository, file), structural ? '{"base":true,"feature":true}\n' : "feature\n");
  git("commit", "-am", "Feature");
  const head = git("rev-parse", "HEAD");
  git("checkout", "main");
  writeFileSync(join(repository, structural || recorded ? file : "other.txt"),
    structural ? '{"base":true,"upstream":true}\n' : recorded ? "upstream\n" : "upstream file\n");
  git("add", "."); git("commit", "-m", "Upstream");
  const base = git("rev-parse", "HEAD");
  git("checkout", "feature");
  if (recorded) {
    try { git("merge", "--no-commit", "main"); } catch {}
    writeFileSync(join(repository, "value.txt"), "resolved\n");
    git("rerere");
    git("merge", "--abort");
  }
  git("remote", "add", "origin", "https://github.com/o/r.git");
  git("config", "url." + remote + ".insteadOf", "https://github.com/o/r.git");
  git("push", "origin", "main", "feature");
  writeFileSync(join(repository, "unrelated.txt"), "preserve this local work\n");
  const policy = repositoryPolicy.parse({
    directory: repository, github: "o/r", minimumConfidence: 0.95,
    confidence: { git: 1, rerere: 0.98, mergiraf: structural ? 0.97 : null },
    checks: [[process.execPath, "-e", structural ?
      "const o=JSON.parse(require('node:fs').readFileSync('value.json','utf8'));if(!o.base||!o.feature||!o.upstream)process.exit(1)" :
      "const fs=require('node:fs');if(fs.readFileSync('value.txt','utf8')!==" +
      JSON.stringify(recorded ? "resolved\n" : "feature\n") + ")process.exit(1)"]],
  });
  const pr: PullRequest = { head, base, state: "open", merged: false, draft: false, mergeable: false, mergeableState: "dirty",
    headRef: "feature", baseRef: "main", headRepository: "o/r", baseRepository: "o/r", checks: [], statuses: [] };
  return { root, remote, repository, git, policy, pr,
    cleanup: () => rmSync(root, { recursive: true, force: true }) };
}
