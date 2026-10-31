#!/usr/bin/env bash
set -eu

dotfiles=$1
setup_home=$2
test "$3" = Linux
test -x "$setup_home/.local/bin/atuin-server"
mkdir -p "$setup_home/.config/atuin" "$setup_home/.config/systemd/user"
mkdir -p "$setup_home/.local/share/atuin-server"
chmod 700 "$setup_home/.local/share/atuin-server"
sed "s|__HOME__|$setup_home|g" "$dotfiles/sh/atuin-server.toml.template" \
    > "$setup_home/.config/atuin/server.toml"
ln -fs "$dotfiles/rc/systemd/atuin-server.service" \
    "$setup_home/.config/systemd/user/atuin-server.service"
systemctl --user daemon-reload
systemctl --user enable --now atuin-server.service
systemctl --user restart atuin-server.service
