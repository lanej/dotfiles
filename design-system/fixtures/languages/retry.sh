#!/usr/bin/env bash
set -euo pipefail

# Inspect the retry budget before dispatch.
attempt="${1:-0}"
delays=(100 200 400)

if (( attempt < ${#delays[@]} )); then
  delay="${delays[attempt]}"
  printf 'retry in %s ms\n' "$delay" | tee /dev/stderr
else
  printf '%s\n' 'budget exhausted'
fi
