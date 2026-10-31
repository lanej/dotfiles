#!/usr/bin/env bash
set -eu

install_hostname=$(uname -n)
printf '%s' "$install_hostname" | tr '[:upper:]' '[:lower:]'
