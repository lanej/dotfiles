#!/usr/bin/env bash
set -eu

task=$1
dotfiles=$2
setup_home=$3
os=$4
case "$task" in
    dev-cache)
        node_path=${5:-}
        gopath=${6:-}
        if [ -z "$node_path" ]; then
            node_path="$(dirname "$(command -v node || echo /usr/bin/node)"):$(dirname "$(command -v npm || echo /usr/bin/npm)")"
        fi
        if [ -z "$gopath" ]; then
            gopath=$(GOTOOLCHAIN=local GOWORK=off go env GOPATH 2>/dev/null) || gopath=
        fi
        mkdir -p "$setup_home/.local/state/dev-cache-prune"
        if [ "$os" = Darwin ]; then
            mkdir -p "$setup_home/Library/LaunchAgents"
            plist="$setup_home/Library/LaunchAgents/com.joshlane.dev-cache-prune.plist"
            sed -e "s|__HOME__|$setup_home|g" -e "s|__NODE_PATH__|$node_path|g" -e "s|__GOPATH__|$gopath|g" \
                "$dotfiles/rc/launchd/com.joshlane.dev-cache-prune.plist.template" > "$plist"
            launchctl unload "$plist" 2>/dev/null || true
            launchctl load -w "$plist"
        else
            mkdir -p "$setup_home/.config/systemd/user"
            sed -e "s|__HOME__|$setup_home|g" -e "s|__NODE_PATH__|$node_path|g" -e "s|__GOPATH__|$gopath|g" \
                "$dotfiles/rc/systemd/dev-cache-prune.service.template" > "$setup_home/.config/systemd/user/dev-cache-prune.service"
            cp "$dotfiles/rc/systemd/dev-cache-prune.timer.template" "$setup_home/.config/systemd/user/dev-cache-prune.timer"
            systemctl --user daemon-reload
            systemctl --user enable --now dev-cache-prune.timer
        fi
        ;;
    claude-json)
        mkdir -p "$setup_home/.local/state/claude-json-prune"
        if [ "$os" = Darwin ]; then
            mkdir -p "$setup_home/Library/LaunchAgents"
            plist="$setup_home/Library/LaunchAgents/com.joshlane.claude-json-prune.plist"
            sed -e "s|__HOME__|$setup_home|g" \
                "$dotfiles/rc/launchd/com.joshlane.claude-json-prune.plist.template" > "$plist"
            launchctl unload "$plist" 2>/dev/null || true
            launchctl load -w "$plist"
            echo "claude-json-prune scheduled via launchd (daily, 4am)"
        elif [ "$os" = Linux ]; then
            mkdir -p "$setup_home/.config/systemd/user"
            for kind in service timer; do
                sed -e "s|__HOME__|$setup_home|g" \
                    "$dotfiles/rc/systemd/claude-json-prune.$kind.template" > "$setup_home/.config/systemd/user/claude-json-prune.$kind"
            done
            systemctl --user daemon-reload
            systemctl --user enable --now claude-json-prune.timer
            echo "claude-json-prune scheduled via systemd --user timer (daily, 4am). Headless/no-login box: also run 'loginctl enable-linger $USER' (not run automatically here — that's an account-level setting change, Josh's call)"
        else
            echo "claude-json-prune-schedule: unsupported OS ($os)" >&2
            exit 1
        fi
        ;;
    *) printf 'Unknown maintenance task: %s\n' "$task" >&2; exit 1 ;;
esac
