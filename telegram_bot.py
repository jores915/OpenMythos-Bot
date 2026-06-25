"""
OpenMythos Telegram Bot — Commandes interactives
===============================================
Ajoute des commandes /start, /status, /scan, /stop, /start_agent au bot.
"""

import json
import logging
import os
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)

API_BASE = "http://localhost:8080"


def _api_get(path: str) -> dict:
    try:
        r = urllib.request.urlopen(f"{API_BASE}{path}", timeout=10)
        return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def _api_post(path: str, data: dict = None) -> dict:
    try:
        body = json.dumps(data or {}).encode()
        req = urllib.request.Request(
            f"{API_BASE}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        r = urllib.request.urlopen(req, timeout=30)
        return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def handle_command(text: str, chat_id: int) -> str:
    """Traite une commande Telegram et retourne la réponse."""
    text = text.strip()

    # Ignorer les messages qui ne commencent pas par /
    if not text.startswith("/"):
        return None

    text_lower = text.lower()

    if text_lower in ("/start", "/help"):
        return (
            "◈ OpenMythos Bot — Commandes\n\n"
            "/status  — État du système\n"
            "/sentiment — Sentiment macro\n"
            "/scan — Scanner arbitrage\n"
            "/start_agent — Démarrer l'agent\n"
            "/stop_agent — Arrêter l'agent\n"
            "/tick — Forcer un tick\n"
        )

    if text_lower == "/status":
        s = _api_get("/status")
        if "error" in s:
            return f"❌ Erreur: {s['error']}"
        return (
            f"📊 OpenMythos Status\n\n"
            f"État: {s.get('status', '?')}\n"
            f"Ticks: {s.get('tick_count', 0)}\n"
            f"Dernière action: {s.get('last_action', '—')}\n"
            f"Sentiment: {s.get('last_sentiment', 0):.2f}\n"
            f"Trades: {s.get('total_trades', 0)}\n"
            f"Telegram: {'✅' if s.get('telegram_configured') else '❌'}\n"
        )

    if text == "/sentiment":
        s = _api_get("/sentiment")
        if "error" in s:
            return f"❌ Erreur: {s['error']}"
        score = s.get("score", 0)
        flags = s.get("risk_flags", [])
        titles = s.get("titles", [])[:3]
        emoji = "🟢" if score > 0 else "🔴" if score < 0 else "🟡"
        msg = f"{emoji} Sentiment: {score:.3f}\n"
        if flags:
            msg += f"⚠️ Risque: {', '.join(flags)}\n"
        if titles:
            msg += "\n📰 Titres:\n" + "\n".join(f"• {t[:50]}" for t in titles)
        return msg

    if text == "/scan":
        s = _api_post("/arbitrage/scan")
        if "error" in s:
            return f"❌ Erreur: {s['error']}"
        profit = s.get("simulated_profit_usd", 0)
        profitable = s.get("profitable", False)
        emoji = "💰" if profitable else "⚪"
        return f"{emoji} Scan Arbitrage\n\nProfit simulé: ${profit:.4f}\nRentable: {'OUI' if profitable else 'NON'}"

    if text == "/start_agent":
        s = _api_post("/agent/start")
        return f"▶️ {s.get('message', 'done')}"

    if text == "/stop_agent":
        s = _api_post("/agent/stop")
        return f"■ {s.get('message', 'done')}"

    if text == "/tick":
        s = _api_post("/agent/tick")
        if "error" in s:
            return f"❌ Erreur: {s['error']}"
        return (
            f"⏭ Tick forcé\n\n"
            f"Action: {s.get('action', '?')}\n"
            f"Confiance: {s.get('confidence', 0):.0%}\n"
            f"Raison: {s.get('reasoning', '?')[:100]}\n"
        )

    return "❓ Commande inconnue. Tape /help pour la liste."


def is_command(text: str) -> bool:
    """Vérifie si le message est une commande valide."""
    return text.strip().startswith("/")


def main():
    """Point d'entrée du bot Telegram — polling en boucle."""
    import json as _json
    import time as _time
    import urllib.request as _req
    import logging as _logging

    _logging.basicConfig(level=_logging.INFO)
    _log = _logging.getLogger("telegram")

    BOT_TOKEN = "8770384464:AAEWxnEvlk7DWau1TLuoJBBtctgEcerRFkU"
    API = f"https://api.telegram.org/bot{BOT_TOKEN}"

    def get_updates(offset=None):
        url = f"{API}/getUpdates?timeout=30"
        if offset:
            url += f"&offset={offset}"
        try:
            r = _req.urlopen(url, timeout=60)
            return _json.loads(r.read()).get("result", [])
        except Exception as e:
            _log.error(f"get_updates error: {e}")
            return []

    def send_message(chat_id, text):
        try:
            _req.urlopen(
                f"{API}/sendMessage",
                data=_json.dumps({"chat_id": chat_id, "text": text}).encode(),
                timeout=10,
            )
        except Exception as e:
            _log.error(f"send error: {e}")

    _log.info("Telegram bot polling started")
    offset = None
    while True:
        updates = get_updates(offset)
        for u in updates:
            offset = u["update_id"] + 1
            msg = u.get("message", {})
            text = msg.get("text", "")
            chat_id = msg.get("chat", {}).get("id")
            if text and chat_id:
                _log.info(f"[{chat_id}] {text}")
                if not is_command(text):
                    _log.info(f"[{chat_id}] Ignored non-command: {text[:50]}")
                    continue
                reply = handle_command(text, chat_id)
                if reply:
                    send_message(chat_id, reply)
        _time.sleep(1)
