"""
OpenMythos Multi-DEX Simulator — Aerodrome + Alien Base + SwapBased + Uniswap V3
================================================================================
Simule l'arbitrage cross-DEX avec des prix réalistes pour chaque protocole.
"""

import json
import random
import time
from datetime import datetime, timezone
from typing import Optional

# ─── Tokens ───────────────────────────────────────────────────────────────────
TOKENS = ["USDC", "USDT", "DAI", "WETH", "WBTC", "AERO", "CBETH", "BSD"]
DECIMALS = {"WETH": 18, "USDC": 6, "USDT": 6, "DAI": 18, "WBTC": 8, "AERO": 18, "CBETH": 18, "BSD": 18}
USD_PRICE = {"WETH": 2450.0, "USDC": 1.0, "USDT": 1.0, "DAI": 1.0, "WBTC": 67500.0, "AERO": 1.25, "CBETH": 2465.0, "BSD": 0.85}

# ─── DEX Protocols ───────────────────────────────────────────────────────────
PROTOCOLS = {
    "Uniswap": {
        "weight": 40,
        "spread_range": (0.0003, 0.002),   # 0.03% - 0.2%
        "gas_usd": 0.001,
    },
    "Aerodrome": {
        "weight": 25,
        "spread_range": (0.0004, 0.003),   # 0.04% - 0.3%
        "gas_usd": 0.0012,
    },
    "Alien": {
        "weight": 15,
        "spread_range": (0.0005, 0.004),   # 0.05% - 0.4%
        "gas_usd": 0.0015,
    },
    "SwapBased": {
        "weight": 20,
        "spread_range": (0.0004, 0.0025),  # 0.04% - 0.25%
        "gas_usd": 0.0011,
    },
}

# ─── Pools disponibles sur chaque protocole ──────────────────────────────────
POOLS_BY_PROTOCOL = {
    "Uniswap": [
        ("DAI", "USDC", 800_000, 500000),
        ("USDC", "USDT", 1_200_000, 800000),
        ("WETH", "USDC", 600_000, 1_200_000),
        ("WETH", "USDT", 450_000, 750000),
        ("CBETH", "WETH", 120_000, 180_000),
        ("AERO", "WETH", 80_000, 90000),
    ],
    "Aerodrome": [
        ("USDC", "WETH", 500_000, 950000),
        ("WETH", "USDT", 380_000, 600000),
        ("AERO", "USDC", 150_000, 200000),
        ("DAI", "USDT", 200_000, 150000),
        ("CBETH", "USDC", 90_000, 120000),
    ],
    "Alien": [
        ("WETH", "AERO", 60_000, 70000),
        ("USDC", "AERO", 45_000, 55000),
        ("WETH", "BSD", 35_000, 40000),
        ("USDC", "BSD", 30_000, 35000),
    ],
    "SwapBased": [
        ("WETH", "USDC", 400_000, 700000),
        ("USDT", "WETH", 350_000, 550000),
        ("DAI", "USDC", 180_000, 120000),
        ("AERO", "WETH", 70_000, 80000),
    ],
}


def generate_tx_hash() -> str:
    return "0x" + "".join(random.choices("0123456789abcdef", k=64))


class MultiDexSimulator:
    """Simulateur multi-DEX avec arbitrage cross-protocol."""

    def __init__(self, seed: Optional[int] = None):
        self.trades: list[dict] = []
        self.balance_usd = 100.0
        self.initial_balance = 100.0
        self.block = 18_500_000
        self.rng = random.Random(seed or int(time.time()) % 10000)
        self.total_gas_usd = 0.0

    def scan_all(self) -> list[dict]:
        """Scan tous les pools sur tous les DEXs et cherche des opportunités."""
        opportunities = []

        for protocol, pools in POOLS_BY_PROTOCOL.items():
            proto_config = PROTOCOLS[protocol]
            gas_usd = proto_config["gas_usd"]
            for token_in, token_out, tvl, vol in pools:
                spread_min, spread_max = proto_config["spread_range"]
                spread = self.rng.uniform(spread_min, spread_max)

                # Montant proportionnel au volume du pool (minimum $1 pour la visibilité)
                amount = self.rng.uniform(1.0, min(vol * 0.001, 20.0))

                # Profit brut = montant × spread
                gross = amount * spread
                net = gross - gas_usd

                if net > 0.0001:
                    opportunities.append({
                        "protocol": protocol,
                        "pool": f"{token_in}/{token_out}",
                        "token_in": token_in,
                        "token_out": token_out,
                        "amount_in_usd": round(amount, 6),
                        "spread_pct": round(spread * 100, 4),
                        "gross_profit_usd": round(gross, 6),
                        "gas_usd": round(gas_usd, 6),
                        "net_profit_usd": round(net, 6),
                        "tvl_usd": tvl,
                        "volume_24h": vol,
                        "confidence": round(self.rng.uniform(50, 99), 1),
                    })

        # Trier par profit net décroissant
        opportunities.sort(key=lambda x: x["net_profit_usd"], reverse=True)
        return opportunities

    def execute_best(self) -> Optional[dict]:
        """Exécute le meilleur trade cross-DEX."""
        opportunities = self.scan_all()
        if not opportunities:
            return None

        best = opportunities[0]
        token_in = best["token_in"]
        token_out = best["token_out"]
        amount = best["amount_in_usd"]
        protocol = best["protocol"]

        # Simuler slippage (0-0.01%)
        slippage = self.rng.uniform(0, 0.0001)
        pr_in = USD_PRICE.get(token_in, 1.0)
        pr_out = USD_PRICE.get(token_out, 1.0)

        # Montant en tokens
        amount_in_human = amount / pr_in
        # Après swap (avec spread positif = opportunité)
        spread = best["spread_pct"] / 100
        amount_out_human = amount_in_human * (1 + spread) * (1 - slippage)
        amount_out_usd = amount_out_human * pr_out

        # Gas
        gas_usd = best["gas_usd"]
        gross_profit = amount_out_usd - amount
        net_profit = gross_profit - gas_usd

        if net_profit <= 0:
            return None

        self.block += 1
        self.balance_usd += net_profit
        self.total_gas_usd += gas_usd

        trade = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tx_hash": generate_tx_hash(),
            "protocol": protocol,
            "token_in": token_in,
            "token_out": token_out,
            "amount_in": round(amount, 6),
            "amount_out": round(amount_out_usd, 6),
            "gross_profit_usd": round(gross_profit, 6),
            "gas_usd": round(gas_usd, 6),
            "net_profit_usd": round(net_profit, 6),
            "spread_pct": best["spread_pct"],
            "pool": best["pool"],
            "block_number": self.block,
        }

        self.trades.append(trade)
        return trade

    def get_portfolio(self) -> dict:
        """État complet du portefeuille."""
        if not self.trades:
            return {
                "balance_usd": round(self.balance_usd, 6),
                "initial_balance_usd": self.initial_balance,
                "realized_pnl_usd": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_profit_usd": 0.0,
                "total_gas_usd": 0.0,
                "net_profit_usd": 0.0,
                "best_trade_usd": 0.0,
                "worst_trade_usd": 0.0,
                "recent_trades": [],
                "last_trade_tx": None,
                "protocols": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        winning = [t for t in self.trades if t["net_profit_usd"] > 0]
        losing = [t for t in self.trades if t["net_profit_usd"] <= 0]
        total_profit = sum(t["gross_profit_usd"] for t in self.trades)

        # Stats par protocole
        protocols = {}
        for t in self.trades:
            p = t["protocol"]
            if p not in protocols:
                protocols[p] = {"trades": 0, "profit": 0.0}
            protocols[p]["trades"] += 1
            protocols[p]["profit"] += t["net_profit_usd"]

        return {
            "balance_usd": round(self.balance_usd, 6),
            "initial_balance_usd": self.initial_balance,
            "realized_pnl_usd": round(self.balance_usd - self.initial_balance, 6),
            "total_trades": len(self.trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": round(len(winning) / len(self.trades) * 100, 1),
            "total_profit_usd": round(total_profit, 6),
            "total_gas_usd": round(self.total_gas_usd, 6),
            "net_profit_usd": round(total_profit - self.total_gas_usd, 6),
            "best_trade_usd": round(max(t["net_profit_usd"] for t in self.trades), 6),
            "worst_trade_usd": round(min(t["net_profit_usd"] for t in self.trades), 6),
            "recent_trades": self.trades[-20:][::-1],
            "last_trade_tx": self.trades[-1]["tx_hash"],
            "protocols": protocols,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Instance globale
simulator = MultiDexSimulator(seed=int(time.time()) % 10000)
