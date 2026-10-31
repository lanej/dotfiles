#!/usr/bin/env bash
set -eu

action=$1
setup_home=$2
domain="gui/$(id -u)"
shift 2
labels=("$@")
case "$action" in
    start)
        for label in "${labels[@]}"; do
            test -f "$setup_home/Library/LaunchAgents/$label.plist" || {
                printf 'Missing LaunchAgent: %s\n' "$label" >&2
                exit 1
            }
        done
        for label in "${labels[@]}"; do
            launchctl enable "$domain/$label"
            if ! launchctl print "$domain/$label" >/dev/null 2>&1; then
                launchctl bootstrap "$domain" "$setup_home/Library/LaunchAgents/$label.plist"
            fi
        done
        open -a Paseo
        ;;
    pair)
        certificate="$setup_home/.local/share/paseo-secure/pairing/paseo-lan-ca.cer"
        if test -f "$certificate"; then
            printf '\nAirDrop this certificate to the new iPhone/iPad:\n  %s\n' "$certificate"
            printf '%s\n' 'Open Settings > General > VPN & Device Management, select the downloaded certificate profile, and tap Install.'
            printf '%s\n' 'Then enable it in Settings > General > About > Certificate Trust Settings.'
        fi
        deadline="$(($(date +%s) + 30))"
        until status="$(paseo --home "$setup_home/.paseo" daemon status --json)" &&
            printf '%s\n' "$status" | jq -e -s 'any(.[]; .localDaemon == "running" and .connectedDaemon == "reachable")' >/dev/null; do
            if test "$(date +%s)" -ge "$deadline"; then
                printf '%s\n' 'Paseo did not become reachable. Check paseo daemon status and the LaunchAgent logs.' >&2
                exit 1
            fi
            sleep 1
        done
        endpoint="$(printf '%s\n' "$status" | jq -er '.listen')"
        paseo --host "$endpoint" daemon pair --relay
        ;;
    stop)
        status=0
        for label in "${labels[@]}"; do
            launchctl disable "$domain/$label" || status=1
            if launchctl print "$domain/$label" >/dev/null 2>&1; then
                launchctl bootout "$domain/$label" || status=1
            fi
        done
        pkill -TERM -u "$(id -u)" -x Paseo || { test $? -eq 1 || status=1; }
        exit "$status"
        ;;
    *) printf 'Unknown Paseo action: %s\n' "$action" >&2; exit 1 ;;
esac
