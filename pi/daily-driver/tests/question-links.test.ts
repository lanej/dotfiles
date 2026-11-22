import assert from "node:assert/strict";
import { test } from "node:test";
import {
  getOsc8LinkAtColumn,
  stripTerminalSequences,
  wrapTextWithAnsi,
} from "@earendil-works/pi-tui";
import { questionLink, questionLinks } from "../question-links.ts";

await test("question prose emits OSC 8 for labeled and bare links", () => {
  const rendered = questionLinks(
    "See [the brief](https://example.com/brief) or https://example.com/log.",
  );
  assert.equal(
    stripTerminalSequences(rendered),
    "See the brief or https://example.com/log.",
  );
  assert.equal(getOsc8LinkAtColumn(rendered, 4), "https://example.com/brief");
  assert.equal(getOsc8LinkAtColumn(rendered, 13), undefined);
  assert.equal(getOsc8LinkAtColumn(rendered, 17), "https://example.com/log");
  assert.equal(getOsc8LinkAtColumn(rendered, 40), undefined);
});

await test("evidence keeps its OSC 8 target across wrapped rows", () => {
  const url = "https://github.com/fixture/repo/issues/7";
  const rows = wrapTextWithAnsi(questionLink("Recovery procedure", url), 10);
  assert.equal(rows.length, 2);
  for (const row of rows) assert.equal(getOsc8LinkAtColumn(row, 0), url);
  assert.equal(questionLink("blocked", "file:///tmp/private"), "blocked");
});
