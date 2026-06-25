"""
OpenMythos Agent Loop — Boucle décisionnelle propre
====================================================
Gère le cycle de vie de l'agent : tick → mémoire → boucle.
"""

import asyncio
import logging
import time

logger = logging.getLogger("openmythos.agent")


async def _run_loop():
    """Boucle asynchrone principale."""
    from api.server import controller

    if controller.agent is None:
        await controller.bootstrap()

    while True:
        try:
            decision = await controller.agent.tick()
            logger.info(
                f"[tick {controller.agent.state.tick_count}] "
                f"{decision.action.value} — {decision.reasoning[:80]}"
            )
            # Intervalle adaptatif
            if decision.action.value == "wait":
                interval = 30
            elif decision.action.value == "scan":
                interval = 15
            else:
                interval = 10
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Agent error: {e}")
            await asyncio.sleep(60)


def run_agent_loop():
    """Point d'entrée pour le thread de l'agent."""
    asyncio.run(_run_loop())
