#!/usr/bin/env bash
# Adapt the GitHub bridge to Firstmate's existing ownership and inbox contracts.
set -euo pipefail
feedback_home=$1
action=$2
shift 2
export FM_HOME="$feedback_home"
code=${FIRSTMATE_SOURCE:-$feedback_home}
case "$action" in
    owns-primary)
        # shellcheck source=/dev/null
        source "$code/bin/fm-session-lock-lib.sh"
        if fm_session_lock_owned_by_self "$feedback_home/state"; then printf '%s\n' yes; else printf '%s\n' no; fi
        ;;
    snapshot-input)
        "$code/bin/fm-fleet-snapshot.sh" --contribution-input
        ;;
    task-add)
        "$code/bin/fm-tasks-axi.sh" add "$@"
        ;;
    snapshot)
        snapshot=$(mktemp)
        trap 'rm -f "$snapshot"' EXIT
        "$code/bin/fm-fleet-snapshot.sh" --contribution-input > "$snapshot"
        "$code/bin/fm-contributions.sh" snapshot "$snapshot" --all
        ;;
    enqueue|read|lock)
        # shellcheck source=/dev/null
        source "$code/bin/fm-task-inbox-lib.sh"
        if [[ "$action" == lock ]]; then
            fm_task_inbox_lock_acquire "$1"
            trap 'fm_lock_release "$1"' EXIT
            printf '%s\n' locked
            cat >/dev/null
        elif [[ "$action" == enqueue ]]; then
            message=$(cat)
            fm_task_inbox_write_idempotent "$feedback_home/state" "$1" "$message"
        else
            fm_task_inbox_body "$1"
        fi
        ;;
    *) printf 'Unknown feedback adapter action: %s\n' "$action" >&2; exit 2 ;;
esac
