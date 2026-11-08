#!/usr/bin/env bash
# Sequentially rebase (cherry-pick onto fresh main), wait for CI, and squash-merge PRs.
# Only run after the human has explicitly authorized merging these PRs (see STATE.md).
# Stops at the first problem. Usage: merge-seq.sh PR [PR...]
# Env: EPSCTL_REPO (default easypost-sandbox/epservicesctl), EPSCTL_MERGE_DIR (clone to work in),
# EPSCTL_MERGE_META (per-PR "head<TAB>base<TAB>state<TAB>commit,commit" files named <PR>.tsv).
set -uo pipefail
R=${EPSCTL_REPO:-easypost-sandbox/epservicesctl}
WORK=${EPSCTL_MERGE_DIR:-/tmp/epsctl-merge}
HELPERS=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$WORK" || exit 1
META=${EPSCTL_MERGE_META:-/tmp/epsctl-merge-meta}
[ "$#" -gt 0 ] || { echo "usage: merge-seq.sh PR [PR...]" >&2; exit 64; }
ORDER="$*"
log(){ printf '%s %s\n' "$(date -u +%H:%M:%S)" "$*"; }
for n in $ORDER; do
  IFS=$'\t' read -r head _ _ commits < "$META/$n.tsv"
  cur=$(gh pr view "$n" -R "$R" --json state,baseRefName,headRefName --jq '[.state,.baseRefName,.headRefName]|@tsv')
  state=$(echo "$cur" | cut -f1); curbase=$(echo "$cur" | cut -f2)
  if [ "$state" = "MERGED" ]; then log "#$n already merged, skip"; continue; fi
  if [ "$state" != "OPEN" ]; then log "#$n state=$state, STOP"; exit 2; fi
  if [ "$curbase" != "main" ]; then
    # parent must be merged first (base branch deleted); retarget
    log "#$n retargeting base $curbase -> main"
    gh pr edit "$n" -R "$R" --base main >/dev/null || { log "#$n retarget failed, STOP"; exit 3; }
  fi
  git fetch -q origin main "$head" || { log "#$n fetch failed"; exit 4; }
  git checkout -q -B "work-$n" origin/main
  ok=1
  for c in $(echo "$commits" | tr ',' ' '); do
    if ! git cherry-pick --allow-empty --keep-redundant-commits "$c" >/dev/null 2>&1; then
      if git diff --name-only --diff-filter=U | grep -q .; then
        if [ "$(git diff --name-only --diff-filter=U)" = ".golangci.yml" ] && { python3 "$HELPERS/resolve-golangci.py" >/dev/null 2>&1 || ! grep -q "^<<<<<<<" .golangci.yml; }; then
          git add .golangci.yml
          if git diff --cached --quiet; then git cherry-pick --skip >/dev/null 2>&1; log "#$n auto-resolved .golangci.yml scope conflict (became empty, skipped)"; continue; fi
          GIT_EDITOR=true git cherry-pick --continue >/dev/null 2>&1 && { log "#$n auto-resolved .golangci.yml scope conflict"; continue; }
        fi
        ok=0; log "#$n CONFLICT cherry-picking $c:"; git diff --name-only --diff-filter=U | sed 's/^/    /'; break; fi
      git cherry-pick --skip >/dev/null 2>&1 || true
    fi
  done
  if [ $ok -eq 1 ]; then
    case "$n" in 414) export SCOPE_ADD="dcrouter/";; 415) export SCOPE_ADD="sentryread/";; 417) export SCOPE_ADD="logsearch/";; 419) export SCOPE_ADD="beanstalk/";; 421) export SCOPE_ADD="announce/";; 423) export SCOPE_ADD="";; 426) export SCOPE_ADD="features/";; *) unset SCOPE_ADD;; esac
    if [ -n "$(python3 "$HELPERS/normalize-golangci.py")" ]; then git commit -q -am "fix(lint): normalize typed-enum scope alternation" && log "#$n normalized .golangci.yml scope"; fi
  fi
  if [ $ok -eq 0 ]; then log "#$n needs manual conflict resolution in /tmp/epsctl-merge (branch work-$n), STOP"; exit 5; fi
  if git diff --quiet origin/main HEAD; then log "#$n adds nothing over main (already included), closing is the human's call, STOP"; exit 6; fi
  if ! git diff --quiet "origin/$head" HEAD; then
    log "#$n pushing rebased branch $head"
    git push -q --force-with-lease="$head:origin/$head" origin "work-$n:$head" 2>&1 | grep -v -E "^remote:|^$" || true
  else log "#$n branch already equals rebased result"; fi
  # wait for checks
  sleep 20
  for _ in $(seq 1 90); do
    raw=$(gh pr checks "$n" -R "$R" 2>&1) || true
    out=$(printf '%s\n' "$raw" | awk -F'\t' 'NF>1{print $2}' | sort | uniq -c | tr '\n' ' ')
    pend=$(printf '%s\n' "$raw" | awk -F'\t' '$2=="pending"||$2=="queued"||$2=="in_progress"{c++} END{print c+0}')
    fail=$(printf '%s\n' "$raw" | awk -F'\t' '$2=="fail"{c++} END{print c+0}')
    [ "$fail" -gt 0 ] && { log "#$n CI FAILED: $out STOP"; printf '%s\n' "$raw" | grep -i fail; exit 7; }
    [ "$pend" -eq 0 ] && [ -n "$out" ] && break
    sleep 45
  done
  log "#$n checks: $out"
  if ! gh pr merge "$n" -R "$R" --squash 2>&1 | tail -2; then log "#$n merge command failed, STOP"; exit 8; fi
  sleep 5
  s=$(gh pr view "$n" -R "$R" --json state --jq .state)
  [ "$s" = "MERGED" ] || { log "#$n not merged (state=$s), STOP"; exit 9; }
  log "#$n MERGED"
done
log "ALL DONE"
