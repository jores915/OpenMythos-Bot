from web3 import Web3

# Connexion à Ganache
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))

def simulate_gain(token_in, amount_in, price_in_usd, token_out, price_out_usd, fee_percent=0.003):
    """
    Simule un arbitrage et calcule le gain en $.
    - token_in : nom du token d'entrée (ex: "ETH")
    - amount_in : montant en wei (ex: 10**18 pour 1 ETH)
    - price_in_usd : prix du token d'entrée en $
    - token_out : nom du token de sortie
    - price_out_usd : prix du token de sortie en $
    - fee_percent : frais de swap (0.3% par défaut)
    """
    # Convertir le montant en unités humaines
    amount_in_human = amount_in / 10**18
    
    # Valeur d'entrée en $
    value_in_usd = amount_in_human * price_in_usd
    
    # Montant de sortie estimé (après frais)
    amount_out_human = amount_in_human * (price_in_usd / price_out_usd) * (1 - fee_percent)
    value_out_usd = amount_out_human * price_out_usd
    
    # Profit en $
    profit_usd = value_out_usd - value_in_usd
    
    print(f"--- Simulation Arbitrage ---")
    print(f"Token entrée : {amount_in_human} {token_in} (${value_in_usd:.2f})")
    print(f"Token sortie : {amount_out_human:.6f} {token_out} (${value_out_usd:.2f})")
    print(f"Gain estimé   : ${profit_usd:.2f}")
    print(f"Gain %        : {(profit_usd / value_in_usd * 100):.4f}%")
    
    return profit_usd

# --- Exemple de test ---
if __name__ == "__main__":
    # Exemple : vous échangez 1 ETH à 2000$ contre des USDC à 1$
    simulate_gain(
        token_in="ETH", 
        amount_in=Web3.to_wei(1, 'ether'),  # 1 ETH
        price_in_usd=2000.0, 
        token_out="USDC", 
        price_out_usd=1.0
    )
    
    print("\n" + "="*40)
    
    # Exemple avec un prix de sortie plus favorable (arbitrage)
    simulate_gain(
        token_in="ETH", 
        amount_in=Web3.to_wei(1, 'ether'), 
        price_in_usd=2000.0, 
        token_out="USDC", 
        price_out_usd=1.005  # L'USDC est plus cher sur ce marché
    )
