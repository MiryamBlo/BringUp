#!/usr/bin/env bash
# start_web_gui.sh - start/stop/restart the Build Automation Web GUI
# Usage: ./start_web_gui.sh start|stop|restart|status [--bg]

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PY="$SCRIPT_DIR/build_automation_web_gui.py"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/web_gui.log"
PID_FILE="$SCRIPT_DIR/web_gui.pid"
PYTHON=${PYTHON:-python3}
BG=false

show_help() {
  cat <<EOF
Usage: $0 {start|stop|restart|status} [--bg]

Commands:
  start       Start the web GUI (default foreground). Use --bg to run in background.
  stop        Stop the running web GUI (PID from $PID_FILE)
  restart     Stop then start
  status      Show status of the server

Logs: $LOG_FILE
PID: $PID_FILE
EOF
}

if [[ ${1:-} == "" ]]; then
  show_help
  exit 1
fi

cmd="$1"; shift || true
for arg in "$@"; do
  case "$arg" in
    --bg) BG=true ;;
    -h|--help) show_help; exit 0 ;;
    *) echo "Unknown arg: $arg"; show_help; exit 1 ;;
  esac
done

is_running() {
  if [[ -f "$PID_FILE" ]]; then
    pid=$(cat "$PID_FILE")
    if ps -p "$pid" > /dev/null 2>&1; then
      return 0
    else
      rm -f "$PID_FILE"
      return 1
    fi
  fi
  return 1
}

start_fg() {
  echo "Starting Build Automation Web GUI (foreground)"
  exec "$PYTHON" "$APP_PY"
}

start_bg() {
  mkdir -p "$LOG_DIR"
  echo "Starting Build Automation Web GUI in background"
  nohup "$PYTHON" "$APP_PY" >> "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  echo "Started with PID $(cat $PID_FILE), logging to $LOG_FILE"
}

stop() {
  if is_running; then
    pid=$(cat "$PID_FILE")
    echo "Stopping PID $pid"
    kill "$pid"
    sleep 1
    if ps -p "$pid" > /dev/null 2>&1; then
      echo "PID $pid did not exit, sending SIGKILL"
      kill -9 "$pid" || true
    fi
    rm -f "$PID_FILE"
    echo "Stopped"
  else
    echo "Not running"
  fi
}

status() {
  if is_running; then
    echo "Running (pid $(cat $PID_FILE))"
  else
    echo "Not running"
  fi
}

case "$cmd" in
  start)
    if is_running; then
      echo "Already running (pid $(cat $PID_FILE))"
      exit 0
    fi
    if [[ "$BG" == true ]]; then
      start_bg
    else
      start_fg
    fi
    ;;
  stop)
    stop
    ;;
  restart)
    stop || true
    if [[ "$BG" == true ]]; then
      start_bg
    else
      start_fg
    fi
    ;;
  status)
    status
    ;;
  *)
    show_help
    exit 1
    ;;
esac
