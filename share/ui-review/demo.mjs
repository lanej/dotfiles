import { createServer } from "node:http";
import { mkdtemp, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { html, rules, config } from "./test/fixtures.mjs";
import { runReview } from "./review.mjs";

// A repeatable calibration example, not a user-approved reference or real carrier data.
const project = await mkdtemp(path.join(tmpdir(), "ui-review-demo-"));
await mkdir(path.join(project, ".ui-review"));
await mkdir(path.join(project, "src"));
let broken = true;
const server = createServer((_req, res) => {
  res.setHeader("Content-Type", "text/html");
  res.end(html(broken));
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const cfg = config(`http://127.0.0.1:${server.address().port}`);
await writeFile(
  path.join(project, ".ui-review/config.json"),
  JSON.stringify({ ...cfg, enforceOnStop: false }, null, 2),
);
await writeFile(
  path.join(project, ".ui-review/rules.json"),
  JSON.stringify(rules, null, 2),
);
const globalDir = path.resolve(import.meta.dirname, "../../claude/ui-review");
try {
  await writeFile(path.join(project, "src/page.html"), html(true));
  const before = await runReview(project, globalDir);
  broken = false;
  await writeFile(path.join(project, "src/page.html"), html(false));
  const after = await runReview(project, globalDir);
  if (before.report.status !== "fail" || after.report.status !== "pass")
    throw new Error(
      `Demo expected fail → pass; got ${before.report.status} → ${after.report.status}. Inspect ${project}`,
    );
  const relative = (file) => path.relative(project, path.dirname(file));
  const output = `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>UI review calibration</title>
<style>body{font:16px/1.5 system-ui;color:#172d27;margin:24px}main{max-width:1440px;margin:auto}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,440px),1fr));gap:24px}img{width:100%;border:1px solid #ccd6d0}figure{margin:0}a{color:#165b41}</style>
<main><h1>UI review calibration</h1><p>Illustrative carrier data. The same content, before and after layout corrections. Neither image is a user-approved reference.</p><div class="grid">
<figure><h2>Broken · ${before.report.summary.errors} errors, ${before.report.summary.warnings} warnings</h2><p><a href="${relative(before.reportFile)}/index.html">Inspect findings</a></p><img alt="Broken carrier comparison" src="${relative(before.reportFile)}/capture-1.png"></figure>
<figure><h2>Corrected · ${after.report.summary.errors} errors, ${after.report.summary.warnings} warnings</h2><p><a href="${relative(after.reportFile)}/index.html">Inspect findings</a></p><img alt="Corrected carrier comparison" src="${relative(after.reportFile)}/capture-1.png"></figure></div></main></html>`;
  await writeFile(path.join(project, "index.html"), output);
  console.log(
    JSON.stringify({
      demo: path.join(project, "index.html"),
      before: before.reportFile,
      after: after.reportFile,
    }),
  );
} finally {
  await new Promise((resolve) => server.close(resolve));
}
