#!/usr/bin/env bash
cd "$(dirname "$0")"

for name in tcp udp web; do
  if [ -f "pids/$name.pid" ]; then
    pid=$(cat "pids/$name.pid")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid"
      echo "[stop_all] Menghentikan $name (PID $pid)"
    fi
    rm -f "pids/$name.pid"
  fi
done
echo "[stop_all] Selesai."
