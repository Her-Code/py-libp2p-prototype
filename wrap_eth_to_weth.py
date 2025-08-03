from web3 import Web3
from eth_account import Account
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to Sepolia via Ankr
w3 = Web3(Web3.HTTPProvider("https://rpc.ankr.com/eth_sepolia/50cc43eb0e3a3f31c8a5af94c16379e0e6ee388a510cd5501b49cb2b94dfbc49"))

# WETH contract on Sepolia
WETH = "0xdd13E55209Fd76AfE204dBda4007C227904f0a81"
WETH_ABI = [
    {
        "inputs": [],
        "name": "deposit",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]

# Load your account
PRIVATE_KEY = os.getenv("EVM_PRIVATE_KEY")
acct = Account.from_key(PRIVATE_KEY)
print("Using address:", acct.address)

# Connect to contract
contract = w3.eth.contract(address=WETH, abi=WETH_ABI)

# Build the transaction
try:
    tx = contract.functions.deposit().build_transaction({
        "from": acct.address,
        "value": w3.to_wei(0.05, "ether"),  # amount to wrap
        "nonce": w3.eth.get_transaction_count(acct.address),
        "gas": 100_000,
        "gasPrice": w3.eth.gas_price,
        "chainId": 11155111  # Sepolia
    })

    # Sign and send transaction
    signed_tx = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    print("✅ WETH deposit tx sent! TX hash:", tx_hash.hex())

    # Optional: Wait for confirmation
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print("✅ Transaction confirmed in block", receipt.blockNumber)

except Exception as e:
    print("❌ Error sending transaction:", str(e))

    # """
# WETH Wrapping Utility for Ethereum (Sepolia Testnet)

# This script allows users to wrap Ether (ETH) into Wrapped Ether (WETH) on the Sepolia testnet.
# WETH is an ERC-20 token representation of ETH, required for many DeFi protocols.

# Usage:
#     python wrap_eth.py

# Requirements:
#     - Web3.py library
#     - Ethereum account with testnet ETH
#     - .env file with configuration
# """

# import os
# from dotenv import load_dotenv
# from web3 import Web3
# from eth_account import Account

# # Load environment variables from .env file
# # Expected variables:
# # - ANKR_SEPOLIA_URL: RPC endpoint URL
# # - EVM_PRIVATE_KEY: Private key for the sending account
# load_dotenv()

# # Setup Web3 connection using Ankr's Sepolia RPC endpoint
# ANKR_SEPOLIA_URL = os.getenv("ANKR_SEPOLIA_URL")
# w3 = Web3(Web3.HTTPProvider(ANKR_SEPOLIA_URL))

# # Validate the connection to the Ethereum node
# if not w3.is_connected():
#     raise ConnectionError("Failed to connect to Ankr Sepolia RPC")

# # WETH contract configuration for Sepolia testnet
# # Contract address for Wrapped Ether (WETH)
# WETH = "0xdd13E55209Fd76AfE204dBda4007C227904f0a81"

# # Minimal ABI required for WETH deposit function
# WETH_ABI = [
#     {
#         "inputs": [],
#         "name": "deposit",
#         "outputs": [],
#         "stateMutability": "payable",  # Accepts ETH payments
#         "type": "function"
#     }
# ]

# # Load the Ethereum account from private key
# # Note: In production, use more secure key management
# PRIVATE_KEY = os.getenv("EVM_PRIVATE_KEY")
# acct = Account.from_key(PRIVATE_KEY)
# print("Using address:", acct.address)

# # Initialize the WETH contract instance
# contract = w3.eth.contract(address=WETH, abi=WETH_ABI)

# """
# Transaction Building and Execution Flow:
# 1. Build the deposit transaction
# 2. Sign the transaction with the private key
# 3. Send the raw transaction
# 4. Wait for confirmation (optional)
# """
# try:
#     # Build the transaction dictionary
#     tx = contract.functions.deposit().build_transaction({
#         "from": acct.address,  # Sender address
#         "value": w3.to_wei(0.05, "ether"),  # Amount of ETH to wrap (0.05 ETH)
#         "nonce": w3.eth.get_transaction_count(acct.address),  # Prevent replay attacks
#         "gas": 100_000,  # Fixed gas limit (sufficient for WETH deposit)
#         "gasPrice": w3.eth.gas_price,  # Current network gas price
#         "chainId": 11155111  # Sepolia testnet chain ID
#     })

#     # Sign the transaction with the private key
#     # This creates the cryptographic signature
#     signed_tx = acct.sign_transaction(tx)

#     # Send the raw signed transaction to the network
#     tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
#     print("WETH deposit tx sent! TX hash:", tx_hash.hex())

#     # Optional: Wait for transaction confirmation
#     # This polls the network until the transaction is mined
#     receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
#     print("Transaction confirmed in block", receipt.blockNumber)

# except Exception as e:
#     # Handle any errors that occur during the process
#     print("Error sending transaction:", str(e))
#     # Note: In production, implement more specific error handling