#!/usr/bin/env bash
# Measures bytes returned by a sub-agent with vs without the receipt contract.
# Usage: run.sh <arm: plain|receipt> <trial> <outdir>
set -euo pipefail
if [ "$#" -ne 3 ] || [[ ! "$1" =~ ^(plain|receipt)$ ]] || [[ ! "$2" =~ ^[0-9]+$ ]]; then
  echo 'Usage: run.sh <plain|receipt> <numeric-trial> <outdir>' >&2
  exit 2
fi
ARM="$1"; T="$2"; OUT="$3"
REPO="$(git rev-parse --show-toplevel)"
mkdir -p "$OUT/$ARM"
OUT="$(cd "$OUT" && pwd -P)"
# Reserve the trial, including failed attempts: never count a stale findings file.
mkdir "$OUT/$ARM/.trial-$T" || { echo 'Use a fresh trial number or output directory.' >&2; exit 2; }
if [ -e "$OUT/$ARM/t$T.jsonl" ] || compgen -G "$OUT/$ARM/*-t$T-*.md" >/dev/null; then
  echo 'Existing trial artifacts would contaminate this measurement.' >&2
  exit 2
fi

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
  reply="$OUT/$ARM/reply-t$T-$i.txt"
  errors="$OUT/$ARM/stderr-t$T-$i.txt"
  if (cd "$REPO" && timeout 300 claude -p "$p" --model claude-haiku-4-5-20251001 \
        --permission-mode acceptEdits --allowedTools Read Grep Glob Write </dev/null >"$reply" 2>"$errors"); then
    [ -s "$reply" ] || { echo "Empty reply for task $i; see $errors" >&2; exit 1; }
  else
    rc=$?
    echo "Claude failed for task $i (exit $rc); see $errors" >&2
    exit "$rc"
  fi
  # Verify the claim, don't trust it: a receipt saying "wrote: X" is worthless
  # if X does not exist. Compliance is measured, not assumed.
  f="$OUT/$ARM/findings-t$T-$i.md"
  wrote=false; fsize=0
  [ -f "$f" ] && { wrote=true; fsize=$(wc -c <"$f"); }
  if [ "$ARM" = receipt ]; then
    expected=$(printf 'status: done\nwrote: %s\nblockers: none' "$f")
    if [ ! -s "$f" ] || [ "$(cat "$reply")" != "$expected" ]; then
      echo "Receipt contract failed for task $i; inspect $reply and $f" >&2
      exit 1
    fi
  fi
  bytes=$(wc -c <"$reply")
  printf '{"arm":"%s","trial":%d,"task":%d,"bytes":%d,"wrote":%s,"fsize":%d}\n' \
    "$ARM" "$((10#$T))" "$i" "$bytes" "$wrote" "$fsize" >> "$OUT/$ARM/t$T.jsonl"
done
