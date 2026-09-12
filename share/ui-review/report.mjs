const escape = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
export function renderDesignPolicy(policy) {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Design rules</title><style>body{font:16px/1.6 system-ui;margin:32px auto;padding:0 20px;max-width:850px;color:#172d27}section{margin:40px 0}code{overflow-wrap:anywhere}</style></head><body>
<h1>Design rules used by this review</h1><p><a href="index.html">Back to review</a> · ${escape(policy.document)}</p><p>Snapshot SHA-256: <code>${escape(policy.sha256)}</code></p>
${policy.rules.map((rule) => `<section id="${escape(rule.id)}"><h2>${escape(rule.id)} — ${escape(rule.title)}</h2><p>${escape(rule.body).replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>").replace(/\n\n/g, "</p><p>")}</p></section>`).join("")}</body></html>`;
}
export function renderReport(report, preferences, reference) {
  const e = escape;
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>UI review</title>
<style>body{font:16px/1.5 system-ui,sans-serif;color:#172d27;background:#f6f8f7;margin:0}main{max-width:1400px;margin:auto;padding:24px}h1,h2{line-height:1.2}small{color:#46594f}table{border-collapse:collapse;width:100%;background:white}th,td{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid #ced8d2}code{overflow-wrap:anywhere}figure{margin:0;min-width:0}img{width:100%;border:1px solid #becbc3}.compare{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:20px}section{margin:32px 0}a{color:#165b41}.error{color:#962e24}.warning{color:#704b0c}.pass{color:#165b41}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style></head><body><main>
<h1>UI review · <span class="${e(report.status)}">${e(report.status)}</span></h1>
<p>${report.summary.errors} errors · ${report.summary.warnings} warnings · ${report.pages.length} captures</p>
<small>${e(report.createdAt)} · <a href="report.json">JSON report</a> · ${e(report.id)}</small>
<p>Automated checks cover configured constraints. <a href="design-rules.html">Design-rule reference used for this run</a>. A passed check establishes only its measured condition; metadata checks do not certify that a chart renders its data faithfully. Inspect the detail images and review unassessed requirements.</p>
${preferences.length ? `<details open><summary>Design guidance and prior feedback</summary><ul>${preferences.map((x) => `<li>${e(typeof x === "string" ? x : x.note)}</li>`).join("")}</ul></details>` : ""}
${report.pages
  .map((p) => {
    const approved = reference?.report.pages.find(
      (x) =>
        x.name === p.name &&
        x.viewport.name === p.viewport.name &&
        x.viewport.width === p.viewport.width &&
        x.viewport.height === p.viewport.height,
    );
    return `<section><h2>${e(p.name)} · ${e(p.viewport.name)} (${p.viewport.width} × ${p.viewport.height})</h2><small>${e(p.url)}</small>
${p.designCoverage ? `<details><summary>Design-rule coverage · ${p.designCoverage.filter((r) => r.status === "unassessed").length} unassessed</summary><p>Checks cover configured parts of each requirement. Unassessed rules are not passes. Human review is still needed for meaning and graphical truth.</p><table><thead><tr><th>Design rule</th><th>Evidence status</th><th>Executed checks</th></tr></thead><tbody>${p.designCoverage.map((r) => `<tr><td><a href="${e(r.href)}">${e(r.id)} — ${e(r.title)}</a></td><td>${e(r.status)}</td><td>${e(r.checks.join(", "))}</td></tr>`).join("")}</tbody></table></details>` : ""}
<div class="compare">${p.screenshot ? `<figure><figcaption>Current</figcaption><a href="${e(p.screenshot)}"><img src="${e(p.screenshot)}" alt="Current ${e(p.name)}"></a></figure>` : ""}
${approved?.screenshot ? `<figure><figcaption>Approved reference · ${e(reference.note)}</figcaption><a href="reference/${e(approved.screenshot)}"><img src="reference/${e(approved.screenshot)}" alt="Approved ${e(p.name)}"></a></figure>` : ""}</div>
${p.details ? `<details><summary>Full-resolution details · ${p.details.capturedTiles}/${p.details.expectedTiles} tiles · ${p.details.complete ? "complete" : "INCOMPLETE"}</summary><p>Open each tile at original size to judge text, spacing, and clipping. Coordinates are CSS pixels from the page origin; adjacent tiles overlap.</p>${p.details.tiles.map((t) => `<figure style="margin:16px 0;overflow:auto"><figcaption>x=${t.x}, y=${t.y} · ${t.width} × ${t.height} · <a href="${e(t.file)}">Open original</a></figcaption><img style="width:${t.width}px;max-width:none" src="${e(t.file)}" alt="Detail at ${t.x}, ${t.y}" loading="lazy"></figure>`).join("")}</details>` : ""}
${p.metrics?.density?.length ? `<table><caption>Region density · measured before any screenshot scaling</caption><thead><tr><th>Region / method</th><th>Coverage</th><th>Elements / 100k px²</th><th>Largest vertical gap</th></tr></thead><tbody>${p.metrics.density.map((d) => `<tr><td><code>${e(d.region)}</code> / ${e(d.measure)}</td><td>${(d.coverage * 100).toFixed(1)}%</td><td>${d.elementsPer100kPixels.toFixed(1)}</td><td>${d.largestVerticalGap.toFixed(1)}px</td></tr>`).join("")}</tbody></table>` : ""}
${p.findings.length ? `<table><thead><tr><th>Severity / rule</th><th>Finding and next action</th><th>Evidence</th></tr></thead><tbody>${p.findings.map((f) => `<tr><td class="${e(f.severity)}">${e(f.severity)}<br><code>${e(f.rule)}</code><br>${(f.designRules ?? []).map((id) => `<a href="design-rules.html#${e(id)}">${e(id)}</a>`).join(", ")}</td><td>${e(f.message)}<br><small>${e(f.reason)}</small><p>${e(f.suggestion)}</p></td><td><code>${e(f.selector)}</code><br>${e(JSON.stringify({ actual: f.actual, expected: f.expected }))}<br><small>${e(f.evidenceKind)}</small></td></tr>`).join("")}</tbody></table>` : '<p class="pass">No automated findings.</p>'}</section>`;
  })
  .join("")}
<section><h2>Record feedback</h2><p>Tell your coding agent what works or what should change. It can run the feedback command below, then convert measurable feedback into a scoped rule. Approval saves a reference; it never waives failing checks.</p>
<pre>ui-review feedback --report .ui-review/runs/${e(report.id)}/report.json --decision approve --note "What works and where it applies"
ui-review feedback --report .ui-review/runs/${e(report.id)}/report.json --decision adjust --note "What to change and why"</pre></section></main></body></html>`;
}
