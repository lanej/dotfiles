import assert from "node:assert/strict";
import { test } from "node:test";
import { questionHints } from "../tui/question-selector.ts";

await test("small question menus use single-key hints", () => {
  assert.deepEqual(questionHints(3), ["a", "s", "d"]);
  assert.ok(questionHints(5).every((hint) => hint.length === 1));
});

await test("a larger visible menu reserves a prefix without shadowing any hint", () => {
  const hints = questionHints(12);
  assert.equal(new Set(hints).size, 12);
  assert.ok(
    hints.every((hint) =>
      hints.every((other) => other === hint || !other.startsWith(hint)),
    ),
  );
  assert.ok(hints.filter((hint) => hint.startsWith("l")).length > 1);
});
