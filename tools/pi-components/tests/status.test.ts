import assert from "node:assert/strict";
import { test } from "bun:test";
import { stripTerminalSequences, visibleWidth } from "@earendil-works/pi-tui";
import {
  ActivityState,
  ConditionState,
  activityIndicator,
  conditionCounts,
  conditionStatus,
  conditionSummary,
  createConditionsPanel,
  type Condition,
  type StatusTheme,
} from "../index.ts";

const plain = (text: string) => text;
const theme: StatusTheme = {
  accent: plain,
  muted: plain,
  bold: plain,
  success: plain,
  warning: plain,
  error: plain,
  selected: (text) => `\x1b[7m${text}\x1b[0m`,
};

const checks: Condition[] = [
  {
    id: "backup",
    label: "Backup",
    state: ConditionState.Satisfied,
    summary: "Archive was restored.",
    details: "Archive 42 opened in recovery.",
  },
  {
    id: "owner",
    label: "Owner",
    state: ConditionState.Open,
    summary: "Choose the recovery owner.",
    details: "The operator has not assigned this responsibility.",
  },
  { id: "region", label: "Region", state: ConditionState.Unknown },
  {
    id: "legacy",
    label: "Old restore",
    state: ConditionState.Satisfied,
    stale: true,
    details: "An earlier archive restored correctly.",
  },
  {
    id: "billing",
    label: "Billing",
    state: ConditionState.NotApplicable,
    summary: "No billable resources in this operation.",
  },
];

test("property observations and activity remain independent, including stale and unknown observations", () => {
  assert.deepEqual(conditionCounts(checks), {
    total: 5,
    satisfied: 1,
    open: 1,
    unknown: 1,
    notApplicable: 1,
    stale: 1,
  });
  assert.match(
    conditionSummary(checks),
    /1 satisfied.*1 open.*1 not assessed.*1 to recheck.*1 not applicable/u,
  );
  assert.equal(conditionSummary([]), "No conditions supplied");
  assert.equal(conditionCounts([]).satisfied, 0);
  const open = checks[1];
  const stale = checks[3];
  assert.ok(open !== undefined && stale !== undefined);
  assert.match(conditionStatus(open, theme), /Open/u);
  assert.match(conditionStatus(stale, theme), /Recheck/u);
  const activity = {
    state: ActivityState.Working,
    label: "Restore check",
    focusId: "owner",
  };
  assert.notEqual(
    activityIndicator(activity, theme, { frame: 0 }),
    activityIndicator(activity, theme, { frame: 1 }),
  );
  assert.equal(
    activityIndicator(activity, theme, { frame: 0, reducedMotion: true }),
    activityIndicator(activity, theme, { frame: 1, reducedMotion: true }),
  );
  assert.equal(
    activityIndicator({ ...activity, state: ActivityState.Waiting }, theme, {
      frame: 0,
    }),
    activityIndicator({ ...activity, state: ActivityState.Waiting }, theme, {
      frame: 1,
    }),
  );
  assert.match(
    activityIndicator(activity, theme, { reducedMotion: true }),
    /Working/u,
  );
  assert.match(conditionStatus(open, theme), /Open/u);
  assert.equal(conditionCounts(checks).satisfied, 1);
});

test("snapshots preserve selection by identity, reject invalid replacements atomically and copy inputs", () => {
  const inputs = checks.map((condition) => ({ ...condition }));
  const panel = createConditionsPanel({
    title: "Recovery checks",
    conditions: inputs,
    theme,
    height: () => 20,
    requestRender() {},
  });
  panel.render(100);
  panel.handleInput("j");
  assert.equal(panel.selectedId(), "owner");
  panel.setActivity({
    state: ActivityState.Working,
    label: "Checking archive",
    focusId: "backup",
  });
  assert.equal(panel.selectedId(), "owner");
  assert.match(panel.render(100).join("\n"), /◆ Backup/u);
  const first = inputs[0];
  assert.ok(first !== undefined);
  first.label = "Mutated after delivery";
  assert.doesNotMatch(panel.render(100).join("\n"), /Mutated after delivery/u);
  panel.setConditions([...checks].reverse());
  assert.equal(panel.selectedId(), "owner");
  assert.throws(() => {
    panel.setConditions([first, first]);
  }, /distinct nonempty/u);
  assert.equal(panel.selectedId(), "owner");
  panel.setConditions(checks.filter(({ id }) => id !== "owner"));
  assert.ok(panel.selectedId() !== "owner");
  panel.setConditions([]);
  assert.equal(panel.selectedId(), undefined);
  assert.match(panel.render(100).join("\n"), /No conditions supplied/u);
});

test("narrow inspection exposes complete evidence and restores the selection after scrolling", () => {
  let height = 12;
  let completions = 0;
  const evidence = Array.from(
    { length: 30 },
    (_, index) => `Observation ${String(index)}: archive opened correctly.`,
  ).join("\n");
  const panel = createConditionsPanel({
    title: "Recovery checks",
    conditions: [
      ...checks,
      {
        id: "trace",
        label: "Restore trace",
        state: ConditionState.Open,
        details: evidence,
      },
    ],
    theme,
    height: () => height,
    requestRender() {},
    onClose() {
      completions++;
    },
  });
  panel.render(38);
  panel.handleInput("\x1b[F");
  assert.equal(panel.selectedId(), "trace");
  panel.handleInput("\r");
  assert.match(panel.render(38).join("\n"), /Observation 0/u);
  panel.handleInput("\x1b[F");
  assert.match(panel.render(38).join("\n"), /Observation 29/u);
  height = 8;
  panel.render(25);
  panel.handleInput("\x1b[F");
  assert.match(panel.render(25).join("\n"), /Observation 29/u);
  panel.handleInput("h");
  assert.equal(panel.selectedId(), "trace");
  assert.equal(completions, 0);
  panel.handleInput("\x1b");
  panel.handleInput("\x1b");
  assert.equal(completions, 1);
});

test("status text is safe and rendering respects terminal cells across small, wide and CJK allocations", () => {
  let height = 26;
  const panel = createConditionsPanel({
    title: "\x1b[2JRecovery",
    conditions: [
      ...checks,
      {
        id: "international",
        label: "地図 é 安全",
        state: ConditionState.Open,
        summary: "\x1b[2J確かめる\twrapped evidence",
        details: `\x1b]8;;https://example.invalid\x07Injected link\x1b]8;;\x07\n${"証拠 ".repeat(60)}`,
      },
    ],
    activity: {
      state: ActivityState.Waiting,
      label: "\x1b[2JAnswer needed",
      detail: "\x1b[2KReview the evidence",
    },
    theme,
    height: () => height,
    requestRender() {},
  });
  panel.handleInput("\x1b[F");
  for (const columns of [0, 1, 2, 4, 20, 38, 76, 100]) {
    for (const rows of [0, 1, 4, 12, 26]) {
      height = rows;
      for (const inspect of [false, true]) {
        panel.handleInput(inspect ? "l" : "h");
        const rendered = panel.render(columns);
        assert.ok(rendered.length <= rows);
        assert.ok(rendered.every((line) => visibleWidth(line) <= columns));
        for (const sequence of ["\x1b[2J", "\x1b[2K", "\x1b]8"])
          assert.ok(!rendered.join("\n").includes(sequence));
      }
    }
  }
});

test("ASCII and static presentations preserve semantic labels without requiring motion", () => {
  const panel = createConditionsPanel({
    title: "Recovery checks",
    conditions: checks,
    theme,
    height: () => 20,
    activity: {
      state: ActivityState.Paused,
      label: "Review later",
      focusId: "owner",
    },
    presentation: { ascii: true, reducedMotion: true },
    requestRender() {},
  });
  const rendered = panel.render(100).map(stripTerminalSequences).join("\n");
  assert.ok(
    Array.from(rendered).every(
      (character) => (character.codePointAt(0) ?? 0) <= 127,
    ),
  );
  assert.match(rendered, /Paused/u);
  assert.match(rendered, /Not assessed/u);
  assert.match(rendered, /Recheck/u);
});
