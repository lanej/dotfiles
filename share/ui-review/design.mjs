import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";

export const policyPath = path.resolve(import.meta.dirname, "../../docs/design-rules.md");
const defaults = {
  align: ["DR-006"], "no-overlap": ["DR-006"], "no-clip": ["DR-006", "DR-007"],
  "visible-count": ["DR-006"], "comparison-set": ["DR-006", "DR-007"],
  context: ["DR-003"], consistent: ["DR-005"],
  "region-density": ["DR-007"], "max-height": ["DR-008"],
};
const advice = {
  align: "Align the declared peers using their shared layout or spacing rules.",
  "no-overlap": "Reflow the affected peers so their content remains readable.",
  "no-clip": "Allow enough space for the full content or provide intentional local scrolling.",
  "visible-count": "Reduce excess spacing or reflow the comparison to reveal the required items.",
  "comparison-set": "Reflow the comparison to preserve the missing identities and expose the configured detail; retain readable type.",
  context: "Display the missing context from the underlying data beside the claim or in its shared heading.",
  consistent: "Correct the shared rendering configuration or identity mapping. Generate metadata from that configuration; do not change evidence alone.",
  attribute: "Correct the renderer or data mapping, then regenerate its metadata. Changing an annotation alone does not repair the display.",
  "region-density": "Use the available comparison area for useful evidence; check the detail tiles before changing spacing.",
  "max-height": "Reduce excess header or container height while preserving necessary controls and context.",
  style: "Use the project's declared style values on the affected component.",
};
export const designIdsFor = (rule) => rule.designRules ?? defaults[rule.type] ??
  (rule.type === "style" ? [/font|line-height/.test(rule.property) ? "DR-007" : /shadow|border|background/.test(rule.property) ? "DR-008" : "DR-005"] : []);

export async function readDesignPolicy() {
  const source = await readFile(policyPath, "utf8");
  const rules = [...source.matchAll(/^## (DR-\d{3}) — (.+)\n([\s\S]*?)(?=^## |$(?![\s\S]))/gm)]
    .map(([, id, title, body]) => ({ id, title, body: body.trim(), href: `design-rules.html#${id}` }));
  if (rules.length !== 8) throw new Error("Design-rule document is missing expected sections");
  return { document: "docs/design-rules.md", sha256: createHash("sha256").update(source).digest("hex"), rules };
}

// Compare observations from the same page/data state across captures. These
// checks validate DOM evidence and declared metadata, not chart data truth.
export function evaluateDesign(report, rules, config) {
  const active = (rule, page) => (!rule.pages || rule.pages.includes(page.name)) &&
    (!rule.viewports || rule.viewports.includes(page.viewport.name));
  const add = (page, rule, message, actual, expected) => page.findings.push({
    rule: rule.id, severity: rule.severity, selector: rule.selector, reason: rule.reason,
    message, actual, expected,
  });
  for (const rule of rules) {
    const pages = report.pages.filter((page) => active(rule, page));
    if (rule.type === "comparison-set") {
      for (const page of pages) {
        const snapshot = page.metrics?.comparisons.find((item) => item.rule === rule.id);
        if (!snapshot) continue;
        const count = rule.minVisibleByViewport[page.viewport.name];
        if (!count || snapshot.keys.length < count)
          add(page, rule, "Too few distinct comparisons fit this viewport.", snapshot.keys.length, count ?? "configured minimum");
        if (page.viewport.name === rule.preserveFrom) continue;
        const baseline = pages.find((p) => p.name === page.name && p.viewport.name === rule.preserveFrom);
        const previous = baseline?.metrics?.comparisons.find((item) => item.rule === rule.id);
        if (!previous) {
          add(page, rule, "Reference viewport was not captured with comparison evidence.", rule.preserveFrom, "available comparison reference");
          continue;
        }
        if (page.viewport.width >= baseline.viewport.width && page.viewport.height >= baseline.viewport.height) {
          const lost = previous.keys.filter((key) => !snapshot.keys.includes(key));
          if (lost.length) add(page, rule, "Larger viewport lost previously visible comparisons.", lost, previous.keys);
        }
      }
    }
    if (rule.type === "consistent") {
      const seen = new Map();
      for (const page of pages)
        for (const item of page.metrics?.consistency.find((entry) => entry.rule === rule.id)?.items ?? []) {
          const key = JSON.stringify([page.name, item.key]);
          const prior = seen.get(key);
          if (prior && JSON.stringify(prior.values) !== JSON.stringify(item.values))
            add(page, rule, `Inconsistent encoding for ${item.key}; reference viewport: ${prior.viewport}.`, item.values, prior.values);
          else if (!prior) seen.set(key, { ...item, viewport: page.viewport.name });
        }
    }
  }
  for (const page of report.pages) {
    for (const finding of page.findings) {
      const rule = rules.find((r) => r.id === finding.rule);
      finding.designRules ??= rule ? designIdsFor(rule) : finding.rule === "page-overflow" ? ["DR-006", "DR-007"] : finding.rule === "detail-coverage" ? ["DR-007"] : [];
      finding.suggestion ??= rule ? advice[rule.type] : "Resolve the capture or accessibility issue and rerun ui-review check.";
      finding.evidenceKind = rule?.type === "attribute" || (rule?.type === "consistent" && rule.attributes.length) ? "DOM and declared metadata" : "DOM/capture";
    }
    page.designCoverage = report.designPolicy.rules.map(({ id, title, href }) => {
      const assigned = rules.filter((rule) => active(rule, page) && designIdsFor(rule).includes(id));
      const observed = assigned.filter((rule) => page.metrics?.evaluations.some((e) => e.rule === rule.id && e.status === "checked"));
      const hasFindings = page.findings.some((finding) => finding.designRules.includes(id));
      const status = hasFindings ? "findings" : observed.length ? "checks-passed" : "unassessed";
      if (config.requiredDesignRules?.includes(id) && !observed.length)
        page.findings.push({
          rule: "design-coverage", designRules: [id], severity: "error",
          message: `No executed check with visible evidence for required ${id}.`,
          actual: "unassessed", expected: "configured applicable check with visible evidence",
          evidenceKind: "coverage",
          suggestion: "Add a scoped check and supply its real evidence. An absent or optional skipped selector does not establish coverage.",
        });
      return { id, title, href, status, checks: observed.map((rule) => rule.id) };
    });
  }
}
