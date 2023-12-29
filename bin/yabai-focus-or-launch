#!/bin/bash

set -x

let wid=$(yabai -m query --windows | jq "[.[] | select(.app == \"$1\") | .id][0]")
echo "$wid"

if [[ "$wid" -eq "0" ]]; then
	$2
else
	yabai -m window --focus "$wid"
fi
