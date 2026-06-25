from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

class BlockchainConnector:
    def __init__(self, rpc_url, private_key=None):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        if private_key:
            self.account = self.w3.eth.account.from_key(private_key)
            self.private_key = private_key
        else:
            self.account = None
            self.private_key = None

    def get_gas_price(self):
        return self.w3.eth.gas_price

    def send_transaction(self, to, data=None, value=0):
        if not self.account:
            raise Exception("Compte non initialisé")
        tx = {
            'from': self.account.address,
            'to': to,
            'value': value,
            'gas': 600000,
            'gasPrice': self.get_gas_price(),
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'data': data or b''
        }
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)
