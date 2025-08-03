from web3 import Web3
from eth_account import Account
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to Sepolia via Ankr
w3 = Web3(Web3.HTTPProvider("https://rpc.ankr.com/eth_sepolia/50cc43eb0e3a3f31c8a5af94c16379e0e6ee388a510cd5501b49cb2b94dfbc49"))
print("Connected to Sepolia:", w3.is_connected())

# WETH contract on Sepolia
WETH_ADDRESS = "0xdd13E55209Fd76AfE204dBda4007C227904f0a81"
WETH_ABI = [
    {
        "inputs": [{"name": "wad", "type": "uint256"}],
        "name": "withdraw",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    }
]

# Load your account
PRIVATE_KEY = os.getenv("EVM_PRIVATE_KEY")
acct = Account.from_key(PRIVATE_KEY)
print("Using address:", acct.address)

# Connect to contract
contract = w3.eth.contract(address=WETH_ADDRESS, abi=WETH_ABI)

# Check WETH balance first
weth_balance = contract.functions.balanceOf(acct.address).call()
print(f"Current WETH balance: {w3.from_wei(weth_balance, 'ether')} WETH")

if weth_balance == 0:
    print("No WETH to unwrap")
    exit()

# Build the unwrap transaction
try:
    tx = contract.functions.withdraw(weth_balance).build_transaction({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address),
        "gas": 100_000,
        "gasPrice": w3.eth.gas_price,
        "chainId": 11155111  # Sepolia
    })

    # Sign and send transaction
    signed_tx = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    print("✅ WETH unwrap tx sent! TX hash:", tx_hash.hex())

    # Wait for confirmation
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print("✅ Transaction confirmed in block", receipt.blockNumber)
    print(f"Unwrapped {w3.from_wei(weth_balance, 'ether')} WETH back to ETH")

except Exception as e:
    print("❌ Error sending transaction:", str(e))