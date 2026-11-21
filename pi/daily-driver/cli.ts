#!/usr/bin/env node
import { Command } from "commander";
import { z } from "zod";
import { BeadsReader, taskDetails, taskLabel, taskTree } from "./beads.ts";
import { dispatchGate, requireDispatch } from "./capabilities.ts";
import { configPath, exampleConfig, loadConfig } from "./config.ts";

enum HelpTopic {
  Tasks = "tasks",
  Compaction = "compaction",
  Profiles = "profiles",
  Dispatch = "dispatch",
}

const program = new Command()
  .name("pi-driver")
  .description(
    "Pi daily-driver configuration, read-only Beads task trees, and capability inspection",
  )
  .version("0.1.0");
const output = (value: unknown): void => {
  console.log(JSON.stringify(value, null, 2));
};
program
  .command("config")
  .description("Inspect configuration without changing settings or credentials")
  .option("--example", "Print a configuration example")
  .action(async (options: { example?: boolean }) => {
    output(
      options.example === true
        ? exampleConfig
        : { path: configPath(), configuration: await loadConfig() },
    );
  });
program
  .command("doctor")
  .description(
    "Verify the configured task source and inspect the managed-launch gate",
  )
  .action(async () => {
    const config = await loadConfig();
    let beads: { configured: boolean; readable?: boolean; error?: string } = {
      configured: false,
    };
    if (config.beads !== undefined) {
      try {
        await new BeadsReader(config.beads).verify();
        beads = { configured: true, readable: true };
      } catch (error) {
        beads = {
          configured: true,
          readable: false,
          error: error instanceof Error ? error.message : String(error),
        };
      }
    }
    output({ beads, dispatch: dispatchGate, profiles: config.profiles });
    process.exitCode = 1;
  });
program
  .command("tasks [id]")
  .description(
    "Inspect a Beads task or containment tree (maximum 1000 records)",
  )
  .option("--json", "Print structured task data")
  .action(async (id: string | undefined, options: { json?: boolean }) => {
    const config = await loadConfig();
    if (config.beads === undefined)
      throw new Error(
        `Configure an explicit Beads workspace, database, and branch in ${configPath()}; discovery never initializes one`,
      );
    const reader = new BeadsReader(config.beads);
    if (id !== undefined && id.length > 0) {
      const task = await reader.show(id);
      if (options.json === true)
        output({ workspace: config.beads.workspace, task });
      else console.log(taskDetails(task, config.beads.workspace));
    } else {
      const tasks = await reader.list();
      if (options.json === true)
        output({
          workspace: config.beads.workspace,
          tasks,
          possiblyTruncated: tasks.length === 1000,
        });
      else {
        console.log(
          `Beads: ${config.beads.workspace} / ${config.beads.database}@${config.beads.branch}`,
        );
        for (const row of taskTree(tasks)) console.log(taskLabel(row));
        if (tasks.length === 1000)
          console.error(
            "Result may be truncated at 1000 tasks; inspect a task by its full ID.",
          );
      }
    }
  });
program
  .command("start")
  .description("Report the prerequisite blocking managed task launch")
  .option("--profile <name>", "work or personal")
  .action(requireDispatch);
program
  .command("resume")
  .description("Report the prerequisite blocking managed task recovery")
  .action(requireDispatch);
program
  .command("skill")
  .description("Read compact agent guidance without configuration or services")
  .option("--topic <topic>", "tasks, compaction, profiles, or dispatch")
  .action((options: { topic?: string }) => {
    const topics = {
      [HelpTopic.Tasks]:
        "Use pi-driver tasks [FULL_ID] [--json]. Reads require an explicit workspace/database/branch and never initialize a database. Containment and blockers remain separate. Observed descriptions are not accepted execution scope.",
      [HelpTopic.Compaction]:
        "Load the Pi package to enable idle compaction. Defaults: five settled minutes AND 60% context use. Active work, drafts, dialogs, queued input, unknown usage, and active child work prevent compaction. Failed attempts do not loop. Pi near-limit compaction remains independent.",
      [HelpTopic.Profiles]:
        "Configure work/personal roles using pi-driver config --example. /driver-profile explicitly selects the lead model in Pi after registry validation. Work requires a configured Bedrock Mantle endpoint; personal uses Pi openai-codex authentication. No credential copies or automatic cross-profile fallback.",
      [HelpTopic.Dispatch]: dispatchGate.reason,
    } satisfies Record<HelpTopic, string>;
    const topic =
      options.topic === undefined
        ? undefined
        : z.enum(HelpTopic).parse(options.topic);
    console.log(
      topic !== undefined
        ? topics[topic]
        : `# Pi daily driver\n\nRead-only foundation; managed dispatch is blocked by Beads scope fencing.\n\nCommands: config, doctor, tasks, start, resume.\nTopics: ${Object.keys(topics).join(", ")}. Read one with pi-driver skill --topic NAME.\n\n${topics[HelpTopic.Dispatch]}`,
    );
  });

try {
  await program.parseAsync();
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
}
