#!/usr/bin/env bash
# A/B eval: does the /handoff vs /delegate rewrite improve routing discrimination?
# Usage: run.sh <arm: old|new> <trial-n> <outdir>
set -uo pipefail
ARM="$1"; TRIAL="$2"; OUT="$3"
REPO="$(git rev-parse --show-toplevel)"
D="$OUT/$ARM"; mkdir -p "$D"

if [ "$ARM" = "old" ]; then
  H=$(git -C "$REPO" show d1206a2~1:claude/commands/handoff.md)
  G=$(git -C "$REPO" show d1206a2~1:claude/commands/delegate.md)
else
  H=$(cat "$REPO/claude/commands/handoff.md")
  G=$(cat "$REPO/claude/commands/delegate.md")
fi

run_one() {
  local id="$1" s="$2"
  local ans
  ans=$(timeout 180 claude -p --model claude-haiku-4-5-20251001 "$(cat <<PROMPT
You are routing a decision using ONLY the two reference documents below.

<doc name="handoff.md">
$H
</doc>

<doc name="delegate.md">
$G
</doc>

SITUATION: $s

Which action should be taken? Answer with EXACTLY ONE of these tokens and nothing else:
HANDOFF   - invoke /handoff, pushing the remaining task out of a spent session
DELEGATE  - dispatch a sub-agent for a sub-task while continuing to drive the session
SELF      - just do it yourself, no sub-agent
ASK       - stop and get clarification from the user first
MANUAL    - context is spent but no transcript exists, so write the brief by hand

Answer:
PROMPT
)" </dev/null 2>/dev/null | tr -d '[:space:]' | grep -oE 'HANDOFF|DELEGATE|SELF|ASK|MANUAL' | head -1)
  echo "{\"arm\":\"$ARM\",\"trial\":$TRIAL,\"id\":\"$id\",\"got\":\"${ans:-PARSE_FAIL}\"}" >> "$D/t$TRIAL.jsonl"
}
export -f run_one; export H G ARM TRIAL D

jq -c . "$REPO/claude/evals/handoff-delegate/scenarios.jsonl" \
  | jq -r '[.id,.s]|@tsv' \
  | while IFS=$'\t' read -r id s; do printf '%s\t%s\n' "$id" "$s"; done \
  | xargs -P 4 -I{} bash -c 'IFS=$'"'"'\t'"'"' read -r id s <<< "{}"; run_one "$id" "$s"'
