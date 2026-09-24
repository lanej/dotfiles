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
cp "$suite/check_size.sh" "$folder/"
# Fixture-local budgets. Copying the repo's own file coupled this detector to
# it: check_size.sh rejects a budget key it cannot `git ls-files`, so the first
# real override made every assertion below fail for the wrong reason.
printf '{}\n' > "$folder/size-budgets.json"
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
# A skill symlinked in from another checkout: oversize warns, never fails.
mkdir -p "$fixture/other/external"
awk 'BEGIN { for (i=0; i<600; i++) print "x" }' > "$fixture/other/external/SKILL.md"
ln -s "$fixture/other/external" claude/skills/external

printf '%031d\r\n' 0 >> "$skill"
awk 'BEGIN { for (i=0; i<501; i++) print "x" }' > AGENTS.md
ln -s "$repo/AGENTS.md" "$installed/CLAUDE.md"
git add AGENTS.md
command=(bash "$folder/check_size.sh" --base HEAD --installed-home "$fixture/home")
status=0
"${command[@]}" > "$fixture/result" 2>&1 || status=$?
if [[ $status -ne 1 ]]; then cat "$fixture/result"; exit 1; fi
grep -Fq 'FAIL AGENTS.md: 501 lines' "$fixture/result"
grep -Fq "FAIL installed $installed/CLAUDE.md: 501 lines" "$fixture/result"
grep -Fq "FAIL installed $installed/skills/example/SKILL.md: 491 lines, ~4051 tokens" "$fixture/result"
grep -Fq "WARN installed $installed/skills/external/SKILL.md: 600 lines" "$fixture/result"

# Restore the existing skill's size and trim both new instruction files.
head -n 490 "$skill" > "$fixture/trimmed"
mv "$fixture/trimmed" "$skill"
head -n 500 AGENTS.md > "$fixture/trimmed"
mv "$fixture/trimmed" AGENTS.md
"${command[@]}" > "$fixture/result" 2>&1 || { cat "$fixture/result"; exit 1; }

# An override raises the limit for the entrypoint it names, source and installed.
awk 'BEGIN { for (i=0; i<520; i++) printf "%031d\r\n", 0 }' > "$skill"
if "${command[@]}" > "$fixture/result" 2>&1; then
    echo 'Expected the oversize skill to fail without an override'; exit 1
fi
grep -Fq "FAIL $skill: 520 lines" "$fixture/result"
cat > "$folder/size-budgets.json" <<'JSON'
{"claude/skills/example/SKILL.md": {"max_lines": 600, "max_estimated_tokens": 5000, "reason": "fixture"}}
JSON
"${command[@]}" > "$fixture/result" 2>&1 || { cat "$fixture/result"; exit 1; }

echo 'PASS: source and installed instruction size budgets'
