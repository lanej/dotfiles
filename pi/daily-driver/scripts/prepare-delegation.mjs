import { readFileSync, writeFileSync } from "node:fs";

const root = new URL("../node_modules/@tintinweb/pi-subagents/", import.meta.url);
const manifest = JSON.parse(readFileSync(new URL("package.json", root), "utf8"));
if (manifest.version !== "0.26.2") throw new Error("Review the managed runner patch for this plugin version");
let source = readFileSync(new URL("src/agent-runner.ts", root), "utf8");
function replace(before, after) {
  if (source.split(before).length !== 2) throw new Error("Managed runner patch no longer applies");
  source = source.replace(before, after);
}
replace("  pi: ExtensionAPI;\n", "  pi: ExtensionAPI;\n  sessionDir?: string;\n  driverTools?: NonNullable<Parameters<typeof createAgentSession>[0]['customTools']>;\n");
replace("    tools: sessionTools,\n    customTools: [...nestedTools, ...structuredTools],",
  "    tools: options.driverTools?.map(tool => tool.name) ?? sessionTools,\n    customTools: options.driverTools ?? [...nestedTools, ...structuredTools],");
replace("resolveConfiguredSessionDir(agentConfig?.sessionDir, effectiveCwd)",
  "options.sessionDir ?? resolveConfiguredSessionDir(agentConfig?.sessionDir, effectiveCwd)");
writeFileSync(new URL("src/driver-runner.ts", root), source);
