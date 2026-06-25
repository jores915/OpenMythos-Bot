import time
import requests
from web3 import Web3
from connectors.blockchain import BlockchainConnector
from connectors.telegram import TelegramNotifier

STABLE_COINS = {
    "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
    "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca",
    "0x50c5725949a6f0c72e6c4a641f24049a917db0cb",
}

def encode_v3_path(token_list, fee=3000):
    token0 = Web3.to_checksum_address(token_list[0]).lower()
    token1 = Web3.to_checksum_address(token_list[1]).lower()
    fee_bytes = fee.to_bytes(3, 'big')
    return bytes.fromhex(token0[2:]) + fee_bytes + bytes.fromhex(token1[2:])

class FlashArbScanner:
    def __init__(self, rpc_url, private_key, contract_address, arb_abi, bot_token=None, chat_id=None):
        self.conn = BlockchainConnector(rpc_url, private_key)
        self.w3 = self.conn.w3
        self.account = self.conn.account
        self.contract = self.w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=arb_abi)
        self.telegram = TelegramNotifier(bot_token, chat_id) if bot_token and chat_id else None

    def simulate_profit(self, token_in, amount_in, path1, path2):
        try:
            q1 = self._quote_paraswap(token_in, path1[-1], amount_in)
            if not q1: return -1
            intermediate = int(q1['destAmount'])
            q2 = self._quote_paraswap(path1[-1], token_in, intermediate)
            if not q2: return -1
            amount_back = int(q2['destAmount'])
            fee = amount_in * 5 // 10000
            owed = amount_in + fee
            profit_tokens = amount_back - owed
            price = 1.0 if token_in.lower() in STABLE_COINS else 0.0
            if price == 0.0: return -1
            profit_usd = (profit_tokens / 10**18) * price
            gas_usd = (self.w3.eth.gas_price * 600000) / 1e18 * 2500
            net = profit_usd - gas_usd
            if profit_tokens > 0 and net > 0.01:
                print(f"[SIM] Net: ${net:.2f}")
                return net
            return -1
        except Exception as e:
            print(f"Simulation error: {e}")
            return -1

    def execute_if_profitable(self, token_in, amount_in, path1, path2, swap_fee=3000, flash_fee=3000):
        profit = self.simulate_profit(token_in, amount_in, path1, path2)
        if profit <= 0: return None
        encoded1 = encode_v3_path(path1, swap_fee)
        encoded2 = encode_v3_path(path2, swap_fee)
        min_out = int(amount_in * 0.95)
        tx = self.contract.functions.startArbitrage(
            token_in, amount_in, encoded1, encoded2, min_out, flash_fee
        ).build_transaction({
            'from': self.account.address,
            'gas': 600000,
            'gasPrice': self.w3.eth.gas_price
        })
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt and self.telegram:
            self.telegram.send(f"<b>💰 Arbitrage exécuté</b>\nTX: <code>{receipt.transactionHash.hex()}</code>")
        return receipt

    def _quote_paraswap(self, src, dst, amount):
        src = src.lower(); dst = dst.lower()
        url = f"https://apiv5.paraswap.io/prices?srcToken={src}&destToken={dst}&srcDecimals=6&destDecimals=18&amount={amount}&side=SELL&network=8453"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if 'priceRoute' in data:
                    return {'destAmount': data['priceRoute']['destAmount']}
        except Exception as e:
            print(f"ParaSwap error: {e}")
        return None
