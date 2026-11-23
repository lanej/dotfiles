import assert from "node:assert/strict";
import { test } from "bun:test";
import {
  stripTerminalSequences,
  visibleWidth,
  type MarkdownTheme,
} from "@earendil-works/pi-tui";
import { createSelector, type SelectorTheme } from "../index.ts";

const plain = (text: string) => text;
const markdown: MarkdownTheme = {
  heading: plain,
  link: plain,
  linkUrl: plain,
  code: plain,
  codeBlock: plain,
  codeBlockBorder: plain,
  quote: plain,
  quoteBorder: plain,
  hr: plain,
  listBullet: plain,
  bold: plain,
  italic: plain,
  strikethrough: plain,
  underline: plain,
};
const theme: SelectorTheme = {
  accent: plain,
  muted: plain,
  bold: plain,
  selected: plain,
  markdown,
};

test("a non-Socrates caller gets focus movement, hint jumps and explicit completion", () => {
  const selections: (number | undefined)[] = [];
  let renders = 0;
  const selector = createSelector({
    title: "Choose a deployment region",
    items: Array.from({ length: 14 }, (_, index) => ({
      label: `Region ${String(index)}`,
      description: "Deployment destination",
    })),
    theme,
    height: () => 24,
    requestRender: () => {
      renders += 1;
    },
    onSelect: (index) => {
      selections.push(index);
    },
  });
  const screen = () =>
    selector.render(80).map(stripTerminalSequences).join("\n");
  assert.match(screen(), /→ Region 0/);
  selector.handleInput("j");
  assert.match(screen(), /→ Region 1/);
  selector.handleInput("k");
  selector.handleInput(";");
  assert.match(screen(), /la Region 8/);
  selector.handleInput("l");
  assert.match(screen(), /la Region 8/);
  selector.handleInput("a");
  assert.match(screen(), /→ Region 8/);
  assert.deepEqual(selections, []);
  selector.handleInput("\r");
  selector.handleInput("\r");
  assert.deepEqual(selections, [8]);
  assert.ok(renders > 0);
});

test("detail recovery, resize and cancellation preserve the focused choice", () => {
  const selections: (number | undefined)[] = [];
  let height = 14;
  const selector = createSelector({
    title: "Choose a report",
    context: "Reports are read only.",
    items: [
      {
        label: "Daily",
        description: "Short report",
        details: "Daily explanation",
      },
      {
        label: "Monthly",
        description: "Long report",
        details: Array.from(
          { length: 20 },
          (_, i) => `Detail ${String(i)}`,
        ).join("\n\n"),
      },
    ],
    theme,
    height: () => height,
    requestRender() {},
    onSelect: (index) => {
      selections.push(index);
    },
  });
  selector.render(80);
  selector.handleInput("j");
  selector.handleInput("l");
  const first = selector.render(30);
  assert.match(first.join("\n"), /Detail 0/);
  selector.handleInput("j");
  assert.notDeepEqual(selector.render(30), first);
  selector.handleInput("\x1b");
  height = 8;
  const narrow = selector.render(30);
  assert.ok(narrow.length <= height);
  assert.ok(narrow.every((line) => visibleWidth(line) <= 30));
  assert.match(narrow.join("\n"), /→ Monthly/);
  selector.handleInput(";");
  selector.render(30);
  selector.handleInput("\x1b");
  assert.deepEqual(selections, []);
  selector.handleInput("\x1b");
  selector.handleInput("\r");
  assert.deepEqual(selections, [undefined]);
});

test("empty choices fail before opening an unusable component", () => {
  assert.throws(
    () =>
      createSelector({
        title: "Empty",
        items: [],
        theme,
        height: () => 10,
        requestRender() {},
        onSelect() {},
      }),
    /at least one item/,
  );
});
