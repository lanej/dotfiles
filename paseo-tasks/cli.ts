import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { z } from "zod";
import { address } from "./shared/contracts";
import { Connection } from "./server/connection";

// The CLI delegates to the existing host service; it never starts another scheduler.
async function main() {
  const command = process.argv[2];
  if (!["submit", "get"].includes(command) || process.argv[3] !== "--json" || process.argv.length !== 4) {
    throw new Error("Usage: npm run maintain -- submit|get --json < request.json");
  }
  const input = (command === "submit" ? address.extend({ url: z.string().url() }).strict() : address)
    .parse(JSON.parse(readFileSync(0, "utf8")));
  const connection = new Connection(process.env.PASEO_HOME ?? join(homedir(), ".paseo"));
  try {
    await connection.open();
    const output = await connection.call(input.serverId, command === "submit" ? "tasks.link" : "tasks.pr_maintenance", input);
    process.stdout.write(JSON.stringify(output) + "\n");
  } finally { await connection.close(); }
}
main().catch(error => {
  process.stderr.write(JSON.stringify({ error: error instanceof Error ? error.message : String(error) }) + "\n");
  process.exitCode = 1;
});
