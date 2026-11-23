export const dispatchGate = {
  enabled: false,
  evaluatedVersion: "1.3.4",
  atomicClaim: true,
  staleOwnerRejected: true,
  repeatedClaimReconciled: true,
  cliOwnerStatusGuardsFenceBrief: false,
  reason:
    "Local coding runs use pi-driver start and the Beads HTTP revision guard. Fleet dispatch, replacement workers and automatic cleanup require separate lifecycle support.",
  contract: "https://github.com/lanej/dotfiles/issues/353",
} as const;

export function requireDispatch(): never {
  throw new Error(
    `${dispatchGate.reason} Inspect the original attempt with pi-driver tasks ID --json before recovery.`,
  );
}
