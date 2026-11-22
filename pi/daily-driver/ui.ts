import { basename } from "node:path";
import {
  type ExtensionContext,
  type Theme,
  type ThemeColor,
  getSelectListTheme,
} from "@earendil-works/pi-coding-agent";
import {
  matchesKey,
  SelectList,
  styleText,
  Text,
  truncateToWidth,
  visibleWidth,
} from "@earendil-works/pi-tui";
import { knownTaskStatus, TaskStatus } from "./beads.ts";
import {
  ArrowSequence,
  isEntry,
  isMessageRole,
  NavigationKey,
  PiEntryType,
  PiMessageRole,
} from "./runtime.ts";

const statusTones = {
  [TaskStatus.Open]: "muted",
  [TaskStatus.InProgress]: "accent",
  [TaskStatus.Blocked]: "error",
  [TaskStatus.Deferred]: "warning",
  [TaskStatus.Closed]: "success",
} satisfies Record<TaskStatus, ThemeColor>;

export function statusPill(status: string, theme: Theme): string {
  const recognized = knownTaskStatus(status);
  const tone = recognized === undefined ? "muted" : statusTones[recognized];
  const label = status
    .replaceAll("_", " ")
    .replace(/\p{C}/gu, " ")
    .toUpperCase();
  return styleText(
    ` ${label} `,
    {
      fg: theme.colors.userMessageBg,
      bg: theme.colors[tone],
      bold: true,
    },
    theme.getColorMode(),
  );
}

export function installFooter(
  ctx: ExtensionContext,
  reasoning: () => string,
  profile: () => string | undefined,
): void {
  ctx.ui.setFooter((tui, theme, data) => ({
    dispose: data.onBranchChange(() => {
      tui.requestRender();
    }),
    invalidate() {},
    render(width) {
      const usage = ctx.getContextUsage();
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
      const metrics = [
        ctx.model?.reasoning === true ? reasoning() : undefined,
        usage?.percent != null && usage.percent > 0
          ? `${Math.round(usage.percent).toString()}% ctx`
          : undefined,
        cost > 0 ? `$${cost.toFixed(2)}` : undefined,
      ]
        .filter(Boolean)
        .join(" · ");
      const model = truncateToWidth(
        ctx.model?.id ?? "No model",
        Math.max(8, width - visibleWidth(metrics) - 3),
      );
      const right = [model, metrics].filter(Boolean).join(" · ");
      const branch = data.getGitBranch();
      const project = [profile(), basename(ctx.cwd), branch]
        .filter(Boolean)
        .join(" · ");
      const leftWidth = Math.max(0, width - visibleWidth(right) - 2);
      const left = leftWidth >= 8 ? truncateToWidth(project, leftWidth) : "";
      const spacing =
        left.length > 0
          ? " ".repeat(
              Math.max(1, width - visibleWidth(left) - visibleWidth(right)),
            )
          : "";
      const statuses = [...data.getExtensionStatuses()].map(([, value]) =>
        truncateToWidth(value, width),
      );
      return [
        theme.fg("muted", truncateToWidth(left + spacing + right, width)),
        ...statuses,
      ];
    },
  }));
}

export async function chooseTask(
  ctx: ExtensionContext,
  title: string,
  items: { value: string; label: string }[],
): Promise<string | undefined> {
  if (items.length === 0) return undefined;
  return ctx.ui.custom<string | undefined>((tui, theme, _keys, done) => {
    const heading = new Text(theme.fg("accent", title), 0, 0);
    const list = new SelectList(
      items,
      Math.max(3, Math.min(12, tui.terminal.rows - 8)),
      {
        ...getSelectListTheme(),
        selectedText: (text) => theme.bg("selectedBg", theme.fg("text", text)),
      },
    );
    list.onSelect = (item) => {
      done(item.value);
    };
    list.onCancel = () => {
      done(undefined);
    };
    return {
      invalidate() {
        heading.invalidate();
        list.invalidate();
      },
      render(width) {
        return [...heading.render(width), "", ...list.render(width)];
      },
      handleInput(input) {
        list.handleInput(
          matchesKey(input, NavigationKey.VimDown)
            ? ArrowSequence.Down
            : matchesKey(input, NavigationKey.VimUp)
              ? ArrowSequence.Up
              : input,
        );
        tui.requestRender();
      },
    };
  });
}

export async function showTask(
  ctx: ExtensionContext,
  details: string,
): Promise<void> {
  await ctx.ui.custom<undefined>((tui, theme, _keys, done) => {
    const text = new Text(theme.fg("text", details), 0, 0);
    let offset = 0;
    let maximum = 0;
    return {
      invalidate() {
        text.invalidate();
      },
      render(width) {
        const lines = text.render(width);
        const height = Math.max(3, tui.terminal.rows - 5);
        maximum = Math.max(0, lines.length - height);
        offset = Math.min(offset, maximum);
        return lines.slice(offset, offset + height);
      },
      handleInput(input) {
        if (
          matchesKey(input, NavigationKey.Escape) ||
          matchesKey(input, NavigationKey.Enter) ||
          matchesKey(input, NavigationKey.Cancel)
        )
          done(undefined);
        else if (
          matchesKey(input, NavigationKey.Down) ||
          matchesKey(input, NavigationKey.VimDown)
        )
          offset = Math.min(maximum, offset + 1);
        else if (
          matchesKey(input, NavigationKey.Up) ||
          matchesKey(input, NavigationKey.VimUp)
        )
          offset = Math.max(0, offset - 1);
        tui.requestRender();
      },
    };
  });
}

// Wave details use the existing themed terminal surface. The action stays
// reachable at narrow widths after scrolling through the exact approval text.
export async function reviewPlan(
  ctx: ExtensionContext,
  heading: string,
  details: string,
  action: string,
): Promise<boolean> {
  return ctx.ui.custom<boolean>((tui, theme, _keys, done) => {
    const text = new Text(details.replace(/[^\P{Cc}\n\t]/gu, " "), 0, 0);
    let offset = 0;
    let maximum = 0;
    return {
      invalidate() {
        text.invalidate();
      },
      render(width) {
        const lines = text.render(width);
        const height = Math.max(3, tui.terminal.rows - 7);
        maximum = Math.max(0, lines.length - height);
        offset = Math.min(offset, maximum);
        return [
          truncateToWidth(theme.fg("accent", heading), width),
          ...lines.slice(offset, offset + height),
          truncateToWidth(
            theme.fg(
              "dim",
              offset < maximum
                ? "↓ More · Esc cancel"
                : `Enter ${action} · Esc cancel`,
            ),
            width,
          ),
        ];
      },
      handleInput(input) {
        if (
          matchesKey(input, NavigationKey.Escape) ||
          matchesKey(input, NavigationKey.Cancel)
        )
          done(false);
        else if (matchesKey(input, NavigationKey.Enter)) {
          if (offset === maximum) done(true);
          else
            offset = Math.min(
              maximum,
              offset + Math.max(1, tui.terminal.rows - 8),
            );
        } else if (
          matchesKey(input, NavigationKey.Down) ||
          matchesKey(input, NavigationKey.VimDown)
        ) {
          offset = Math.min(maximum, offset + 1);
        } else if (
          matchesKey(input, NavigationKey.Up) ||
          matchesKey(input, NavigationKey.VimUp)
        ) {
          offset = Math.max(0, offset - 1);
        }
        tui.requestRender();
      },
    };
  });
}
