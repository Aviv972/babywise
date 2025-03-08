"""
Test Redis connection and basic operations for the Babywise Chatbot.
"""

import os
import sys
import json
import logging
import asyncio
from datetime import datetime

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from backend.services.redis_service import (
    ensure_redis_initialized,
    get_thread_state,
    save_thread_state,
    delete_thread_state
)
from backend.models.message_types import (
    HumanMessage, AIMessage, StateModel,
    Context, Metadata, Routines
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_redis_operations():
    """Test basic Redis operations with our custom message types."""
    try:
        # Initialize Redis
        if not await ensure_redis_initialized():
            logger.error("Failed to initialize Redis")
            return False

        # Generate a unique test thread ID
        test_thread_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Testing Redis operations with thread ID: {test_thread_id}")
        
        # Create test messages
        human_msg = HumanMessage(content="My baby is 3 months old and having trouble sleeping")
        ai_msg = AIMessage(
            content="I understand you're having sleep issues with your 3-month-old. Can you tell me more about their current sleep schedule?",
            function_call=None
        )
        
        logger.info(f"Created human message: {human_msg.model_dump()}")
        logger.info(f"Created AI message: {ai_msg.model_dump()}")
        
        # Create metadata
        metadata = Metadata(
            thread_id=test_thread_id,
            created_at=datetime.utcnow().isoformat()
        )
        
        # Create context
        context = Context(
            baby_age={
                "value": 3,
                "unit": "months",
                "confidence": 0.8
            }
        )
        
        # Create routines
        routines = Routines()
        
        # Create a test state using StateModel
        test_state = StateModel(
            messages=[human_msg, ai_msg],
            context=context,
            domain="sleep",
            extracted_entities={"baby_age"},
            language="en",
            metadata=metadata,
            user_context={},
            routines=routines
        )
        
        # Test serialization
        logger.info("Testing serialization...")
        serialized = test_state.to_dict()
        logger.info(f"Serialized state: {json.dumps(serialized, indent=2)}")
        
        # Test 1: Save state
        logger.info("Testing save_thread_state...")
        save_success = await save_thread_state(test_thread_id, serialized)
        assert save_success, "Failed to save thread state"
        logger.info("✓ save_thread_state test passed")
        
        # Test 2: Get state
        logger.info("Testing get_thread_state...")
        retrieved_state = await get_thread_state(test_thread_id)
        logger.info(f"Retrieved state: {json.dumps(retrieved_state, indent=2)}")
        assert retrieved_state is not None, "Failed to retrieve thread state"
        assert len(retrieved_state["messages"]) == 2, "Message count mismatch"
        assert retrieved_state["messages"][0]["type"] == "human", "First message should be HumanMessage"
        assert retrieved_state["messages"][1]["type"] == "ai", "Second message should be AIMessage"
        assert retrieved_state["domain"] == "sleep", "Domain mismatch"
        assert "baby_age" in retrieved_state["extracted_entities"], "Extracted entities mismatch"
        logger.info("✓ get_thread_state test passed")
        
        # Test 3: Delete state
        logger.info("Testing delete_thread_state...")
        delete_success = await delete_thread_state(test_thread_id)
        assert delete_success, "Failed to delete thread state"
        
        # Verify deletion
        deleted_state = await get_thread_state(test_thread_id)
        assert deleted_state is None, "State still exists after deletion"
        logger.info("✓ delete_thread_state test passed")
        
        logger.info("All Redis operations tests passed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Redis operations test failed: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    asyncio.run(test_redis_operations()) 