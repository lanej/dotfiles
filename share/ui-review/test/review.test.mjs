import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { createServer } from "node:http";
import { spawnSync } from "node:child_process";
import {
  validateConfig,
  validateRules,
  mergeRules,
  loadProject,
} from "../config.mjs";
import {
  fingerprint,
  recordFeedback,
  learnRule,
  hookDecision,
} from "../state.mjs";
import { runReview } from "../review.mjs";
import { chromium } from "playwright";
import { inspectPage } from "../checks.mjs";
import { renderReport } from "../report.mjs";

import { config, rules, html } from "./fixtures.mjs";

async function fixture(t) {
  const project = await mkdtemp(path.join(tmpdir(), "ui-review-"));
  t.after(() => rm(project, { recursive: true, force: true }));
  await mkdir(path.join(project, ".ui-review"));
  await mkdir(path.join(project, "src"));
  await writeFile(path.join(project, "src/page.html"), html(false));
  await writeFile(
    path.join(project, ".ui-review/rules.json"),
    JSON.stringify(rules),
  );
  const globalDir = path.join(project, "global");
  await mkdir(globalDir);
  await writeFile(path.join(globalDir, "rules.json"), "[]");
  await writeFile(path.join(globalDir, "preferences.json"), "[]");
  return { project, globalDir };
}

test("configuration rejects typos, invalid scopes, missing thresholds and duplicate IDs", () => {
  assert.throws(() =>
    validateConfig({ ...config("http://localhost:3000"), enforceOnStpo: true }),
  );
  assert.throws(() =>
    validateConfig({ ...config("http://localhost:3000"), pages: [] }),
  );
  assert.throws(() => validateRules([{ ...rules[0], min: -1 }]));
  assert.throws(() => validateRules([{ ...rules[0], type: "magic-density" }]));
  assert.throws(() => validateRules([{ ...rules[0], minimun: 5 }]));
  assert.throws(() => validateRules([rules[0], rules[0]]));
  assert.deepEqual(mergeRules([rules[0]], [{ ...rules[0], min: 6 }]), [
    { ...rules[0], min: 6 },
  ]);
});

test("freshness changes on source and rule changes, not generated reports", async (t) => {
  const { project, globalDir } = await fixture(t);
  const cfg = config("http://localhost:3000");
  await writeFile(
    path.join(project, ".ui-review/config.json"),
    JSON.stringify(cfg),
  );
  const first = await fingerprint(project, cfg, globalDir);
  await mkdir(path.join(project, ".ui-review/runs"));
  await writeFile(path.join(project, ".ui-review/runs/report.json"), "{}");
  assert.equal(await fingerprint(project, cfg, globalDir), first);
  await writeFile(path.join(project, "src/page.html"), html(true));
  assert.notEqual(await fingerprint(project, cfg, globalDir), first);
  await writeFile(path.join(project, "src/page.html"), html(false));
  await writeFile(
    path.join(globalDir, "rules.json"),
    JSON.stringify([rules[0]]),
  );
  assert.notEqual(await fingerprint(project, cfg, globalDir), first);
});

test("render, feedback, rule learning, and Stop enforcement work end to end", async (t) => {
  const { project, globalDir } = await fixture(t);
  let broken = true;
  const server = createServer((_req, res) => {
    res.setHeader("Content-Type", "text/html");
    res.end(html(broken));
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(() => new Promise((resolve) => server.close(resolve)));
  const cfg = config(`http://127.0.0.1:${server.address().port}`);
  await writeFile(
    path.join(project, ".ui-review/config.json"),
    JSON.stringify(cfg),
  );
  assert.equal(
    (await hookDecision({ cwd: project }, globalDir)).decision,
    "block",
  );
  const bad = await runReview(project, globalDir);
  const ids = new Set(bad.report.pages[0].findings.map((x) => x.rule));
  for (const id of [
    "page-overflow",
    "rows",
    "header",
    "edges",
    "context",
    "clip",
    "space",
  ])
    assert.ok(ids.has(id), id + ": " + JSON.stringify(bad.report.pages));
  assert.equal(bad.report.status, "fail");
  const note = await recordFeedback(
    project,
    globalDir,
    bad.reportFile,
    "adjust",
    "Keep eight carrier rows visible.",
    "project",
  );
  const learned = { ...rules[0], min: 8 };
  await learnRule(project, globalDir, note.id, learned, "project");
  const saved = JSON.parse(
    await readFile(path.join(project, ".ui-review/rules.json")),
  );
  assert.equal(saved.find((x) => x.id === "rows").feedbackId, note.id);
  assert.equal(
    (await hookDecision({ cwd: project }, globalDir)).decision,
    "block",
  );
  broken = false;
  await writeFile(path.join(project, "src/page.html"), html(false));
  const good = await runReview(project, globalDir);
  assert.equal(good.report.status, "pass", JSON.stringify(good.report.pages));
  assert.deepEqual(await hookDecision({ cwd: project }, globalDir), {});
  const approval = await recordFeedback(
    project,
    globalDir,
    good.reportFile,
    "approve",
    "This comparison layout works.",
    "project",
  );
  assert.ok(approval.reference);
  const reference = JSON.parse(
    await readFile(
      path.join(project, ".ui-review/approved", approval.id, "report.json"),
    ),
  );
  assert.equal(reference.status, "pass");
  await writeFile(path.join(project, "src/page.html"), html(true));
  assert.equal(
    (await hookDecision({ cwd: project }, globalDir)).decision,
    "block",
  );
  assert.deepEqual(
    await hookDecision({ cwd: project, stop_hook_active: true }, globalDir),
    {},
  );
  await assert.rejects(
    recordFeedback(
      project,
      globalDir,
      good.reportFile,
      "approve",
      "",
      "project",
    ),
  );
  await assert.rejects(
    learnRule(project, globalDir, "nonexistent", learned, "project"),
  );
  const current = await runReview(project, globalDir);
  const output = await readFile(
    path.join(path.dirname(current.reportFile), "index.html"),
    "utf8",
  );
  assert.match(output, /Approved reference/);
});

test("CLI rejects unknown options and emits an actionable setup error", () => {
  const cli = path.resolve(import.meta.dirname, "../cli.mjs");
  const result = spawnSync(process.execPath, [cli, "check", "--typo"], {
    encoding: "utf8",
  });
  assert.equal(result.status, 2);
  assert.match(result.stderr, /Unknown option/);
});

test("scoped DOM checks distinguish intentional scroll, hidden variants, and missing evidence", async (t) => {
  const browser = await chromium.launch({
    executablePath: process.env.UI_REVIEW_BROWSER_PATH || undefined,
  });
  t.after(() => browser.close());
  const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
  await page.setContent(
    '<div class="scroll" style="width:100px;overflow:auto"><div style="width:300px">Long content</div></div><p class="number" style="font-size:18px">42</p><p class="hidden" style="display:none">Hidden</p>',
  );
  const result = await page.evaluate(inspectPage, [
    {
      id: "scroll",
      type: "no-clip",
      selector: ".scroll",
      severity: "error",
      reason: "Allow local scrolling.",
    },
    {
      id: "missing",
      type: "context",
      selector: ".missing",
      required: [".period"],
      severity: "error",
      reason: "Require evidence.",
    },
    {
      id: "optional",
      type: "context",
      selector: ".missing",
      required: [".period"],
      optional: true,
      severity: "error",
      reason: "Optional component.",
    },
    {
      id: "font",
      type: "style",
      selector: ".number",
      property: "font-size",
      allowed: ["14px"],
      severity: "error",
      reason: "Type scale.",
    },
    {
      id: "hidden",
      type: "visible-count",
      selector: ".hidden",
      min: 1,
      severity: "error",
      reason: "Must be visible.",
    },
  ]);
  assert.deepEqual(
    result.findings.map((x) => x.rule),
    ["missing", "font", "hidden"],
  );
});

test("HTTP errors and missing ready selectors fail capture instead of yielding a green report", async (t) => {
  const { project, globalDir } = await fixture(t);
  const server = createServer((req, res) => {
    res.statusCode = req.url === "/missing" ? 404 : 200;
    res.end("<main>Loading</main>");
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(() => new Promise((resolve) => server.close(resolve)));
  const cfg = {
    ...config(`http://127.0.0.1:${server.address().port}`),
    timeoutMs: 1000,
    pages: [
      { name: "missing", path: "/missing", ready: "main" },
      { name: "loading", path: "/", ready: "table" },
    ],
  };
  await writeFile(
    path.join(project, ".ui-review/config.json"),
    JSON.stringify(cfg),
  );
  const result = await runReview(project, globalDir);
  assert.equal(result.report.status, "fail");
  assert.equal(result.report.summary.errors, 2);
  assert.match(result.report.pages[0].findings[0].message, /404/);
  assert.match(result.report.pages[1].findings[0].message, /Timeout/);
});

test("global feedback is reusable without copying project screenshots and approval never clears failure", async (t) => {
  const { project, globalDir } = await fixture(t);
  const dir = path.join(project, ".ui-review/runs/fixture");
  await mkdir(dir, { recursive: true });
  const report = {
    version: 1,
    id: "fixture",
    project: await import("node:fs/promises").then((fs) =>
      fs.realpath(project),
    ),
    fingerprint: "abc",
    status: "fail",
    pages: [],
  };
  await writeFile(path.join(dir, "report.json"), JSON.stringify(report));
  const entry = await recordFeedback(
    project,
    globalDir,
    path.join(dir, "report.json"),
    "approve",
    "Prefer compact comparison tables.",
    "global",
  );
  const globalEntry = JSON.parse(
    (await readFile(path.join(globalDir, "feedback.jsonl"), "utf8")).trim(),
  );
  assert.equal(globalEntry.reference, undefined);
  assert.equal(globalEntry.note, entry.note);
  await learnRule(project, globalDir, entry.id, rules[1], "global");
  assert.equal(
    JSON.parse(await readFile(path.join(globalDir, "rules.json")))[0]
      .feedbackId,
    entry.id,
  );
  assert.equal(
    JSON.parse(
      await readFile(
        path.join(project, ".ui-review/approved", entry.id, "report.json"),
      ),
    ).status,
    "fail",
  );
});

test("report escapes page content and feedback rather than executing it", () => {
  const output = renderReport(
    {
      id: "test",
      status: "pass",
      summary: { errors: 0, warnings: 0 },
      pages: [],
      createdAt: "today",
    },
    ["<script>alert(1)</script>"],
  );
  assert.ok(!output.includes("<script>"));
  assert.match(output, /&lt;script&gt;/);
});

test("symlink launcher and hook preserve unrelated projects and reject malformed opted-in configuration", async (t) => {
  const { project } = await fixture(t);
  const launcher = path.resolve(import.meta.dirname, "../../../bin/ui-review");
  const { symlink } = await import("node:fs/promises");
  const link = path.join(project, "ui-review");
  await symlink(launcher, link);
  assert.equal(spawnSync(link, ["--help"], { encoding: "utf8" }).status, 0);
  const run = () =>
    spawnSync(link, ["hook"], {
      input: JSON.stringify({ cwd: project }),
      encoding: "utf8",
    });
  assert.equal(run().stdout, "");
  await writeFile(path.join(project, ".ui-review/config.json"), "broken JSON");
  assert.equal(JSON.parse(run().stdout).decision, "block");
  await writeFile(
    path.join(project, ".ui-review/config.json"),
    JSON.stringify({
      ...config("http://localhost:3000"),
      enforceOnStop: false,
    }),
  );
  assert.equal(run().stdout, "");
});

test("global page scopes can target other projects while local scope typos fail", async (t) => {
  const { project, globalDir } = await fixture(t);
  await writeFile(
    path.join(project, ".ui-review/config.json"),
    JSON.stringify(config("http://localhost:3000")),
  );
  await writeFile(
    path.join(globalDir, "rules.json"),
    JSON.stringify([
      { ...rules[1], id: "global-header", pages: ["other-page"] },
    ]),
  );
  assert.ok(await loadProject(project, globalDir));
  await writeFile(
    path.join(project, ".ui-review/rules.json"),
    JSON.stringify([{ ...rules[1], pages: ["typo"] }]),
  );
  await assert.rejects(loadProject(project, globalDir), /unknown page typo/);
});

test("density measures selected regions without double-counting and detects sparse large-screen layouts", async (t) => {
  const browser = await chromium.launch({
    executablePath: process.env.UI_REVIEW_BROWSER_PATH || undefined,
  });
  t.after(() => browser.close());
  const page = await browser.newPage({
    viewport: { width: 1000, height: 800 },
  });
  await page.setContent(
    '<style>body{margin:0}main{width:100vw;height:100vh}.content{width:1000px;height:600px}.nested{width:1000px;height:600px}</style><main><div class="content"><div class="nested">Data</div></div></main>',
  );
  const rule = {
    id: "density",
    type: "region-density",
    region: "main",
    selector: ".content,.nested",
    measure: "boxes",
    minCoverage: 0.6,
    maxVerticalGap: 250,
    severity: "error",
    reason: "Use the comparison workspace.",
  };
  const normal = await page.evaluate(inspectPage, [rule]);
  assert.equal(normal.metrics.density[0].coverage, 0.75);
  assert.equal(normal.findings.length, 0);
  await page.setViewportSize({ width: 2560, height: 1440 });
  const large = await page.evaluate(inspectPage, [rule]);
  assert.ok(large.metrics.density[0].coverage < 0.2);
  assert.equal(large.metrics.density[0].largestVerticalGap, 840);
  assert.equal(large.findings.filter((f) => f.rule === "density").length, 2);
  await page.addStyleTag({
    content: ".content,.nested{width:100vw;height:calc(100vh - 100px)}",
  });
  const fixed = await page.evaluate(inspectPage, [rule]);
  assert.equal(fixed.findings.length, 0);
  const text = await page.evaluate(inspectPage, [{ ...rule, measure: "text" }]);
  assert.ok(
    text.metrics.density[0].coverage < 0.01,
    "inflating containers must not inflate text coverage",
  );
});

test("detail captures retain 1:1 pixels and cover the far edge of a 4K page", async (t) => {
  const { captureDetails, tilePlan } = await import("../capture.mjs");
  const { project } = await fixture(t);
  const browser = await chromium.launch({
    executablePath: process.env.UI_REVIEW_BROWSER_PATH || undefined,
  });
  t.after(() => browser.close());
  const page = await browser.newPage({
    viewport: { width: 3840, height: 2160 },
    deviceScaleFactor: 1,
  });
  await page.setContent(
    "<style>body{margin:0;background:white}p{position:absolute;right:0;bottom:0;margin:0;background:rgb(255,0,0);width:100px;height:50px}</style><p>Far edge</p>",
  );
  const details = await captureDetails(page, project, "large");
  assert.equal(details.complete, true);
  assert.equal(details.scale, 1);
  assert.ok(details.tiles.length > 1);
  const final = details.tiles.at(-1);
  assert.equal(final.x + final.width, 3840);
  assert.equal(final.y + final.height, 2160);
  const png = await readFile(path.join(project, final.file));
  assert.equal(png.readUInt32BE(16), final.width);
  assert.equal(png.readUInt32BE(20), final.height);
  const corner = await page.evaluate(async (data) => {
    const image = new Image();
    image.src = "data:image/png;base64," + data;
    await image.decode();
    const canvas = document.createElement("canvas");
    canvas.width = image.width;
    canvas.height = image.height;
    const context = canvas.getContext("2d");
    context.drawImage(image, 0, 0);
    return [
      ...context.getImageData(image.width - 2, image.height - 2, 1, 1).data,
    ];
  }, png.toString("base64"));
  assert.deepEqual(
    corner,
    [255, 0, 0, 255],
    "the final tile must contain the actual bottom-right marker",
  );
  const points = tilePlan(3840, 2160);
  for (let y = 0; y < 2160; y += 16)
    for (let x = 0; x < 3840; x += 16)
      assert.ok(
        points.some(
          (p) =>
            x >= p.x && x < p.x + p.width && y >= p.y && y < p.y + p.height,
        ),
      );
  const capped = await captureDetails(page, project, "limited", {
    width: 1000,
    height: 800,
    overlap: 64,
    maxTiles: 1,
  });
  assert.equal(capped.complete, false);
  assert.equal(capped.capturedTiles, 1);
  assert.ok(capped.expectedTiles > 1);
});

test("incomplete detail evidence fails the review gate", async (t) => {
  const { project, globalDir } = await fixture(t);
  const server = createServer((_req, res) => {
    res.setHeader("Content-Type", "text/html");
    res.end(html(false));
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(() => new Promise((resolve) => server.close(resolve)));
  const cfg = {
    ...config(`http://127.0.0.1:${server.address().port}`),
    detailCapture: { width: 1000, height: 800, overlap: 64, maxTiles: 1 },
  };
  await writeFile(
    path.join(project, ".ui-review/config.json"),
    JSON.stringify(cfg),
  );
  const result = await runReview(project, globalDir);
  assert.equal(result.report.status, "fail");
  assert.ok(
    result.report.pages[0].findings.some((f) => f.rule === "detail-coverage"),
  );
  assert.equal(
    (await hookDecision({ cwd: project }, globalDir)).decision,
    "block",
  );
});

test("viewport density includes whitespace outside content wrappers", async (t) => {
  const browser = await chromium.launch({
    executablePath: process.env.UI_REVIEW_BROWSER_PATH || undefined,
  });
  t.after(() => browser.close());
  const page = await browser.newPage({
    viewport: { width: 2000, height: 1000 },
  });
  await page.setContent(
    '<style>body{margin:0}main,.content{width:1000px;height:500px}</style><main><div class="content">Data</div></main>',
  );
  const rule = {
    id: "use",
    type: "region-density",
    region: "viewport",
    selector: ".content",
    measure: "boxes",
    minCoverage: 0.5,
    maxVerticalGap: 1000,
    severity: "error",
    reason: "Use the screen.",
  };
  const report = await page.evaluate(inspectPage, [rule]);
  assert.equal(report.metrics.density[0].coverage, 0.25);
  assert.equal(report.findings.length, 1);
  const wrapper = await page.evaluate(inspectPage, [
    { ...rule, region: "main" },
  ]);
  assert.equal(wrapper.metrics.density[0].coverage, 1);
});
