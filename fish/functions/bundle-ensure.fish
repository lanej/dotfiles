#!/usr/bin/env fish
function bundle-ensure --description 'Ensure bundle dependencies met'
  if not bundle check 1>/dev/null
    bundle install --local --jobs 5; or bundle install --jobs 5
  end
end
