#!/usr/bin/env bash
# Instruction budgets: physical lines and ceil(bytes / 4), not tokenizer counts.
set -euo pipefail
export LC_ALL=C

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
config="$root/claude/evals/skill-maintenance/size-budgets.json"
base= installed_home=
while (($#)); do
    case $1 in
        --base) base=$2; shift 2 ;;
        --installed-home) installed_home=$2; shift 2 ;;
        -h|--help) echo "Usage: $0 --base REF [--installed-home DIR]"; exit 0 ;;
        *) echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done
: "${base:?Use --base REF to select the comparison commit}"
[[ -z $installed_home || $installed_home = /* ]] || installed_home="$PWD/$installed_home"
installed_home=${installed_home%/}
cd "$root"
base=$(git rev-parse --verify "$base^{commit}")
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT

is_entrypoint() {
    case ${1##*/} in SKILL.md|AGENTS.md|CLAUDE.md|GEMINI.md) return 0 ;; esac
    case $1 in claude/CONSTITUTION.md|claude/commands/*.md|claude/agents/*.md) return 0 ;; esac
    return 1
}

# jq is already used by setup; retain the existing reviewed JSON overrides.
jq -e 'type == "object" and all(to_entries[]; .value |
    type == "object" and
    ((keys - ["max_lines", "max_estimated_tokens", "reason"]) | length == 0) and
    (. == {} or (.reason | type == "string" and test("\\S"))) and
    all(to_entries[] | select(.key != "reason");
        .value | type == "number" and . > 0 and . == floor))' "$config" >/dev/null
jq -j 'keys[] | ., "\u0000"' "$config" > "$scratch/overrides"
while IFS= read -r -d '' name; do
    if ! is_entrypoint "$name" || ! git --literal-pathspecs ls-files --error-unmatch -- "$name" >/dev/null; then
        echo "Invalid budget entrypoint: $name" >&2; exit 1
    fi
done < "$scratch/overrides"

measure() {
    read -r lines bytes < <(wc -l -c < "$1")
    # wc counts newlines; include an unterminated final line too.
    if [[ -s $1 && $(tail -c 1 "$1" | wc -l) -eq 0 ]]; then lines=$((lines + 1)); fi
    tokens=$(((bytes + 3) / 4))
}

failed=0 count=0
check_file() {
    local name=$1 path=$2 label=$3 budget_lines budget_tokens current_lines current_tokens
    local old_lines=0 old_tokens=0 limit_lines limit_tokens status=EXISTING
    count=$((count + 1))
    if [[ ! -f $path || ! -r $path ]]; then
        echo "FAIL $label: missing or unreadable instruction"; failed=1; return
    fi
    read -r budget_lines budget_tokens < <(jq -r --arg name "$name" '
        .[$name] // {} | [.max_lines // 500, .max_estimated_tokens // 4000] | @tsv' "$config")
    measure "$path"
    current_lines=$lines current_tokens=$tokens
    # A Git symlink blob is a path, not the previous instruction text.
    if [[ $(git --literal-pathspecs ls-tree "$base" -- "$name") = 100* ]]; then
        git show "$base:$name" > "$scratch/base"
        measure "$scratch/base"
        old_lines=$lines old_tokens=$tokens
    fi
    limit_lines=$((old_lines > budget_lines ? old_lines : budget_lines))
    limit_tokens=$((old_tokens > budget_tokens ? old_tokens : budget_tokens))
    if ((current_lines > limit_lines || current_tokens > limit_tokens)); then status=FAIL; failed=1; fi
    if ((current_lines > budget_lines || current_tokens > budget_tokens)); then
        echo "$status $label: $current_lines lines, ~$current_tokens tokens; allowed $limit_lines / ~$limit_tokens"
    fi
}

git ls-files -z > "$scratch/sources"
while IFS= read -r -d '' name; do
    is_entrypoint "$name" || continue
    [[ -f $name && ! -L $name ]] || continue
    check_file "$name" "$name" "$name"
done < "$scratch/sources"
echo "Checked $count source entrypoints."

if [[ -n $installed_home ]]; then
    count=0
    : > "$scratch/installed"
    # Instruction destinations linked by Makefile, including local additions.
    for name in claude/CLAUDE.md claude/CONSTITUTION.md claude/commands claude/agents claude/skills gemini/skills; do
        path="$installed_home/.$name"
        if [[ -L $path && ! -e $path ]]; then
            check_file "$name" "$path" "installed $path"
        elif [[ -e $path ]]; then
            find -L "$path" \( -type f -o -type l \) -print0 >> "$scratch/installed" || failed=1
        fi
    done
    while IFS= read -r -d '' path; do
        name=${path#"$installed_home/."}
        is_entrypoint "$name" || continue
        check_file "$name" "$path" "installed $path"
    done < "$scratch/installed"
    echo "Checked $count installed entrypoints."
fi
echo "Token estimates use ceil(UTF-8 bytes / 4), not the Claude tokenizer."
exit "$failed"
