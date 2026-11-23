import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { Command } from "commander";
import { z } from "zod";
import { Connection } from "./server/connection";
import { address } from "./shared/contracts";

// Native Beads HTTP and bd support task inspection independently of Paseo.
const cli = new Command()
  .name("maintain")
  .description("Task host PR maintenance");
cli
  .command("skill")
  .description("Read task integration guidance without contacting a host")
  .action(() => {
    process.stdout.write(
      "# Task integration\n\nTask content lives in the configured Beads HTTP service. Inspect it independently of Paseo with native Beads tools or the service API. Pi retains native worker sessions; new coding workers require worktree manager. Existing data is never migrated implicitly. Submit/get retain the existing PR maintenance interface.\n",
    );
  });
for (const [name, method] of [
  ["submit", "tasks.link"],
  ["get", "tasks.pr_maintenance"],
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
