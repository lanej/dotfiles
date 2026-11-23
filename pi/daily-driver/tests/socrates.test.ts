import assert from "node:assert/strict";
import { test } from "node:test";
import {
  DecisionDisposition,
  SpecStatus,
  preserveDecisions,
  specDraft,
  specRecord,
} from "../socrates/spec.ts";

const legacy = {
  objective: "Preserve the transcript",
  scope: ["Managed checkout"],
  requirements: [
    {
      id: "R1",
      outcome: "Keep the transcript",
      acceptance: "Open the archive",
    },
  ],
  decisions: [
    {
      decision: "Keep archives locally",
      basis: "decided",
      evidence: "Operator brief",
    },
  ],
  blockingQuestions: [],
};

await test("a frozen specification from the previous driver still loads unchanged", () => {
  const attempt = {
    status: SpecStatus.Frozen,
    version: 1,
    draft: legacy,
    acceptedRevision: "old",
    approvalAt: "2026-11-21T00:00:00.000Z",
  };
  assert.deepEqual(specRecord.parse(attempt), attempt);
});

await test("a settled decision can change through a linked successor", () => {
  const settled = specDraft.parse({
    ...legacy,
    decisions: [
      {
        ...legacy.decisions[0],
        id: "D1",
        disposition: DecisionDisposition.Resolved,
        uncertainty: "None",
      },
    ],
  });
  const first = settled.decisions[0];
  if (first === undefined) throw new Error("Missing fixture decision");
  assert.throws(() => {
    preserveDecisions(settled, {
      ...settled,
      decisions: [{ ...first, decision: "Delete archives" }],
    });
  }, /Preserve settled decision D1/u);
  const updated = specDraft.parse({
    ...settled,
    decisions: [
      { ...first, disposition: DecisionDisposition.Superseded },
      {
        ...first,
        id: "D2",
        supersedes: "D1",
        decision: "Keep archives in the workspace",
      },
    ],
  });
  preserveDecisions(settled, updated);
});
