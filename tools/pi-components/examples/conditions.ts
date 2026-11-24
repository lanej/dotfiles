import {
  ProcessTerminal,
  TuiAltScreen,
  parseColor,
  styleText,
} from "@earendil-works/pi-tui";
import {
  ActivityState,
  ConditionState,
  createConditionsPanel,
  type Condition,
  type StatusTheme,
} from "../index.ts";

const color = (hex: string) => (text: string) =>
  styleText(text, { fg: parseColor(hex) }, "truecolor");
const theme: StatusTheme = {
  accent: color("#9adbc1"),
  muted: color("#9aa8a1"),
  success: color("#a2d9a3"),
  warning: color("#eac486"),
  error: color("#ef9a9a"),
  bold: (text) => styleText(text, { bold: true }, "truecolor"),
  selected: (text) =>
    styleText(text, { bg: parseColor("#253c32") }, "truecolor"),
};
const conditions: Condition[] = [
  {
    id: "backup",
    label: "Recoverable backup",
    state: ConditionState.Satisfied,
    summary:
      "The latest archive restored in the isolated recovery environment.",
    details:
      "Evidence: archive-42 restore log; 218 records read back with matching checksums.",
  },
  {
    id: "owner",
    label: "Recovery owner",
    state: ConditionState.Open,
    summary: "The operator must choose who can initiate a restore.",
    details:
      "The on-call engineer can observe failures. Authority to restore production data has not been assigned.",
  },
  {
    id: "latency",
    label: "Restore time",
    state: ConditionState.Unknown,
    summary: "No timed recovery has been recorded.",
  },
  {
    id: "retention",
    label: "Retention boundary",
    state: ConditionState.Satisfied,
    stale: true,
    summary: "The retention policy changed after this assessment.",
    details:
      "Previous evidence: 30-day retention was agreed. A new 7-day limit requires a fresh check.",
  },
  {
    id: "billing",
    label: "Billing approval",
    state: ConditionState.NotApplicable,
    summary: "This rehearsal uses existing local resources.",
  },
];

const terminal = new ProcessTerminal();
const tui = new TuiAltScreen(terminal);
const still = process.argv.includes("--still");
const renderOnly = process.argv.includes("--render");
let timer: ReturnType<typeof setInterval> | undefined;
const panel = createConditionsPanel({
  title: "Recovery readiness",
  conditions,
  activity: {
    state: ActivityState.Working,
    label: "Checking recovery ownership",
    focusId: "owner",
    detail: "Reading the on-call escalation policy.",
  },
  theme,
  height: () => (renderOnly ? 19 : terminal.rows - 1),
  presentation: {
    reducedMotion: still,
    ascii: process.argv.includes("--ascii"),
  },
  requestRender: () => {
    tui.requestRender();
  },
  onClose() {
    clearInterval(timer);
    tui.stop();
  },
});
if (renderOnly) {
  process.stdout.write(`${panel.render(100).join("\n")}\n`);
} else {
  tui.addChild(panel);
  tui.setFocus(panel);
  tui.start();
  if (!still) {
    let frame = 0;
    timer = setInterval(() => {
      panel.setFrame(frame++);
    }, 100);
  }
}
