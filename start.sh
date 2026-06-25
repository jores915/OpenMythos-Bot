#!/bin/bash
# OpenMythos Bot —.Script de lancement complet
cd "$(dirname "$0")"
source venv/bin/activate
lsof -ti:8080 | xargs -r kill -9 2>/dev/null
sleep 1

python -c "
import threading, time

def run_api():
    import uvicorn
    uvicorn.run('api.server:app', host='0.0.0.0', port=8080, log_level='warning', access_log=False)

t = threading.Thread(target=run_api, daemon=True)
t.start()
time.sleep(3)

from simulator import simulator
for i in range(15):
    simulator.execute_best()
print(f'[OK] Simulator: {len(simulator.trades)} trades, \${simulator.balance_usd:.6f}')

from agent_loop import run_agent_loop
t2 = threading.Thread(target=run_agent_loop, daemon=True)
t2.start()

from telegram_bot import main as run_tg
t3 = threading.Thread(target=run_tg, daemon=True)
t3.start()

print('[LIVE] http://localhost:8080')
while True: time.sleep(5)
" 2>&1