"""
Stellar Asset Issuance and Distribution Script

This script demonstrates a complete workflow for:
1. Creating a custom asset on the Stellar network
2. Establishing a trustline from a receiver account
3. Distributing the asset from issuer to receiver

Requires:
- Python Stellar SDK
- Testnet account credentials
- Environment variables setup
"""

from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# ==================== NETWORK CONFIGURATION ====================

# Initialize connection to Stellar testnet Horizon server
server = Server("https://horizon-testnet.stellar.org")

# Get network passphrase for testnet
network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE

# ==================== ACCOUNT SETUP ====================

# Load keypairs from environment variables
issuer_keypair = Keypair.from_secret(os.getenv("ISSUER_SECRET_KEY"))  # Asset issuer
receiver_keypair = Keypair.from_secret(os.getenv("RECEIVER_SECRET_KEY"))  # Asset receiver

# Get asset code from environment (e.g., "MYASSET")
asset_code = os.getenv("ASSET_CODE")

# Define the custom asset
asset = Asset(code=asset_code, issuer=issuer_keypair.public_key)

# ==================== TRUSTLINE SETUP ====================

def establish_trustline():
    """
    Establish a trustline from receiver to issuer for the custom asset.
    
    Steps:
    1. Load receiver account sequence number
    2. Build change trust transaction
    3. Sign and submit transaction
    
    A trustline is required before an account can hold a custom asset.
    """
    print(f"Establishing trustline for {asset_code}...")

    # Load current receiver account data
    receiver_account = server.load_account(receiver_keypair.public_key)

    # Build trustline transaction
    trust_tx = (
        TransactionBuilder(
            source_account=receiver_account,
            network_passphrase=network_passphrase,
            base_fee=100  # Minimum fee (in stroops)
        )
        .append_change_trust_op(asset=asset)  # Add trustline operation
        .set_timeout(30)  # Transaction timeout (seconds)
        .build()
    )

    # Sign with receiver's key
    trust_tx.sign(receiver_keypair)

    # Submit to network
    server.submit_transaction(trust_tx)
    print(f"Trustline established for {asset_code}")

# ==================== ASSET DISTRIBUTION ====================

def send_asset():
    """
    Send assets from issuer to receiver.
    
    Steps:
    1. Load issuer account sequence number
    2. Build payment transaction
    3. Sign and submit transaction
    
    Note: Trustline must be established first.
    """
    print(f"Preparing to send {asset_code}...")

    # Load current issuer account data
    issuer_account = server.load_account(issuer_keypair.public_key)

    # Build payment transaction
    payment_tx = (
        TransactionBuilder(
            source_account=issuer_account,
            network_passphrase=network_passphrase,
            base_fee=100  # Minimum fee (in stroops)
        )
        .append_payment_op(
            destination=receiver_keypair.public_key,
            asset=asset,
            amount="1000"  # Amount of asset to send
        )
        .set_timeout(30)  # Transaction timeout (seconds)
        .build()
    )

    # Sign with issuer's key
    payment_tx.sign(issuer_keypair)

    # Submit to network
    server.submit_transaction(payment_tx)
    print(f"Sent 1000 {asset_code} from issuer to receiver")

# ==================== MAIN EXECUTION ====================

if __name__ == "__main__":
    # First establish trustline (receiver must trust issuer)
    establish_trustline()
    send_asset()