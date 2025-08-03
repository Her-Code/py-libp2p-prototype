"""
Agent A Implementation for Stellar P2P Coordination Network

This module implements the initiator node (Agent A) in a peer-to-peer network 
that coordinates Stellar transactions and cross-chain swaps. It handles:
- Peer discovery and connection management
- Intent broadcasting and response handling
- Direct connections to known peers
- Continuous network presence advertising
"""

import trio
import json
import logging
import warnings
from libp2p import new_host
from libp2p.peer.peerinfo import info_from_p2p_addr
from multiaddr import Multiaddr
from protocol import PROTOCOL_ID
import os

# ==================== CONFIGURATION SETUP ====================

# Configure logging and suppress warnings
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AgentA")

# Suppress debug logs from libp2p and web3 for cleaner output
logging.getLogger('libp2p').setLevel(logging.WARNING)
logging.getLogger('multiaddr').setLevel(logging.WARNING)
warnings.filterwarnings("ignore", message="pkg_resources is deprecated")

# Network constants (replace with actual values)
AGENT_B_PEER_ID = "QmT2BHjCYTn8fnbMyUmDefQMsbsj2D5jsQSaU5Tjnw7Nor"  # Agent B's peer ID
AGENT_B_ADDRESS = "/ip4/127.0.0.1/tcp/9000"  # Default localhost address for Agent B

# ==================== AGENT A IMPLEMENTATION ====================

class AgentA:
    """Main class implementing Agent A's P2P functionality."""

    def __init__(self):
        """Initialize Agent A with default settings and empty peer list."""
        self.known_peers = set()  # Set of known peer addresses
        self.discovery_topic = "/stellar/peers/v0.1"  # Pubsub topic for peer discovery
        self.connected = False  # Connection status flag
        self.host = None  # Will hold the libp2p host instance
        logger.info("AgentA initialized")

    async def initialize_host(self):
        """
        Initialize and configure the libp2p host.
        
        Creates a new libp2p host instance and sets up network listening.
        """
        logger.info("Initializing libp2p host...")
        self.host = new_host()
        logger.info(f"AgentA Peer ID: {self.host.get_id().to_base58()}")

        # Listen on all interfaces at port 9001
        await self.host.get_network().listen(Multiaddr("/ip4/0.0.0.0/tcp/9001"))
        logger.info("Host initialization complete")

    async def discover_peers(self):
        """
        Continuously discover and maintain connections with peers.
        
        Listens on the discovery topic for new peer advertisements and
        attempts to connect to any newly discovered peers.
        """
        while True:
            try:
                async with self.host.pubsub.subscribe(self.discovery_topic) as subscriber:
                    logger.info(f"Listening for peers on {self.discovery_topic}")
                    async for message in subscriber:
                        try:
                            peer_addr = Multiaddr(message.data.decode())
                            if peer_addr not in self.known_peers:
                                logger.info(f"Discovered new peer: {peer_addr}")
                                peer_info = info_from_p2p_addr(peer_addr)
                                await self.connect_to_peer(peer_info)
                        except Exception as e:
                            logger.error(f"Peer processing error: {e}")
            except Exception as e:
                logger.error(f"Discovery error: {e}")
                await trio.sleep(5)  # Wait before retrying

    async def connect_to_peer(self, peer_info):
        """
        Establish connection to a specific peer.
        
        Args:
            peer_info: PeerInfo object containing peer's ID and addresses
            
        Attempts connection and sends initial intent if this is the first
        successful connection.
        """
        try:
            logger.info(f"Attempting connection to {peer_info.peer_id}")
            await self.host.connect(peer_info)
            self.known_peers.add(peer_info.addrs[0])
            logger.info(f"Successfully connected to {peer_info.peer_id}")

            # If this is our first connection, send an initial intent
            if not self.connected:
                if await self.send_intent(peer_info.peer_id):
                    self.connected = True
        except Exception as e:
            logger.error(f"Connection failed to {peer_info.peer_id}: {e}")

    async def advertise_self(self):
        """
        Continuously advertise our presence on the network.
        
        Periodically publishes our multiaddress to the discovery topic
        so other peers can find and connect to us.
        """
        while True:
            try:
                # Create our full multiaddress (IP + Port + Peer ID)
                our_addr = self.host.get_addrs()[0].encapsulate(
                    f"/p2p/{self.host.get_id()}"
                )

                # Publish to discovery topic
                await self.host.pubsub.publish(
                    self.discovery_topic,
                    str(our_addr).encode()
                )
                logger.debug("Published our address to network")
                await trio.sleep(30)  # Advertise every 30 seconds
            except Exception as e:
                logger.error(f"Advertising error: {e}")
                await trio.sleep(5)  # Wait before retrying

    async def send_intent(self, peer_id, intent_path="intents/sample_intent.json"):
        """
        Send an intent to a specific peer.
        
        Args:
            peer_id: ID of the peer to send to
            intent_path: Path to JSON file containing intent data
            
        Returns:
            bool: True if intent was successfully sent and acknowledged
            
        Opens a new stream to the peer, sends the intent, and waits for response.
        """
        try:
            logger.info(f"Opening stream to {peer_id}")
            stream = await self.host.new_stream(peer_id, [PROTOCOL_ID])

            try:
                writer = stream.get_writer()
                reader = stream.get_reader()

                # Load and send intent data
                with open(intent_path) as f:
                    intent_data = json.load(f)

                logger.info(f"Sending intent to {peer_id}")
                await writer.write(json.dumps(intent_data).encode())
                await writer.drain()  # Ensure all data is sent

                # Wait for response
                response = await reader.read(1000)
                logger.info(f"Received response: {response.decode()}")
                return True
            finally:
                await stream.close()  # Always close the stream
        except Exception as e:
            logger.error(f"Intent sending failed: {e}")
            return False

# ==================== MAIN EXECUTION ====================

async def main():
    """
    Main entry point for Agent A.
    
    Initializes the agent, establishes connections, and manages the main event loop.
    """
    agent = AgentA()
    await agent.initialize_host()

    # Attempt direct connection to Agent B first
    agent_b_addr = Multiaddr(f"{AGENT_B_ADDRESS}/p2p/{AGENT_B_PEER_ID}")
    agent_b_info = info_from_p2p_addr(agent_b_addr)

    try:
        logger.info(f"Attempting direct connection to Agent B: {AGENT_B_PEER_ID}")
        await agent.host.connect(agent_b_info)
        logger.info("Successfully connected to Agent B")

        # Send initial intent immediately after connecting
        if await agent.send_intent(agent_b_info.peer_id):
            agent.connected = True
    except Exception as e:
        logger.error(f"Failed to connect to Agent B: {e}")

    # Start background tasks for peer discovery and advertising
    async with trio.open_nursery() as nursery:
        nursery.start_soon(agent.discover_peers)
        nursery.start_soon(agent.advertise_self)

        # Main connection maintenance loop
        while True:
            # If not connected, try sending to known peers
            if not agent.connected and agent.known_peers:
                for peer_addr in agent.known_peers:
                    peer_info = info_from_p2p_addr(peer_addr)
                    if await agent.send_intent(peer_info.peer_id):
                        agent.connected = True
                        break
            await trio.sleep(10)  # Check connection status every 10 seconds

if __name__ == "__main__":
    try:
        trio.run(main)
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")