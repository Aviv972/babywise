#!/usr/bin/env python3
"""
Test script for the chat function
"""

import logging
import sys
import asyncio
from backend.services.chat_service import process_chat

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   handlers=[logging.StreamHandler(sys.stdout)])

logger = logging.getLogger(__name__)

async def test_chat():
    """Test the chat function"""
    try:
        logger.info("Testing chat function")
        
        # Call the chat function
        result = await process_chat(
            thread_id="test123",
            message="hello",
            language="en"
        )
        
        logger.info(f"Chat result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in test_chat: {str(e)}", exc_info=True)
        return {"error": str(e)}

if __name__ == "__main__":
    asyncio.run(test_chat()) 