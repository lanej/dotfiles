import assert from "node:assert/strict";
import { test } from "node:test";
import type { ThemeColor } from "@earendil-works/pi-coding-agent";
import { visibleWidth } from "@earendil-works/pi-tui";
import {
  diagnosticRows,
  type DiagnosticSnapshot,
} from "../code-intelligence/diagnostics.ts";
const plain = {
  fg: (_tone: ThemeColor, value: string) => value,
  bold: (value: string) => value,
};
await test("inline diagnostics distinguish pending and reported results, wrap, and expand", () => {
  const value: DiagnosticSnapshot = {
    path: "/project/retry.ts",
    state: "received",
    freshness: "unversioned",
    total: 3,
    diagnostics: [
      {
        line: 3,
        column: 1,
        severity: "warning",
        message: "Unused value",
        code: 6133,
        source: "ts",
      },
      {
        line: 7,
        column: 3,
        severity: "error",
        message: "Type 'string' is not assignable to type 'number'.",
        code: 2322,
        source: "ts",
      },
      {
        line: 8,
        column: 3,
        severity: "error",
        message: "Invalid value\x1b[31m",
        code: 2322,
        source: "ts",
      },
    ],
  };
  const narrow = diagnosticRows(value, plain, 30, false);
  assert.ok(narrow.every((row) => visibleWidth(row) <= 30));
  const text = narrow.join("\n");
  assert.match(text, /E 7:3/u);
  assert.doesNotMatch(text, /W 3:1/u);
  assert.match(text, /1 more diagnostics/u);
  assert.equal(text.includes("\x1b"), false);
  assert.match(
    diagnosticRows(value, plain, 100, true).join("\n"),
    /W 3:1.*Unused value/u,
  );
  assert.match(text, /document version/u);
  assert.match(
    diagnosticRows(
      { path: value.path, state: "pending", diagnostics: [] },
      plain,
      100,
      false,
    ).join("\n"),
    /checking/u,
  );
  const empty = diagnosticRows(
    { path: value.path, state: "received", total: 0, diagnostics: [] },
    plain,
    100,
    false,
  ).join("\n");
  assert.match(empty, /no errors or warnings reported/u);
  assert.doesNotMatch(empty, /project clean/u);
});
