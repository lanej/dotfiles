
#!/usr/bin/env fish
function travis-browse --description 'Open travis build for current revision'
  set rev (git rev-parse --abbrev-ref HEAD)
  set build (travis show $rev | egrep -o 'Build #(\d+)' | egrep -o '\d+')
  travis open $build
end
