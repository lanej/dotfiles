#!/usr/bin/env fish
function current-release
	set release (git tag -l 'v*' | sed -E 's/^v//g' | sort -g | tail -n 1)
  if test -z $release
    set release 0
  end
  echo $release
end
