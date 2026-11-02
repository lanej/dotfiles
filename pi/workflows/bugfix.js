// Run through pi-subagents' public workflow API. The parent owns intake and finish.
for (const name of ['task', 'verifyCommand', 'workerModel', 'reviewerModel']) {
  if (typeof args[name] !== 'string' || !args[name].trim()) {
    throw new Error(name + ' must be an explicit, nonempty string');
  }
}
if (args.task.length > 16000 || args.verifyCommand.length > 4000) {
  throw new Error('The task or verification command is too large');
}
const timeoutMs = args.timeoutMs ?? 300000;
if (!Number.isSafeInteger(timeoutMs) || timeoutMs < 1000 || timeoutMs > 3600000) {
  throw new Error('timeoutMs must be an integer between 1000 and 3600000');
}
const build = await runs.run('build', {
  agent: 'worker',
  model: args.workerModel,
  task: args.task + '\n\nWork only in the assigned checkout. Follow applicable AGENTS.md files. '
    + 'Run the required verification command: ' + args.verifyCommand + '. '
    + 'Leave the patch unstaged and uncommitted. Do not publish, merge, or finish the task.',
  context: 'fresh',
  worktree: true,
  timeoutMs,
  acceptance: {
    level: 'verified',
    evidence: ['changed-files', 'commands-run', 'no-staged-files'],
    verify: [{ id: 'required', command: args.verifyCommand, timeoutMs }],
    // Review is the separate fresh child below; this gate establishes test evidence.
    review: false,
  },
});
if (!build.ok) throw new Error('Implementation or required verification failed: ' + (build.error ?? build.output));
const acceptance = build.results?.[0]?.acceptance;
if (acceptance?.evidenceStatus !== 'verified'
    || !acceptance.verifyRuns?.some(check => check.id === 'required'
      && check.command === args.verifyCommand && check.status === 'passed' && check.exitCode === 0)) {
  throw new Error('The implementation has no successful host verification evidence');
}
const handoff = {
  runId: build.runId,
  artifactPaths: build.artifactPaths,
  output: build.output,
  acceptance,
};
const review = await runs.run('review', {
  agent: 'reviewer',
  model: args.reviewerModel,
  context: 'fresh',
  worktree: false,
  timeoutMs,
  task: 'Independently review this proposed bug fix.\n\nTask:\n' + args.task
    + '\n\nBuilder handoff:\n' + JSON.stringify(handoff)
    + '\n\nRead the handoff manifest and its captured patch from these artifacts, then read relevant '
    + 'source and instructions. The source checkout remains at the original base: a clean git diff '
    + 'there is not evidence of an empty proposal. Review the captured change. '
    + 'Use only read tools. Do not edit, run commands, or claim you ran tests. '
    + 'The required command was run by the host; inspect its recorded acceptance evidence. '
    + 'Return the exact builder runId as reviewedRunId, a verdict, and a Markdown review. '
    + 'Use inconclusive if the patch, base, or evidence cannot be assessed.',
  outputSchema: {
    type: 'object',
    properties: {
      reviewedRunId: { type: 'string' },
      verdict: { type: 'string', enum: ['approve', 'changes_requested', 'inconclusive'] },
      review: { type: 'string', minLength: 1 },
    },
    required: ['reviewedRunId', 'verdict', 'review'],
    additionalProperties: false,
  },
});
if (!review.ok) throw new Error('Independent review failed: ' + (review.error ?? review.output));
const verdict = review.structuredOutput;
if (!verdict || verdict.reviewedRunId !== build.runId) {
  throw new Error('The review is not bound to this builder run');
}
return {
  status: verdict.verdict === 'approve' ? 'ready_for_integration' : verdict.verdict,
  handoff,
  review: { runId: review.runId, ...verdict },
  // Parent must check the handoff base, apply the patch, rerun checks, and obey finish policy.
  finished: false,
};
