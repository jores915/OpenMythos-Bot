# OpenMythos Bot

**LLM-Powered Crypto Intelligence**

Recurrent-Depth Transformer (RDT) implementation for autonomous flash-arbitrage trading on DEXs (Uniswap V3). Includes smart contracts in Solidity (~50 000 lines), a FastAPI dashboard, Telegram bot, RL agent loop, and multiple LLM integrations (Claude, OpenRouter, DeepSeek).

---

## Stack

- **Language:** Python 3.13 / Solidity 0.8.20
- **Blockchain:** Uniswap V3, Flash Arbitrage, Base/Arbitrum
- **AI:** RDT (Recurrent-Depth Transformer), MoE, MLA, GQA
- **Infra:** FastAPI, Telegram Bot, RL Agents, Foundry, vLLM

---

## Structure

```
src/
├── open_mythos/        # RDT model (1B to 1T)
├── contracts/          # Solidity flash-arb contracts
├── agents/             # RL agents, news, macro
├── connectors/         # Telegram, blockchain RPC
├── api/                # FastAPI dashboard
├── tests/              # Benchmarks and unit tests
└── training/           # Fine-tuning scripts (3B)
```

---

## Dashboard

After running `start.sh`:

> `http://<host>:8080`

`GET /api/status` returns JSON status for inference, contracts, agents, network.

---

## Setup

```bash
# Clone
git clone https://github.com/lionj4/openmythos-bot.git

# Python
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Contracts (Foundry)
cd contracts && forge script src/OpenMythosMicroArb.sol:OpenMythosMicroArb

# Run full bot
./start.sh
```

---

## Commands

| Action | Command |
|---|---|
| API only | `python run.py --no-agent --no-telegram` |
| Full start | `./start.sh` |
| Simulate profit | `python simulate_profit.py` |
| Health check | `curl http://localhost:8080/health` |

---

## Author

Lionel Jores · [@lionelj4](https://x.com/lionelj4)

---

## License

MIT
