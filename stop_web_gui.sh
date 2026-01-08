#!/usr/bin/env bash
# stop_web_gui.sh - stop the Build Automation Web GUI
# Usage: ./stop_web_gui.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/web_gui.pid"

# Try stopping via PID file first
if [[ -f "$PID_FILE" ]]; then
  pid=$(cat "$PID_FILE")
  if ps -p "$pid" > /dev/null 2>&1; then
    echo "Stopping Build Automation Web GUI (pid $pid)..."
    kill "$pid" || true
    sleep 1
    if ps -p "$pid" > /dev/null 2>&1; then
      echo "PID $pid did not exit, sending SIGKILL"
      kill -9 "$pid" || true
    fi
    rm -f "$PID_FILE"
    echo "Stopped"
    exit 0
  else
    echo "PID file exists but process $pid not running; removing PID file"
    rm -f "$PID_FILE"
  fi
fi

# Fallback: kill by process name
echo "Looking for running web GUI process..."
pids=$(pgrep -af build_automation_web_gui.py | awk '{print $1}' | tr '\n' ' ')
if [[ -n "$pids" ]]; then
  echo "Killing pids: $pids"
  pkill -f build_automation_web_gui.py || true
  sleep 1
  echo "Stopped"
  exit 0
fi

echo "No running Build Automation Web GUI process found."
exit 1
