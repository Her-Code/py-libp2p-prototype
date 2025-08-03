"""
Intent Handler for Stellar P2P Network

This module implements the protocol handler for processing Stellar transaction intents
received over libp2p streams. It validates transaction envelopes and provides responses.
"""

import trio
import json
import logging
from libp2p.network.stream.net_stream import INetStream
from stellar_sdk import TransactionEnvelope, Network
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IntentHandler")

PROTOCOL_ID = "/stellar/coordination/1.0.0"  # Protocol identifier for communication

async def handle_intent(stream: INetStream) -> None:
    """
    Handle incoming intent stream from peers.
    
    Args:
        stream: The incoming network stream containing the intent data
        
    Processes the intent by:
    1. Reading and parsing the JSON data
    2. Validating the intent structure
    3. Verifying the Stellar transaction
    4. Sending back a response
    
    Closes the stream when done, regardless of success/failure.
    """
    logger.info("Intent handler triggered")
    reader = stream.get_reader()
    writer = stream.get_writer()

    try:
        # 1. Read and parse intent
        logger.debug("Waiting for intent data...")
        data = await reader.read(1000)
        intent = json.loads(data.decode())
        logger.debug(f"Received intent: {intent}")

        # 2. Validate intent structure
        required_fields = ["xdr", "metadata"]
        if not all(k in intent for k in required_fields):
            error_msg = f"Missing required fields. Expected: {required_fields}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # 3. Verify Stellar transaction
        is_valid = await validate_stellar_intent(intent)
        logger.info(f"Intent validation result: {is_valid}")

        # 4. Prepare response
        response = {
            "status": "VALID" if is_valid else "INVALID",
            "message": "Intent processed",
            "valid_signature": is_valid,
            "source_account": intent.get("metadata", {}).get("source")
        }
        logger.debug(f"Prepared response: {response}")

        # 5. Send response
        writer.write(json.dumps(response).encode())
        await writer.drain()
        logger.info("Response sent successfully")

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        response = {"status": "ERROR", "message": f"Invalid JSON: {str(e)}"}
        await writer.write(json.dumps(response).encode())
    except Exception as e:
        logger.error(f"Intent processing failed: {e}")
        response = {"status": "ERROR", "message": str(e)}
        await writer.write(json.dumps(response).encode())
    finally:
        logger.debug("Closing stream")
        await stream.close()

async def validate_stellar_intent(intent_data: Dict[str, Any]) -> bool:
    """
    Validate a Stellar transaction intent.
    
    Args:
        intent_data: Dictionary containing the intent data including XDR envelope
        
    Returns:
        bool: True if the transaction is valid, False otherwise
        
    Performs the following validations:
    1. Basic data type checking
    2. Required field presence
    3. XDR envelope parsing
    4. Signature verification
    5. Sequence number validation
    """
    try:
        # 1. Basic data type checking
        if not isinstance(intent_data, dict):
            raise ValueError("Intent data must be a dictionary")

        # 2. Required fields check
        if "xdr" not in intent_data:
            raise ValueError("Missing XDR transaction envelope")

        # 3. Parse XDR envelope
        logger.debug("Parsing transaction envelope")
        tx_envelope = TransactionEnvelope.from_xdr(
            intent_data["xdr"],
            network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE
        )

        # 4. Signature verification
        if not tx_envelope.signatures:
            raise ValueError("No signatures present in transaction")

        # 5. Sequence number validation
        if tx_envelope.transaction.sequence == 0:
            raise ValueError("Invalid sequence number (0)")

        # 6. Full verification
        tx_envelope.verify()
        logger.debug("Transaction validation successful")
        return True

    except Exception as e:
        logger.error(f"Validation failed: {type(e).__name__}: {str(e)}")
        return False