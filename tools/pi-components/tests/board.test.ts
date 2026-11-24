import assert from "node:assert/strict";
import { test } from "bun:test";
import { visibleWidth } from "@earendil-works/pi-tui";
import {
  createStatusBoard,
  renderStatusDock,
  conditionMark,
  ConditionState,
  renderStatusCounts,
  type StatusColumn,
  type StatusTheme,
} from "../index.ts";

const plain = (value: string) => value;
const theme: StatusTheme = {
  accent: plain,
  muted: plain,
  bold: plain,
  selected: plain,
  warning: plain,
  success: plain,
  error: plain,
};
const left: StatusColumn = {
  id: "checks",
  title: "Recovery checks",
  status: { label: "Review", glyph: "◐", tone: "warning" },
  counts: [
    { label: "partial", value: 1, tone: "warning" },
    { label: "satisfied", value: 4, tone: "success" },
  ],
  focusId: "timing",
  groups: [
    {
      id: "attention",
      label: "Needs attention",
      items: [
        {
          id: "timing",
          label: "Restore time budget",
          status: conditionMark({ state: ConditionState.Partial }),
          details: "Warm restore passed; cold restore has no timing sample.",
        },
      ],
    },
    {
      id: "done",
      label: "Satisfied",
      collapsed: true,
      showStatusLabels: false,
      tone: "success",
      items: Array.from({ length: 4 }, (_, i) => ({
        id: `restore-${String(i)}`,
        label: `Restored archive ${String(i)}`,
        status: conditionMark({ state: ConditionState.Satisfied }),
        details: `Verified checksum ${String(i)}.`,
      })),
    },
  ],
};
const right: StatusColumn = {
  id: "work",
  title: "Recovery work",
  status: { label: "Proposed", glyph: "◇", tone: "muted" },
  counts: [{ label: "planned", value: 2, tone: "muted" }],
  groups: [
    {
      id: "first",
      label: "Wave 1",
      items: [
        {
          id: "check",
          label: "Inspect archive",
          summary: "R1",
          status: { label: "Blocked", glyph: "×", tone: "error" },
          details: "Blocked by missing archive.",
        },
        {
          id: "restore",
          label: "Rehearse restore",
          status: { label: "Open", glyph: "○", tone: "accent" },
          details: "Read the package and restore safely.",
        },
      ],
    },
  ],
};

const parts = [left, right];
const screen = (lines: string[]) => lines.join("\n");

test("passive dock keeps both phases visible at compact heights; expansion reserves space for folded work", () => {
  for (const width of [60, 100]) {
    const compact = renderStatusDock({
      columns: parts,
      width,
      expanded: false,
      theme,
    });
    assert.ok(compact.length <= 3);
    assert.match(screen(compact), /Recovery checks.*Review/u);
    assert.match(screen(compact), /Recovery work.*Proposed/u);
    assert.doesNotMatch(screen(compact), /Restored archive 0|Needs attention/u);
    const expanded = renderStatusDock({
      columns: parts,
      width,
      expanded: true,
      theme,
    });
    assert.ok(expanded.length <= 8);
    assert.match(screen(expanded), /◐ Restore time/u);
    assert.match(screen(expanded), /▸ Satisfied 4/u);
    assert.doesNotMatch(screen(expanded), /Restored archive 0/u);
    assert.ok(
      [...compact, ...expanded].every((line) => visibleWidth(line) <= width),
    );
  }
  const branded: StatusTheme = {
    ...theme,
    success: (text) => `[success:${text}]`,
    warning: (text) => `[warning:${text}]`,
  };
  assert.match(
    renderStatusCounts(left.counts ?? [], branded),
    /\[warning:1 partial\].*\[success:4 satisfied\]/u,
  );
});

test("folds and the two independent selections survive reordering and resize; Enter inspects evidence", () => {
  const board = createStatusBoard({
    title: "Recovery",
    columns: parts,
    theme,
    height: () => 15,
    requestRender() {},
  });
  assert.equal(board.selection()?.itemId, "timing");
  assert.match(screen(board.render(100)), /› ◐ Restore time budget ◆/u);
  board.handleInput("j");
  assert.equal(board.selection()?.groupId, "done");
  assert.match(screen(board.render(100)), /› ▸ Satisfied 4/u);
  board.handleInput("\r");
  board.handleInput("j");
  assert.equal(board.selection()?.itemId, "restore-0");
  assert.match(screen(board.render(100)), /› ● Restored archive 0/u);
  board.handleInput("\t");
  board.handleInput("j");
  assert.equal(board.selection()?.itemId, "restore");
  const list = screen(board.render(60));
  assert.match(list, /Recovery checks.*Review/u);
  assert.match(list, /Recovery work.*Proposed/u);
  assert.doesNotMatch(list, /Restored archive/u);
  board.handleInput("\r");
  assert.match(
    screen(board.render(60)),
    /Read the package and restore safely/u,
  );
  board.handleInput("h");
  board.handleInput("h");
  assert.equal(board.selection()?.itemId, "restore-0");
  board.setColumns([...parts].reverse());
  assert.equal(board.selection()?.itemId, "restore-0");
  assert.match(screen(board.render(100)), /▾ Satisfied 4/u);
  assert.throws(() => {
    board.setColumns([left, left]);
  }, /distinct/u);
  assert.equal(board.selection()?.itemId, "restore-0");
  board.handleInput("\r");
  board.setColumns([right]);
  assert.equal(board.selection()?.columnId, "work");
  assert.doesNotMatch(screen(board.render(100)), /Verified checksum/u);
});

test("empty and narrow views preserve native bounds with wide text and large rows", () => {
  const long = {
    ...right,
    title: "復旧作業",
    groups: [
      {
        id: "items",
        label: "項目",
        items: [
          {
            id: "a",
            label: "長い項目 ".repeat(30),
            summary: "R1 ".repeat(76),
            status: { glyph: "◐", label: "Partial", tone: "warning" as const },
            details: "Details\n".repeat(150),
          },
        ],
      },
    ],
  };
  let height = 6;
  const board = createStatusBoard({
    title: "状態",
    columns: [left, long],
    theme,
    height: () => height,
    requestRender() {},
  });
  board.handleInput("\t");
  for (const width of [0, 1, 12, 60, 110])
    for (const count of [0, 1, 6, 18]) {
      height = count;
      const dock = renderStatusDock({
        columns: [left, long],
        width,
        maxRows: count,
        expanded: true,
        theme,
      });
      for (const input of ["\r", "\x1b"]) {
        board.handleInput(input);
        const lines = board.render(width);
        for (const view of [lines, dock]) {
          assert.ok(view.length <= count);
          assert.ok(view.every((line) => visibleWidth(line) <= width));
        }
      }
    }
});
