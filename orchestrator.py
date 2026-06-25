import json
import time
import logging
from connectors.blockchain import BlockchainConnector
from connectors.telegram import TelegramNotifier
from flash_scanner import FlashArbScanner
from agents.macro_sentinel import MacroSentinel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AngelOfDeath:
    def __init__(self, config):
        with open(config["abi_file"]) as f:
            abi = json.load(f)
        self.scanner = FlashArbScanner(
            config["rpc_url"], config["private_key"], config["contract_address"],
            abi, config.get("telegram", {}).get("bot_token"),
            config.get("telegram", {}).get("chat_id"))
        self.sentinel = MacroSentinel(
            events_file=config["events_file"],
            finnhub_token=config.get("finnhub_token"),
            region=config.get("aws_region", "us-east-1"))
        self.opps = [
            ("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", 100_000_000_000,
             ["0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "0x4200000000000000000000000000000000000006"],
             ["0x4200000000000000000000000000000000000006", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"],
             3000, 3000),
        ]

    def run(self):
        print("👼 Ange de la mort en patrouille...")
        while True:
            mode = self.sentinel.get_mode()
            mult = mode.get("multiplier", 1.0)
            print(f"Mode: {mode['mode']} (x{mult})")
            for token_in, amount, p1, p2, swap_fee, flash_fee in self.opps:
                self.scanner.execute_if_profitable(
                    token_in, int(amount * mult), p1, p2, swap_fee, flash_fee)
                time.sleep(2)
            time.sleep(10)

if __name__ == "__main__":
    from load_secrets import load_config
    try:
        cfg = load_config("config.json")
        bot = AngelOfDeath(cfg)
        bot.run()
    except FileNotFoundError:
        logger.error("config.json introuvable")
    except RuntimeError as e:
        logger.error(f"Secrets error: {e}")
