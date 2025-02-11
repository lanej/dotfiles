#!/bin/bash

host=$1

if [ -z "$host" ]; then
	echo "Usage: $0 <host>"
	exit 1
fi

set -ex

# scp bootstrap.sh and run it
scp -T bootstrap.sh "$host":/tmp/bootstrap.sh && ssh -t "$host" "bash -l /tmp/bootstrap.sh"
git config --global user.email | xargs -I {} ssh -t "$host" "git config --global user.email {}"
git config --global user.name | xargs -I {} ssh -t "$host" "git config --global user.name {}"
