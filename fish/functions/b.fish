#!/usr/bin/env fish
function b --description 'bundle with met dependencies'
  bundle-ensure; and bundle $argv; or echo 'Could not install bundler dependencies'
end
