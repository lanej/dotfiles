#!/usr/bin/env bash
# Keep the setup reporter independent of optional Python/package dependencies.
set -u

make_command=()
while [[ $# -gt 0 && $1 != -- ]]; do
    make_command+=("$1")
    shift
done
shift

green='' red='' reset=''
if [[ -z ${NO_COLOR+x} && ( ( -t 1 && ${TERM:-dumb} != dumb ) || ${CLICOLOR_FORCE:-0} != 0 ) ]]; then
    green=$'\033[32m' red=$'\033[31m' reset=$'\033[0m'
fi

log=$(mktemp "${TMPDIR:-/tmp}/dotfiles-setup.XXXXXX") || exit 1
trap 'rm -f "$log"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
completed=0 failed=0 seen=' '
printf 'Dotfiles setup\n\n'
for target in "$@"; do
    # Prerequisites and appended setup groups may name the same step.
    case $seen in *" $target "*) continue ;; esac
    seen+="$target "
    if "${make_command[@]}" -- "$target" >"$log" 2>&1; then
        printf '%s✓%s %s\n' "$green" "$reset" "$target"
        completed=$((completed + 1))
    else
        printf '%s✗%s %s\n' "$red" "$reset" "$target"
        while IFS= read -r line || [[ -n $line ]]; do
            printf '    %s\n' "$line"
        done < "$log"
        failed=$((failed + 1))
    fi
done
printf '\n%d completed; %d incomplete.\n' "$completed" "$failed"
if ((failed)); then
    printf 'Fix the reported issues and rerun make to finish setup.\n'
    exit 1
fi
