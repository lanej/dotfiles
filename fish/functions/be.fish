#!/usr/bin/env fish
function be --description 'bundle exec with met dependencies'
  bundle-ensure; and bundle exec $argv; or echo 'Could not install bundler dependencies'
end
