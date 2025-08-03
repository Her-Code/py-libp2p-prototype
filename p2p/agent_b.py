"""
Stellar P2P Network - Agent B Implementation

This module implements the responder node (Agent B) in a peer-to-peer network
that coordinates Stellar transactions and cross-chain swaps. Key responsibilities:
- Listening for and processing incoming intents
- Validating and executing Stellar transactions
- Coordinating cross-chain swaps via 1inch API
- Maintaining network presence through peer discovery
"""

import os
import trio
from libp2p import new_host
from libp2p.peer.peerinfo import info_from_p2p_addr
from multiaddr import Multiaddr
from typing import Dict, Any
import json
from web3 import Web3
from enum import Enum
from stellar_sdk import TransactionEnvelope, Network, Server
import requests
from dataclasses import dataclass
import logging
from dotenv import load_dotenv

# ==================== CONFIGURATION SETUP ====================

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AgentB")

# Network Constants
PROTOCOL_ID = "/stellar/coordination/1.0.0"  # Protocol identifier for communication
HORIZON_URL = "https://horizon-testnet.stellar.org"  # Stellar testnet Horizon server
INCH_API_URL = "https://api.1inch.dev/swap/v5.2/11155111"  # 1inch API endpoint for Sepolia

# Peer Configuration (Update with Agent A's actual values)
AGENT_A_PEER_ID = "Qm..."  # Replace with Agent A's peer ID
AGENT_A_ADDRESS = "/ip4/127.0.0.1/tcp/9001"  # Default localhost address for Agent A

# ==================== DATA STRUCTURES ====================

@dataclass
class SwapParams:
    """Container for swap parameters needed for 1inch API requests."""
    from_token: str  # Source token contract address
    to_token: str    # Destination token contract address
    amount: int      # Amount to swap (in wei/smallest unit)
    slippage: float  # Maximum acceptable slippage percentage
    deadline: int    # Unix timestamp for swap expiration

class AgentRoles(Enum):
    """Enumeration defining possible roles for the agent."""
    PAYER = 1            # Initiates payments
    RECIPIENT = 2        # Receives payments
    ORACLE = 3           # Provides external data
    SWAP_COORDINATOR = 4 # Handles cross-chain swaps

# ==================== AGENT B IMPLEMENTATION ====================

class AgentB:
    """Main class implementing Agent B's core functionality."""

    def __init__(self):
        """Initialize Agent B with network connections and services."""
        logger.info("Initializing AgentB...")
        self.role = AgentRoles.SWAP_COORDINATOR
        self.stellar_server = Server(HORIZON_URL)
        self.connected = False  # Track connection status

        # Configure Web3 connection to Ethereum network
        infura_url = f"https://sepolia.infura.io/v3/{os.getenv('INFURA_KEY')}"
        self.w3 = Web3(Web3.HTTPProvider(infura_url))
        logger.info(f"Web3 connected: {self.w3.is_connected()}")

        # Configure 1inch API access
        self.inch_headers = {"Authorization": f"Bearer {os.getenv('INCH_API_KEY')}"}
        logger.info("AgentB initialized successfully")

    async def submit_stellar_tx(self, tx_envelope: TransactionEnvelope) -> Dict[str, Any]:
        """
        Submit a Stellar transaction to the network.
        
        Args:
            tx_envelope: Signed transaction envelope in XDR format
            
        Returns:
            Dictionary containing:
            - status: "SUCCESS" or "ERROR"
            - tx_hash: Transaction hash (if successful)
            - reason: Error message (if failed)
        """
        try:
            logger.info("Submitting Stellar transaction...")
            response = self.stellar_server.submit_transaction(tx_envelope)
            logger.info(f"Stellar tx successful: {response['hash']}")
            return {
                "status": "SUCCESS",
                "tx_hash": response["hash"],
                "ledger": response["ledger"]
            }
        except Exception as e:
            logger.error(f"Stellar submission failed: {e}")
            return {"status": "ERROR", "reason": str(e)}

    async def get_1inch_quote(self, params: SwapParams) -> Dict[str, Any]:
        """
        Get a swap quote from 1inch API.
        
        Args:
            params: SwapParams containing token addresses and amounts
            
        Returns:
            Dictionary containing swap quote or error information
        """
        try:
            logger.info("Fetching 1inch quote...")
            url = f"{INCH_API_URL}/quote"
            params = {
                "src": params.from_token,
                "dst": params.to_token,
                "amount": params.amount,
                "slippage": params.slippage
            }
            response = requests.get(url, headers=self.inch_headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"1inch quote failed: {e}")
            return {"status": "ERROR", "reason": str(e)}

    async def initiate_1inch_swap(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a cross-chain swap using 1inch API.
        
        Args:
            intent: Dictionary containing swap parameters from received intent
            
        Returns:
            Dictionary containing swap transaction details or error information
        """
        try:
            logger.info("Initiating 1inch swap...")
            swap_params = SwapParams(
                from_token=intent["swap_params"]["from_token"],
                to_token=intent["swap_params"]["to_token"],
                amount=int(intent["swap_params"]["amount"]),
                slippage=float(intent["swap_params"]["slippage"]),
                deadline=int(intent["swap_params"].get("deadline", 1800))
            )

            quote = await self.get_1inch_quote(swap_params)
            if quote.get("status") == "ERROR":
                return quote

            return {
                "status": "SWAP_READY",
                "quote": quote,
                "tx": {
                    "to": quote["tx"]["to"],
                    "data": quote["tx"]["data"],
                    "value": quote["tx"]["value"],
                    "gas": 300000
                }
            }
        except Exception as e:
            logger.error(f"Swap initiation failed: {e}")
            return {"status": "ERROR", "reason": str(e)}

    async def handle_stellar_payment(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a Stellar payment intent.
        
        Args:
            intent: Dictionary containing payment details and XDR envelope
            
        Returns:
            Dictionary containing processing results for both Stellar and swap (if applicable)
        """
        try:
            logger.info("Processing Stellar payment intent...")
            tx = TransactionEnvelope.from_xdr(
                intent["xdr"],
                network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE
            )

            stellar_result = await self.submit_stellar_tx(tx)
            if stellar_result["status"] != "SUCCESS":
                return stellar_result

            if intent.get("swap_required"):
                swap_result = await self.initiate_1inch_swap(intent)
                return {
                    "stellar": stellar_result,
                    "swap": swap_result
                }

            return {"stellar": stellar_result}
        except Exception as e:
            logger.error(f"Payment processing failed: {e}")
            return {"status": "ERROR", "reason": str(e)}

# ==================== NETWORK HANDLERS ====================

async def enhanced_handle_intent(stream):
    """
    Handle incoming intent streams from peers.
    
    Args:
        stream: Incoming network stream containing intent data
        
    Processes the intent and sends back a response containing:
    - Status of processing
    - Results of Stellar transaction
    - Swap details (if applicable)
    """
    agent = AgentB()
    reader = stream.get_reader()
    writer = stream.get_writer()

    try:
        # Read and parse incoming intent
        data = await reader.read(2048)
        intent = json.loads(data.decode())
        logger.info(f"Received intent of type: {intent.get('type', 'unknown')}")

        # Validate required fields
        if "xdr" not in intent:
            response = {"status": "ERROR", "reason": "No XDR provided"}
            await writer.write(json.dumps(response).encode())
            return

        # Role-based processing
        if agent.role == AgentRoles.SWAP_COORDINATOR:
            if intent.get("type") == "stellar_payment":
                result = await agent.handle_stellar_payment(intent)
                response = {
                    "status": "PROCESSED",
                    "results": result
                }
            else:
                response = {"status": "UNSUPPORTED_INTENT_TYPE"}

        # Send response back to sender
        await writer.write(json.dumps(response).encode())
        await writer.drain()

    except Exception as e:
        logger.error(f"Intent handling failed: {e}")
        await writer.write(json.dumps({"status": "ERROR", "reason": str(e)}).encode())
    finally:
        await stream.close()  # Ensure stream is always closed

async def advertise_self(host):
    """
    Continuously advertise our presence on the network.
    
    Args:
        host: libp2p host instance
        
    Publishes our multiaddress to the discovery topic at regular intervals
    to allow other peers to find and connect to us.
    """
    while True:
        try:
            our_addr = host.get_addrs()[0].encapsulate(f"/p2p/{host.get_id()}")
            await host.pubsub.publish("/stellar/peers/v0.1", str(our_addr).encode())
            await trio.sleep(30)  # Advertise every 30 seconds
        except Exception as e:
            logger.error(f"Advertising error: {e}")
            await trio.sleep(5)  # Wait before retrying

# ==================== MAIN EXECUTION ====================

async def main():
    """
    Main entry point for Agent B.
    
    Initializes the libp2p host, sets up network listeners,
    and maintains connection with Agent A.
    """
    logger.info("🚀 Starting Agent B")

    try:
        # Initialize libp2p host
        logger.info("Initializing libp2p host...")
        host = new_host()
        logger.info(f"Peer ID: {host.get_id().to_base58()}")

        # Network setup - listen on port 9000
        listen_addr = Multiaddr("/ip4/0.0.0.0/tcp/9000")
        await host.get_network().listen(listen_addr)
        host.set_stream_handler(PROTOCOL_ID, enhanced_handle_intent)
        logger.info(f"Listening on: {listen_addr}")

        # Start background services
        async with trio.open_nursery() as nursery:
            # Start advertising our presence
            nursery.start_soon(advertise_self, host)

            # Attempt direct connection to Agent A
            try:
                agent_a_addr = Multiaddr(f"{AGENT_A_ADDRESS}/p2p/{AGENT_A_PEER_ID}")
                agent_a_info = info_from_p2p_addr(agent_a_addr)
                await host.connect(agent_a_info)
                logger.info(f"Connected to Agent A: {AGENT_A_PEER_ID}")
            except Exception as e:
                logger.warning(f"Couldn't connect to Agent A: {e}")

            logger.info("Agent B ready and waiting for connections...")
            await trio.sleep_forever()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    try:
        trio.run(main)
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")