import subprocess
import json
import os

def load_private_key() -> str:
    result = subprocess.run(
        ["gpg", "--batch", "--yes", "-d",
         os.path.expanduser("~/.secrets/openmythos.gpg")],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return result.stdout.strip()
    raise RuntimeError("Impossible de charger la clé privée")

def load_config(config_path="config.json") -> dict:
    with open(config_path) as f:
        config = json.load(f)
    config["private_key"] = load_private_key()
    return config

if __name__ == "__main__":
    cfg = load_config()
    from eth_account import Account
    acc = Account.from_key(cfg["private_key"])
    print("✅ Config chargée")
    print("Adresse publique:", acc.address)
