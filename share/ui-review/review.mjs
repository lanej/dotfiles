import { chromium } from "playwright";
import AxeBuilder from "@axe-core/playwright";
import { mkdir, writeFile, realpath, copyFile } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import path from "node:path";
import { loadProject, readJSON } from "./config.mjs";
import { fingerprint, writeJSON, feedbackEntries } from "./state.mjs";
import { inspectPage } from "./checks.mjs";
import { renderReport, renderDesignPolicy } from "./report.mjs";
import { captureDetails } from "./capture.mjs";
import { readDesignPolicy, evaluateDesign } from "./design.mjs";

export async function runReview(project, globalDir) {
  project = await realpath(project);
  const { config, rules } = await loadProject(project, globalDir);
  const before = await fingerprint(project, config, globalDir);
  const id =
    new Date().toISOString().replace(/[:.]/g, "-") +
    "-" +
    randomUUID().slice(0, 8);
  const dir = path.join(project, ".ui-review/runs", id);
  await mkdir(dir, { recursive: true, mode: 0o700 });
  await writeJSON(path.join(project, ".ui-review/latest.json"), {
    status: "running",
    fingerprint: before,
  });
  const report = {
    version: 1,
    id,
    project,
    createdAt: new Date().toISOString(),
    fingerprint: before,
    status: "fail",
    summary: { errors: 0, warnings: 0 },
    pages: [],
    designPolicy: await readDesignPolicy(),
  };
  let browser;
  try {
    browser = await chromium.launch({
      executablePath: process.env.UI_REVIEW_BROWSER_PATH || undefined,
    });
    for (const pageConfig of config.pages)
      for (const viewport of config.viewports) {
        const url = new URL(pageConfig.path, config.baseURL).href;
        const result = {
          name: pageConfig.name,
          url,
          viewport,
          findings: [],
          screenshot: null,
        };
        report.pages.push(result);
        let context;
        try {
          context = await browser.newContext({
            viewport: { width: viewport.width, height: viewport.height },
            deviceScaleFactor: 1,
            reducedMotion: "reduce",
            colorScheme: "light",
            storageState: config.storageState
              ? path.resolve(project, config.storageState)
              : undefined,
          });
          const page = await context.newPage();
          page.setDefaultTimeout(config.timeoutMs ?? 15000);
          const response = await page.goto(url, { waitUntil: "load" });
          if (response && !response.ok())
            throw new Error(`HTTP ${response.status()}`);
          if (new URL(page.url()).origin !== new URL(url).origin)
            throw new Error(
              "Navigation left the configured origin; check authentication.",
            );
          await page
            .locator(pageConfig.ready)
            .first()
            .waitFor({ state: "visible" });
          await page.evaluate(() => document.fonts.ready);
          await page.addStyleTag({
            content:
              "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}",
          });
          await page.evaluate(() => window.scrollTo(0, 0));
          result.screenshot = `capture-${report.pages.length}.png`;
          await page.screenshot({
            path: path.join(dir, result.screenshot),
            fullPage: true,
            animations: "disabled",
          });
          result.details = await captureDetails(
            page,
            dir,
            `capture-${report.pages.length}`,
            config.detailCapture,
          );
          if (!result.details.complete)
            result.findings.push({
              rule: "detail-coverage",
              severity: "error",
              message: `Captured ${result.details.capturedTiles} of ${result.details.expectedTiles} detail tiles.`,
              reason:
                "Full-scale visual evidence is incomplete. Narrow the page state or increase detailCapture.maxTiles.",
            });
          const active = rules.filter(
            (r) =>
              (!r.pages || r.pages.includes(pageConfig.name)) &&
              (!r.viewports || r.viewports.includes(viewport.name)),
          );
          const inspection = await page.evaluate(inspectPage, active);
          result.findings.push(...inspection.findings);
          result.metrics = inspection.metrics;
          result.coverage = {
            layoutRules: active.map((r) => r.id),
            accessibility: config.accessibility,
          };
          if (config.accessibility) {
            const axe = await new AxeBuilder({ page })
              .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
              .analyze();
            for (const violation of axe.violations)
              for (const node of violation.nodes)
                result.findings.push({
                  rule: `axe:${violation.id}`,
                  severity: "error",
                  selector: node.target.join(" "),
                  message: violation.help,
                  reason: node.failureSummary,
                  actual: violation.impact,
                  expected: "no automatically detectable violation",
                });
            result.accessibilityNeedsReview = axe.incomplete.map((v) => ({
              id: v.id,
              help: v.help,
              targets: v.nodes.map((n) => n.target),
            }));
          }
        } catch (err) {
          result.findings.push({
            rule: "review-error",
            severity: "error",
            selector: pageConfig.ready,
            message: err.message,
            reason:
              "The page must render and be inspectable before a review can pass.",
          });
        } finally {
          await context?.close();
        }
      }
  } catch (err) {
    report.pages.push({
      name: "Browser setup",
      url: config.baseURL,
      viewport: config.viewports[0],
      findings: [
        {
          rule: "browser-error",
          severity: "error",
          message: err.message,
          reason: "Install Chromium with make ui-review.",
        },
      ],
    });
  } finally {
    await browser?.close();
  }
  const after = await fingerprint(project, config, globalDir);
  if (before !== after)
    report.pages[0].findings.push({
      rule: "source-changed",
      severity: "error",
      message: "Source or rules changed during capture. Rerun the review.",
    });
  evaluateDesign(report, rules, config);
  for (const page of report.pages)
    for (const f of page.findings)
      report.summary[f.severity === "error" ? "errors" : "warnings"]++;
  report.status = report.summary.errors ? "fail" : "pass";
  const feedback = await feedbackEntries(path.join(project, ".ui-review"));
  const approved = feedback.findLast(
    (e) => e.decision === "approve" && e.reference,
  );
  let reference;
  if (approved) {
    const refDir = path.join(project, ".ui-review", approved.reference);
    const refReport = await readJSON(path.join(refDir, "report.json"));
    reference = { report: refReport, note: approved.note };
    await mkdir(path.join(dir, "reference"));
    for (const p of refReport.pages)
      if (p.screenshot) {
        if (!/^capture-\d+\.png$/.test(p.screenshot))
          throw new Error("Invalid reference screenshot path");
        await copyFile(
          path.join(refDir, p.screenshot),
          path.join(dir, "reference", p.screenshot),
        );
      }
  }
  const preferences = [
    ...(await readJSON(path.join(globalDir, "preferences.json"), [])),
    ...(await feedbackEntries(globalDir)),
    ...feedback,
  ];
  const reportFile = path.join(dir, "report.json");
  await writeJSON(reportFile, report);
  await writeFile(path.join(dir, "design-rules.html"), renderDesignPolicy(report.designPolicy));
  await writeFile(
    path.join(dir, "index.html"),
    renderReport(report, preferences, reference),
  );
  await writeJSON(path.join(project, ".ui-review/latest.json"), {
    status: report.status,
    fingerprint: before,
    reportFile,
    blockingFindings: report.pages.flatMap((page) => page.findings
      .filter((f) => f.severity === "error")
      .map((f) => `${f.designRules.join(", ") || f.rule} · ${page.name}/${page.viewport.name}: ${f.message}`)).slice(0, 5),
  });
  return { report, reportFile };
}
