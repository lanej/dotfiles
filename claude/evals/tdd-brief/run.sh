#!/usr/bin/env bash
# Ablation: does "write tests first" in an Agent brief change sub-agent behavior?
# Usage: run.sh <arm: omit|state> <trial> <outdir>
# See DESIGN.md — the decision rule is pre-registered there, not here.
set -euo pipefail
if [ "$#" -ne 3 ] || [[ ! "$1" =~ ^(omit|state)$ ]] || [[ ! "$2" =~ ^[0-9]+$ ]]; then
  echo 'Usage: run.sh <omit|state> <numeric-trial> <outdir>' >&2
  exit 2
fi
ARM="$1"; T="$2"; OUT="$3"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
mkdir -p "$OUT/$ARM"
OUT="$(cd "$OUT" && pwd -P)"
# Reserve the trial, failed attempts included: never let a stale run be counted.
mkdir "$OUT/$ARM/.trial-$T" || { echo 'Use a fresh trial number or output directory.' >&2; exit 2; }
if [ -e "$OUT/$ARM/t$T.jsonl" ]; then
  echo 'Existing trial artifacts would contaminate this measurement.' >&2
  exit 2
fi

# Four implementation tasks. Deliberately unambiguous: the outcome measured is
# the ORDER of writes, so task difficulty must not be the confound.
SUBPROBLEMS=(
"Add a slugify(text) function to textkit/core.py. It lowercases, replaces each run of non-alphanumeric characters with a single hyphen, and strips leading and trailing hyphens."
"Add a truncate(text, limit) function to textkit/core.py. It returns text unchanged when len(text) <= limit, otherwise the first limit-1 characters followed by a single U+2026 ellipsis."
"Add a word_count(text) function to textkit/core.py. It returns the number of whitespace-separated words, and 0 for empty or whitespace-only input."
"Add a dedupe_spaces(text) function to textkit/core.py. It collapses every run of whitespace to a single space and strips leading and trailing whitespace."
)

for i in "${!SUBPROBLEMS[@]}"; do
  work="$OUT/$ARM/work-t$T-$i"
  home="$OUT/$ARM/home-t$T-$i"
  rm -rf "$work" "$home"
  cp -R "$HERE/fixture" "$work"
  # Empty HOME: no global CLAUDE.md, no user settings. The brief must be the
  # only instructional difference between the two arms.
  mkdir -p "$home/.claude"

  success="The new function behaves as described and \`python -m pytest\` passes in the package directory."
  [ "$ARM" = "state" ] && success="Write tests first. $success"

  prompt="Context: You are working in the Python package at $work. It is a small string-helper library with an existing test suite run by \`python -m pytest\`.
Domain: Python library code.
Sub-problem: ${SUBPROBLEMS[$i]}
Success: $success
Constraints: Do not modify existing functions or existing tests. Do not create files outside $work. Use Write or Edit for file changes and Read/Grep/Glob for inspection. Bash is only for python -m pytest (optionally with -q or -v); other shell commands make the measurement unclassifiable.
Output format: Reply with one line naming the files you changed."

  events="$OUT/$ARM/events-t$T-$i.jsonl"
  errors="$OUT/$ARM/stderr-t$T-$i.txt"
  # NOTE: --allowedTools is variadic; the prompt MUST precede it or it is
  # swallowed as a tool name and the call returns nothing.
  if (cd "$work" && HOME="$home" timeout 600 claude -p "$prompt" \
        --output-format stream-json --verbose \
        --permission-mode acceptEdits \
        --allowedTools Read Write Edit Grep Glob Bash </dev/null >"$events" 2>"$errors"); then
    [ -s "$events" ] || { echo "Empty event stream for task $i; see $errors" >&2; exit 1; }
  else
    rc=$?
    echo "Claude failed for task $i (exit $rc); see $errors" >&2
    exit "$rc"
  fi

  record="$(python3 "$HERE/classify.py" --events "$events" --root "$work" \
    --arm "$ARM" --trial "$((10#$T))" --task "$i")"
  printf '%s\n' "$record" >> "$OUT/$ARM/t$T.jsonl"
done
