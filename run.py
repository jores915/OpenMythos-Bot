#!/usr/bin/env python3
"""
OpenMythos — Point d'entrée principal
Lance : API + Agent loop + Telegram polling
"""

import argparse
import logging
import os
import signal
import sys
import threading

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("openmythos")


def banner():
    print("""
  ╔═══════════════════════════════════════════════╗
  ║   ◈  O P E N M Y T H O S   B O T            ║
  ║   LLM-Powered Crypto Intelligence            ║
  ╠═══════════════════════════════════════════════╣
  ║   API     : http://{host}:{port}                ║
  ║   Docs    : http://{host}:{port}/docs           ║
  ║   Dash    : http://{host}:{port}/dashboard      ║
  ║   Telegram: @OpenMythos_bot                   ║
  ╚═══════════════════════════════════════════════╝
    """)


def check_config():
    """Vérifier que config.json existe et est valide."""
    if not os.path.exists("config.json"):
        logger.error("config.json introuvable!")
        logger.info("Copiez config.json.example → config.json et remplissez les valeurs.")
        sys.exit(1)

    import json
    with open("config.json") as f:
        cfg = json.load(f)

    # Vérifications minimales
    if not cfg.get("private_key"):
        logger.warning("Clé privée vide — le trading ne fonctionnera pas.")
    if not cfg.get("rpc_url"):
        logger.warning("RPC URL vide — pas de connexion blockchain.")
    tg = cfg.get("telegram", {})
    if not tg.get("bot_token") or not tg.get("chat_id"):
        logger.warning("Telegram non configuré — notifications désactivées.")


def run_api(host: str, port: int, no_reload: bool):
    """Lance le serveur FastAPI dans un thread."""
    import uvicorn
    uvicorn.run(
        "api.server:app",
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
        reload=no_reload,
    )


def run_telegram_polling():
    """Lance le polling Telegram dans un thread."""
    from telegram_bot import main
    main()


def main():
    parser = argparse.ArgumentParser(description="OpenMythos Bot")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--no-agent", action="store_true")
    parser.add_argument("--no-telegram", action="store_true")
    parser.add_argument("--no-reload", action="store_true", default=True)
    args = parser.parse_args()

    banner()
    check_config()

    # Thread API
    api_thread = threading.Thread(
        target=run_api,
        args=(args.host, args.port, args.no_reload),
        daemon=True,
    )
    api_thread.start()
    logger.info(f"API server started on http://{args.host}:{args.port}")

    # Attendre que l'API soit prête
    import time
    time.sleep(2)

    # Thread Telegram
    if not args.no_telegram:
        tg_thread = threading.Thread(
            target=run_telegram_polling,
            daemon=True,
        )
        tg_thread.start()
        logger.info("Telegram bot polling started")

    # Thread Agent Loop
    if not args.no_agent:
        from agent_loop import run_agent_loop
        agent_thread = threading.Thread(
            target=run_agent_loop,
            daemon=True,
        )
        agent_thread.start()
        logger.info("Agent loop started")

    logger.info("All systems running. Press Ctrl+C to stop.")

    # Garder le processus vivant
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()
