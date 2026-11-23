#!/usr/bin/env bun
import { inspectIntegrations } from "./integrations.ts";
import { inspectPackageResources } from "./package-resources.ts";
import { Command } from "commander";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { z } from "zod";
import {
  BeadsReader,
  taskDetails,
  taskLabel,
  taskSchema,
  taskTree,
} from "./beads.ts";
import { TaskBeads } from "./task-service.ts";
import { dispatchGate } from "./capabilities.ts";
import {
  configPath,
  driverProfileSchema,
  exampleConfig,
  loadConfig,
} from "./config.ts";

enum HelpTopic {
  Tasks = "tasks",
  Compaction = "compaction",
  Profiles = "profiles",
  Dispatch = "dispatch",
}

const program = new Command()
  .name("pi-driver")
  .description(
    "Run a local Pi worker on an existing bead and inspect task state",
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
    let beadsService: {
      configured: boolean;
      verified: boolean;
      error?: string;
    } = { configured: false, verified: false };
    if (config.beadsService !== undefined) {
      try {
        await new TaskBeads(config.beadsService).verifyAuthority();
        beadsService = { configured: true, verified: true };
      } catch (cause) {
        beadsService = {
          configured: true,
          verified: false,
          error: cause instanceof Error ? cause.message : String(cause),
        };
      }
    }
    const integrations = await inspectIntegrations(config);
    const resources = await inspectPackageResources();
    output({
      resources,
      integrations,
      beads,
      beadsService,
      dispatch: dispatchGate,
      profiles: config.profiles,
    });
    process.exitCode =
      !resources.available ||
      beads.readable === false ||
      (beadsService.configured && !beadsService.verified) ||
      Object.values(integrations).some(
        (integration) => integration.enabled && !integration.present,
      )
        ? 1
        : 0;
  });
program
  .command("tasks [id]")
  .description(
    "Inspect a Beads task or containment tree (maximum 1000 records)",
  )
  .option("--json", "Print structured task data")
  .action(async (id: string | undefined, options: { json?: boolean }) => {
    const config = await loadConfig();
    if (config.beadsService !== undefined) {
      const service = new TaskBeads(config.beadsService);
      const projectId = config.beadsService.projectId;
      if (id !== undefined) {
        const task = await service.get(id);
        const { Attempts, stateDirectory } = await import("./attempts.ts");
        const directory = stateDirectory();
        let attempt = null;
        if (existsSync(join(directory, "attempts.sqlite"))) {
          const db = new Attempts(directory, true);
          try {
            attempt = db.latest(projectId, id);
          } finally {
            db.close();
          }
        }
        if (options.json === true) output({ projectId, task, attempt });
        else {
          console.log(taskDetails(taskSchema.parse(task), projectId));
          if (attempt !== null)
            console.log(`${attempt.phase} · ${attempt.message}`);
        }
      } else {
        const page = await service.list();
        const tasks = z.array(taskSchema).parse(page.items);
        if (options.json === true)
          output({ projectId, tasks, possiblyTruncated: page.has_more });
        else {
          for (const row of taskTree(tasks)) console.log(taskLabel(row));
          if (page.has_more)
            console.error(
              "Additional tasks are available. Inspect a task by its full ID.",
            );
        }
      }
      return;
    }
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
  .command("start <bead-id> [verifier...]")
  .description(
    "Start or focus a lead Pi session. Pass the agreed check as argv after --",
  )
  .requiredOption("--profile <name>", "work or personal")
  .option("--worker", "Start a direct worker without a lead plan")
  .option("--tab-id <id>", "Place a new worker in this Zellij tab")
  .action(
    async (
      id: string,
      verifier: string[],
      options: { profile: string; tabId?: string; worker?: boolean },
    ) => {
      if (verifier.length > 0 && !process.argv.slice(2).includes("--"))
        throw new Error("Place the agreed verification command after --");
      const { tabId } = await import("./zellij.ts");
      const { startTask } = await import("./task-run.ts");
      output(
        await startTask(
          id,
          driverProfileSchema.parse(options.profile),
          verifier,
          options.tabId === undefined ? undefined : tabId(options.tabId),
          options.worker !== true,
        ),
      );
    },
  );
program
  .command("resume <bead-id>")
  .description("Resume a settled lead in its existing worktree")
  .option("--tab-id <id>", "Place the reopened lead in this Zellij tab")
  .action(async (id: string, options: { tabId?: string }) => {
    const { resumeLead } = await import("./task-run.ts");
    const { tabId } = await import("./zellij.ts");
    output(
      await resumeLead(
        id,
        options.tabId === undefined ? undefined : tabId(options.tabId),
      ),
    );
  });
program
  .command("publish <bead-id>")
  .description("Publish the verified lead commit through Octo")
  .requiredOption("--title <title>", "Reviewed PR title")
  .requiredOption("--body-file <path>", "Reviewed PR description")
  .requiredOption("--base <branch>", "GitHub base branch")
  .action(
    async (
      id: string,
      options: { title: string; bodyFile: string; base: string },
    ) => {
      const { publishLead } = await import("./delivery.ts");
      output(
        await publishLead(id, options.title, options.bodyFile, options.base),
      );
    },
  );
program
  .command("ready <bead-id>")
  .description("Record owner assessment of current PR feedback in Octo")
  .requiredOption("--head <sha>", "Full verified commit SHA")
  .action(async (id: string, options: { head: string }) => {
    const { leadDeliveryDecision } = await import("./delivery.ts");
    output(await leadDeliveryDecision(id, options.head, undefined));
  });
program
  .command("merge <bead-id>")
  .description("Request an exact-head merge from an Octo Ready notice")
  .requiredOption("--head <sha>", "Full verified commit SHA")
  .requiredOption("--notice <id>", "Ready notice ID from /octo-inbox")
  .action(async (id: string, options: { head: string; notice: string }) => {
    const { leadDeliveryDecision } = await import("./delivery.ts");
    output(await leadDeliveryDecision(id, options.head, options.notice));
  });
program
  .command("archive <bead-id>")
  .description("Archive a settled lead after Octo confirms its merge")
  .action(async (id: string) => {
    const { archiveLead } = await import("./lead-archive.ts");
    output(await archiveLead(id));
  });
program
  .command("skill")
  .description("Read compact agent guidance without configuration or services")
  .option("--topic <topic>", "tasks, compaction, profiles, or dispatch")
  .action((options: { topic?: string }) => {
    const topics = {
      [HelpTopic.Tasks]:
        "Use pi-driver tasks [FULL_ID] [--json]. Use beadsService.url and projectId for the HTTP workflow. Existing workspace/database/branch settings still support read-only inspection. Containment and blockers remain separate. Observed descriptions are not accepted execution scope.",
      [HelpTopic.Compaction]:
        "Load the Pi package to enable idle compaction. Defaults: five settled minutes AND 60% context use. Active work, drafts, dialogs, queued input, unknown usage, and active child work prevent compaction. Failed attempts do not loop. Pi near-limit compaction remains independent.",
      [HelpTopic.Profiles]:
        "Configure work/personal roles using pi-driver config --example. /driver-profile explicitly selects the lead model in Pi after registry validation. Work requires a configured Bedrock Mantle endpoint; personal uses Pi openai-codex authentication. No credential copies or automatic cross-profile fallback.",
      [HelpTopic.Dispatch]:
        "From the repository in Zellij: pi-driver start BEAD_ID --profile work -- make test. Supply a check that covers the accepted criteria; omit it for human review. Repeat the command to focus the registered worker. Use /task-submit SUMMARY in its Pi pane. Inspect pi-driver tasks BEAD_ID --json for the result.",
    } satisfies Record<HelpTopic, string>;
    const topic =
      options.topic === undefined
        ? undefined
        : z.enum(HelpTopic).parse(options.topic);
    console.log(
      topic !== undefined
        ? topics[topic]
        : `# Pi daily driver\n\nStart one bead locally in Pi or inspect its result from the CLI.\n\nCommands: config, doctor, tasks, start, resume.\nTopics: ${Object.keys(topics).join(", ")}. Read one with pi-driver skill --topic NAME.\n\n${topics[HelpTopic.Dispatch]}`,
    );
  });

try {
  await program.parseAsync();
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
}
