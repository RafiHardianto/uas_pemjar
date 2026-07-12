#!/usr/bin/env bash
# Menjalankan tcp_server.py, udp_server.py, dan app.py sekaligus di background.
# Cocok untuk demo cepat di VM tanpa perlu 3 terminal terpisah / systemd.
#
# Pakai:
#   chmod +x run_all.sh stop_all.sh
#   ./run_all.sh
#   tail -f logs/web.log      # untuk lihat log salah satu servicenya
#   ./stop_all.sh             # untuk menghentikan semua

set -e
cd "$(dirname "$0")"

if [ -d "venv" ]; then
  source venv/bin/activate
fi

mkdir -p logs pids

echo "[run_all] Menjalankan tcp_server.py ..."
nohup python3 tcp_server.py > logs/tcp.log 2>&1 &
echo $! > pids/tcp.pid

echo "[run_all] Menjalankan udp_server.py ..."
nohup python3 udp_server.py > logs/udp.log 2>&1 &
echo $! > pids/udp.pid

sleep 1

echo "[run_all] Menjalankan app.py (web) ..."
nohup python3 app.py > logs/web.log 2>&1 &
echo $! > pids/web.pid

sleep 1
echo ""
echo "[run_all] Semua service berjalan:"
echo "  - TCP upload server : PID $(cat pids/tcp.pid)  (log: logs/tcp.log)"
echo "  - UDP stream server : PID $(cat pids/udp.pid)  (log: logs/udp.log)"
echo "  - Web app (Flask)   : PID $(cat pids/web.pid)  (log: logs/web.log)"
echo ""
echo "Buka http://<ip-vm>:5000 (atau PORT di .env) di browser."
echo "Hentikan semua dengan: ./stop_all.sh"
