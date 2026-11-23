import assert from "node:assert/strict";
import { test } from "node:test";
import {
  getOsc8LinkAtColumn,
  stripTerminalSequences,
  wrapTextWithAnsi,
} from "@earendil-works/pi-tui";
import { questionEvidence } from "../socrates/evidence.ts";
import {
  questionLink,
  questionLinks,
  renderQuestionEvidence,
} from "../socrates/links.ts";

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

await test("source references link to the managed worktree and retain the line", () => {
  const rendered = renderQuestionEvidence(
    { label: "Parser", path: "src/input parser.ts", line: 12 },
    "/workspace/task",
  );
  assert.equal(
    stripTerminalSequences(rendered),
    "Parser · src/input parser.ts:12",
  );
  assert.equal(
    getOsc8LinkAtColumn(rendered, 0),
    "file:///workspace/task/src/input%20parser.ts#L12",
  );
  for (const path of ["../main.ts", "/etc/hosts", ".git/config"]) {
    assert.equal(
      questionEvidence.safeParse([{ label: "Source", path }]).success,
      false,
    );
  }
});

await test("observations and existing web links are both valid evidence", () => {
  const items = [
    { label: "Verifier", observation: "exit status 7" },
    { label: "Issue", url: "https://example.com/issue" },
  ];
  assert.deepEqual(questionEvidence.parse(items), items);
  const rendered = renderQuestionEvidence(
    { label: "Verifier", observation: "exit status 7" },
    "/workspace",
  );
  assert.equal(rendered, "Verifier\nexit status 7");
  assert.equal(getOsc8LinkAtColumn(rendered, 0), undefined);
});
