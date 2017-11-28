#!/usr/bin/env fish
function current-release
	git tag -l 'v*' | sed -E 's/^v//g' | sort -g | tail -n 1
end
