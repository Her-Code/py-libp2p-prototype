import os
import json
import time
import requests
from dotenv import load_dotenv
from eth_account import Account
from eth_account.messages import encode_structured_data
from web3 import Web3

# 🔐 Load .env config
load_dotenv()
CHAIN_ID = 11155111  # Sepolia
PRIVATE_KEY = os.getenv("EVM_PRIVATE_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
API_KEY = os.getenv("INCH_API_KEY")

MAKER_ASSET = "0xdd13E55209Fd76AfE204dBda4007C227904f0a81"  # WETH on Sepolia
TAKER_ASSET = "0xdd13E55209Fd76AfE204dBda4007C227904f0a81"  # WETH on Sepolia
PERMIT2_CONTRACT = "0x000000000022D473030F116dDEE9F6B43aC78BA3"

def register_wallet():
    """Registers the user wallet with 1inch Fusion."""
    url = f"https://api.1inch.dev/fusion/1.0/{CHAIN_ID}/users/{WALLET_ADDRESS}/register"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "accept": "application/json"
    }

    print("📬 Registering wallet with 1inch Fusion...")
    response = requests.post(url, headers=headers)
    print("🔐 Wallet registration response:")
    print(response.status_code)
    print(response.text)

def get_permit2_bytes():
    """Encodes and signs a permit2 message."""
    amount = int(Web3.to_wei("0.05", "ether"))
    nonce = 0
    deadline = int(time.time()) + 3600

    domain = {
        "name": "Permit2",
        "version": "1",
        "chainId": CHAIN_ID,
        "verifyingContract": PERMIT2_CONTRACT,
    }

    types = {
        "EIP712Domain": [
            {"name": "name", "type": "string"},
            {"name": "version", "type": "string"},
            {"name": "chainId", "type": "uint256"},
            {"name": "verifyingContract", "type": "address"},
        ],
        "PermitSingle": [
            {"name": "details", "type": "PermitDetails"},
            {"name": "spender", "type": "address"},
            {"name": "sigDeadline", "type": "uint256"},
        ],
        "PermitDetails": [
            {"name": "token", "type": "address"},
            {"name": "amount", "type": "uint160"},
            {"name": "expiration", "type": "uint48"},
            {"name": "nonce", "type": "uint48"},
        ],
    }

    message = {
        "details": {
            "token": MAKER_ASSET,
            "amount": amount,
            "expiration": deadline,
            "nonce": nonce,
        },
        "spender": TAKER_ASSET,
        "sigDeadline": deadline,
    }

    structured_data = {
        "types": types,
        "domain": domain,
        "primaryType": "PermitSingle",
        "message": message,
    }

    signed = Account.sign_message(encode_structured_data(structured_data), PRIVATE_KEY)
    signature = signed.signature.hex()

    # Manual encoding
    permit_bytes = (
        Web3.to_bytes(hexstr=MAKER_ASSET).rjust(32, b'\x00') +
        amount.to_bytes(32, "big") +
        Web3.to_bytes(hexstr=TAKER_ASSET).rjust(32, b'\x00') +
        nonce.to_bytes(32, "big") +
        deadline.to_bytes(32, "big") +
        len(Web3.to_bytes(hexstr=signature)).to_bytes(32, "big") +
        Web3.to_bytes(hexstr=signature)
    )

    return "0x" + permit_bytes.hex()

def submit_fusion_order(permit_bytes: str):
    """Submits a Fusion order to the 1inch Fusion API."""
    url = f"https://api.1inch.dev/fusion/1.0/{CHAIN_ID}/orders"

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    order_payload = {
        "fromTokenAddress": MAKER_ASSET,
        "toTokenAddress": TAKER_ASSET,
        "amount": Web3.to_wei("0.05", "ether"),
        "fromAddress": WALLET_ADDRESS,
        "receiver": WALLET_ADDRESS,
        "permit": permit_bytes,
        "duration": 1800,
        "auctionBasis": "receiver",
        "salt": str(int(time.time())),
    }

    response = requests.post(url, headers=headers, data=json.dumps(order_payload))
    print("📝 Fusion order response:")
    print(response.status_code)
    print(response.text)

if __name__ == "__main__":
    register_wallet()

    print("⏳ Generating permit2 bytes...")
    permit_bytes = get_permit2_bytes()
    print("✅ Permit bytes generated")

    print("🚀 Submitting Fusion order...")
    submit_fusion_order(permit_bytes)

    # """
# 1inch Fusion Order Submission Script

# This script facilitates the creation and submission of limit orders to 1inch Fusion API.
# It handles:
# 1. Wallet registration with 1inch Fusion
# 2. EIP-712 compliant Permit2 signature generation
# 3. Order creation and submission

# Requirements:
# - Web3.py library
# - 1inch API key
# - Ethereum private key with testnet funds
# """

# import os
# import json
# import time
# import requests
# from dotenv import load_dotenv
# from eth_account import Account
# from eth_account.messages import encode_structured_data
# from web3 import Web3

# # ==================== CONFIGURATION ====================

# # Load environment variables from .env file
# load_dotenv()

# # Network configuration
# CHAIN_ID = 11155111  # Sepolia testnet chain ID

# # Wallet credentials from environment
# PRIVATE_KEY = os.getenv("EVM_PRIVATE_KEY")  # Private key for signing
# WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")  # Corresponding wallet address
# API_KEY = os.getenv("INCH_API_KEY")  # 1inch API key

# # Token contract addresses
# MAKER_ASSET = "0xdd13E55209Fd76AfE204dBda4007C227904f0a81"  # WETH on Sepolia
# TAKER_ASSET = "0xdd13E55209Fd76AfE204dBda4007C227904f0a81"  # WETH on Sepolia

# # Permit2 contract address (standard across all chains)
# PERMIT2_CONTRACT = "0x000000000022D473030F116dDEE9F6B43aC78BA3"

# # ==================== CORE FUNCTIONS ====================

# def register_wallet():
#     """
#     Register the wallet with 1inch Fusion service.

#     This is a prerequisite before submitting any orders to the Fusion API.
#     The registration allows 1inch to track orders and settlements for your address.
#     """
#     url = f"https://api.1inch.dev/fusion/1.0/{CHAIN_ID}/users/{WALLET_ADDRESS}/register"
#     headers = {
#         "Authorization": f"Bearer {API_KEY}",
#         "accept": "application/json"
#     }

#     print("Registering wallet with 1inch Fusion...")
#     response = requests.post(url, headers=headers)

#     # Print response details for debugging
#     print("Wallet registration response:")
#     print(f"Status Code: {response.status_code}")
#     print(f"Response: {response.text}")

# def get_permit2_bytes() -> str:
#     """
#     Generate EIP-712 compliant Permit2 signature data.

#     Returns:
#         str: Hex-encoded Permit2 authorization bytes

#     This creates a signed message that authorizes 1inch to spend tokens
#     on behalf of the user, following the Permit2 standard.
#     """
#     # Transaction parameters
#     amount = int(Web3.to_wei("0.05", "ether"))  # 0.05 WETH in wei
#     nonce = 0  # Unique order nonce
#     deadline = int(time.time()) + 3600  # 1 hour validity

#     # EIP-712 Domain separator
#     domain = {
#         "name": "Permit2",
#         "version": "1",
#         "chainId": CHAIN_ID,
#         "verifyingContract": PERMIT2_CONTRACT,
#     }

#     # Type definitions for structured data signing
#     types = {
#         "EIP712Domain": [
#             {"name": "name", "type": "string"},
#             {"name": "version", "type": "string"},
#             {"name": "chainId", "type": "uint256"},
#             {"name": "verifyingContract", "type": "address"},
#         ],
#         "PermitSingle": [
#             {"name": "details", "type": "PermitDetails"},
#             {"name": "spender", "type": "address"},
#             {"name": "sigDeadline", "type": "uint256"},
#         ],
#         "PermitDetails": [
#             {"name": "token", "type": "address"},
#             {"name": "amount", "type": "uint160"},
#             {"name": "expiration", "type": "uint48"},
#             {"name": "nonce", "type": "uint48"},
#         ],
#     }

#     # The actual message content
#     message = {
#         "details": {
#             "token": MAKER_ASSET,
#             "amount": amount,
#             "expiration": deadline,
#             "nonce": nonce,
#         },
#         "spender": TAKER_ASSET,
#         "sigDeadline": deadline,
#     }

#     # Create and sign the structured data
#     structured_data = {
#         "types": types,
#         "domain": domain,
#         "primaryType": "PermitSingle",
#         "message": message,
#     }

#     signed = Account.sign_message(
#         encode_structured_data(structured_data),
#         PRIVATE_KEY
#     )
#     signature = signed.signature.hex()

#     # Manually encode all parameters into a single bytes string
#     permit_bytes = (
#         Web3.to_bytes(hexstr=MAKER_ASSET).rjust(32, b'\x00') +  # Maker token
#         amount.to_bytes(32, "big") +                            # Amount
#         Web3.to_bytes(hexstr=TAKER_ASSET).rjust(32, b'\x00') +  # Taker token
#         nonce.to_bytes(32, "big") +                             # Nonce
#         deadline.to_bytes(32, "big") +                          # Deadline
#         len(Web3.to_bytes(hexstr=signature)).to_bytes(32, "big") +  # Sig length
#         Web3.to_bytes(hexstr=signature)                         # Signature
#     )

#     return "0x" + permit_bytes.hex()

# def submit_fusion_order(permit_bytes: str):
#     """
#     Submit a Fusion order to 1inch API.

#     Args:
#         permit_bytes: Hex-encoded Permit2 authorization data

#     Creates a limit order with specified parameters and submits
#     it to 1inch Fusion API for execution.
#     """
#     url = f"https://api.1inch.dev/fusion/1.0/{CHAIN_ID}/orders"

#     # API request headers
#     headers = {
#         "accept": "application/json",
#         "Authorization": f"Bearer {API_KEY}",
#         "Content-Type": "application/json",
#     }

#     # Order parameters
#     order_payload = {
#         "fromTokenAddress": MAKER_ASSET,
#         "toTokenAddress": TAKER_ASSET,
#         "amount": Web3.to_wei("0.05", "ether"),
#         "fromAddress": WALLET_ADDRESS,
#         "receiver": WALLET_ADDRESS,
#         "permit": permit_bytes,  # Our signed authorization
#         "duration": 1800,  # 30 minutes order duration
#         "auctionBasis": "receiver",  # Who gets the price improvement
#         "salt": str(int(time.time())),  # Unique order identifier
#     }

#     # Submit the order
#     response = requests.post(url, headers=headers, data=json.dumps(order_payload))

#     # Print response details
#     print("Fusion order response:")
#     print(f"Status Code: {response.status_code}")
#     print(f"Response: {response.text}")

# # ==================== MAIN EXECUTION ====================

# if __name__ == "__main__":
#     # Step 1: Register wallet with 1inch Fusion
#     register_wallet()

#     # Step 2: Generate Permit2 authorization signature
#     print("⏳ Generating permit2 bytes...")
#     permit_bytes = get_permit2_bytes()
#     print("Permit bytes generated")

#     # Step 3: Submit the Fusion order
#     print("Submitting Fusion order...")
#     submit_fusion_order(permit_bytes)