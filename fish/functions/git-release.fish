function git-release
	git fetch origin -q
	set current_release (current-release)
	echo "Current release: v$current_release"
	local next_release=v( math $current_release + 1 )
	echo "Releasing: $next_release"
	git tag $next_release && git push origin $next_release
  if ls Capfile
	  printf "deploy with:\n\tREVISION=$next_release bundle exec cap production deploy"
  end
end
