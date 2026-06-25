"""
NewsFetcher — Agrégateur d'événements multi-sources pour MacroSentinel
=======================================================================
Sources :
  1. Finnhub          — headlines macro générales
  2. DeFiLlama        — TVL spikes, nouveaux protocoles, hacks
  3. The Graph        — événements on-chain Base
  4. Governance APIs  — votes Snapshot actifs
  5. Deribit          — expirations d'options BTC/ETH
  6. Web3 Events      — logs on-chain en temps réel
"""

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests
from web3 import Web3

logger = logging.getLogger(__name__)

BASE_CONTRACTS = {
    "uniswap_v3_factory": "0x33128a8fC17869897dcE68Ed026d694621f6FDfD",
    "aave_pool":          "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",
    "aerodrome_voter":    "0x16613524e02ad97eDfeF371bC883F2F5d6C480A5",
    "morpho_blue":        "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb",
    "compound_v3_usdc":   "0xb125E6687d4313864e53df431d5425969c15Eb2",
}

EVENT_TOPICS = {
    "Swap":        "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822",
    "Liquidation": "0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286",
    "VoteCast":    "0xb8e138887d0aa13bab447e82de9d5c1777041ecd21ca36ba824ff1e6c07ddda4",
    "Upgraded":    "0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b",
}


class NewsFetcher:
    FINNHUB_URL   = "https://finnhub.io/api/v1"
    DEFILLAMA_URL = "https://api.llama.fi"
    SNAPSHOT_URL  = "https://hub.snapshot.org/graphql"
    DERIBIT_URL   = "https://www.deribit.com/api/v2/public"

    def __init__(self, api_key: Optional[str] = None, rpc_url: str = "https://mainnet.base.org"):
        self.api_key = api_key
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self._cache: dict = {}
        self._cache_ts: float = 0.0
        self.CACHE_TTL = 300

    def get_macro_sentiment(self) -> dict:
        now = time.time()
        if self._cache and (now - self._cache_ts < self.CACHE_TTL):
            return self._cache
        titles       = self._fetch_finnhub()
        defi_events  = self._fetch_defillama()
        gov_events   = self._fetch_governance()
        options_data = self._fetch_options_expiry()
        onchain      = self._fetch_onchain_events()
        risk_flags   = self._compute_risk_flags(defi_events, options_data, onchain)
        score        = self._compute_score(titles, risk_flags)
        result = {
            "score": score, "titles": titles,
            "defi_events": defi_events, "gov_events": gov_events,
            "options": options_data, "onchain_events": onchain,
            "risk_flags": risk_flags,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        self._cache    = result
        self._cache_ts = now
        return result

    def _fetch_finnhub(self) -> list:
        if not self.api_key:
            return []
        try:
            r = requests.get(f"{self.FINNHUB_URL}/news?category=crypto&token={self.api_key}", timeout=8)
            if r.status_code == 200:
                return [a.get("headline", "") for a in r.json()[:15] if a.get("headline")]
        except Exception as e:
            logger.warning(f"Finnhub error: {e}")
        return []

    def _fetch_defillama(self) -> list:
        events = []
        try:
            r = requests.get(f"{self.DEFILLAMA_URL}/hacks", timeout=8)
            if r.status_code == 200:
                cutoff = (datetime.now(timezone.utc) - timedelta(days=3)).timestamp()
                for h in r.json():
                    if h.get("date", 0) > cutoff:
                        events.append({"type": "HACK", "protocol": h.get("name","?"),
                                       "amount": h.get("amount",0), "chain": h.get("chain","?"), "impact": "CRITICAL"})
        except Exception as e:
            logger.warning(f"DeFiLlama error: {e}")
        try:
            r = requests.get(f"{self.DEFILLAMA_URL}/protocols", timeout=10)
            if r.status_code == 200:
                for p in r.json():
                    if "base" in str(p.get("chains",[])).lower() and p.get("listedAt",0) > time.time()-86400*7:
                        events.append({"type": "NEW_PROTOCOL", "protocol": p.get("name","?"),
                                       "tvl": p.get("tvl",0), "impact": "LOW"})
        except Exception as e:
            logger.warning(f"DeFiLlama protocols error: {e}")
        return events

    def _fetch_governance(self) -> list:
        events = []
        spaces = ["aave.eth", "uniswapgovernance.eth", "compound-governance.eth", "morpho.eth"]
        query = '{ proposals(first:10, where:{space_in:' + str(spaces).replace("'",'"') + ', state:"active"}, orderBy:"created", orderDirection:desc) { id title space{id} end state } }'
        try:
            r = requests.post(self.SNAPSHOT_URL, json={"query": query}, timeout=10,
                              headers={"Content-Type": "application/json"})
            if r.status_code == 200:
                for p in r.json().get("data",{}).get("proposals",[]):
                    hours_left = (p.get("end",0) - time.time()) / 3600
                    events.append({"type": "GOVERNANCE_VOTE",
                                   "protocol": p.get("space",{}).get("id","?"),
                                   "title": p.get("title","")[:80],
                                   "hours_left": round(hours_left,1),
                                   "impact": "HIGH" if hours_left < 24 else "MEDIUM"})
        except Exception as e:
            logger.warning(f"Snapshot error: {e}")
        return events

    def _fetch_options_expiry(self) -> dict:
        result = {"btc_expiry_soon": False, "eth_expiry_soon": False,
                  "btc_open_interest": 0, "eth_open_interest": 0}
        try:
            for coin in ["BTC", "ETH"]:
                r = requests.get(f"{self.DERIBIT_URL}/get_instruments",
                                 params={"currency": coin, "kind": "option", "expired": False}, timeout=8)
                if r.status_code == 200:
                    now_ms = time.time() * 1000
                    soon = [i for i in r.json().get("result",[])
                            if 0 < i.get("expiration_timestamp",0) - now_ms < 86400*1000*2]
                    if soon:
                        result[f"{coin.lower()}_expiry_soon"] = True
        except Exception as e:
            logger.warning(f"Deribit error: {e}")
        return result

    def _fetch_onchain_events(self) -> list:
        events = []
        if not self.w3.is_connected():
            return events
        try:
            latest = self.w3.eth.block_number
            from_block = latest - 500
            liq_logs = self.w3.eth.get_logs({
                "address":   Web3.to_checksum_address(BASE_CONTRACTS["aave_pool"]),
                "fromBlock": from_block, "toBlock": "latest",
                "topics":    [EVENT_TOPICS["Liquidation"]],
            })
            if liq_logs:
                events.append({"type": "LIQUIDATIONS", "protocol": "aave",
                                "count": len(liq_logs),
                                "impact": "HIGH" if len(liq_logs) > 5 else "MEDIUM"})
            up_logs = self.w3.eth.get_logs({
                "fromBlock": from_block, "toBlock": "latest",
                "topics":    [EVENT_TOPICS["Upgraded"]],
            })
            if up_logs:
                events.append({"type": "CONTRACT_UPGRADE", "count": len(up_logs), "impact": "HIGH"})
            aero_logs = self.w3.eth.get_logs({
                "address":   Web3.to_checksum_address(BASE_CONTRACTS["aerodrome_voter"]),
                "fromBlock": from_block, "toBlock": "latest",
                "topics":    [EVENT_TOPICS["VoteCast"]],
            })
            if aero_logs:
                events.append({"type": "EPOCH_VOTES", "protocol": "aerodrome",
                                "count": len(aero_logs), "impact": "MEDIUM"})
        except Exception as e:
            logger.warning(f"Web3 events error: {e}")
        return events

    def _compute_risk_flags(self, defi_events, options_data, onchain) -> list:
        flags = []
        if any(e["type"] == "HACK" for e in defi_events):
            flags.append("RECENT_HACK")
        if options_data.get("btc_expiry_soon") or options_data.get("eth_expiry_soon"):
            flags.append("OPTIONS_EXPIRY_IMMINENT")
        liq = [e for e in onchain if e.get("type") == "LIQUIDATIONS"]
        if liq and liq[0].get("count", 0) > 10:
            flags.append("LIQUIDATION_CASCADE")
        if any(e.get("type") == "CONTRACT_UPGRADE" for e in onchain):
            flags.append("CONTRACT_UPGRADED")
        return flags

    def _compute_score(self, titles: list, risk_flags: list) -> float:
        score = 0.0
        neg = ["hack","exploit","crash","ban","sec","lawsuit","liquidat","rug","scam","suspend","delist"]
        pos = ["etf","approve","bullish","rally","upgrade","launch","partnership","adoption","ath"]
        for title in titles:
            t = title.lower()
            for w in neg: score -= 0.1 if w in t else 0
            for w in pos: score += 0.1 if w in t else 0
        penalties = {"RECENT_HACK": -0.5, "OPTIONS_EXPIRY_IMMINENT": -0.2,
                     "LIQUIDATION_CASCADE": -0.3, "CONTRACT_UPGRADED": -0.1}
        for flag in risk_flags:
            score += penalties.get(flag, 0)
        return round(max(-1.0, min(1.0, score)), 3)
