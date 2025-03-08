"""
Babywise Chatbot - Chat Service

This module provides chat services for the Babywise Chatbot,
handling the interaction with the LangGraph workflow.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from backend.models.message_types import AIMessage, HumanMessage

from backend.workflow.workflow import get_workflow, thread_states, memory_saver
from backend.services.redis_service import get_thread_state, save_thread_state, delete_thread_state

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def process_chat(thread_id: str, message: str, language: str = "en") -> Dict[str, Any]:
    """
    Process a chat message and return a response.
    
    Args:
        thread_id: The ID of the conversation thread
        message: The user's message
        language: The language code (default: "en")
        
    Returns:
        Dict containing the response text, domain, context, and metadata
    """
    try:
        logger.info(f"Processing chat for thread {thread_id}")
        workflow = get_workflow()
        logger.info(f"Configured workflow with thread_id: {thread_id}")
        
        # Create a human message with our custom type
        human_message = HumanMessage(content=message)
        logger.info(f"Created human message: {message}")
        
        # Try to get state from Redis first
        redis_state = await get_thread_state(thread_id)
        
        # Check if we have existing state for this thread
        if redis_state:
            logger.info(f"Using existing state from Redis for thread {thread_id}")
            state = redis_state
            logger.info(f"State type: {type(state).__name__}")
            
            # Add the new message to the state
            if "messages" not in state:
                state["messages"] = []
            state["messages"].append(human_message)
            logger.info(f"Added human message to state, message count: {len(state['messages'])}")
        elif thread_id in thread_states:
            logger.info(f"Using existing state from memory for thread {thread_id}")
            state = thread_states[thread_id]
            logger.info(f"State type: {type(state).__name__}")
            
            # Add the new message to the state
            if "messages" not in state:
                state["messages"] = []
            state["messages"].append(human_message)
            logger.info(f"Added human message to state, message count: {len(state['messages'])}")
        else:
            # Try to retrieve state from memory
            try:
                logger.info(f"Attempting to retrieve state from memory for thread {thread_id}")
                state = memory_saver.get(thread_id)
                if "messages" not in state:
                    state["messages"] = []
                state["messages"].append(human_message)
                logger.info(f"Retrieved state from memory and added message, message count: {len(state['messages'])}")
            except Exception as e:
                logger.info(f"Creating new state for thread {thread_id}: {str(e)}")
                # Create a new state
                state = {
                    "messages": [human_message],
                    "context": {},
                    "domain": "general",
                    "extracted_entities": set(),
                    "language": language,
                    "metadata": {
                        "created_at": datetime.utcnow().isoformat(),
                        "language": language,
                        "thread_id": thread_id
                    },
                    "user_context": {},
                    "routines": {
                        "sleep": [],
                        "feeding": [],
                        "diaper": []
                    }
                }
                logger.info(f"Created new state dictionary, message count: {len(state['messages'])}")
        
        # Run the workflow
        logger.info(f"Running workflow for thread {thread_id}")
        logger.info(f"State before workflow: {state}")
        
        try:
            # Configure the workflow with the thread_id for checkpointing
            workflow_instance = await get_workflow()
            result = await workflow_instance(state)
            logger.info(f"Workflow invoke completed")
            logger.info(f"Result type: {type(result).__name__}")
            
            # Convert result to dictionary if it's not already
            result_dict = dict(result) if not isinstance(result, dict) else result
            
            # Store the updated state in memory as fallback
            thread_states[thread_id] = result_dict
            logger.info(f"Stored updated state in thread_states (memory)")
            
            # Store the updated state in Redis
            redis_save_success = await save_thread_state(thread_id, result_dict)
            if redis_save_success:
                logger.info(f"Successfully stored state in Redis for thread {thread_id}")
            else:
                logger.warning(f"Failed to store state in Redis for thread {thread_id}")
            
            # Extract the assistant's response using our custom AIMessage type
            logger.info(f"Extracting assistant response from messages")
            logger.info(f"Messages count: {len(result_dict['messages'])}")
            logger.info(f"Message types: {[type(msg).__name__ for msg in result_dict['messages']]}")
            assistant_messages = [msg for msg in result_dict['messages'] if isinstance(msg, AIMessage)]
            logger.info(f"Assistant messages count: {len(assistant_messages)}")
            
            # Check if there's a command response (which would be the last message)
            if "metadata" in result_dict and result_dict["metadata"].get("command_processed"):
                logger.info(f"Command was processed, using the last assistant message as response")
                response_text = assistant_messages[-1].content
            else:
                # Use the last assistant message that's not a command response
                response_text = assistant_messages[-1].content if assistant_messages else "I'm sorry, I couldn't generate a response."
            
            logger.info(f"Response text: {response_text[:50]}...")
            
            # Log the context for debugging
            logger.info(f"Context for thread {thread_id}: {json.dumps(result_dict['context'], default=str)}")
            
            # Convert set to list for JSON serialization
            context_copy = result_dict['context'].copy() if result_dict['context'] else {}
            logger.info(f"Created context copy for JSON serialization")
            
            return {
                "text": response_text,
                "domain": result_dict['domain'],
                "context": context_copy,
                "metadata": result_dict['metadata'],
                "language": language
            }
        except Exception as e:
            logger.error(f"Error during workflow.invoke: {str(e)}", exc_info=True)
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error args: {e.args}")
            raise
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}", exc_info=True)
        logger.error(f"Error details: {type(e).__name__}")
        logger.error(f"Error args: {e.args}")
        return {
            "text": f"I'm sorry, I encountered an error processing your message. Error type: {type(e).__name__}. Please try again.",
            "domain": "general",
            "context": {},
            "metadata": {},
            "language": language
        }


async def get_thread_context(thread_id: str) -> Dict[str, Any]:
    """
    Get the current context for a thread.
    
    Args:
        thread_id: The ID of the conversation thread
        
    Returns:
        Dict containing the context and domain
    """
    try:
        # Try to get state from Redis first
        redis_state = await get_thread_state(thread_id)
        if redis_state:
            logger.info(f"Retrieved context from Redis for thread {thread_id}")
            return {
                "context": redis_state["context"],
                "domain": redis_state["domain"]
            }
        
        # Check if we have existing state for this thread in memory
        if thread_id in thread_states:
            state = thread_states[thread_id]
            return {
                "context": state["context"],
                "domain": state["domain"]
            }
        
        # Try to retrieve state from memory
        try:
            state = memory_saver.get(thread_id)
            return {
                "context": state["context"],
                "domain": state["domain"]
            }
        except Exception as e:
            logger.info(f"No state found for thread {thread_id}: {str(e)}")
            return {
                "context": {},
                "domain": "general"
            }
    except Exception as e:
        logger.error(f"Error getting context: {str(e)}", exc_info=True)
        return {
            "context": {},
            "domain": "general"
        }


async def reset_thread_state(thread_id: str) -> Dict[str, Any]:
    """
    Reset the state for a thread.
    
    Args:
        thread_id: The ID of the conversation thread
        
    Returns:
        Dict containing a success message
    """
    try:
        # Remove from thread_states if it exists
        if thread_id in thread_states:
            del thread_states[thread_id]
            logger.info(f"Removed thread {thread_id} from thread_states")
        
        # Try to remove from memory saver
        try:
            memory_saver.delete(thread_id)
            logger.info(f"Removed thread {thread_id} from memory saver")
        except Exception as e:
            logger.info(f"Could not remove thread {thread_id} from memory saver: {str(e)}")
        
        # Remove from Redis
        redis_delete_success = await delete_thread_state(thread_id)
        if redis_delete_success:
            logger.info(f"Successfully deleted state from Redis for thread {thread_id}")
        else:
            logger.warning(f"Failed to delete state from Redis for thread {thread_id}")
        
        return {
            "message": f"Thread {thread_id} has been reset",
            "success": True
        }
    except Exception as e:
        logger.error(f"Error resetting thread: {str(e)}", exc_info=True)
        return {
            "message": f"Error resetting thread {thread_id}: {str(e)}",
            "success": False
        } 