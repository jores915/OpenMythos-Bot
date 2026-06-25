#!/bin/bash
# OpenMythos — Service daemon persistent
# Survit aux déconnexions terminal
# Usage: nohup ./daemon.sh &

cd "$(dirname "$0")"
source venv/bin/activate

# Nettoyer le port
lsof -ti:8080 | xargs -r kill -9 2>/dev/null
sleep 1

echo "[$(date)] Starting OpenMythos services..."

# Lancer l'API + Agent + Telegram dans un seul processus Python
exec python -c "
import threading, time, sys, os

def run_api():
    import uvicorn
    uvicorn.run('api.server:app', host='0.0.0.0', port=8080, log_level='warning', access_log=False)

# API thread
t = threading.Thread(target=run_api, daemon=True)
t.start()
time.sleep(3)

# Seed simulator
from simulator import simulator
for i in range(10):
    simulator.simulate_execute()
print(f'[INIT] Simulator: {len(simulator.trades)} trades, \${simulator.balance_usd:.4f}')

# Agent loop
from agent_loop import run_agent_loop
t2 = threading.Thread(target=run_agent_loop, daemon=True)
t2.start()
print('[INIT] Agent loop started')

# Telegram
from telegram_bot import main as run_tg
t3 = threading.Thread(target=run_tg, daemon=True)
t3.start()
print('[INIT] Telegram polling started')

print('[LIVE] All services running. API: http://localhost:8080')
print('[LIVE] Dashboard: http://localhost:8080/dashboard')
print('[LIVE] Press Ctrl+C to stop.')

try:
    while True:
        time.sleep(5)
except KeyboardInterrupt:
    print('\n[STOP] Shutting down...')
    sys.exit(0)
"
