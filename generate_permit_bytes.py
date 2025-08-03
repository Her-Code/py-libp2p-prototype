"""
Permit2 Authorization Generator for 1inch Fusion

This script generates EIP-712 compliant Permit2 authorization signatures that allow
1inch Fusion to spend tokens on behalf of the user without requiring separate approvals.

The script:
1. Configures EIP-712 typed data structure
2. Signs the authorization message
3. Encodes the signed data for submission to 1inch API
"""

import os
import time
import json
from eth_account import Account
from eth_account.messages import encode_structured_data
from eth_abi import encode
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ==================== CONFIGURATION ====================

# Network configuration
CHAIN_ID = 11155111  # Sepolia testnet chain ID

# Contract addresses
PERMIT2_ADDRESS = "0x000000000022D473030F116dDEE9F6B43aC78BA3"  # Standard Permit2 contract
WETH_ADDRESS = "0xdd13E55209Fd76AfE204dBda4007C227904f0a81"  # Wrapped Ether on Sepolia
FUSION_SPENDER = "0x1111111254EEB25477B68fb85Ed929f73A960582"  # 1inch Fusion executor

# Wallet setup
PRIVATE_KEY = os.getenv("EVM_PRIVATE_KEY")
assert PRIVATE_KEY, "Missing EVM_PRIVATE_KEY in .env"  # Validate env var exists
ACCOUNT = Account.from_key(PRIVATE_KEY)  # Create account from private key
WALLET_ADDRESS = ACCOUNT.address  # Derived wallet address

# Transaction parameters
AMOUNT = int(0.05 * 1e18)  # 0.05 WETH in wei (18 decimals)
NONCE = 0  # Order nonce (should be incremented for subsequent orders)
DEADLINE = int(time.time()) + 600  # 10 minute validity window

# ==================== EIP-712 STRUCTURE ====================

# EIP-712 typed data structure for Permit2 authorization
typed_data = {
    "types": {
        # Domain separator - identifies the contract and chain
        "EIP712Domain": [
            {"name": "name", "type": "string"},
            {"name": "chainId", "type": "uint256"},
            {"name": "verifyingContract", "type": "address"},
        ],
        # Permit2 transfer authorization structure
        "PermitTransferFrom": [
            {"name": "permitted", "type": "TokenPermissions"},
            {"name": "spender", "type": "address"},
            {"name": "nonce", "type": "uint256"},
            {"name": "deadline", "type": "uint256"},
        ],
        # Token allowance details
        "TokenPermissions": [
            {"name": "token", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
    },
    "primaryType": "PermitTransferFrom",  # Main type being signed
    # Domain separator values
    "domain": {
        "name": "Permit2",
        "chainId": CHAIN_ID,
        "verifyingContract": PERMIT2_ADDRESS,
    },
    # The actual authorization message
    "message": {
        "permitted": {
            "token": WETH_ADDRESS,  # Token being authorized
            "amount": AMOUNT,       # Amount being authorized
        },
        "spender": FUSION_SPENDER,  # 1inch Fusion contract
        "nonce": NONCE,             # Unique order identifier
        "deadline": DEADLINE,       # Expiration timestamp
    },
}

# ==================== SIGNATURE GENERATION ====================

# Create and sign the EIP-712 message
signed_msg = Account.sign_message(
    encode_structured_data(primitive=typed_data),
    private_key=PRIVATE_KEY
)
sig = signed_msg.signature
print(f"Signature: {sig.hex()}")

# ==================== DATA ENCODING ====================

# Extract the message components for encoding
permit_msg = typed_data["message"]
permitted = permit_msg["permitted"]

# ABI encode all parameters into a single bytes string
permit_bytes = encode(
    # Encoding schema:
    # 1. Token and amount tuple
    # 2. Spender address
    # 3. Nonce
    # 4. Deadline
    # 5. Signature bytes
    ["(address,uint256)", "address", "uint256", "uint256", "bytes"],
    [
        (permitted["token"], permitted["amount"]),  # Token and amount
        permit_msg["spender"],                      # 1inch Fusion spender
        permit_msg["nonce"],                        # Order nonce
        permit_msg["deadline"],                     # Expiration time
        sig,                                        # ECDSA signature
    ],
)

# Output the final encoded permit data
print(f"permit_bytes: 0x{permit_bytes.hex()}")