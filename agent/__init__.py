"""
OpenMythos Brain Agent — Intelligent orchestrator
=================================================
Connects the LLM (OpenMythos) to real-time data sources and trading.
Replaces the blind while-loop with a thinking, self-aware agent.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import AsyncIterator, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Decision model
# ---------------------------------------------------------------------------

class Action(str, Enum):
    WAIT = "wait"
    SCAN = "scan"
    EXECUTE = "execute"
    ANALYZE = "analyze"
    ALERT = "alert"
    HALT = "halt"


@dataclass
class Decision:
    """A decision made by the agent at one timestep."""
    timestamp: str
    action: Action
    reasoning: str            # human-readable (or LLM-generated) rationale
    confidence: float         # 0 – 1
    sentiment_score: float    # -1 – 1
    risk_flags: list[str] = field(default_factory=list)
    scan_result: Optional[dict] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "action": self.action.value,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "sentiment_score": self.sentiment_score,
            "risk_flags": self.risk_flags,
            "scan_result": self.scan_result,
            "metadata": self.metadata,
        }


@dataclass
class SessionState:
    """Mutable session state tracked across tick cycles."""
    tick_count: int = 0
    last_action: Optional[str] = None
    last_sentiment: float = 0.0
    last_trade_tx: Optional[str] = None
    total_trades: int = 0
    total_profit_usd: float = 0.0
    start_time: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    memory: list[str] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "tick_count": self.tick_count,
            "last_action": self.last_action,
            "last_sentiment": self.last_sentiment,
            "last_trade_tx": self.last_trade_tx,
            "total_trades": self.total_trades,
            "total_profit_usd": self.total_profit_usd,
            "uptime_since": self.start_time,
            "recent_memory": self.memory[-10:],
        }
