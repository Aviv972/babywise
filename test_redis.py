"""
Babywise Chatbot - Redis Test Script

This script tests the Redis functionality for the Babywise Chatbot.
"""

import logging
import os
import uuid
import json
from datetime import datetime

from backend.services.redis_service import (
    kv_client,
    save_thread_state,
    get_thread_state,
    delete_thread_state
)
from backend.services.message_types import HumanMessage, AIMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_redis_operations():
    """Test basic Redis operations directly with the KV client"""
    # Generate a unique thread ID for testing
    thread_id = f"test_{uuid.uuid4().hex[:8]}"
    logger.info(f"Testing Redis operations with thread ID: {thread_id}")
    
    # Create a test state (simplified to avoid LangChain dependencies)
    test_state = {
        "messages": [
            HumanMessage(
                content="Hello, I have a question about my baby's sleep.",
                additional_kwargs={}
            ),
            AIMessage(
                content="I'd be happy to help with your baby's sleep. How old is your baby?",
                additional_kwargs={}
            )
        ],
        "context": {
            "baby_age": "6 months",
            "sleep_issue": "waking up frequently"
        },
        "domain": "sleep",
        "extracted_entities": {"baby_age", "sleep_issue"},
        "language": "en",
        "metadata": {
            "created_at": datetime.utcnow().isoformat(),
            "thread_id": thread_id
        },
        "user_context": {},
        "routines": {
            "sleep": [],
            "feeding": [],
            "diaper": []
        }
    }
    
    if not kv_client:
        logger.error("Redis client not initialized. Check your environment variables.")
        return
    
    # Test direct Redis operations
    try:
        # Test saving state
        logger.info("Testing Redis SET operation...")
        result = save_thread_state(thread_id, test_state)
        logger.info(f"SET operation result: {result}")
        
        # Test retrieving state
        logger.info("Testing Redis GET operation...")
        retrieved_state = get_thread_state(thread_id)
        
        if retrieved_state:
            logger.info("Successfully retrieved state from Redis")
            logger.info(f"Domain: {retrieved_state['domain']}")
            logger.info(f"Context: {retrieved_state['context']}")
            logger.info(f"Message count: {len(retrieved_state['messages'])}")
            
            # Verify the messages were properly retrieved
            for i, msg in enumerate(retrieved_state['messages']):
                logger.info(f"Message {i+1} type: {msg.__class__.__name__}")
                logger.info(f"Message {i+1} content: {msg.content[:50]}...")
        else:
            logger.error("Failed to retrieve state from Redis")
        
        # Test deleting state
        logger.info("Testing Redis DELETE operation...")
        result = delete_thread_state(thread_id)
        logger.info(f"DELETE operation result: {result}")
        
        # Verify deletion
        logger.info("Verifying deletion...")
        deleted_state = get_thread_state(thread_id)
        if deleted_state is None:
            logger.info("Successfully verified deletion")
        else:
            logger.error("Failed to delete state from Redis")
            
    except Exception as e:
        logger.error(f"Error during Redis operations: {str(e)}")

if __name__ == "__main__":
    # Run the test
    test_redis_operations() 