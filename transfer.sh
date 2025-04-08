#!/bin/bash

host=$1

if [ -z "$host" ]; then
	echo "Usage: $0 <host>"
	exit 1
fi

set -ex

# scp bootstrap.sh and run it
scp -A -T bootstrap.sh "$host":/tmp/bootstrap.sh && ssh -A -t "$host" "bash -l /tmp/bootstrap.sh"

# if git user.email is not set, set it based on the current host's global setting
if ! ssh -t "$host" "git config --global user.email" | grep -q .; then
	git config --global user.email | xargs -I {} ssh -t "$host" "git config --global user.email {}"
fi

# if git user.name is not set, set it based on the current host's global settinr
if ! ssh -t "$host" "git config --global user.name" | grep -q .; then
	git config --global user.name | xargs -I {} ssh -t "$host" "git config --global user.name {}"
fi

# if .env exists locally and not remotely, scp it to the remote host
if [ -f .env ] && ! ssh -t "$host" "test -f .env"; then
	scp .env "$host":.env
fi
