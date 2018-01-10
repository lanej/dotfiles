function git-release
	git fetch origin -q
	set current_release (current-release)
	echo "Current release: v$current_release"
	set next_release v( math $current_release + 1 )
	echo "Releasing: $next_release"
	git tag $next_release; and git push origin $next_release
  if ls Capfile > /dev/null
	  printf "deploy with:\n\tREVISION=$next_release bundle exec cap production deploy"
  end
end
