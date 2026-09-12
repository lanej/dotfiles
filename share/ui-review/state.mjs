import { createHash, randomUUID } from "node:crypto";
import {
  readFile,
  writeFile,
  appendFile,
  readdir,
  mkdir,
  rename,
  open,
  unlink,
  cp,
  realpath,
} from "node:fs/promises";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { readJSON, loadProject, validateRules } from "./config.mjs";
import { policyPath } from "./design.mjs";

export async function writeJSON(file, value) {
  await mkdir(path.dirname(file), { recursive: true });
  const temp = `${file}.${randomUUID()}.tmp`;
  await writeFile(temp, JSON.stringify(value, null, 2) + "\n", { mode: 0o600 });
  await rename(temp, file);
}
const excluded = new Set([
  ".git",
  "node_modules",
  ".ui-review",
  "dist",
  "build",
  ".next",
  "coverage",
  ".cache",
]);
async function walk(root, relative = "") {
  const files = [];
  for (const entry of await readdir(path.join(root, relative), {
    withFileTypes: true,
  })) {
    if (excluded.has(entry.name)) continue;
    const file = path.join(relative, entry.name);
    if (entry.isDirectory()) files.push(...(await walk(root, file)));
    else if (entry.isFile()) files.push(file);
  }
  return files;
}
export async function fingerprint(project, config, globalDir) {
  const hash = createHash("sha256");
  const listed = spawnSync(
    "git",
    [
      "-C",
      project,
      "ls-files",
      "-z",
      "--cached",
      "--others",
      "--exclude-standard",
    ],
    { encoding: "utf8", maxBuffer: 16 * 1024 * 1024 },
  );
  const files =
    listed.status === 0
      ? [...new Set(listed.stdout.split("\0").filter(Boolean))]
      : await walk(project);
  const inScope = (file) =>
    !file.split("/").some((p) => excluded.has(p)) &&
    config.sourcePaths.some(
      (p) =>
        p === "." || file === p || file.startsWith(p.replace(/\/$/, "") + "/"),
    );
  for (const file of files.filter(inScope).sort()) {
    hash.update(file + "\0");
    try {
      hash.update(await readFile(path.join(project, file)));
    } catch (err) {
      if (err.code !== "ENOENT") throw err;
      hash.update("deleted");
    }
  }
  for (const file of [
    path.join(project, ".ui-review/config.json"),
    path.join(project, ".ui-review/rules.json"),
    path.join(globalDir, "rules.json"),
    path.join(globalDir, "preferences.json"),
  ]) {
    hash.update(file + "\0");
    try {
      hash.update(await readFile(file));
    } catch (err) {
      if (err.code !== "ENOENT") throw err;
    }
  }
  // Changing the checker itself invalidates old passing runs after a dotfiles update.
  for (const file of [
    "config.mjs",
    "capture.mjs",
    "checks.mjs",
    "design.mjs",
    "review.mjs",
    "state.mjs",
    "package-lock.json",
  ])
    hash.update(await readFile(path.join(import.meta.dirname, file)));
  hash.update(await readFile(policyPath));
  return hash.digest("hex");
}
export async function feedbackEntries(dir) {
  try {
    return (await readFile(path.join(dir, "feedback.jsonl"), "utf8"))
      .split("\n")
      .filter(Boolean)
      .map((line) => JSON.parse(line));
  } catch (err) {
    if (err.code === "ENOENT") return [];
    throw err;
  }
}
export async function recordFeedback(
  project,
  globalDir,
  reportFile,
  decision,
  note,
  scope,
) {
  if (
    !["approve", "adjust"].includes(decision) ||
    !["project", "global"].includes(scope) ||
    !note?.trim()
  )
    throw new Error(
      "Feedback requires approve|adjust, project|global, and a nonempty note.",
    );
  const resolved = await realpath(reportFile);
  const runs = await realpath(path.join(project, ".ui-review/runs"));
  if (
    !resolved.startsWith(runs + path.sep) ||
    path.basename(resolved) !== "report.json"
  )
    throw new Error(
      "Use a report.json from this project’s .ui-review/runs directory.",
    );
  const report = await readJSON(resolved);
  if (
    report.project !== (await realpath(project)) ||
    report.version !== 1 ||
    !Array.isArray(report.pages)
  )
    throw new Error("Report does not belong to this project.");
  const entry = {
    id: randomUUID(),
    createdAt: new Date().toISOString(),
    decision,
    note: note.trim(),
    scope,
    reportId: report.id,
    fingerprint: report.fingerprint,
  };
  if (decision === "approve") {
    entry.reference = `approved/${entry.id}`;
    await cp(
      path.dirname(resolved),
      path.join(project, ".ui-review", entry.reference),
      { recursive: true, errorOnExist: true, force: false },
    );
  }
  await appendFile(
    path.join(project, ".ui-review/feedback.jsonl"),
    JSON.stringify(entry) + "\n",
    { mode: 0o600 },
  );
  if (scope === "global") {
    await mkdir(globalDir, { recursive: true });
    // Global preferences retain words and provenance, never project URLs or screenshots.
    const { reference, ...globalEntry } = entry;
    await appendFile(
      path.join(globalDir, "feedback.jsonl"),
      JSON.stringify(globalEntry) + "\n",
      { mode: 0o600 },
    );
  }
  return entry;
}
export async function learnRule(project, globalDir, feedbackId, rule, scope) {
  if (!["project", "global"].includes(scope))
    throw new Error("Scope must be project or global.");
  const dir = scope === "global" ? globalDir : path.join(project, ".ui-review");
  const feedback = (await feedbackEntries(dir)).find(
    (e) => e.id === feedbackId,
  );
  if (!feedback)
    throw new Error(
      "Unknown feedback ID in the requested scope. Record feedback first.",
    );
  const learned = { ...rule, feedbackId };
  validateRules([learned]);
  const file = path.join(dir, "rules.json");
  const lock = await open(file + ".lock", "wx").catch((err) => {
    throw new Error(
      `Cannot lock rules for editing (${err.code}); another writer may be active.`,
    );
  });
  try {
    const existing = validateRules(await readJSON(file, []));
    const next = [...existing.filter((r) => r.id !== learned.id), learned];
    await writeJSON(file, next);
  } finally {
    await lock.close();
    await unlink(file + ".lock");
  }
  return learned;
}
export async function hookDecision(payload, globalDir) {
  if (!payload.cwd || payload.stop_hook_active) return {};
  const project = await realpath(payload.cwd);
  const raw = await readJSON(
    path.join(project, ".ui-review/config.json"),
    null,
  );
  if (!raw || raw.enforceOnStop === false) return {};
  try {
    const { config } = await loadProject(project, globalDir);
    const latest = await readJSON(
      path.join(project, ".ui-review/latest.json"),
      null,
    );
    if (
      latest?.status === "pass" &&
      latest.fingerprint === (await fingerprint(project, config, globalDir))
    )
      return {};
    return {
      decision: "block",
      reason:
        "UI review is missing, failing, or stale. Run ui-review check, then inspect the cited design rules and full-resolution details. Repair the app and rerun; do not weaken checks or edit evidence to pass. " +
        (latest?.reportFile ? `Last report: ${latest.reportFile}. ` : "") +
        (latest?.blockingFindings?.join("\n") ?? ""),
    };
  } catch (err) {
    return {
      decision: "block",
      reason: `UI review configuration or verification failed: ${err.message}`,
    };
  }
}
