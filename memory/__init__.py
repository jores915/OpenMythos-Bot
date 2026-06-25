"""
Agent mémoire — persistent SQLite + in-memory embedding index
"""

import asyncio
import json
import logging
import time
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,
    reasoning TEXT,
    confidence REAL,
    sentiment_score REAL,
    risk_flags TEXT,
    scan_result TEXT,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    kind TEXT NOT NULL,       -- 'decision', 'alert', 'user', 'system'
    content TEXT NOT NULL,
    embedding_id INTEGER REFERENCES decisions(id) NULL
);

CREATE INDEX IF NOT EXISTS idx_memories_ts ON memories(ts);
CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind);
"""


class MemoryStore:
    """Async SQLite-backed memory for long-term state."""

    def __init__(self, db_path: str = "agent_memory.db"):
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None
        self._cache: list[dict] = []  # LLM-context window (last N)

    async def connect(self):
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(SCHEMA)
        await self._db.commit()
        logger.info(f"Memory connected → {self.db_path}")

    async def close(self):
        if self._db:
            await self._db.close()

    async def record_decision(self, d: dict) -> int:
        cur = await self._db.execute(
            """INSERT INTO decisions
               (timestamp, action, reasoning, confidence, sentiment_score, risk_flags, scan_result, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                d.get("timestamp", ""),
                d.get("action", ""),
                d.get("reasoning", ""),
                d.get("confidence", 0.0),
                d.get("sentiment_score", 0.0),
                json.dumps(d.get("risk_flags", [])),
                json.dumps(d.get("scan_result")) if d.get("scan_result") else None,
                json.dumps(d.get("metadata", {})),
            ),
        )
        self._cache.append(d)
        if len(self._cache) > 50:
            self._cache = self._cache[-50:]
        await self._db.commit()
        return cur.lastrowid

    async def remember(self, kind: str, content: str):
        await self._db.execute(
            "INSERT INTO memories (ts, kind, content) VALUES (?, ?, ?)",
            (time.time(), kind, content),
        )
        await self._db.commit()

    async def recent_decisions(self, limit: int = 10) -> list[dict]:
        async with self._db.execute(
            "SELECT * FROM decisions ORDER BY id DESC LIMIT ?", (limit,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def recent_memories(self, kind: str = "decision", limit: int = 5) -> list[str]:
        async with self._db.execute(
            "SELECT content FROM memories WHERE kind = ? ORDER BY ts DESC LIMIT ?",
            (kind, limit),
        ) as cur:
            rows = await cur.fetchall()
            return [r["content"] for r in rows]

    async def stats(self) -> dict:
        async with self._db.execute("SELECT COUNT(*) as n FROM decisions") as cur:
            total = (await cur.fetchone())["n"]
        async with self._db.execute(
            "SELECT COUNT(*) as n FROM decisions WHERE action = 'execute'"
        ) as cur:
            trades = (await cur.fetchone())["n"]
        return {"total_decisions": total, "total_trades": trades}

    def context_window(self) -> list[dict]:
        """Last N decisions to inject into LLM prompt."""
        return self._cache[-10:]
