#!/usr/bin/env bash
# One regression detector: trim source and installed instructions to budget.
set -euo pipefail

suite=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
fixture=$(mktemp -d)
trap 'rm -rf "$fixture"' EXIT
repo="$fixture/repo"
installed="$fixture/home/.claude"
folder="$repo/claude/evals/skill-maintenance"
mkdir -p "$folder" "$repo/claude/skills/example" "$installed"
cp "$suite/check_size.sh" "$suite/size-budgets.json" "$folder/"
cd "$repo"
git init -q
git config user.name Fixture
git config user.email fixture@example.invalid
git config core.autocrlf false
skill=claude/skills/example/SKILL.md
# CRLF must count: this existing skill is ~4043 tokens, below 500 lines.
awk 'BEGIN { for (i=0; i<490; i++) printf "%031d\r\n", 0 }' > "$skill"
git add "$skill"
git commit -qm baseline
ln -s "$repo/claude/skills" "$installed/skills"

printf '%031d\r\n' 0 >> "$skill"
awk 'BEGIN { for (i=0; i<501; i++) print "x" }' > AGENTS.md
cp AGENTS.md "$installed/CLAUDE.md"
git add AGENTS.md
command=(bash "$folder/check_size.sh" --base HEAD --installed-home "$fixture/home")
status=0
"${command[@]}" > "$fixture/result" 2>&1 || status=$?
if [[ $status -ne 1 ]]; then cat "$fixture/result"; exit 1; fi
grep -Fq 'FAIL AGENTS.md: 501 lines' "$fixture/result"
grep -Fq "FAIL installed $installed/CLAUDE.md: 501 lines" "$fixture/result"
grep -Fq "FAIL installed $installed/skills/example/SKILL.md: 491 lines, ~4051 tokens" "$fixture/result"

# Restore the existing skill's size and trim both new instruction files.
head -n 490 "$skill" > "$fixture/trimmed"
mv "$fixture/trimmed" "$skill"
head -n 500 AGENTS.md > "$fixture/trimmed"
mv "$fixture/trimmed" AGENTS.md
cp AGENTS.md "$installed/CLAUDE.md"
"${command[@]}" > "$fixture/result" 2>&1 || { cat "$fixture/result"; exit 1; }
echo 'PASS: source and installed instruction size budgets'
