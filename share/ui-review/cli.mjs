#!/usr/bin/env node
import { parseArgs } from "node:util";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { readJSON, validateConfig } from "./config.mjs";
import { runReview } from "./review.mjs";
import {
  feedbackEntries,
  recordFeedback,
  learnRule,
  hookDecision,
} from "./state.mjs";

const help = `ui-review — rendered UI checks and a versioned design feedback loop

  init --url http://localhost:3000       Create project config (never overwrite)
  check                                Capture pages, check rules, write HTML + JSON
  feedback --report PATH --decision approve|adjust --note TEXT [--scope project|global]
                                       Save feedback; approval preserves screenshots
  learn --feedback ID --rule FILE [--scope project|global]
                                       Convert recorded feedback into a JSON rule
  guidance                             Print design preferences and prior feedback
  hook                                 Claude Stop hook; opt-in per project

Common: --project DIR (default cwd), --help
Project files: .ui-review/config.json, rules.json, feedback.jsonl, approved/
Global files: dotfiles/claude/ui-review/{rules.json,preferences.json,feedback.jsonl}
Exit codes: 0 checks pass, 1 checks fail, 2 setup/configuration/usage error.
See docs/ui-review.md in your dotfiles for rule types and CI use.
`;
try {
  const { values: args, positionals } = parseArgs({
    allowPositionals: true,
    options: Object.fromEntries(
      [
        "url",
        "project",
        "report",
        "decision",
        "note",
        "scope",
        "feedback",
        "rule",
      ]
        .map((k) => [k, { type: "string" }])
        .concat([["help", { type: "boolean" }]]),
    ),
  });
  const command = positionals[0];
  const project = path.resolve(args.project ?? process.cwd());
  const globalDir =
    process.env.UI_REVIEW_GLOBAL_DIR ??
    path.resolve(import.meta.dirname, "../../claude/ui-review");
  if (args.help || !command) console.log(help);
  else if (positionals.length !== 1)
    throw new Error("Expected one command; use --help.");
  else if (command === "init") {
    const dir = path.join(project, ".ui-review");
    const config = validateConfig({
      version: 1,
      baseURL: args.url ?? "http://localhost:3000",
      enforceOnStop: false,
      sourcePaths: ["."],
      accessibility: true,
      pages: [{ name: "main", path: "/", ready: "main" }],
      viewports: [
        { name: "desktop", width: 1440, height: 900 },
        { name: "wide", width: 1920, height: 1080 },
        { name: "large", width: 2560, height: 1440 },
        { name: "4k", width: 3840, height: 2160 },
        { name: "mobile", width: 390, height: 844 },
      ],
    });
    await mkdir(dir, { recursive: true });
    await writeFile(
      path.join(dir, "config.json"),
      JSON.stringify(config, null, 2) + "\n",
      { flag: "wx" },
    );
    for (const [name, content] of [
      ["rules.json", "[]\n"],
      [".gitignore", "runs/\nlatest.json\n*.lock\n*.tmp\nauth*.json\n"],
    ]) {
      try {
        await writeFile(path.join(dir, name), content, { flag: "wx" });
      } catch (err) {
        if (err.code !== "EEXIST") throw err;
      }
    }
    console.log(
      `Created ${dir}/config.json. Set routes, ready selectors, and rules before reviewing. Stop enforcement is off until enforceOnStop is true.`,
    );
  } else if (command === "check") {
    const result = await runReview(project, globalDir);
    console.log(
      JSON.stringify({
        status: result.report.status,
        ...result.report.summary,
        report: result.reportFile,
        html: path.join(path.dirname(result.reportFile), "index.html"),
        designRules: path.join(path.dirname(result.reportFile), "design-rules.html"),
        findings: result.report.pages.flatMap((page) => page.findings.map((finding) => ({
          page: page.name, viewport: page.viewport.name, ...finding,
        }))),
      }),
    );
    process.exitCode = result.report.status === "pass" ? 0 : 1;
  } else if (command === "feedback") {
    if (!args.report) throw new Error("--report is required");
    console.log(
      JSON.stringify(
        await recordFeedback(
          project,
          globalDir,
          path.resolve(project, args.report),
          args.decision,
          args.note,
          args.scope ?? "project",
        ),
      ),
    );
  } else if (command === "learn") {
    if (!args.rule || !args.feedback)
      throw new Error("--rule and --feedback are required");
    console.log(
      JSON.stringify(
        await learnRule(
          project,
          globalDir,
          args.feedback,
          await readJSON(path.resolve(project, args.rule)),
          args.scope ?? "project",
        ),
      ),
    );
  } else if (command === "guidance") {
    console.log(
      JSON.stringify(
        {
          preferences: await readJSON(
            path.join(globalDir, "preferences.json"),
            [],
          ),
          globalFeedback: await feedbackEntries(globalDir),
          projectFeedback: await feedbackEntries(
            path.join(project, ".ui-review"),
          ),
        },
        null,
        2,
      ),
    );
  } else if (command === "hook") {
    let input = "";
    for await (const chunk of process.stdin) input += chunk;
    console.log(
      JSON.stringify(await hookDecision(JSON.parse(input), globalDir)),
    );
  } else throw new Error(`Unknown command: ${command}`);
} catch (err) {
  console.error(`ui-review: ${err.message}`);
  process.exitCode = 2;
}
