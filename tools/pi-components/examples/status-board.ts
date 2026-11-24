import {
  Input,
  ProcessTerminal,
  TuiAltScreen,
  matchesKey,
  parseColor,
  styleText,
  visibleWidth,
  type OverlayHandle,
} from "@earendil-works/pi-tui";
import {
  ConditionState,
  conditionMark,
  createStatusBoard,
  renderStatusDock,
  type StatusColumn,
  type StatusTheme,
} from "../index.ts";

const color = (hex: string) => (text: string) =>
  styleText(text, { fg: parseColor(hex) }, "truecolor");
const theme: StatusTheme = {
  accent: color("#8dd8df"),
  muted: color("#a0aaa6"),
  success: color("#9ddb9b"),
  warning: color("#edc17c"),
  error: color("#ee9293"),
  bold: (text) => styleText(text, { bold: true }, "truecolor"),
  selected: (text) =>
    styleText(text, { bg: parseColor("#284139") }, "truecolor"),
};
const columns: StatusColumn[] = [
  {
    id: "checks",
    title: "Recovery checks",
    status: { glyph: "◷", ascii: "?", label: "Review", tone: "warning" },
    summary: "Awaiting the restore budget decision.",
    focusId: "budget",
    counts: [
      { label: "open", value: 1, tone: "warning" },
      { label: "partial", value: 1, tone: "warning" },
      { label: "satisfied", value: 2, tone: "success" },
    ],
    groups: [
      {
        id: "gaps",
        label: "Needs attention",
        tone: "warning",
        items: [
          {
            id: "owner",
            label: "Recovery owner",
            status: conditionMark({ state: ConditionState.Open }),
            details:
              "The on-call team can investigate, but no recovery owner is assigned.",
          },
          {
            id: "budget",
            label: "Restore time budget",
            status: conditionMark({ state: ConditionState.Partial }),
            details:
              "Warm restore finished in three minutes. A timed cold restore is still missing.",
          },
        ],
      },
      {
        id: "confirmed",
        label: "Satisfied",
        collapsed: true,
        tone: "success",
        showStatusLabels: false,
        items: [
          {
            id: "backup",
            label: "Recoverable backup",
            status: conditionMark({ state: ConditionState.Satisfied }),
            details: "Archive 42 restored with all 218 checksums matching.",
          },
          {
            id: "scope",
            label: "Rehearsal boundary",
            status: conditionMark({ state: ConditionState.Satisfied }),
            details: "The operator confirmed an isolated recovery environment.",
          },
        ],
      },
    ],
  },
  {
    id: "tasks",
    title: "Recovery work",
    status: { glyph: "◐", ascii: "*", label: "Rehearsal", tone: "accent" },
    counts: [
      { label: "active", value: 1, tone: "accent" },
      { label: "blocked", value: 1, tone: "error" },
    ],
    groups: [
      {
        id: "prepare",
        label: "Wave 1",
        items: [
          {
            id: "restore",
            label: "Rehearse cold restore",
            summary: "JOB-8",
            status: { glyph: "◐", ascii: "*", label: "Active", tone: "accent" },
            details:
              "JOB-8 will measure the longest recovery path. Linked check: restore time budget.",
          },
        ],
      },
      {
        id: "review",
        label: "Wave 2",
        items: [
          {
            id: "publish",
            label: "Publish runbook",
            summary: "JOB-9",
            status: { glyph: "×", ascii: "!", label: "Blocked", tone: "error" },
            details: "JOB-9 depends on JOB-8 and naming the recovery owner.",
          },
        ],
      },
    ],
  },
];

const terminal = new ProcessTerminal();
const tui = new TuiAltScreen(terminal);
const editor = new Input({
  prompt: "> ",
  placeholder: "Type here while the dock is visible",
});
let expanded = false;
let overlay: OverlayHandle | undefined;
const close = () => {
  overlay?.hide();
  overlay = undefined;
  tui.setFocus(editor);
};
const makeBoard = () =>
  createStatusBoard({
    title: "Recovery rehearsal",
    columns,
    theme,
    height: () => Math.max(1, terminal.rows - 3),
    requestRender: () => {
      tui.requestRender();
    },
    onClose: close,
  });
const dock = {
  invalidate() {},
  render(width: number) {
    if (overlay !== undefined) return [];
    return renderStatusDock({ columns, theme, width, expanded });
  },
};
if (process.argv.includes("--render")) {
  const width = process.argv.includes("--narrow") ? 60 : 110;
  expanded = process.argv.includes("--expanded");
  const lines = process.argv.includes("--inspect")
    ? makeBoard().render(width)
    : dock.render(width);
  process.stdout.write(`${lines.join("\n")}\n`);
} else {
  tui.addChild(dock);
  tui.addChild({
    invalidate() {},
    render: () =>
      overlay === undefined
        ? [
            theme.muted(
              "Alt+s expand/collapse  ·  Ctrl+o inspect  ·  Ctrl+c quit",
            ),
          ]
        : [],
  });
  tui.addChild(editor);
  tui.setFocus(editor);
  tui.addInputListener((key) => {
    if (matchesKey(key, "ctrl+c") && overlay === undefined) {
      tui.stop();
      return { consume: true };
    }
    if (overlay !== undefined) return;
    if (matchesKey(key, "alt+s")) {
      expanded = !expanded;
      tui.requestRender();
      return { consume: true };
    }
    if (matchesKey(key, "ctrl+o")) {
      // A panel completes once. New inspection starts with fresh navigation.
      const inspector = makeBoard();
      overlay = tui.showOverlay(
        {
          ...inspector,
          render(width) {
            return inspector
              .render(width - 2)
              .map((line) =>
                styleText(
                  ` ${line}${" ".repeat(Math.max(1, width - 1 - visibleWidth(line)))}`,
                  { bg: parseColor("#14231e") },
                  "truecolor",
                ),
              );
          },
        },
        { width: "100%", anchor: "center" },
      );
      return { consume: true };
    }
    return;
  });
  tui.start();
}
