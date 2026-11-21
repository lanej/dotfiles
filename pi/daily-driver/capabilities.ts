export const dispatchGate = {
  enabled: false,
  evaluatedVersion: "1.3.4",
  atomicClaim: true,
  staleOwnerRejected: true,
  repeatedClaimReconciled: true,
  staleAcceptedScopeRejected: false,
  reason:
    "Beads 1.3.4 owner/status guards allow an old attempt to close a task after its brief changes. A demonstrated per-task revision guard is required before managed launch, coding delegation, acceptance, or automatic cleanup can be enabled.",
  contract: "https://github.com/lanej/dotfiles/issues/353",
} as const;

export function requireDispatch(): never {
  throw new Error(
    `${dispatchGate.reason} Run npm run test:beads-native for the isolated capability probe. No task claim, worktree allocation, or Pi process was started.`,
  );
}
