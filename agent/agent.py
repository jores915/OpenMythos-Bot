"""
OpenMythos Agent — Cerveau intelligent
======================================
Connecte le LLM aux données news et trading.
Prend des décisions raisonnées au lieu d'une boucle aveugle.
"""

import logging
import os
import json
import time
from datetime import datetime, timezone
from typing import Optional

from agent import Action, Decision, SessionState
from memory import MemoryStore

logger = logging.getLogger(__name__)

# Lazy imports — on ne charge le LLM que si nécessaire
_llm_model = None
_news_fetcher = None


def _get_llm():
    """Lazy-load OpenMythos (lourd — ne charger qu'au premier usage)."""
    global _llm_model
    if _llm_model is None:
        import torch
        from open_mythos import MythosConfig, OpenMythos

        # Config rapide pour raisonnement (petit modèle)
        cfg = MythosConfig(
            vocab_size=32000,
            dim=512,
            n_heads=8,
            n_kv_heads=2,
            max_seq_len=1024,
            max_loop_iters=4,
            prelude_layers=1,
            coda_layers=1,
            attn_type="mla",
            kv_lora_rank=128,
            q_lora_rank=256,
            qk_rope_head_dim=32,
            qk_nope_head_dim=64,
            v_head_dim=64,
            n_experts=16,
            n_shared_experts=2,
            n_experts_per_tok=4,
            expert_dim=512,
            lora_rank=8,
        )
        _llm_model = OpenMythos(cfg)
        _llm_model.eval()
        logger.info(f"LLM loaded — {sum(p.numel() for p in _llm_model.parameters()):,} params")
    return _llm_model


def _get_news():
    """Lazy-load NewsFetcher."""
    global _news_fetcher
    if _news_fetcher is None:
        from agents.news_fetcher import NewsFetcher
        finnhub_token = os.getenv("FINNHUB_TOKEN", "")
        _news_fetcher = NewsFetcher(api_key=finnhub_token if finnhub_token else None)
    return _news_fetcher


class MythosAgent:
    """
    L'agent intelligent qui remplace la boucle while True.

    Chaque tick :
    1. Récupère les news/sentiment en temps réel
    2. Interroge le LLM pour un raisonnement
    3. Décide d'une action (scan, execute, wait, alert, halt)
    4. Exécute et enregistre la décision en mémoire
    5. Notifie Telegram si configuré
    """

    def __init__(self, config_path: str = "config.json"):
        with open(config_path) as f:
            self.config = json.load(f)

        self.state = SessionState()
        self.memory = MemoryStore()
        self.llm_prompt_template = (
            "Tu es un agent de trading crypto intelligent. "
            "Voici l'état actuel:\n"
            "- Sentiment macro: {sentiment}\n"
            "- Flags de risque: {risk_flags}\n"
            "- Décisions récentes: {history}\n"
            "- Tick numéro: {tick}\n\n"
            "Que dois-tu faire? Réponds en JSON: "
            '\'{{"action": "wait|scan|execute|alert", "reasoning": "...", "confidence": 0.0-1.0}}\''
        )

    async def bootstrap(self):
        """Initialize memory and warm up subsystems."""
        await self.memory.connect()
        await self.memory.remember("system", "Agent initialized")
        logger.info("Agent bootstrapped")

    async def shutdown(self):
        await self.memory.remember("system", f"Agent shutdown after {self.state.tick_count} ticks")
        await self.memory.close()

    async def tick(self) -> Decision:
        """Un cycle décisionnel complet."""
        self.state.tick_count += 1
        ts = datetime.now(timezone.utc).isoformat()

        # 1. Récupérer le sentiment
        news = _get_news()
        sentiment_data = news.get_macro_sentiment()
        sentiment_score = sentiment_data.get("score", 0.0)
        risk_flags = sentiment_data.get("risk_flags", [])
        titles = sentiment_data.get("titles", [])[:5]

        self.state.last_sentiment = sentiment_score

        # 2. Contexte mémoire pour le LLM
        recent = await self.memory.recent_decisions(limit=5)
        history_str = "\n".join(
            f"  [{r['action']}] {r.get('reasoning','?')[:80]}"
            for r in recent
        ) if recent else "  (aucun historique)"

        # 3. Décision : rule-based principal + LLM si disponible
        # Le LLM non-entraîné produit du bruit → on utilise rule-based comme base
        # et on n'appelle le LLM que pour enrichir la réflexion
        decision = self._rule_based_decision(sentiment_score, risk_flags)

        # Tenter d'enrichir avec le LLM (optionnel, non-bloquant)
        if self.state.tick_count % 5 == 0:  # Appeler LLM seulement tous les 5 ticks
            try:
                llm_decision = await self._think_with_llm(
                    sentiment_score, risk_flags, history_str, titles
                )
                # Utiliser le raisonnement LLM pour enrichir la décision rule-based
                if llm_decision.confidence > 0.8 and decision.action == Action.WAIT:
                    # Si le LLM est confiant et qu'on attendait, promouvoir en scan
                    decision.action = Action.SCAN
                    decision.reasoning += f" [LLM boost: {llm_decision.reasoning[:60]}]"
            except Exception:
                pass  # Silencieux — le rule-based est notre base

        decision.timestamp = ts
        decision.sentiment_score = sentiment_score
        decision.risk_flags = risk_flags

        # 4. Exécuter l'action
        if decision.action == Action.SCAN:
            decision.scan_result = await self._do_scan(decision)
        elif decision.action == Action.EXECUTE:
            decision.scan_result = await self._do_execute(decision)
        elif decision.action == Action.ALERT:
            await self._do_alert(decision, titles)

        # 5. Enregistrer en mémoire
        await self.memory.record_decision(decision.to_dict())
        await self.memory.remember(
            "decision",
            f"Tick {self.state.tick_count}: {decision.action.value} — {decision.reasoning[:120]}"
        )

        self.state.last_action = decision.action.value
        return decision

    async def _think_with_llm(
        self,
        sentiment: float,
        risk_flags: list[str],
        history: str,
        titles: list[str],
    ) -> Decision:
        """Utilise OpenMythos pour raisonner (appel synchrone dans thread)."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._sync_think, sentiment, risk_flags, history, titles
        )

    def _sync_think(
        self,
        sentiment: float,
        risk_flags: list[str],
        history: str,
        titles: list[str],
    ) -> Decision:
        """Appel LLM synchrone — utilisé uniquement comme signal d'enrichissement.
        Le modèle non-entraîné ne peut pas prendre de décisions fiables,
        on utilise donc une heuristique très conservatrice basée sur le sentiment.
        """
        import torch
        model = _get_llm()
        cfg = model.cfg

        prompt = self.llm_prompt_template.format(
            sentiment=sentiment,
            risk_flags=", ".join(risk_flags) if risk_flags else "aucun",
            history=history,
            tick=self.state.tick_count,
        )

        # Tokeniser avec un hash simple
        words = prompt.split()
        input_ids = [(hash(w) % cfg.vocab_size) for w in words[:256]]
        if not input_ids:
            input_ids = [0]
        input_tensor = torch.tensor([input_ids], dtype=torch.long)

        with torch.no_grad():
            output = model.generate(
                input_tensor,
                max_new_tokens=32,
                n_loops=1,
                temperature=0.5,
                top_k=20,
            )

        generated_ids = output[0].tolist()[len(input_ids):]
        if not generated_ids:
            generated_ids = [0]

        # Signal très conservateur : on utilise juste la variance comme indicateur
        # d'"intérêt" du modèle pour le contexte (plus de variance = plus d'info)
        import statistics
        variance = statistics.variance(generated_ids) if len(generated_ids) > 1 else 0

        # Pour un modèle non-entraîné, on retourne toujours WAIT avec une confidence basse
        # sauf si la variance est extrême (indiquant un pattern rare)
        if variance > cfg.vocab_size * 0.1:
            action = Action.SCAN
            reasoning = f"LLM high variance ({variance:.0f}), possible signal"
            confidence = 0.4  # Basse confiance — c'est du bruit
        else:
            action = Action.WAIT
            reasoning = f"LLM low variance ({variance:.0f}), no clear signal"
            confidence = 0.3

        return Decision(
            timestamp="",
            action=action,
            reasoning=reasoning,
            confidence=confidence,
            sentiment_score=sentiment,
        )

    def _rule_based_decision(self, sentiment: float, risk_flags: list[str]) -> Decision:
        """Fallback sans LLM — règles simples mais efficaces."""
        if "RECENT_HACK" in risk_flags or "LIQUIDATION_CASCADE" in risk_flags:
            return Decision(
                timestamp="",
                action=Action.HALT,
                reasoning=f"Risk flags detected: {risk_flags}. Stopping for safety.",
                confidence=0.95,
                sentiment_score=sentiment,
                risk_flags=risk_flags,
            )

        if sentiment < -0.5:
            return Decision(
                timestamp="",
                action=Action.ALERT,
                reasoning=f"Strong negative sentiment ({sentiment:.2f}). Alerting only.",
                confidence=0.8,
                sentiment_score=sentiment,
                risk_flags=risk_flags,
            )

        if sentiment > 0.3:
            return Decision(
                timestamp="",
                action=Action.SCAN,
                reasoning=f"Positive sentiment ({sentiment:.2f}). Scanning for opportunities.",
                confidence=0.7,
                sentiment_score=sentiment,
                risk_flags=risk_flags,
            )

        return Decision(
            timestamp="",
            action=Action.WAIT,
            reasoning=f"Neutral sentiment ({sentiment:.2f}). Waiting.",
            confidence=0.6,
            sentiment_score=sentiment,
            risk_flags=risk_flags,
        )

    async def _do_scan(self, decision: Decision) -> Optional[dict]:
        """Scan ParaSwap pour opportunités d'arbitrage."""
        try:
            from flash_scanner import FlashArbScanner
            from load_secrets import load_config

            cfg = load_config("config.json")
            scanner = FlashArbScanner(
                cfg["rpc_url"],
                cfg["private_key"],
                cfg["contract_address"],
                json.load(open(cfg["abi_file"])),
            )

            # Scan sur les pools définis
            results = []
            for token_in, amount, p1, p2, swap_fee, flash_fee in [
                ("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", 100_000_000_000,
                 ["0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "0x4200000000000000000000000000000000000006"],
                 ["0x4200000000000000000000000000000000000006", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"],
                 3000, 3000),
            ]:
                profit = scanner.simulate_profit(token_in, amount, p1, p2)
                results.append({
                    "token": token_in[:10] + "...",
                    "simulated_profit_usd": round(profit, 4),
                    "profitable": profit > 0.5,
                })

            profitable = [r for r in results if r.get("profitable")]
            if profitable:
                decision.action = Action.EXECUTE
                decision.reasoning += " → Profitable! Executing."

            return {"pools_scanned": len(results), "profitable": profitable}
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            return {"error": str(e)}

    async def _do_execute(self, decision: Decision) -> Optional[dict]:
        """Exécute un arbitrage."""
        try:
            from flash_scanner import FlashArbScanner
            from load_secrets import load_config

            cfg = load_config("config.json")
            scanner = FlashArbScanner(
                cfg["rpc_url"],
                cfg["private_key"],
                cfg["contract_address"],
                json.load(open(cfg["abi_file"])),
                bot_token=self.config.get("telegram", {}).get("bot_token"),
                chat_id=self.config.get("telegram", {}).get("chat_id"),
            )

            receipt = scanner.execute_if_profitable(
                "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                100_000_000_000,
                ["0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "0x4200000000000000000000000000000000000006"],
                ["0x4200000000000000000000000000000000000006", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"],
                3000, 3000,
            )

            if receipt:
                self.state.total_trades += 1
                tx_hash = receipt.transactionHash.hex() if hasattr(receipt, 'transactionHash') else str(receipt)
                self.state.last_trade_tx = tx_hash
                return {"tx_hash": tx_hash, "status": "executed"}
            return {"status": "not_profitable"}
        except Exception as e:
            logger.error(f"Execute failed: {e}")
            return {"error": str(e)}

    async def _do_alert(self, decision: Decision, titles: list[str]):
        """Envoie une alerte Telegram."""
        tg = self.config.get("telegram", {})
        bot_token = tg.get("bot_token")
        chat_id = tg.get("chat_id")

        if not bot_token or not chat_id:
            return

        msg = f"🚨 ALERTE OpenMythos\n\nSentiment: {decision.sentiment_score:.2f}\n"
        msg += f"Risque: {', '.join(decision.risk_flags)}\n\n"
        msg += f"Titres:\n" + "\n".join(f"• {t[:60]}" for t in titles[:5])

        try:
            from connectors.telegram import TelegramNotifier
            notifier = TelegramNotifier(bot_token, chat_id)
            notifier.send(msg)
        except Exception as e:
            logger.error(f"Telegram alert failed: {e}")

    def status(self) -> dict:
        """État complet du système."""
        return {
            "agent": self.state.summary(),
            "config_loaded": bool(self.config),
        }
