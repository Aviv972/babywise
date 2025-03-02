"""
Babywise Chatbot - Chat Module

This module implements the chat function that interfaces with the service module
to process user messages and generate responses.
"""

import logging
import os
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the chat service function
from backend.services.chat_service import process_chat

async def chat(thread_id: Optional[str], message: str, language: str = "en") -> Dict[str, Any]:
    """
    Process a chat message and return a response using the chat service.
    
    Args:
        thread_id: Optional thread ID for conversation continuity
        message: User message
        language: Language code (e.g., 'en', 'he', 'ar')
        
    Returns:
        Dict containing the response text, thread_id, domain, context, and metadata
    """
    try:
        logger.info(f"Processing chat message for thread {thread_id}")
        
        # Generate a thread ID if not provided
        if not thread_id:
            thread_id = os.urandom(16).hex()
            logger.info(f"Generated new thread ID: {thread_id}")
        
        # Call the chat service function
        result = await process_chat(
            thread_id=thread_id,
            message=message,
            language=language
        )
        
        logger.info(f"Generated response for thread {thread_id}")
        
        # Return the response
        return {
            "text": result["text"],
            "thread_id": thread_id,
            "domain": result["domain"],
            "context": result["context"],
            "metadata": result["metadata"]
        }
    except Exception as e:
        logger.error(f"Error in chat function: {str(e)}", exc_info=True)
        raise 