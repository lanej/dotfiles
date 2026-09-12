import Ajv from "ajv";
import { readFile } from "node:fs/promises";
import path from "node:path";

const text = { type: "string", minLength: 1 };
const names = { type: "array", minItems: 1, uniqueItems: true, items: text };
const positive = { type: "integer", minimum: 1 };
const designIds = { type: "array", uniqueItems: true, items: { enum: Array.from({ length: 8 }, (_, i) => `DR-00${i + 1}`) } };
const object = (properties, required) => ({
  type: "object",
  additionalProperties: false,
  properties,
  required,
});
export const configSchema = object(
  {
    version: { const: 1 },
    baseURL: text,
    enforceOnStop: { type: "boolean" },
    sourcePaths: names,
    accessibility: { type: "boolean" },
    requiredDesignRules: designIds,
    storageState: text,
    timeoutMs: { type: "integer", minimum: 1000, maximum: 120000 },
    detailCapture: object(
      {
        width: { type: "integer", minimum: 256, maximum: 1280 },
        height: { type: "integer", minimum: 256, maximum: 1280 },
        overlap: { type: "integer", minimum: 0, maximum: 128 },
        maxTiles: { type: "integer", minimum: 1, maximum: 256 },
      },
      ["width", "height", "overlap", "maxTiles"],
    ),
    pages: {
      type: "array",
      minItems: 1,
      items: object({ name: text, path: text, ready: text }, [
        "name",
        "path",
        "ready",
      ]),
    },
    viewports: {
      type: "array",
      minItems: 1,
      items: object({ name: text, width: positive, height: positive }, [
        "name",
        "width",
        "height",
      ]),
    },
  },
  [
    "version",
    "baseURL",
    "pages",
    "viewports",
    "sourcePaths",
    "enforceOnStop",
    "accessibility",
  ],
);
const common = {
  id: text,
  selector: text,
  severity: { enum: ["error", "warning"] },
  reason: text,
  pages: names,
  viewports: names,
  optional: { type: "boolean" },
  feedbackId: text,
  designRules: { ...designIds, minItems: 1 },
};
const types = {
  align: {
    edge: { enum: ["left", "right", "top", "bottom"] },
    tolerance: { type: "number", minimum: 0 },
  },
  "no-overlap": {},
  "no-clip": {},
  "visible-count": { min: positive },
  "max-height": { max: { type: "number", exclusiveMinimum: 0 } },
  style: { property: text, allowed: names },
  attribute: { attribute: text, allowed: names },
  consistent: {
    keyAttribute: text,
    properties: { type: "array", uniqueItems: true, items: text },
    attributes: { type: "array", uniqueItems: true, items: text },
  },
  "comparison-set": {
    keyAttribute: text,
    requiredKeys: names,
    minVisibleByViewport: { type: "object", minProperties: 1, additionalProperties: positive },
    preserveFrom: text,
    minFontSize: { type: "number", exclusiveMinimum: 0 },
  },
  context: { required: names },
  "region-density": {
    region: text,
    measure: { enum: ["boxes", "text"] },
    minCoverage: { type: "number", minimum: 0, maximum: 1 },
    maxVerticalGap: { type: "number", minimum: 0 },
  },
};
export const ruleSchema = {
  oneOf: Object.entries(types).map(([type, extra]) =>
    object({ ...common, type: { const: type }, ...extra }, [
      "id",
      "type",
      "selector",
      "severity",
      "reason",
      ...Object.keys(extra),
    ]),
  ),
};
const ajv = new Ajv({ allErrors: true });
const checkConfig = ajv.compile(configSchema);
const checkRules = ajv.compile({ type: "array", items: ruleSchema });
function unique(values, label) {
  if (new Set(values).size !== values.length)
    throw new Error(`Duplicate ${label}`);
}
export function validateConfig(config) {
  if (!checkConfig(config))
    throw new Error(`Invalid config: ${ajv.errorsText(checkConfig.errors)}`);
  const url = new URL(config.baseURL);
  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password
  )
    throw new Error("baseURL must be HTTP(S) without embedded credentials");
  unique(
    config.pages.map((p) => p.name),
    "page name",
  );
  unique(
    config.viewports.map((v) => v.name),
    "viewport name",
  );
  for (const p of config.pages) {
    if (new URL(p.path, url).origin !== url.origin)
      throw new Error("Page paths must stay on baseURL origin");
  }
  for (const p of config.sourcePaths) {
    if (path.isAbsolute(p) || p.split(/[\\/]/).includes(".."))
      throw new Error("sourcePaths must stay inside the project");
  }
  return config;
}
export function validateRules(rules) {
  if (!checkRules(rules))
    throw new Error(`Invalid rules: ${ajv.errorsText(checkRules.errors)}`);
  unique(
    rules.map((r) => r.id),
    "rule ID",
  );
  for (const rule of rules)
    if (rule.type === "consistent" && !rule.properties.length && !rule.attributes.length)
      throw new Error(`Rule ${rule.id}: choose at least one property or attribute to compare`);
    else if (rule.type === "attribute" && !rule.designRules)
      throw new Error(`Rule ${rule.id}: attribute checks must cite designRules`);
  return rules;
}
export function mergeRules(global, local) {
  validateRules(global);
  validateRules(local);
  return [...new Map([...global, ...local].map((r) => [r.id, r])).values()];
}
export async function readJSON(file, fallback) {
  try {
    return JSON.parse(await readFile(file, "utf8"));
  } catch (err) {
    if (err.code === "ENOENT" && fallback !== undefined) return fallback;
    throw err;
  }
}
export async function loadProject(project, globalDir) {
  const config = validateConfig(
    await readJSON(path.join(project, ".ui-review/config.json")),
  );
  const local = await readJSON(path.join(project, ".ui-review/rules.json"), []);
  const rules = mergeRules(
    await readJSON(path.join(globalDir, "rules.json"), []),
    local,
  );
  // Global rules may target page/viewport names used by other projects.
  // Local scope typos should still fail loudly.
  for (const r of local) {
    for (const n of r.pages ?? [])
      if (!config.pages.some((p) => p.name === n))
        throw new Error(`Rule ${r.id}: unknown page ${n}`);
    for (const n of r.viewports ?? [])
      if (!config.viewports.some((v) => v.name === n))
        throw new Error(`Rule ${r.id}: unknown viewport ${n}`);
    if (r.type === "comparison-set") {
      const active = config.viewports.filter((v) => !r.viewports || r.viewports.includes(v.name));
      if (!active.some((v) => v.name === r.preserveFrom))
        throw new Error(`Rule ${r.id}: preserveFrom must name an active viewport`);
      for (const name of Object.keys(r.minVisibleByViewport))
        if (!active.some((v) => v.name === name))
          throw new Error(`Rule ${r.id}: count targets an inactive viewport ${name}`);
      for (const v of active)
        if (!r.minVisibleByViewport[v.name])
          throw new Error(`Rule ${r.id}: missing visible count for ${v.name}`);
    }
  }
  return { config, rules };
}
