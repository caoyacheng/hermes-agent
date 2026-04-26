#!/bin/bash
#
# Restart two Hermes profiles (gateway + dashboard).
#
# Defaults:
#   profiles: default,instance2
#   dashboard ports: 9119,9120
#
# Usage:
#   bash scripts/restart_instances.sh
#   bash scripts/restart_instances.sh --profiles instance1,instance2 --ports 9119,9120
#   bash scripts/restart_instances.sh --no-dashboard
#

set -euo pipefail

PROFILES_CSV="${PROFILES_CSV:-default,instance2}"
PORTS_CSV="${PORTS_CSV:-9119,9120}"
RESTART_DASHBOARD=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERMES_BIN="${HERMES_BIN:-${SCRIPT_DIR}/../venv/bin/hermes}"
if [[ ! -x "$HERMES_BIN" ]]; then
  HERMES_BIN="${HERMES_BIN:-hermes}"
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profiles)
      PROFILES_CSV="${2:?missing value for --profiles}"
      shift 2
      ;;
    --ports)
      PORTS_CSV="${2:?missing value for --ports}"
      shift 2
      ;;
    --no-dashboard)
      RESTART_DASHBOARD=0
      shift 1
      ;;
    -h|--help)
      sed -n '1,40p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

IFS=',' read -r -a PROFILES <<<"$PROFILES_CSV"
IFS=',' read -r -a PORTS <<<"$PORTS_CSV"

if [[ ${#PROFILES[@]} -ne 2 || ${#PORTS[@]} -ne 2 ]]; then
  echo "Expected exactly 2 profiles and 2 ports." >&2
  echo "Got profiles=${#PROFILES[@]} ports=${#PORTS[@]}" >&2
  exit 2
fi

kill_by_pattern() {
  local pattern="$1"
  local pids=""
  pids="$(pgrep -f "$pattern" || true)"
  if [[ -z "$pids" ]]; then
    return 0
  fi

  echo "Stopping: $pattern"
  echo "$pids" | xargs -n 1 kill -TERM 2>/dev/null || true

  local tries=0
  while [[ $tries -lt 30 ]]; do
    sleep 0.2
    if ! pgrep -f "$pattern" >/dev/null 2>&1; then
      return 0
    fi
    tries=$((tries + 1))
  done

  echo "Still running; force killing: $pattern" >&2
  pgrep -f "$pattern" | xargs -n 1 kill -KILL 2>/dev/null || true
}

start_gateway() {
  local profile="$1"

  local log_dir="${HOME}/.hermes/profiles/${profile}/logs"
  if [[ "$profile" == "default" ]]; then
    log_dir="${HOME}/.hermes/logs"
  fi
  mkdir -p "$log_dir"
  local log_file="${log_dir}/gateway.run.log"

  echo "Starting gateway: profile=${profile}"
  nohup "$HERMES_BIN" -p "$profile" gateway run --replace >"$log_file" 2>&1 &
  disown || true
  echo "  log: $log_file"
}

start_dashboard() {
  local profile="$1"
  local port="$2"

  local log_dir="${HOME}/.hermes/profiles/${profile}/logs"
  if [[ "$profile" == "default" ]]; then
    log_dir="${HOME}/.hermes/logs"
  fi
  mkdir -p "$log_dir"
  local log_file="${log_dir}/dashboard.${port}.log"

  echo "Starting dashboard: profile=${profile} port=${port}"
  nohup "$HERMES_BIN" -p "$profile" dashboard --port "$port" --no-open >"$log_file" 2>&1 &
  disown || true
  echo "  log: $log_file"
}

for i in 0 1; do
  profile="${PROFILES[$i]}"
  port="${PORTS[$i]}"

  echo ""
  echo "=== ${profile} ==="

  echo "Restarting gateway (stop + run --replace)..."
  kill_by_pattern "$HERMES_BIN -p ${profile} gateway run"
  kill_by_pattern "python .* -m hermes_cli\\.main --profile ${profile} gateway run"
  start_gateway "$profile"

  if [[ "$RESTART_DASHBOARD" -eq 1 ]]; then
    kill_by_pattern "$HERMES_BIN -p ${profile} dashboard"
    start_dashboard "$profile" "$port"
  fi
done

echo ""
echo "Done."
