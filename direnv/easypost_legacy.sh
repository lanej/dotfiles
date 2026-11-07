# Shared direnv loader. Preserve the parent environment; direnv handles restoration.
use_easypost_legacy() {
  if [[ ${IN_SRVENV:-0} == 1 ]]; then
    log_error 'EasyPost legacy direnv cannot load inside srvenv'
    return 1
  fi
  local checkout primary common selected candidate metadata had_allexport
  local -a files
  local easypost_library="${BASH_SOURCE[0]}"
  checkout=$(git rev-parse --show-toplevel) || return 1
  common=$(git rev-parse --path-format=absolute --git-common-dir) || return 1
  primary=$(git --git-dir="$common" worktree list --porcelain | sed -n '1s/^worktree //p')
  export SERVICEDIR="$checkout"
  watch_file "$easypost_library"
  for metadata in /usr/local/etc/ep_distro /usr/local/etc/datacenter; do
    watch_file "$metadata"
    if [[ -f $metadata ]]; then
      case $metadata in
        */ep_distro) export EP_DISTRO="$(cat "$metadata")" ;;
        */datacenter) export EP_DATACENTER="$(cat "$metadata")" ;;
      esac
    fi
  done
  read -r -a files <<< "${ENVFILE:-.env .env-build .env-runtime .env-override .env-secrets} ${EXTRA_ENVFILES:-}"
  for selected in "${files[@]}"; do
    candidate="$selected"
    [[ $candidate == /* ]] || candidate="$checkout/$selected"
    watch_file "$candidate"
    if [[ ! -e $candidate && ( $selected == .env-override || $selected == .env-secrets ) ]]; then
      candidate="$primary/$selected"
      watch_file "$candidate"
    fi
    [[ -f $candidate ]] || continue
    had_allexport=0
    [[ $- == *a* ]] && had_allexport=1
    set -a
    # Suppress source diagnostics/output, which may contain expanded secrets.
    if ! source "$candidate" >/dev/null 2>&1; then
      [[ $had_allexport == 1 ]] || set +a
      log_error "EasyPost environment file failed: $selected"
      return 1
    fi
    [[ $had_allexport == 1 ]] || set +a
  done
}
