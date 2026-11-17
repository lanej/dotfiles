import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { Command } from "commander";
import { z } from "zod";
import { Connection } from "./server/connection";
import { address } from "./shared/contracts";

// Native bd remains the service-independent task CLI; this client handles migration and legacy maintenance.
const cli = new Command()
  .name("maintain")
  .description("Task host migration and maintenance");
cli
  .command("skill")
  .description("Read task integration guidance without contacting a host")
  .action(() => {
    process.stdout.write(
      "# Task integration\n\nUse bd list, bd show and bd history in the dedicated task repository without Paseo. Pi and Paseo retain their native worker sessions. Use beads-migrate --json with a host-qualified task address on stdin only after pausing the selected task at an idle boundary. Distributed replicas are unsupported. Submit/get retain the existing PR maintenance interface.\n",
    );
  });
for (const [name, method] of [
  ["submit", "tasks.link"],
  ["get", "tasks.pr_maintenance"],
  ["beads-migrate", "tasks.beads_migrate"],
]) {
  cli
    .command(name)
    .requiredOption("--json", "Read a request from stdin and return JSON")
    .action(async () => {
      const schema =
        name === "submit"
          ? address.extend({ url: z.string().url() }).strict()
          : address;
      const input = schema.parse(JSON.parse(readFileSync(0, "utf8")));
      const connection = new Connection(
        process.env.PASEO_HOME ?? join(homedir(), ".paseo"),
      );
      try {
        await connection.open();
        const output = await connection.call(input.serverId, method, input);
        process.stdout.write(`${JSON.stringify(output)}\n`);
      } finally {
        await connection.close();
      }
    });
}
cli.parseAsync().catch((error: unknown) => {
  process.stderr.write(
    `${JSON.stringify({ error: error instanceof Error ? error.message : String(error) })}\n`,
  );
  process.exitCode = 1;
});
