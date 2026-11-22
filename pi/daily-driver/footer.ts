import { homedir } from "node:os";
import { isAbsolute, relative, sep } from "node:path";
import type {
  ExtensionContext,
  ThemeColor,
} from "@earendil-works/pi-coding-agent";
import {
  sliceByColumn,
  truncateToWidth,
  visibleWidth,
} from "@earendil-works/pi-tui";
import { z } from "zod";
import { ReasoningLevel } from "./config.ts";
import { type FooterGit, watchFooterGit } from "./footer-git.ts";
import { githubLink } from "./github-links.ts";
import { LeadMode } from "./lead-plan.ts";
import { run } from "./process.ts";
import {
  FooterStatus,
  isEntry,
  isMessageRole,
  PiEntryType,
  PiMessageRole,
} from "./runtime.ts";

const clean = (value: string) => value.replace(/\p{Cc}/gu, " ").trim();
const separator = " ";
const primaryStatus = new Set<string>([FooterStatus.Bead, FooterStatus.Plan]);

const modeGlyph = {
  [LeadMode.Planning]: ["◇", "warning"],
  [LeadMode.Applying]: ["◐", "warning"],
  [LeadMode.Implementing]: ["◆", "accent"],
} satisfies Record<LeadMode, [string, ThemeColor]>;

const reasoningGlyph = {
  [ReasoningLevel.Off]: ["", "dim"],
  [ReasoningLevel.Minimal]: ["▁", "muted"],
  [ReasoningLevel.Low]: ["▂", "muted"],
  [ReasoningLevel.Medium]: ["▄", "accent"],
  [ReasoningLevel.High]: ["▆", "accent"],
  [ReasoningLevel.ExtraHigh]: ["█", "accent"],
} satisfies Record<ReasoningLevel, [string, ThemeColor]>;

const modelVariantGlyph = new Map([
  ["sol", "\uE30D"],
  ["luna", "\uF186"],
  ["terra", "\uF0AC"],
  ["astra", "\uF005"],
]);

export function footerModelLabel(id: string): string {
  const [, gpt, reasoning, variant] =
    /^(?:openai\.)?(?:gpt-(\d+(?:\.\d+)?o?)|(o\d+))(?:-([a-z0-9][a-z0-9-]*))?$/u.exec(
      id,
    ) ?? [];
  const version = gpt ?? reasoning;
  if (version === undefined) return id;
  const name =
    variant === undefined
      ? ""
      : (modelVariantGlyph.get(variant) ??
        `${variant.charAt(0).toUpperCase()}${variant.slice(1)}`);
  return name === "" ? `⊛ ${version}` : `⊛ ${version} ${name}`;
}

export function installFooter(
  ctx: ExtensionContext,
  reasoning: () => string,
  trackedPullRequest?: () => string | undefined,
): void {
  ctx.ui.setFooter((tui, theme, data) => {
    const cwd = ctx.cwd;
    const home = homedir();
    const local = relative(home, cwd);
    const underHome =
      !isAbsolute(local) && local !== ".." && !local.startsWith(`..${sep}`);
    const prefix = underHome ? "~/" : "";
    let directory = clean(
      underHome ? (local === "" ? "~" : prefix + local) : cwd,
    );
    let disposed = false;
    if (local !== "" || !underHome)
      void run("shortpath", ["--null", "--", underHome ? local : cwd], {
        cwd: home,
        timeout: 1000,
      })
        .then((output) => {
          const [label, end, ...extra] = output.split("\0");
          if (
            disposed ||
            label === undefined ||
            label === "" ||
            end !== "" ||
            extra.length > 0
          )
            return;
          directory = clean(prefix + label);
          tui.requestRender();
        })
        .catch(() => {
          // Keep the full directory label if the optional executable is unavailable.
        });
    let git: FooterGit = {};
    const stopGit = watchFooterGit(cwd, trackedPullRequest, (status) => {
      git = status;
      tui.requestRender();
    });
    const stop = data.onBranchChange(() => {
      tui.requestRender();
    });
    return {
      dispose() {
        disposed = true;
        stop();
        stopGit();
      },
      invalidate() {},
      render(width) {
        if (width <= 2) return [];
        let cost = 0;
        for (const entry of ctx.sessionManager.getEntries()) {
          if (
            isEntry(entry, PiEntryType.Message) &&
            isMessageRole(entry.message, PiMessageRole.Assistant)
          ) {
            cost += entry.message.usage.cost.total;
          } else if (
            isEntry(entry, PiEntryType.Message) &&
            isMessageRole(entry.message, PiMessageRole.ToolResult)
          ) {
            cost += entry.message.usage?.cost.total ?? 0;
          } else if (
            isEntry(entry, PiEntryType.Usage) ||
            isEntry(entry, PiEntryType.Compaction) ||
            isEntry(entry, PiEntryType.BranchSummary)
          ) {
            cost += entry.usage?.cost.total ?? 0;
          }
        }
        const statuses = data.getExtensionStatuses();
        const bead = clean(statuses.get(FooterStatus.Bead) ?? "");
        const plan = z
          .enum(LeadMode)
          .safeParse(statuses.get(FooterStatus.Plan));
        const mode = plan.success ? modeGlyph[plan.data] : undefined;
        const branch = clean(data.getGitBranch() ?? "");
        const model = footerModelLabel(clean(ctx.model?.id ?? "No model"));
        const usage = ctx.getContextUsage()?.percent ?? 0;
        const level = z.enum(ReasoningLevel).safeParse(reasoning());
        const effort =
          ctx.model?.reasoning === true && level.success
            ? reasoningGlyph[level.data]
            : undefined;
        const inner = width - 2;
        const marker = git.linked === true ? "▣" : "▸";
        const pathWidth = visibleWidth(`${marker} ${directory}`);
        const minimumPath = Math.min(
          pathWidth,
          inner - 1,
          Math.max(8, Math.floor(inner / 4)),
        );
        const modelBudget = Math.max(0, inner - minimumPath - 1);
        const modelLabel = truncateToWidth(model, modelBudget);
        let remaining = Math.max(0, modelBudget - visibleWidth(modelLabel));
        const fit = (value: string): string => {
          const cells = visibleWidth(value) + visibleWidth(separator);
          if (value === "" || cells > remaining) return "";
          remaining -= cells;
          return value;
        };

        const context = fit(
          usage > 0
            ? theme.fg("muted", `◔${Math.round(usage).toString()}%`)
            : "",
        );
        const price = fit(
          cost > 0
            ? theme.fg("muted", cost < 0.01 ? "<$0.01" : `~$${cost.toFixed(2)}`)
            : "",
        );
        const pr = fit(
          git.pullRequest === undefined
            ? ""
            : theme.fg("accent", githubLink(git.pullRequest, true) ?? ""),
        );
        const counts = git.changes;
        const stats =
          counts === undefined
            ? ""
            : [
                counts.files > 0
                  ? theme.fg("muted", `Δ${counts.files.toString()}`)
                  : "",
                counts.added > 0
                  ? theme.fg("success", `+${counts.added.toString()}`)
                  : "",
                counts.removed > 0
                  ? theme.fg("error", `−${counts.removed.toString()}`)
                  : "",
                counts.untracked > 0
                  ? theme.fg("warning", `?${counts.untracked.toString()}`)
                  : "",
              ]
                .filter((part) => part !== "")
                .join(" ");
        const changes = fit(stats);
        const reasoningLevel = fit(
          effort === undefined || effort[0] === ""
            ? ""
            : theme.fg(effort[1], effort[0]),
        );
        const task = fit(
          bead === ""
            ? ""
            : [
                mode === undefined ? "" : theme.fg(mode[1], mode[0]),
                theme.bold(theme.fg("text", bead)),
              ]
                .filter((part) => part !== "")
                .join(" "),
        );
        const branchLabel = fit(
          branch === "" ? "" : theme.fg("muted", `↱ ${branch}`),
        );
        const secondary = [...statuses].flatMap(([key, value]) =>
          primaryStatus.has(key) || value.trim() === "" ? [] : [fit(value)],
        );
        const left = [task, branchLabel, changes, pr, ...secondary]
          .filter((part) => part !== "")
          .join(separator);
        const right = [
          theme.fg("accent", modelLabel),
          reasoningLevel,
          context,
          price,
        ]
          .filter((part) => part !== "")
          .join(separator);
        const pathRoom = Math.min(pathWidth, minimumPath + remaining);
        const pathLabel =
          pathRoom >= pathWidth
            ? `${marker} ${directory}`
            : pathRoom > 3
              ? `${marker} …${sliceByColumn(directory, Math.max(0, visibleWidth(directory) - pathRoom + 3), pathRoom - 3, true)}`
              : truncateToWidth(`${marker} ${directory}`, pathRoom);
        const leftLine = [theme.fg("text", pathLabel), left]
          .filter((part) => part !== "")
          .join(separator);
        const gap = " ".repeat(
          Math.max(0, inner - visibleWidth(leftLine + right)),
        );
        return [theme.bg("userMessageBg", ` ${leftLine}${gap}${right} `)];
      },
    };
  });
}
