export const config = (url) => ({
  version: 1,
  baseURL: url,
  enforceOnStop: true,
  sourcePaths: ["src"],
  pages: [{ name: "comparison", path: "/", ready: "table" }],
  viewports: [{ name: "desktop", width: 1280, height: 800 }],
  accessibility: true,
});
export const rules = [
  {
    id: "rows",
    type: "visible-count",
    selector: "tbody tr",
    min: 8,
    severity: "error",
    reason: "Compare carriers together.",
  },
  {
    id: "header",
    type: "max-height",
    selector: "header",
    max: 160,
    severity: "warning",
    reason: "Keep evidence visible.",
  },
  {
    id: "edges",
    type: "align",
    selector: ".metric",
    edge: "top",
    tolerance: 2,
    severity: "error",
    reason: "Related metrics align.",
  },
  {
    id: "context",
    type: "context",
    selector: ".metric",
    required: [".period", ".baseline"],
    severity: "error",
    reason: "Numbers need context.",
  },
  {
    id: "clip",
    type: "no-clip",
    selector: ".label",
    severity: "error",
    reason: "Show the complete label.",
  },
  {
    id: "space",
    type: "no-overlap",
    selector: ".metric",
    severity: "error",
    reason: "Metrics must remain legible.",
  },
  {
    id: "type",
    type: "style",
    selector: "td",
    property: "font-size",
    allowed: ["14px"],
    severity: "error",
    reason: "Readable tabular data.",
  },
];
export const html = (
  broken,
) => `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Carrier comparison</title><style>
body{margin:24px;color:#142c27;background:#fff;font:14px Arial,sans-serif}header{height:${broken ? 450 : 100}px}
.metrics{display:flex;gap:24px}.metric{width:220px;padding:8px;border-bottom:1px solid #ccc}
${broken ? ".metric:nth-child(2){position:relative;top:20px;left:-100px}.label{width:60px;overflow:hidden;white-space:nowrap}body{min-width:1500px}" : ""}
table{border-collapse:collapse;width:100%;margin-top:20px}td,th{padding:10px;text-align:left;border-bottom:1px solid #ddd}td{font-size:14px}th:nth-child(n+2),td:nth-child(n+2){text-align:right;font-variant-numeric:tabular-nums}
</style></head><body><header><h1>Carrier comparison</h1><p>Choose the carrier with the best cost and reliability.</p></header><main>
<div class="metrics"><section class="metric"><h2>On time</h2><strong>98.2%</strong><p class="period">Last 30 days</p><p class="baseline">+0.8 points vs prior period</p></section>
<section class="metric"><h2>Average cost</h2><strong>$5.42</strong><p class="period">Last 30 days</p>${broken ? "" : '<p class="baseline">−$0.18 vs prior period</p>'}</section></div>
<p class="label">Carrier service and delivery window</p><table><caption>Comparable service levels · illustrative data</caption><thead><tr><th>Carrier</th><th>On time</th><th>Cost</th></tr></thead><tbody>
${Array.from({ length: 8 }, (_, i) => `<tr><td>Carrier ${i + 1}</td><td>98.${i}%</td><td>$${(5 + i / 10).toFixed(2)}</td></tr>`).join("")}
</tbody></table></main></body></html>`;
