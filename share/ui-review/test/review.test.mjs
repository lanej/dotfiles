import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { createServer } from "node:http";
import { execFile } from "node:child_process";
import { config, rules, reviewHtml } from "./fixtures.mjs";

// One user workflow through the installed entrypoint; no helper/edge-case matrix.
test("UI review cites design violations, learns feedback, and accepts a repaired responsive comparison", { timeout: 60000 }, async (t) => {
  const project = await mkdtemp(path.join(tmpdir(), "ui-review-"));
  t.after(() => rm(project, { recursive: true, force: true }));
  const globalDir = path.join(project, "global");
  await mkdir(globalDir);
  await mkdir(path.join(project, "src"));
  await mkdir(path.join(project, ".ui-review"));
  const source = path.join(project, "src/page.html");
  await writeFile(source, reviewHtml(true));
  const server = createServer(async (_req, res) => {
    res.setHeader("Content-Type", "text/html");
    res.end(await readFile(source));
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(() => new Promise((resolve) => server.close(resolve)));
  const cfg = {
    ...config(`http://127.0.0.1:${server.address().port}`),
    viewports: [{ name: "desktop", width: 1280, height: 800 }, { name: "4k", width: 3840, height: 2160 }],
    requiredDesignRules: ["DR-001", "DR-003", "DR-006", "DR-007"],
  };
  const density = {
    id: "density", type: "region-density", region: "viewport",
    selector: "tbody", measure: "boxes", minCoverage: 0.1, maxVerticalGap: 1600,
    severity: "error", reason: "Use the comparison workspace.",
  };
  await writeFile(path.join(project, ".ui-review/config.json"), JSON.stringify(cfg));
  await writeFile(path.join(project, ".ui-review/rules.json"), JSON.stringify([...rules, density, {
    id: "comparison", type: "comparison-set", selector: "tbody tr",
    keyAttribute: "data-comparison", requiredKeys: ["carrier-1", "carrier-2"],
    minVisibleByViewport: { desktop: 8, "4k": 12 }, preserveFrom: "desktop", minFontSize: 14,
    severity: "error", reason: "Keep alternatives visible and use the larger screen for additional carriers.",
  }, {
    id: "period", type: "consistent", selector: "table", keyAttribute: "data-measure",
    properties: [], attributes: ["data-period"], designRules: ["DR-001"],
    severity: "error", reason: "Resizing must preserve the reporting period.",
  }]));
  const launcher = path.resolve(import.meta.dirname, "../../../bin/ui-review");
  const cli = (args, input = "") => new Promise((resolve, reject) => {
    const child = execFile(launcher, args, {
      cwd: project,
      env: { ...process.env, UI_REVIEW_GLOBAL_DIR: globalDir },
      timeout: 30000,
    }, (error, stdout, stderr) => {
      if (error && typeof error.code !== "number") return reject(error);
      resolve({ code: error?.code ?? 0, stdout, stderr });
    });
    child.stdin.end(input);
  });
  const hook = async () => JSON.parse((await cli(["hook"], JSON.stringify({ cwd: project }))).stdout);

  const bad = await cli(["check"]);
  assert.equal(bad.code, 1, bad.stderr);
  const badOutput = JSON.parse(bad.stdout);
  const badReport = JSON.parse(await readFile(badOutput.report));
  const wide = badReport.pages.find((page) => page.viewport.name === "4k");
  assert.ok(wide.findings.some((finding) => finding.designRules.includes("DR-001")));
  assert.ok(wide.findings.some((finding) => finding.message.includes("lost previously visible") && finding.actual.includes("carrier-8")));
  const blocked = await hook();
  assert.equal(blocked.decision, "block");
  assert.match(blocked.reason, /DR-007/);

  const note = await cli(["feedback", "--report", badOutput.report,
    "--decision", "adjust", "--note", "Give the comparison more of the viewport."]);
  assert.equal(note.code, 0, note.stderr);
  const ruleFile = path.join(project, "density-rule.json");
  await writeFile(ruleFile, JSON.stringify({ ...density, minCoverage: 0.12 }));
  const learned = await cli(["learn", "--feedback", JSON.parse(note.stdout).id, "--rule", ruleFile]);
  assert.equal(learned.code, 0, learned.stderr);
  const savedRules = JSON.parse(await readFile(path.join(project, ".ui-review/rules.json")));
  assert.equal(savedRules.find((rule) => rule.id === "density").feedbackId, JSON.parse(note.stdout).id);

  await writeFile(source, reviewHtml(false));
  const good = await cli(["check"]);
  assert.equal(good.code, 0, good.stderr || good.stdout);
  assert.deepEqual(await hook(), {});
  const output = JSON.parse(good.stdout);
  const report = JSON.parse(await readFile(output.report));
  const details = report.pages.find((page) => page.viewport.name === "4k").details;
  assert.equal(details.complete, true);
  const last = details.tiles.at(-1);
  assert.deepEqual([last.x + last.width, last.y + last.height], [3840, 2160]);
  const png = await readFile(path.join(path.dirname(output.report), last.file));
  assert.deepEqual([png.readUInt32BE(16), png.readUInt32BE(20)], [1024, 800]);
  assert.match(await readFile(output.html, "utf8"), /capture-1-detail-/);
  assert.equal(report.pages[0].designCoverage.find((rule) => rule.id === "DR-002").status, "unassessed");
  assert.match(await readFile(path.join(path.dirname(output.report), "design-rules.html"), "utf8"), /id="DR-007"/);

  await writeFile(source, reviewHtml(true));
  assert.equal((await hook()).decision, "block", "Source changes invalidate the passing review");
});
