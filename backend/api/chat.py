"""
Babywise Assistant - Chat API Router

This module implements the chat-related API endpoints.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.models.message_types import HumanMessage, AIMessage
from backend.workflow.workflow import get_workflow, get_default_state

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Thread state storage
thread_states: Dict[str, Dict[str, Any]] = {}

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
        
        # Get or create thread state
        thread_id = request.thread_id or "default"
        if thread_id not in thread_states:
            thread_states[thread_id] = get_default_state()
            thread_states[thread_id]["metadata"]["language"] = request.language
            thread_states[thread_id]["metadata"]["thread_id"] = thread_id
            logger.info(f"Created new thread state for {thread_id}")
        
        state = thread_states[thread_id]
        state["language"] = request.language  # Ensure language is set in state
        
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
            raise HTTPException(status_code=500, detail=f"Workflow error: {str(e)}")
        
        # Get the last message (response)
        if not result or "messages" not in result or not result["messages"]:
            logger.error("No response from workflow")
            raise HTTPException(status_code=500, detail="No response from workflow")
            
        last_message = result["messages"][-1]
        if not isinstance(last_message, AIMessage):
            logger.error("Invalid response from workflow")
            raise HTTPException(status_code=500, detail="Invalid response from workflow")
        
        # Update thread state
        thread_states[thread_id] = result
        
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
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/context/{thread_id}")
async def get_context(thread_id: str):
    """
    Get the context for a specific thread
    """
    try:
        logger.info(f"Getting context for thread {thread_id}")
        if thread_id not in thread_states:
            logger.info(f"No context found for thread {thread_id}")
            return {"context": None}
        
        state = thread_states[thread_id]
        context = {
            "domain": state.get("domain", ""),
            "metadata": state.get("metadata", {}),
            "language": state.get("metadata", {}).get("language", "en")
        }
        logger.info(f"Returning context for thread {thread_id}: {context}")
        return {"context": context}
    except Exception as e:
        logger.error(f"Error getting context: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset/{thread_id}")
async def reset_thread(thread_id: str):
    """
    Reset a conversation thread
    """
    try:
        logger.info(f"Resetting thread {thread_id}")
        if thread_id in thread_states:
            del thread_states[thread_id]
            logger.info(f"Thread {thread_id} reset successfully")
        return {"success": True}
    except Exception as e:
        logger.error(f"Error resetting thread: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 