#!/bin/bash
# OpenMythos MicroArb — Script de deploiement Base Sepolia
# Usage: ./deploy_sepolia.sh <PRIVATE_KEY>
# Requires: cast (foundry), python3

set -euo pipefail

CONTRACT_PATH="contracts/src/OpenMythosMicroArb.sol:OpenMythosMicroArb"
ROUTER="0x2626664c2603336E57B271c5C0b26F421741e481"
RPC="https://sepolia.base.org"

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <PRIVATE_KEY>"
    exit 1
fi

PRIVATE_KEY="$1"

echo "[1/3] Compiling..."
forge build

echo "[2/3] Extracting bytecode..."
BYTECODE=$(python3 -c "import json; d=json.load(open('contracts/out/OpenMythosMicroArb.sol/OpenMythosMicroArb.json')); print(d['bytecode']['object'])")

# Constructor arg: router address (32 bytes, left-padded)
CONSTRUCTOR_ARGS="0000000000000000000000002626664c2603336e57b271c5c0b26f421741e481"

echo "[3/3] Deploying to Base Sepolia..."
cast send --rpc-url "$RPC" --private-key "$PRIVATE_KEY" --create "${BYTECODE}${CONSTRUCTOR_ARGS}" --broadcast

echo "[DONE] Contract deployed. Save the address above."
