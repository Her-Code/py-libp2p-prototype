"""
Ethereum Wallet Balance Checker

This script connects to the Sepolia testnet via Ankr RPC and checks:
- Native ETH balance
- ERC-20 token balances for specified contracts

Requires:
- Web3.py library
- Ankr RPC endpoint URL
- Valid Ethereum wallet address
- Token contract addresses
"""

import os
from web3 import Web3
from dotenv import load_dotenv
from decimal import Decimal, getcontext

# Set precision for Decimal to handle token balances with up to 28 decimal places
# This prevents floating point precision issues with token amounts
getcontext().prec = 28

# Load environment variables from .env file
load_dotenv()

# Configuration constants from environment
ANKR_SEPOLIA_URL = os.getenv("ANKR_SEPOLIA_URL")  # Ankr RPC endpoint for Sepolia
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")      # Wallet address to check balances

# ERC-20 token contracts to check on Sepolia testnet
# Format: { "TOKEN_SYMBOL": { "address": "0x..." } }
TOKENS = {
    "WETH": {
        "address": "0xdd13E55209Fd76AfE204dBda4007C227904f0a81"  # Wrapped Ether contract
    }
    # Additional tokens can be added here following the same format
}

# Minimal ERC-20 ABI (Application Binary Interface) required for balance checks
ERC20_ABI = [
    # balanceOf - Gets the token balance of a specific address
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    # decimals - Gets the number of decimals the token uses
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
    # symbol - Gets the token's ticker symbol
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
]

def main():
    """
    Main function that executes the balance checking workflow.
    
    Steps:
    1. Connects to Sepolia via Ankr RPC
    2. Checks native ETH balance
    3. Checks balances for all specified ERC-20 tokens
    4. Prints formatted results
    """

    # Initialize Web3 connection
    w3 = Web3(Web3.HTTPProvider(ANKR_SEPOLIA_URL))

    # Verify connection to Ethereum node
    if not w3.is_connected():
        print("Failed to connect to Sepolia network.")
        return

    print(f"🔎 Checking balances for: {WALLET_ADDRESS}\n")

    # Check native ETH balance
    try:
        eth_balance = w3.eth.get_balance(Web3.to_checksum_address(WALLET_ADDRESS))
        # Convert from wei to ether and print
        print(f"Ξ ETH Balance: {w3.from_wei(eth_balance, 'ether')} ETH\n")
    except Exception as e:
        print(f"⚠️ Error fetching ETH balance: {e}\n")

    # Check ERC-20 token balances
    for symbol, info in TOKENS.items():
        try:
            # Initialize contract object
            token = w3.eth.contract(
                address=Web3.to_checksum_address(info["address"]),
                abi=ERC20_ABI
            )

            # Get token metadata
            decimals = token.functions.decimals().call()
            actual_symbol = token.functions.symbol().call()

            # Get token balance
            balance = token.functions.balanceOf(
                Web3.to_checksum_address(WALLET_ADDRESS)
            ).call()

            # Convert raw balance to human-readable format
            human_readable = Decimal(balance) / Decimal(10 ** decimals)
            print(f"{actual_symbol} Balance: {human_readable:.6f} {actual_symbol}")

        except Exception as e:
            print(f"⚠️ Error fetching {symbol} balance: {e}")

if __name__ == "__main__":
    # Execute main function when run as a script
    main()