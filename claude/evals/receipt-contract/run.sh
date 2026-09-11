#!/usr/bin/env bash
# Measures bytes returned by a sub-agent with vs without the receipt contract.
# Usage: run.sh <arm: plain|receipt> <trial> <outdir>
set -uo pipefail
ARM="$1"; T="$2"; OUT="$3"; mkdir -p "$OUT/$ARM"
REPO="$(git rev-parse --show-toplevel)"

TASKS=(
"Investigate how this dotfiles repo wires Claude Code configuration into the user's home directory. Cover the Makefile target, what gets symlinked, and the selective-versioning pattern."
"Investigate the delegation and sub-agent rules in this repo's Claude configuration. Cover when work is delegated, what a brief must contain, and the rules about forks."
"Investigate how this repo organizes skills. Cover where they live, their file structure, and how EP-specific skills are brought in."
)
CONTRACT='

OUTPUT CONTRACT — this overrides any default urge to explain your findings in the reply:
Write your full findings to '"$OUT"'/'"$ARM"'/findings-t'"$T"'-IDX.md
Then reply with AT MOST three lines, nothing else:
status: done|blocked
wrote: <path>
blockers: <one phrase or none>'

for i in "${!TASKS[@]}"; do
  p="${TASKS[$i]}"
  [ "$ARM" = "receipt" ] && p="$p${CONTRACT//IDX/$i}"
  # NOTE: --allowedTools is variadic; the prompt MUST come before it or it is
  # swallowed as a tool name and the call errors out returning zero bytes.
  o=$(cd "$REPO" && timeout 300 claude -p "$p" --model claude-haiku-4-5-20251001 \
        --permission-mode acceptEdits --allowedTools Read Grep Glob Write </dev/null 2>/dev/null)
  # Verify the claim, don't trust it: a receipt saying "wrote: X" is worthless
  # if X does not exist. Compliance is measured, not assumed.
  f="$OUT/$ARM/findings-t$T-$i.md"
  wrote=false; fsize=0
  [ -f "$f" ] && { wrote=true; fsize=$(wc -c <"$f"); }
  printf '%s' "$o" > "$OUT/$ARM/reply-t$T-$i.txt"
  echo "{\"arm\":\"$ARM\",\"trial\":$T,\"task\":$i,\"bytes\":${#o},\"wrote\":$wrote,\"fsize\":$fsize}" >> "$OUT/$ARM/t$T.jsonl"
done
