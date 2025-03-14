"""
Babywise Assistant - Chat API Router

This module implements the chat-related API endpoints.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from backend.models.message_types import HumanMessage, AIMessage
from backend.workflow.workflow import get_workflow, get_default_state
from backend.services.redis_service import get_thread_state, save_thread_state, delete_thread_state

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/chat")

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    language: Optional[str] = "en"
    local_event_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    command_processed: bool = False
    command_type: Optional[str] = None
    command_data: Optional[Dict[str, Any]] = None

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a chat message, handling both commands and general chat.
    """
    try:
        logger.info(f"Received chat request: {request.message[:50]}... (thread: {request.thread_id}, language: {request.language})")
        
        # Get or create thread ID
        thread_id = request.thread_id or f"default_{request.language}"
        
        # Try to get thread state from Redis
        state = None
        try:
            state = await get_thread_state(thread_id)
            if state:
                logger.info(f"Retrieved thread state from Redis for {thread_id}")
                # Convert set to list for JSON serialization if needed
                if "extracted_entities" in state and isinstance(state["extracted_entities"], set):
                    state["extracted_entities"] = list(state["extracted_entities"])
        except Exception as e:
            logger.error(f"Error retrieving thread state from Redis: {str(e)}")
            # Continue with a new state
        
        # Create new state if not found
        if not state:
            state = get_default_state()
            state["metadata"]["language"] = request.language
            state["metadata"]["thread_id"] = thread_id
            logger.info(f"Created new thread state for {thread_id}")
        
        # Ensure language is set in state
        state["language"] = request.language
        
        # Add user message to state
        user_message = HumanMessage(content=request.message)
        state["messages"].append(user_message)
        logger.info(f"Added user message to state: {request.message[:50]}...")
        
        # Get workflow instance
        workflow = await get_workflow()
        if not workflow:
            logger.error("Failed to initialize workflow")
            raise HTTPException(status_code=500, detail="Failed to initialize workflow")
        
        # Process through workflow
        try:
            logger.info("Processing message through workflow")
            result = await workflow(state)
            logger.info("Workflow processing completed")
        except Exception as e:
            logger.error(f"Error in workflow processing: {str(e)}")
            # Add error message to state
            error_message = f"I apologize, but I encountered an error processing your request. Please try again."
            state["messages"].append(AIMessage(content=error_message))
            
            # Try to save the state with the error message
            try:
                await save_thread_state(thread_id, state)
            except Exception as save_error:
                logger.error(f"Error saving thread state after workflow error: {str(save_error)}")
            
            return ChatResponse(response=error_message)
        
        # Get the last message (response)
        if not result or "messages" not in result or not result["messages"]:
            logger.error("No response from workflow")
            error_message = "I apologize, but I couldn't generate a response. Please try again."
            return ChatResponse(response=error_message)
            
        last_message = result["messages"][-1]
        if not isinstance(last_message, AIMessage):
            logger.error("Invalid response from workflow")
            error_message = "I apologize, but I received an invalid response. Please try again."
            return ChatResponse(response=error_message)
        
        # Convert set to list for JSON serialization if needed
        if "extracted_entities" in result and isinstance(result["extracted_entities"], set):
            result["extracted_entities"] = list(result["extracted_entities"])
        
        # Save thread state to Redis
        try:
            save_success = await save_thread_state(thread_id, result)
            if save_success:
                logger.info(f"Saved thread state to Redis for {thread_id}")
            else:
                logger.warning(f"Failed to save thread state to Redis for {thread_id}")
        except Exception as e:
            logger.error(f"Error saving thread state to Redis: {str(e)}")
        
        # Check if command was processed
        command_processed = result.get("skip_chat", False)
        command_data = None
        command_type = None
        
        if command_processed and "command_result" in result:
            command_result = result["command_result"]
            command_type = command_result.get("response_type")
            command_data = command_result.get("event_data")
            logger.info(f"Command processed: {command_type}")
        
        response_text = last_message.content
        logger.info(f"Returning response: {response_text[:50]}...")
        
        return ChatResponse(
            response=response_text,
            command_processed=command_processed,
            command_type=command_type,
            command_data=command_data
        )
    
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        return ChatResponse(
            response=f"I apologize, but I encountered an error. Please try again."
        )

@router.get("/context/{thread_id}")
async def get_context(thread_id: str):
    """
    Get the context for a specific thread
    """
    try:
        logger.info(f"Getting context for thread {thread_id}")
        
        # Try to get thread state from Redis
        state = None
        try:
            state = await get_thread_state(thread_id)
        except Exception as e:
            logger.error(f"Error retrieving thread state from Redis: {str(e)}")
            # Return empty context
            return {"context": None}
        
        if not state:
            logger.info(f"No context found for thread {thread_id}")
            return {"context": None}
        
        context = {
            "domain": state.get("domain", ""),
            "metadata": state.get("metadata", {}),
            "language": state.get("metadata", {}).get("language", "en")
        }
        logger.info(f"Returning context for thread {thread_id}: {context}")
        return {"context": context}
    except Exception as e:
        logger.error(f"Error getting context: {str(e)}")
        return {"context": None, "error": str(e)}

@router.post("/reset/{thread_id}")
async def reset_thread(thread_id: str):
    """
    Reset a conversation thread
    """
    try:
        logger.info(f"Resetting thread {thread_id}")
        
        # Delete thread state from Redis
        try:
            delete_success = await delete_thread_state(thread_id)
            if delete_success:
                logger.info(f"Thread {thread_id} reset successfully")
            else:
                logger.warning(f"Failed to reset thread {thread_id}")
        except Exception as e:
            logger.error(f"Error deleting thread state from Redis: {str(e)}")
            
        return {"success": True}
    except Exception as e:
        logger.error(f"Error resetting thread: {str(e)}")
        return {"success": False, "error": str(e)}

async def process_chat(message_text: str, thread_id: str, language: str = "en") -> Dict[str, Any]:
    """Process the incoming chat message and return a response."""
    logger.info(f"Processing chat message for thread: {thread_id}")
    try:
        # Initialize workflow
        workflow = await get_workflow()
        
        # Initialize state with message and context
        state = {
            "input": message_text,
            "thread_id": thread_id,
            "language": language
        }
        
        # Get conversation history
        context = await get_thread_state(thread_id)
        if context:
            state["context"] = context
            
        logger.info(f"Starting workflow with state: {state}")
        
        # Process the workflow
        result = await workflow.invoke(state)
        logger.info(f"Workflow completed with result: {result}")
        
        if "messages" in result and result["messages"] and len(result["messages"]) > 0:
            # Extract the response from the last AI message
            last_message = result["messages"][-1]
            response_text = last_message.content if hasattr(last_message, "content") else str(last_message)
            
            # Save the updated thread state
            await save_thread_state(thread_id, result.get("context", {}))
            
            # Check if this is a command
            command_processed = False
            command_type = None
            command_data = None
            
            # Return the response
            return {
                "message": response_text,
                "thread_id": thread_id,
                "processed": True,
                "command_processed": command_processed,
                "command_type": command_type,
                "command_data": command_data
            }
        else:
            logger.error("No response generated by workflow")
            return {
                "message": "I'm sorry, I encountered an error processing your request. Please try again.",
                "thread_id": thread_id,
                "processed": False
            }
    except Exception as e:
        logger.exception(f"Error processing chat message: {e}")
        return {
            "message": "I'm sorry, I encountered an error processing your request. Please try again.",
            "thread_id": thread_id,
            "processed": False
        } 